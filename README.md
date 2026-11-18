# WindPulse UK — Renewable Forecast & Procurement Intelligence

Backend for a UK electricity utility's day-ahead wind procurement analysis. It ingests national
GB wind **actual** generation (Elexon `FUELHH`) and national wind **forecasts** (Elexon `WINDFOR`),
preserves every forecast publication vintage, and answers one question honestly: *what did the
forecast say at the moment the purchasing decision had to be made, and how wrong was it?*

**Stage 2 status: backend complete and running against real Elexon data.** No frontend yet.

- Python 3.12 · FastAPI · SQLAlchemy 2 · Pydantic 2 · Pandas · NumPy · HTTPX · PyMySQL · Alembic
- MySQL 8.0.46 (Docker) · pytest 166 tests · 90 % coverage
- Data source: `https://data.elexon.co.uk/bmrs/api/v1` (public, no API key)

---

## 1. Real results already in the database

These are measured outputs from an actual backfill run on 17 November 2026 against the live
Elexon API — not illustrative figures. Reproduce them with the commands in §5 and §7.

**Ingestion (settlement dates 2026-01-01 → 2026-02-28; vintages published 2025-12-29 → 2026-03-02)**

| Dataset | Result |
|---|---|
| `FUELHH` actuals | 2,832 rows = 2,832 distinct settlement periods = 59 days × 48 SPs, 100 % of the window |
| `WINDFOR` vintages | 504 vintages, 36,792 hourly points, 63 HTTP requests, HTTP 200, 0 rejected rows |
| As-of selections | 2,832 intervals, 2,832 selected, **0 missing**, 0 fallbacks |
| Lead times | 990 – 2,400 minutes (16.5 h – 40 h), consistent with a D-1 09:20 cutoff |

**Forecast accuracy, January 2026** (`GET /api/v1/analysis/accuracy?from=2026-01-01&to=2026-01-31`)

| Metric | Value |
|---|---|
| MAE | 2,145.166 MW |
| RMSE | 2,615.812 MW |
| WAPE | 18.524 % |
| Bias (signed) | +1,851.904 MW (+15.991 %) — forecasts ran above outturn |
| Evaluated observations | 1,488 of 1,488 (coverage 100 %) |
| Missing forecast / actual | 0 / 0 |

**Illustrative procurement scenario** (15,000 MW constant demand, 2026-01-15)

48 intervals: 42 shortfall, 6 surplus; total demand 360,000 MW·h; forecast wind 278,630 MW·h;
total delta +81,370 MW·h; 0 unavailable intervals. This is arithmetic, not a purchasing
recommendation — see §8.

> Method caveat that matters: `WINDFOR` is **hourly**, `FUELHH` is half-hourly. The half-hourly
> view duplicates each hourly forecast value across two settlement periods, so `n` at that
> granularity counts duplicated forecast information. Use `granularity=hourly` for a statistically
> clean sample (24 observations per day instead of 48).

---

## 2. Prerequisites

- Python 3.12 (verified with 3.12.10)
- Docker Desktop (verified with Docker 29.9.3 / Compose 5.7.0) — for MySQL 8.0.46
- No Elexon account or API key: the Insights API is public

## 3. Quick start

