# WindPulse UK — Frontend

React 18 dashboard for day-ahead UK wind forecast accuracy and illustrative
procurement analysis. It reads the Stage 2 FastAPI backend directly: every KPI,
metric and scenario number comes from the API, and the UI never invents a value.

## Stack (pinned)

| Concern | Choice |
| --- | --- |
| UI | React 18.3.1, React DOM 18.3.1 |
| Language | JavaScript (no TypeScript) |
| Build | Vite 7.3.8, `@vitejs/plugin-react` 5.2.0 |
| Styling | Tailwind CSS 4.3.5 via `@tailwindcss/vite` (CSS-first config) |
| Charts | Recharts 3.10.1 |
| HTTP | Axios 1.21.1 |
| Routing | react-router-dom 7.18.5 |
| Icons | lucide-react 1.74.0 |
| Tests | Vitest 5.1.0, React Testing Library 16.3.3, user-event 14.6.12, jsdom 31.0.1 |
| E2E | Playwright 1.65.1 |

Exact versions are pinned in `package.json` and `package-lock.json`.
Tailwind 4 has no `tailwind.config.js`: the theme (colours, font stack) lives in
`src/index.css` under `@theme`.

## Run locally

1. Start the backend (from the repository root):

   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

   The database container must be up (`docker compose up -d db` from the root).

2. Configure the frontend (optional — the default points at `127.0.0.1:8000`):

   ```bash
   cd frontend
   cp .env.example .env.local
   ```

   | Variable | Meaning | Default |
   | --- | --- | --- |
   | `VITE_API_BASE_URL` | FastAPI base URL including `/api/v1` | `http://127.0.0.1:8000/api/v1` |
   | `VITE_API_TIMEOUT_MS` | Axios timeout | `20000` |

3. Install and run:

   ```bash
   npm install
   npm run dev
   ```

   Open http://localhost:5173. CORS on the backend already allows that origin.
   `npm run build` produces `dist/`; `npm run preview` serves it on port 4173.

## Pages

| Route | Purpose |
| --- | --- |
| `/` | Latest available forecast, FUELHH outturn, MAE/RMSE/WAPE/bias for the decision window, daily performance, freshness and availability |
| `/forecast` | Delivery-date explorer: 30-minute settlement periods, per-interval forecast vs actual, decision cutoff, vintage lineage and a native hourly vintage comparison |
| `/accuracy` | Backend accuracy metrics, daily charts, lead-time charts, observation counts and metric definitions |
| `/procurement` | Demand scenario → illustrative shortfall/surplus, calculated by `POST /procurement/scenario` |
| `/data` | Elexon FUELHH and WINDFOR provenance, last ingestion, coverage by settlement day and data-quality issues |

## How data flows

- `src/api/client.js` — one Axios instance, base URL from env, every rejection
  normalised to `ApiError` (`src/api/errors.js`).
- `src/api/endpoints.js` — one function per backend route, returning `{ data, meta }`
  from the response envelope and accepting an `AbortSignal`.
- `src/hooks/useApiResource.js` — cancellation-aware fetch hook; aborts in-flight
  work when the date, policy or granularity changes.
- `src/hooks/useAppData.jsx` — loads `/meta/config`, derives the loaded data window
  from successful ingestion runs, then asks `/data/status`. Cutoff policies, the
  latest delivery date and the default 14-day accuracy window all come from here,
  so no date or policy is hard-coded in a page.
- `src/utils/chartData.js` — reshapes API rows for Recharts. Accuracy aggregates
  are copied from `/analysis/accuracy`; the only arithmetic is the per-interval
  signed difference `forecast − actual`, which is labelled as such and is not used
  for any KPI.

Missing values are preserved as `null` and charted as gaps (`connectNulls={false}`),
never as zero. Empty backend responses render explicit empty states.

## Tests

```bash
npm test          # watch mode
npm run test:run  # single run
npm run coverage  # V8 coverage report
```

Unit and component tests mock the API module (`src/api/index.js`) and assert on
real interaction: loading, error and empty states, date selection, input
validation, procurement submission, navigation and vintage selection.

End-to-end journeys live in `e2e/` and run against the **real** backend and a
real Chromium:

```bash
npx playwright install chromium   # first time only
npm run e2e
```

They navigate all five pages, check the dashboard KPIs and chart, the cutoff and
selected vintage in the explorer, and submit a procurement scenario.

## Accessibility and design notes

- Semantic landmarks (`nav`, `main`, `header`, `footer`), one `h1` per page,
  labelled form controls, `aria-invalid` plus `aria-describedby` on validated
  inputs, and a skip link.
- Status is never conveyed by colour alone: badges carry text, error boxes carry
  a code, procurement bars carry a classification column in the table.
- Charts expose an `aria-label` summary and every charted dataset is also
  available in a table.
- `prefers-reduced-motion` disables transitions; chart animations are off.

## Known limitations

- Procurement figures are an arithmetic estimate of `demand − forecast`, not a
  purchasing recommendation; the API disclaimer is shown with every result.
- The dashboard uses the API's default 14-day window ending at the latest actual
  settlement date; the Accuracy page exposes a custom range (max 180 days, the
  backend guard).
- WINDFOR is hourly while settlement periods are 30 minutes; the half-hourly
  selection is the backend's documented mapping, so the frontend never applies
  its own interpolation.
- There is no authentication: the backend is assumed to be a local/private
  deployment.
