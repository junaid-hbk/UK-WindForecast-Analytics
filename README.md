# WindPulse UK
### Renewable Forecast & Procurement Intelligence Platform

WindPulse UK is a full-stack data analytics platform designed to help energy procurement teams understand national wind generation forecasts and evaluate their accuracy against actual generation.

The platform uses historical and forecast data from the **Elexon BMRS API** to investigate an important procurement question:

*What wind generation forecast was available when a day-ahead purchasing decision was made, and how accurately did that forecast represent actual generation?*

The application combines a Python-based data processing backend with a React analytics dashboard.

---

## 1. Project Overview

Electricity procurement decisions depend partly on expectations of renewable generation. However, forecasts change as new information becomes available.

Using the latest forecast without considering when it was published can introduce look-ahead bias into historical analysis.

WindPulse UK addresses this by preserving forecast publication vintages and selecting only the latest forecast available before a configurable day-ahead decision cutoff.

The platform then compares the selected forecast with actual wind generation and presents the results through interactive analytics.

## 2. Key Features

- **Forecast Vintage Tracking:** Preserves different forecast publication versions instead of overwriting historical forecasts.
- **As-of Forecast Selection:** Selects the latest eligible forecast published before the decision cutoff.
- **Forecast Accuracy Analysis:** Calculates MAE, RMSE, WAPE and forecast bias.
- **Daily Performance Analysis:** Examines forecast errors across settlement dates.
- **Lead-Time Analysis:** Evaluates how forecast accuracy changes with the time between publication and delivery.
- **Procurement Scenario Analysis:** Estimates the difference between a user-provided demand scenario and forecast wind generation.
- **Data Quality Monitoring:** Tracks ingestion runs, missing observations and data coverage.
- **Interactive Dashboard:** Provides a visual interface for exploring forecasts, accuracy and procurement scenarios.

## 3. Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, JavaScript, Vite |
| Styling | Tailwind CSS |
| Visualisation | Recharts |
| API communication | Axios |
| Backend | Python 3.12, FastAPI |
| Data processing | Pandas, NumPy |
| Database | MySQL 8 |
| ORM | SQLAlchemy 2 |
| Validation | Pydantic 2 |
| Database migrations | Alembic |
| Testing | pytest, Vitest, Playwright |
| Infrastructure | Docker, Docker Compose |
| Version control | Git, GitHub |

## 4. System Architecture

The application follows a layered architecture.

```text
                 Elexon BMRS API
                        |
                        v
              Data Ingestion Layer
                        |
                        v
              Data Validation Layer
                        |
                        v
                 MySQL Database
                        |
                        v
              Repository Layer
                        |
                        v
                Service Layer
           /        |          \
          /         |           \
    Forecast     Accuracy    Procurement
    Selection    Analysis     Analysis
          \         |           /
           \        |          /
                  FastAPI
                     |
                  REST API
                     |
                     v
               React Frontend
                     |
                     v
              Analytics Dashboard
```

Each layer has a separate responsibility. Data retrieval, database operations, business calculations and presentation are kept separate to make the application easier to maintain and test.

## 5. Project Structure and Important Files

The project is organised into separate frontend, backend, database and documentation directories.