```bash
# 1 — start MySQL 8 (creates windpulse + windpulse_test, grants both)
docker compose up -d db

# 2 — Python environment
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt

# 3 — configuration
cp backend/.env.example backend/.env      # edit if your passwords/ports differ

# 4 — schema + views + cutoff policies
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m alembic check        # expect: no new upgrade operations

# 5 — real data (live Elexon; ~5 minutes for two months)
../.venv/Scripts/python.exe -m app.cli backfill --from 2026-01-01 --to 2026-02-28

# 6 — run the API
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Then: <http://127.0.0.1:8000/docs> (Swagger UI), <http://127.0.0.1:8000/openapi.json>,
<http://127.0.0.1:8000/api/v1/health>.

macOS/Linux: replace `.venv/Scripts/python.exe` with `.venv/bin/python`.

Full stack in containers (db → migration → api):

```bash
docker compose up --build
curl http://127.0.0.1:8000/api/v1/health
```

---

## 4. Database setup

### 4.1 With Docker (recommended)

`docker compose up -d db` starts MySQL 8.0.46 on `127.0.0.1:3307` with:

- database `windpulse`, user `windpulse`
- database `windpulse_test` **and a grant for the app user** (`docker/init/01-test-database.sql`) —
  without that grant every DB test fails with `Access denied … 'windpulse_test'`
- server timezone `+00:00`, `utf8mb4` / `utf8mb4_0900_ai_ci`

Credentials come from the environment (`MYSQL_*` in `docker-compose.yml`, defaulted for local
development only). Nothing is hard-coded in application code.

### 4.2 With an existing MySQL 8 server

```sql
CREATE DATABASE windpulse      CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE windpulse_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'windpulse'@'%' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON windpulse.*      TO 'windpulse'@'%';
GRANT ALL PRIVILEGES ON windpulse_test.* TO 'windpulse'@'%';
```

Then set `DATABASE_URL` (see §6) and run `alembic upgrade head`.

### 4.3 Migrations

| Revision | Content |
|---|---|
| `0001_initial_schema` | 10 tables, all constraints and indexes |
| `0002_views` | `v_actual_generation_latest`, `v_analysis_interval`, `v_forecast_coverage_daily` |
| `0003_seed_cutoff_policies` | The three documented GB day-ahead gate-closure policies (parameterised inserts) |

```bash
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m alembic current     # 0003 (head)
../.venv/Scripts/python.exe -m alembic check       # detects model/DB drift
```

`schema` is never created with `create_all`: Alembic is the only path, so a reviewer can see the
exact SQL that produced the database.

### 4.4 Data model, briefly

- `actual_generation` — one row per `(settlement_date, settlement_period, fuel_type, source_publish_time_utc)`.
  Revisions are **kept**; `v_actual_generation_latest` is the only sanctioned read path.
- `forecast_vintage` — one row per distinct `WINDFOR` `publishTime`; append-only.
- `forecast_point` — hourly points per vintage, primary key `(vintage_id, valid_from_utc)`.
- `forecast_selection` — the materialised as-of answer per `(policy, settlement date, period)`,
  recording chosen vintage, publish time, lead time, value, fallback depth and status.
- `ingestion_run` / `ingestion_watermark` — run bookkeeping, counts, error code, payload checksum.
- `data_quality_issue` — rejected rows, revisions, days with no usable forecast.
- All instants are `DATETIME(6)` in UTC, normalised by a `UTCDateTime` type decorator (MySQL has
  no timezone, so the driver returns naive values; the decorator re-attaches UTC on read).

---

## 5. Ingestion

```bash
cd backend

# everything, in dependency order (actuals → vintages → selections)
../.venv/Scripts/python.exe -m app.cli backfill  --from 2026-01-01 --to 2026-02-28

# individual steps
../.venv/Scripts/python.exe -m app.cli actuals    --from 2026-01-01 --to 2026-01-07
../.venv/Scripts/python.exe -m app.cli forecasts  --from 2025-12-29T00:00:00Z --to 2026-03-02T00:00:00Z
../.venv/Scripts/python.exe -m app.cli selections --from 2026-01-01 --to 2026-02-28

