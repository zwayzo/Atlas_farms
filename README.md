# Atlas Fresh — Daily Apple Export Planner

A browser workspace for the fictional Atlas Fresh daily Production–Commercial committee. It compares planned and actual farm production, calculates a deterministic export allocation, shows client service status, and highlights fruit sent to the local market. The committee remains responsible for approving the plan.

## Requirements

- Python 3.12 (`python3.12` available in the terminal)
- Node.js 20.19+ or 22.12+, with npm
- No API key or paid service is required for the planner

## Start the application

From a clean clone:

```bash
git clone https://github.com/zwayzo/Atlas_farms.git
cd Atlas_farms
./start.sh
```

The script installs missing dependencies, creates `backend/.venv` and `backend/.env` if necessary, then starts the backend and frontend. Open **http://127.0.0.1:5173** and click **Load today's snapshot**. Press Ctrl+C to stop both servers.

Backend API documentation: **http://127.0.0.1:8000/docs**.


## Run tests and build

After running `./start.sh` once to install dependencies, open another terminal at the repository root.

Backend tests:

```bash
backend/.venv/bin/python -m pytest -q backend/tests
```

Frontend production build:

```bash
cd frontend
npm run build
```

Use `backend/.venv/bin/python`, not a global Python 3.14 installation. During review, **15 backend tests passed** and the frontend build succeeded. The tests emitted one nonfatal Starlette deprecation warning.

## How the plan works

1. The server loads and validates the supplied daily workbook. The interface loads `backend/app/data/seed.xlsx`; the original workbook remains in the repository root. A modified workbook can also be sent to `POST /api/plan` as an `.xlsx` multipart upload with field name `file`.
2. Production compares expected farm capacity and expected A/B/C/D mix with actual receipts. Only **actual** fruit can be allocated.
3. The engine processes clients by export price, highest first; ties are broken by client ID. `EXACT` accepts only the requested segment. `MINIMUM` accepts the requested segment or a better one.
4. Compatible supply is selected by the smallest quality upgrade, then farm ID. The engine allocates in 5 t increments without exceeding client demand, farm supply or station capacity.
5. Every unexported tonne goes to the local market. Its value is calculated from its segment reference price and the workbook's local-market ratio. The assistant explains the computed plan but cannot change it.

The supplied workbook produces **600 t planned, 560 t received, 500 t exported, 60 t local, an 89.3% export rate, €549,500 export revenue, €4,500 local value and €554,000 total value**. C02 and C09 are partial because compatible fruit runs short. C08 is partial because station capacity is reached.

## Architecture and assumptions

- `backend/app/engine/validators.py`: workbook parsing and input validation. Invalid IDs, modes, segments, mixes, prices and quantities are rejected rather than silently corrected.
- `backend/app/engine/allocation.py`: deterministic allocation, client statuses, local residual and KPIs.
- `backend/app/main.py`: seed, workbook-upload and assistant API routes.
- `frontend/src/`: React/Vite planning workspace.

This is one fictional daily snapshot with one export station. The source workbook does not assign farms to clients; the engine creates those traceable assignments. The result supports a human decision and does not execute it.

## Verification, limitations and next steps

**AI tools used:** ChatGPT/Codex assisted with code review, debugging, tests and documentation. The supplied baseline, recalculation after an input change, invalid-workbook rejection, backend tests and frontend build were checked.

**Approximate time spent:** 13 hours, including debugging and verification. This is about one hour beyond the suggested 10–12 hour timebox.

**Limitations and deliberate omissions:** No deployment or multi-day forecasting. Workbook upload exists through the API but has no button in the interface. Hosted assistant responses reject unknown farm/client IDs, but their numerical claims are not fully checked against the plan. The interface does not explicitly show which farm shortfall contributes to which client risk. Validation errors and server failures share one retry screen. Keyboard use and layouts at 1024 px and 1440 px have not been formally verified.

**Next three production steps:**

1. Validate assistant numbers and evidence against the computed plan, with a server-side fallback.
2. Show the connection between farm shortages and affected clients; improve error states and accessibility checks.
3. Add access controls, monitoring and decision history if the tool becomes a production product.

The case and data are fictional. Authentication, persistence, multi-day optimization and a paid AI service are outside this assessment. The submission email should contain the repository URL, a **3–5 minute walkthrough video URL**, and the approximate time spent. A deployed URL is optional.