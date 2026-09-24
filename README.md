# Atlas Fresh — Daily Apple Export Planner

Decision support for a fictional daily Production–Commercial committee. The FastAPI server validates the supplied Excel workbook and applies a deterministic allocation policy; the React workspace displays the resulting production gaps, client orders, farm-to-client allocations, and local residual. Final execution remains a human decision.

## Requirements

- Python 3.12 (tested) and Node.js 20.19+ or 22.12+
- No paid service or API key is needed for the plan or the deterministic assistant summary.

## Run locally

From the repository root, in terminal 1. On macOS, use Python 3.12 to create a fresh virtual environment, then call its Python explicitly:

```bash
cd backend
python3.12 -m venv --clear .venv
.venv/bin/python -m pip install -r app/requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

In terminal 2:

```bash
cd frontend
npm ci
npm run dev
```

Open the URL Vite prints (normally `http://localhost:5173`) and select **Load today's snapshot**. Vite proxies `/api` to `http://127.0.0.1:8000`. The source workbook is kept in `backend/app/data/seed.xlsx` and is read on each seed request. To try a modified workbook without changing the seed, POST an `.xlsx` to `/api/plan` with multipart field `file` (the API docs are at `http://127.0.0.1:8000/docs`).

## Tests and build

From `backend/`:

```bash
.venv/bin/python -m pytest -q tests
```

From `frontend/`:

```bash
npm run build
```

The baseline automated check covers 600 t planned, 560 t received, 500 t exported, 60 t local, €549,500 export revenue, €4,500 local value, and the three partial clients C02, C09, C08. Other tests cover allocation ordering, compatibility, capacity, invalid Excel values, and assistant output.

If the traceback mentions `/Library/Frameworks/Python.framework/Versions/3.14/...`, the global Python is being used. Run the three backend commands above from `backend/`. If `python3.12` is missing, install Python 3.12 first. Use `.venv/bin/python --version` to confirm the selected interpreter.

## Policy and architecture

- `backend/app/engine/validators.py`: parses the supplied workbook, checks IDs, segment rules, quantity increments and station/reference data.
- `backend/app/engine/allocation.py`: server-side policy. Clients are ordered by price descending then ID; compatible supply is ordered by smallest quality upgrade then farm ID. It allocates in 5 t steps within available supply, demand and station capacity. Unexported supply goes to the local market at its segment reference price times the local ratio.
- `backend/app/main.py`: `/api/plan/seed`, `/api/plan` and read-only `/api/assistant` routes.
- `frontend/src/`: a single workspace for production, commercial, allocation and assistant views.

Planned farm mix is for expected-versus-actual comparison only; it is never allocated as real supply. Local reference prices do not determine client priority. The assistant never changes the plan.

## Optional model configuration

Copy `backend/.env.example` to `backend/.env` and set `GROQ_API_KEY` locally if you want to try the hosted explanation path. Never commit `.env`. Without a key, the interface uses a labelled deterministic summary. The core app works without it.

## Submission notes

- AI assistance: used for code review, bug fixes, and the automated test suite. Verify and describe your own use of AI before submission.
- Approximate total time spent: **[candidate: fill in before sending]**.
- Current limitations: the hosted model path requires a user-provided key. Model output rejects unknown farm/client IDs but does not fully check every generated numeric claim; review model explanations before making a decision. There is an API workbook upload but no upload control in the interface.
- Intentional omissions: deployment and forecasting across multiple days; this assessment uses one supplied daily snapshot. **[candidate: adjust to reflect your actual timebox]**.
- Next three production steps: (1) show segment-level planned/actual gaps and connect them to client shortages; (2) move assistant context validation and fallback summaries fully server-side, with clearer provider error states; (3) add operational access controls and monitoring.

The candidate brief and original supplied workbook are included in the repository root for reference. Record a 3–5 minute walkthrough and include its URL when submitting.