# what is stored, and where the gaps are
../.venv/Scripts/python.exe -m app.cli verify --from 2026-01-01 --to 2026-02-28
```

The `backfill` window is deliberately wider than the analysis window: a 1 January delivery needs
vintages published from 29 December, and the last February delivery needs vintages published into
early March. That is why the forecast run above queries `2025-12-29 → 2026-03-02`.

Behaviour worth knowing:

- **Idempotent.** Re-running any window inserts nothing new (`rows_inserted: 0`). A value that
  upstream republished under the same key is applied and recorded as `REVISED_VALUE`.
- **Fails loudly, keeps your data.** An upstream failure marks the run `failed` with the real
  error code/status, leaves previously ingested rows untouched, and exits non-zero.
- **Rate-limit friendly.** Sequential chunked requests (7 days for actuals, 1 day for forecasts).
  The documented ceiling is 5,000 requests/minute; a two-month backfill uses 72.
- **One transaction per run.** A run commits once, after every chunk validates, so an interrupted
  backfill writes no partial vintages. Consequence: a very long window is all-or-nothing — split it
  by month if you need partial progress.

## 6. Configuration

`backend/.env` (copy from `backend/.env.example`; it is git-ignored):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `mysql+pymysql://windpulse:…@127.0.0.1:3307/windpulse?charset=utf8mb4` | SQLAlchemy URL |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Upstream API |
| `ELEXON_MAX_ATTEMPTS` / `…BACKOFF_*` | 4 / 0.5 s / 8 s | Retry policy (never retries HTTP 400) |
| `ELEXON_ACTUAL_CHUNK_DAYS` / `…FORECAST_CHUNK_DAYS` | 7 / 1 | Request granularity |
| `DEFAULT_CUTOFF_POLICY_CODE` | `EPEX_GB_DA_1H_0920` | Decision cutoff used when a request omits one |
| `WINDFOR_SP_MAPPING` | `step` | `step` or `linear` hourly→half-hourly mapping |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Explicit allow-list, never `*` |
| `ADMIN_TOKEN` | empty | Empty disables all `/admin/*` endpoints (they answer **503 `ADMIN_DISABLED`**); a missing/wrong token while enabled answers 401 |
| `PAGE_SIZE_MAX` | 5000 | Upper bound for `limit` (422 above it) |
| `MAX_QUERY_DAYS` | 180 | Upper bound for analysis ranges (400 above it) |

Secrets live only in the environment or the host's secret store. `ADMIN_TOKEN` should be a long
random value in any shared environment.

---

## 7. API

Base path `/api/v1`. Interactive docs: `/docs`; schema: `/openapi.json` (18 documented paths).

Success envelope `{"data": …, "meta": {…}}`; errors `{"error": {"code", "message", "details"}}`
with codes `VALIDATION_ERROR` (422), `INVALID_REQUEST` (400), `RANGE_TOO_LARGE` (400),
`NOT_FOUND` (404), `DATA_UNAVAILABLE` (409), `UNAUTHORIZED` (401), `ADMIN_DISABLED` (503),
`UPSTREAM_ERROR` / `ELEXON_*` (502).

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness, no DB access |
| GET | `/health/ready` | `SELECT 1` + current Alembic revision |
| GET | `/meta/config` | Policies, timezones, mapping mode, metric definitions, disclaimers |
| GET | `/actuals?from&to&limit&offset` | Latest revision per SP; `pagination` in `meta` |
| GET | `/actuals/daily?from&to` | Mean MW and MW·h per settlement day |
| GET | `/forecast/latest?delivery_date&cutoff_policy` | As-of series + summary; 409 if never rebuilt |
| GET | `/forecast/vintages?delivery_date` | Lineage: every vintage, `is_used_at_cutoff`, `is_after_cutoff` |
| GET | `/forecast/vintages/{vintage_id}` | One vintage's hourly points; 404 if unknown |
| GET | `/analysis/accuracy?from&to&cutoff_policy&granularity` | MAE, RMSE, WAPE, bias, counts, coverage |
| GET | `/analysis/accuracy/daily?…` | Same per settlement day, plus `accuracy_pct = 100 − WAPE` |
| GET | `/analysis/accuracy/by-lead-time?…` | Buckets `0-6h … >48h`, plus `unknown`; empty buckets included |
| POST | `/procurement/scenario` | `{demand_mw, date_from, date_to, cutoff_policy?, include_intervals?}` |
| GET | `/data/status?from&to` | Coverage per day, counts, staleness, issue counts |
| GET | `/data/runs?dataset&limit&offset` | Ingestion history |
| GET | `/data/issues?severity&from&limit&offset` | Data-quality issues |
| POST | `/admin/ingest/actuals` | Token-guarded incremental actuals |
| POST | `/admin/ingest/forecasts` | Token-guarded vintage discovery |
| POST | `/admin/selections/rebuild` | Token-guarded selection rebuild |

Examples:

```bash
curl "http://127.0.0.1:8000/api/v1/analysis/accuracy?from=2026-01-01&to=2026-01-31"
curl "http://127.0.0.1:8000/api/v1/forecast/vintages?delivery_date=2026-01-15"
curl "http://127.0.0.1:8000/api/v1/actuals?from=2026-01-15&to=2026-01-15&limit=4"

curl -X POST http://127.0.0.1:8000/api/v1/procurement/scenario \
  -H "Content-Type: application/json" \
  -d '{"demand_mw": 15000, "date_from": "2026-01-15", "date_to": "2026-01-15"}'
```