```text
wind_forecasting/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── integrations/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── main.py
│   │   └── cli.py
│   │
│   ├── alembic/
│   │   └── versions/
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── frontend/
│   ├── e2e/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── test/
│   │   └── utils/
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
├── docker/
│   └── init/
│
├── docs/
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

### Backend — Important files

| File / Directory | Purpose |
|---|---|
| `app/main.py` | Creates the FastAPI application and registers the application components. |
| `app/cli.py` | Provides command-line operations for data ingestion, backfilling and verification. |
| `app/api/routes/` | Contains REST API endpoints for actuals, forecasts, accuracy, procurement and data status. |
| `app/core/config.py` | Loads and manages application configuration and environment settings. |
| `app/core/time.py` | Handles UTC timestamps, Europe/London timezone conversion and settlement-period calculations. |
| `app/integrations/elexon/` | Communicates with Elexon's API and normalises actual and forecast data. |
| `app/models/` | Defines SQLAlchemy database models. |
| `app/repositories/` | Handles database queries and persistence operations. |
| `app/schemas/` | Defines and validates API request and response structures using Pydantic. |
| `app/services/` | Contains the main business logic for ingestion, forecast selection, accuracy and procurement. |
| `alembic/versions/` | Stores version-controlled database schema migrations. |
| `tests/` | Contains unit, integration and API tests. |
| `requirements.txt` | Lists runtime Python dependencies. |
| `requirements-dev.txt` | Lists development and testing dependencies. |
| `Dockerfile` | Defines the backend container build. |

### Frontend — Important files

| File / Directory | Purpose |
|---|---|
| `src/main.jsx` | Frontend application entry point. |
| `src/App.jsx` | Root React application component. |
| `src/api/client.js` | Configures the HTTP client used to communicate with FastAPI. |
| `src/api/endpoints.js` | Organises API endpoint definitions. |
| `src/components/` | Contains reusable dashboard components, charts, tables and interface elements. |
| `src/pages/` | Contains the main application pages. |
| `src/hooks/` | Contains reusable React hooks for API resources and application data. |
| `src/layouts/` | Defines the shared application layout. |
| `src/routes/` | Handles frontend navigation and route configuration. |
| `src/utils/` | Contains reusable formatting, date/time and chart-data functions. |
| `e2e/` | Contains browser-based end-to-end tests. |
| `package.json` | Defines frontend dependencies and development scripts. |
| `vite.config.js` | Configures the Vite development and build environment. |

### Root-level configuration files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Defines the MySQL, migration and backend services. |
| `.gitignore` | Prevents local environments, credentials and generated files from entering Git. |
| `docs/` | Stores project architecture and technical documentation. |

## 6. Data Sources

WindPulse UK uses national-level GB wind data from the public Elexon BMRS API.

**API:** https://data.elexon.co.uk/bmrs/api/v1

| Dataset | Purpose |
|---|---|
| `FUELHH` | Actual wind generation observations. |
| `WINDFOR` | Published wind generation forecasts and their publication times. |

The analysis uses 30-minute settlement periods.

An important difference is that WINDFOR publishes hourly forecast values, while FUELHH actuals are half-hourly. The application documents this resolution difference rather than treating duplicated half-hourly forecast values as independent observations.

No Elexon API key is required for the public endpoints used by the application.

## 7. Forecast Selection Methodology

For each delivery period, the application selects the latest forecast vintage satisfying:

```text
forecast.publishTime <= decision_cutoff
```

Forecasts published after the cutoff are excluded.

This prevents future information from entering historical procurement analysis.

The default implementation uses an illustrative 09:20 Europe/London D-1 cutoff policy. Alternative cutoff policies are available for comparison.

The cutoff is configurable and is not presented as a universal official deadline for every market arrangement.

## 8. Forecast Accuracy Metrics

The platform calculates:

| Metric | Description |
|---|---|
| MAE | Mean Absolute Error |
| RMSE | Root Mean Squared Error |
| WAPE | Weighted Absolute Percentage Error |
| Bias | Mean signed forecast error |

Forecast error is defined as:

```text
Error = Forecast - Actual
```

A positive bias indicates that forecasts were higher than actual generation on average.

The application also provides daily accuracy and lead-time analysis, with sample counts and missing-data information.

## 9. Procurement Scenario Analysis

The procurement module uses a user-provided demand scenario to estimate the difference between demand and forecast wind generation.

```text
Additional procurement estimate =
Demand scenario - Forecast wind generation
```

- Positive result: estimated shortfall.
- Negative result: potential surplus.

This is an illustrative calculation, not an actual purchasing recommendation. It does not include electricity prices, actual demand, thermal generation, interconnectors or other market variables.

## 10. Running the Project Locally

### Prerequisites

- Python 3.12
- Node.js and npm
- Docker Desktop
- Git

### Backend setup

From the project root:

```powershell
py -3.12 -m venv .venv

.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

Configure the backend environment:

```powershell
Copy-Item backend/.env.example backend/.env
```

Edit `backend/.env` with the appropriate local MySQL connection details.

Start MySQL using your configured database environment, then run migrations:

```powershell
cd backend

..\ .venv\Scripts\python.exe -m alembic upgrade head
```

Run the backend:

```powershell
..\ .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend setup

Open another terminal:

```powershell
cd frontend

npm install

npm run dev
```

Configure `frontend/.env.example` as `.env.local` if your backend API address differs from the default.

### Local application addresses

| Service | Address |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://127.0.0.1:8000 |
| API documentation | http://127.0.0.1:8000/docs |
| Backend health | http://127.0.0.1:8000/api/v1/health |

## 11. Testing and Validation

The project includes several levels of testing:

- Backend unit tests for calculations, time handling and forecast selection.
- Backend integration tests for database operations and ingestion workflows.
- API tests for endpoint behaviour, validation and error handling.
- Frontend component and page tests.
- Playwright end-to-end tests for browser workflows.

The latest independent local audit reported:

| Validation | Result |
|---|---|
| Backend tests | 166 passed |
| Backend coverage | 90% |
| Frontend tests | 73 passed |
| Frontend production build | Passed |
| Playwright end-to-end tests | 4 passed |

These are local audit results, not a claim of production deployment verification.

## 12. Known Limitations

- Forecast and actual generation datasets may have differences in their underlying fleet definitions.
- Hourly forecasts are mapped to half-hourly settlement periods, so half-hourly sample counts can contain duplicated forecast information.
- The procurement module is illustrative and does not model the complete electricity market.
- Raw Elexon response payloads are not archived on disk; ingestion records store response checksums.
- Automated scheduled ingestion is not bundled with the application.
- Production deployment and security configuration must be completed separately.

## 13. Future Improvements

Potential extensions include:

- Production deployment with managed database infrastructure.
- Automated scheduled ingestion and data freshness monitoring.
- Additional forecast performance comparisons.
- Expanded procurement scenarios using more market variables.
- Improved operational monitoring and logging.

---

**Data source:** Elexon BMRS public API

**Project:** WindPulse UK

**Repository:** https://github.com/junaid-hbk/UK-WindForecast-Analytics