Every timestamp is emitted as ISO-8601 UTC (`…Z`); list endpoints also return a London-rendered
label (`"2026-01-15 00:00 GMT"`). CORS answers only configured origins — an unlisted origin gets no
`access-control-allow-origin` header.

---

## 8. Method

### 8.1 Decision cutoff

A configurable row in `cutoff_policy`, not a constant. The default is
`EPEX_GB_DA_1H_0920`: **09:20 Europe/London on D-1**, the earliest GB hourly day-ahead gate
closure (EPEX SPOT Operational Rules; DESNZ references the 09:20 and 09:50 GB auctions). Two
alternatives ship for sensitivity: `N2EX_GB_DA_1H_0950` (09:50) and `EPEX_GB_DA_30M_1530` (15:30).
The cutoff is resolved through `zoneinfo` per date, so it is 09:20Z in January and 08:20Z during
BST; every selection row stores the resulting `cutoff_utc` and the policy that produced it.

### 8.2 Vintage selection (no look-ahead)

For each settlement period:

1. Resolve the cutoff for that delivery date.
2. Consider only vintages with `publish_time_utc <= cutoff_utc` — the single comparison where
   look-ahead could enter, covered by tests.
3. Order them newest first (tie-break on id) and take the first whose hourly point covers the
   interval; if the newest lacks that hour, fall back and record `fallback_depth`.
4. Persist the outcome, including failures: `no_vintage_before_cutoff`, `no_point_for_interval`.

A vintage published after the cutoff is *never* used, and neither is one published after the
interval has begun. Missing forecasts stay `NULL` — never `0`. The 2,832 real selections above had
zero fallbacks and zero gaps, so the D-1 forecast horizon covers its delivery day comfortably.

### 8.3 Hourly forecast → half-hourly settlement periods

`WINDFOR` publishes one value per hour; delivery is settled per half hour. The default `step`
mapping applies each hourly value to the two settlement periods whose start falls inside that hour,
adding no information Elexon did not publish. `linear` (interpolate at the half-hour midpoint) is
implemented and unit-tested but **not** the default. The active mode is reported in every response's
`meta` and in `/meta/config`.

### 8.4 Metrics

Error `e = forecast − actual`; **positive means over-forecast** (a shortfall risk for the buyer).

| Metric | Definition | Guard |
|---|---|---|
| MAE | mean(\|e\|) | `n = 0` → `null`, `insufficient_data: true` |
| RMSE | √mean(e²) | same |
| WAPE | 100 · Σ\|e\| / Σ\|actual\| | `Σ\|actual\| = 0` → `null` + `ZERO_ACTUAL_ENERGY` |
| Bias | mean(e), signed MW | `n = 0` → `null` |
| Bias % | 100 · Σe / Σactual | `Σactual = 0` → `null` |
| Daily accuracy | per day, `accuracy_pct = 100 − WAPE` (clamped) | per-day guards |
| Lead time | interval start − chosen vintage publish time, whole minutes | reported with every forecast |

MAPE is deliberately not offered: wind output approaches zero, which makes percentage errors
unbounded. Missing values are excluded and counted (`n_missing_forecast`, `n_missing_actual`,
`n_no_vintage_before_cutoff`, `n_invalid_timestamps`, `n_duplicate_intervals`), never imputed.
No metric is returned without its `n`.

### 8.5 Procurement estimate

`additional procurement = demand scenario − as-of forecast wind`, per interval. Positive =
estimated shortfall, negative = potential surplus; intervals with no forecast are counted as
`unavailable_intervals` and excluded from the delta rather than treated as zero forecast. Totals are
converted to MW·h at 0.5 h per period. The response carries an explicit disclaimer and
`meta.kind = "illustrative_estimate"`.

---

## 9. Tests

```bash
cd backend
../.venv/Scripts/python.exe -m pytest --cov=app --cov-report=term-missing
# 159 passed — TOTAL 90 %
```

With an HTML report and the CI-style exit gate:

```bash
../.venv/Scripts/python.exe -m pytest --cov=app --cov-report=html --cov-report=term \
  --cov-fail-under=85
```

Isolation: the suite sets `TEST_DATABASE_URL` (default `windpulse_test`) **before** importing the
app, migrates that database once per session, and truncates every table before each DB test. It
never touches `windpulse`. Live Elexon is never called: HTTP is mocked with `httpx.MockTransport`
and hand-written row fixtures that mirror the real payload shapes.

Coverage by area (from `--cov-report=term-missing`): `core/time` 100 %, `core/config` 100 %,
models 93–100 %, `selection_rules` 97 %, `ingestion_service` 94 %, integration clients 93–96 %,
`forecast_selection_service` 87 %. Lower: `cli.py` 0 % (exercised manually, see §5),
`data_status_service`/`procurement_service` ~60 % (paths covered mainly through the API tests).

What is proven by tests, not by assertion:

| Area | Tests |
|---|---|
| Look-ahead prevention | post-cutoff vintage never selected; equality-at-cutoff behaviour; fallback depth |
| Time | 46/48/50-SP days, GMT/BST cutoffs, settlement-date boundaries |
| Metrics | MAE/RMSE/WAPE/bias against hand-computed values, null handling, zero denominator, empty range, duplicates |
| Ingestion | idempotency, duplicate vintage prevention, revision capture, upstream failure preserves data + records the run |
| Repositories | unique constraints, latest-revision view, selection replace-range |
| API | envelope/status codes, pagination, 422 vs 400, 404/409, CORS allow-list, admin token guard |
| Elexon client | 429→200 retry, 500→200 retry, 400 no-retry, malformed payload, bare-array vs `{"data": …}` |

---

## 10. Layout

```
backend/
  app/
    api/            routes, deps, error mapping, request validation
    core/           config, time (UTC ↔ Europe/London, settlement periods), logging, errors
    integrations/elexon/  httpx client, row schemas, actual/forecast normalisation
    models/         SQLAlchemy 2 models, UTC type, typed view definitions
    repositories/   persistence + read SQL (no business rules)
    schemas/        Pydantic request/response models
    services/       ingestion, forecast selection, accuracy, procurement, data status
    utils/          chunking
    main.py, cli.py
  alembic/          env + 3 revisions
  tests/            unit / integration / api, fixtures, builders
  requirements.txt, requirements-dev.txt, alembic.ini, pytest.ini, Dockerfile, .env.example
docker-compose.yml  db + migrate + api
docker/init/        test database + grant
docs/               Stage 1 architecture document
```

## 11. Known limitations

Documented deliberately rather than hidden:

1. **No frontend yet** (Stage 3). The API is complete and documented at `/docs`.
2. **No on-disk raw payload archive.** Stage 1 planned gzipped raw responses; this build records a
   SHA-256 of the response bodies on each run (`ingestion_run.payload_checksum`) but does not write
   the payloads to disk. MySQL remains the source of truth.
3. **One transaction per ingestion run.** Long windows are all-or-nothing; split very large
   backfills by month.
4. **No bundled scheduler service.** Ingestion is a one-shot CLI plus token-guarded admin
   endpoints, intended to be driven by host cron or GitHub Actions (§5 commands).
5. **`FUELHH` WIND vs `WINDFOR` population.** Both are national wind, but whether the forecast and
   outturn populations are defined identically is not stated in the endpoint documentation I could
   verify. Accuracy is therefore a comparison of the two published series, and the caveat is
   surfaced in the API notes.
6. **Half-hourly duplication.** `n` at SP granularity double-counts each hourly forecast value; use
   `granularity=hourly` for statistical claims.
7. **`linear` mapping** is implemented and unit-tested but not exposed as a default or exercised
   end-to-end.
8. **No authentication/authorisation.** Out of scope for this stage; admin routes use a shared
   token and are disabled when `ADMIN_TOKEN` is unset.
9. **No retention/compaction job.** Actual revisions and all vintages are retained indefinitely by
   design (auditability), which is fine at this data volume (~40k rows for two months).
10. **Procurement is illustrative only.** The figure is arithmetic on one forecast series. It
    excludes actual demand, non-wind generation, interconnectors, losses and prices — by
    construction, not by oversight.

## 12. Next stage

Stage 3 (frontend: React 18 + Vite + Tailwind + Recharts + Axios + React Router) is **not** started,
per the brief. The API contracts it will consume are the endpoints in §7.
