cat > README.md <<'ATLAS_FRESH_README'
# Atlas Fresh — Daily Apple Export Planner

Atlas Fresh is a decision-support workspace for a fictional daily meeting between Production and Commercial. It compares what 20 farms were expected to deliver with what actually arrived, allocates real fruit to 10 export clients using the rules in the assessment brief, and makes the remaining local-market volume and its value visible. The committee reviews and approves the final operating decision.

**Repository:** https://github.com/zwayzo/Atlas_farms  
**Live backend:** https://atlas-farms.onrender.com/docs  
**Walkthrough:** https://youtu.be/aN12tLNQbCc.

## Run it from a clean clone

You need **Python 3.12**, **Node.js 20.19+ or 22.12+**, npm, and Git. On macOS or Linux, run:

```bash
git clone https://github.com/zwayzo/Atlas_farms.git
cd Atlas_farms
./start.sh
```

The script creates `backend/.venv`, installs the Python and frontend packages, creates `backend/.env` from `backend/.env.example` if absent, and starts both servers. It does not overwrite an existing `.env`. Open **http://127.0.0.1:5173** and select **Load today's snapshot**. Press **Ctrl+C** to stop the servers. The API documentation is at **http://127.0.0.1:8000/docs**.

The export plan and the labelled deterministic assistant summary work **without an API key**. Python 3.12 matters: using a global Python 3.14 installation caused an incompatible `pydantic_core` import error during development. `./start.sh` selects the project's Python 3.12 environment.

### Run the services separately

From the repository root, in one terminal:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r app/requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

The local Vite server forwards `/api` requests to the backend at `127.0.0.1:8000`.

## Run the tests and build

After dependencies are installed, from the repository root:

```bash
backend/.venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
```

The backend tests cover the supplied baseline, changed inputs, quality compatibility, price/order priority, station and supply limits, input validation, residual accounting, and assistant failure handling. A successful frontend build checks that Vite can bundle the interface. Use the virtual-environment Python shown above, not your global `python` or `pytest` commands.

## What the daily workspace shows

| View | Decision it supports |
| --- | --- |
| Overview | Expected and received tonnes, station capacity, export rate, revenue, total value, and the local-market loss of value. |
| Production | Expected capacity and A/B/C/D mix versus actual quantities and gaps for every farm. |
| Commercial | Client demand, accepted quality, allocated tonnes, remaining tonnes, status, revenue, and shortage reason. |
| Allocations | Which farm and quality segment supplies each client, plus local residual by farm and segment. |
| Assistant | Three fixed questions about client risk, farm gaps, and local fruit; explanations refer to the computed plan. |

**Baseline supplied with the assessment:** 600 t planned; 560 t received; 500 t exported within the station's 500 t capacity; 60 t sold locally. The export rate is 89.3%, export revenue is €549,500, local value is €4,500, and combined value is €554,000. C02 and C09 are partially served because compatible fruit runs short; C08 is partially served because station capacity is reached. These figures are calculated from the workbook and should change when valid inputs change.

### How the planning rules work

The workbook has four sheets: `Read Me`, `Farms`, `Clients`, and `Station`. The seed workbook at `backend/app/data/seed.xlsx` is the single daily snapshot loaded by the interface; the original supplied workbook in the repository root is retained as reference.

1. Validate the workbook on the server: required sheets and IDs, quality rules, segment reference prices, expected mixes, nonnegative values, and the required 5 t increments.
2. Calculate expected segment tonnes as `expected_daily_capacity_t × expected_segment_pct`; compare them with actual segment tonnes. For example, F01 expects 35 t at 90% A, or 31.5 t A. If 25 t A arrive, its A gap is −6.5 t. Extra B fruit can partly offset that gap in F01's total variance.
3. Use **actual receipts only** as allocatable supply. Process clients by export price descending, then client ID. `EXACT` accepts only the requested segment; `MINIMUM` accepts that segment or better. Prefer the smallest quality upgrade, then farm ID, and allocate in 5 t steps until demand, compatible supply, or station capacity is exhausted.
4. Send all unexported actual fruit to the local market. Its value equals the residual tonnes multiplied by the workbook's local-market ratio and that segment's reference price. Segment reference prices do not change the order of export clients.

The same input produces the same plan. No LLM makes allocation decisions, sets KPIs, or changes server results.

## Use another workbook

The current interface has a **Load today's snapshot** action for the bundled workbook. The backend already accepts a different `.xlsx` workbook of the **same four-sheet structure** through `POST /api/plan` with multipart field `file`. For example, from the repository root while the backend is running:

```bash
curl -X POST \
  -F 'file=@Atlas_Fresh_Production_Commercial_Data.xlsx' \
  http://127.0.0.1:8000/api/plan \
  -o plan.json
```

You can also upload a modified workbook interactively at **http://127.0.0.1:8000/docs**. Invalid data is rejected with an error instead of silently repaired. The uploaded file is used for that request; it does not replace the bundled seed workbook.

**Next interface upgrade:** add an upload button, show validation feedback beside it, and display the recalculated plan for each uploaded workbook. This would let users plan other daily snapshots without editing the seed or using the API docs. Each workbook would still need the agreed sheet names and schema; arbitrary Excel formats, multi-day history, and saved plans would require additional work.

## Optional Groq assistant

The allocation engine does not need Groq. To enable model-generated explanations locally:

1. Create an account at [GroqCloud](https://console.groq.com/) and create a key on its [API Keys page](https://console.groq.com/keys).
2. Open `backend/.env` (created automatically by `./start.sh`; otherwise copy `backend/.env.example` to `backend/.env`). Set **your own** key and a model your account can use:

   ```dotenv
   GROQ_API_KEY=<your-new-api-key>
   GROQ_MODEL=openai/gpt-oss-20b
   ```

3. Restart the backend or `./start.sh`, load the snapshot, and ask one of the three questions on the Assistant tab.

The example model ID is the repository's default. Model availability can vary by account and over time; check [Groq's current model list](https://console.groq.com/docs/models) if you get `MODEL_UNAVAILABLE` or `model_not_found`. To list models available to **your key** without printing the key, run from `backend/` after installing dependencies:

```bash
.venv/bin/python - <<'PY'
from dotenv import load_dotenv
load_dotenv('.env')
from groq import Groq
for model in Groq().models.list().data:
    print(model.id)
PY
```

`backend/.env.example` contains variable names and nonsecret defaults and belongs in the repository. `backend/.env` holds the real key, is ignored by Git, and must **never** be committed or pasted into the frontend. If a key has been exposed, revoke it and create a new one. For the deployed backend, add `GROQ_API_KEY` and `GROQ_MODEL` under the **Render service's Environment Variables**, then save and deploy; do not put the secret into Vercel frontend variables.

With no key, the API returns `501 No AI model configured` for `/api/assistant`, while the interface shows a clearly labelled deterministic summary from the plan. If Groq is unavailable, the same labelled fallback appears. The model explains the already-computed structured result and cannot modify allocations.

## Code map and choices

| Location | Responsibility |
| --- | --- |
| `backend/app/engine/validators.py` | Read and validate workbook data. |
| `backend/app/engine/allocation.py` | Deterministic planning policy, allocation rows, client statuses, residuals, and KPIs. |
| `backend/app/engine/assistant.py` | Optional read-only Groq explanation, restricted context, and ID checks. |
| `backend/app/main.py` | FastAPI routes: `/api/plan/seed`, `/api/plan`, `/api/assistant`. |
| `backend/tests/` | Planning, validation, invariants, and assistant checks. |
| `frontend/src/` | React/Vite planning workspace and labelled assistant fallback. |
| `start.sh` | One-command local setup and startup. |

FastAPI keeps validation and business calculations on the server; React provides one place for Production and Commercial to review the same result. The assistant receives a reduced structured plan instead of the raw workbook. All example farm and client data is fictional.

### Technical choices and rationale

| Choice | Why it fits this assessment |
| --- | --- |
| Python, pandas and openpyxl | Read the supplied Excel workbook and validate its four sheets without changing the original. |
| FastAPI | Keep workbook validation, allocation rules, and KPIs together on the server, with an API that can accept another workbook. |
| Deterministic allocation engine | Follow the exact client and quality priorities from the brief; the same input always gives the same traceable result. |
| React and Vite | Present Production, Commercial, allocations and the assistant in one browser workspace with a straightforward local build. |
| Optional Groq assistant | Explain the calculated plan when a key is configured, while keeping the core planning workflow usable without a model or paid service. |
| `start.sh` and local `.env` | Make a clean clone simple to run while keeping API keys out of version control. |
 ## AI coding tools ##
I used ChatGPT/Codex to help me understand the brief, break the project into main steps, and think through business rules, edge cases, and tests. I then implemented the application and personally checked the baseline results, changed-input behavior, tests, and deployment. AI was a guide during development; the planning decisions in the application are calculated by deterministic code.
## Scope, verification, and next steps

- **Verified:** the supplied baseline, recalculation from modified input, automated backend tests during development, and a successful frontend production build. The existing Starlette/httpx test-client deprecation warning does not prevent tests from passing.
- **AI coding tools:** I used ChatGPT/Codex to organize the initial work, outline the main features, and assist with debugging and test ideas. I implemented the project and checked its behavior against the brief and the supplied baseline.
- **Approximate time spent:** **13 hours**, including debugging, testing, and deployment.
- **Current limitations:** the UI loads the bundled snapshot and has no workbook upload button. The assistant rejects invented farm/client IDs but does not verify every numerical statement generated by the model. The interface could show the link between a specific farm shortfall and an affected client more directly. This is one daily snapshot, not a multi-day planning history.
- **Intentionally out of scope:** seasonal forecasting, automatic execution of commercial decisions, authentication, a database, and integrations with farms or clients. These were not needed for the assessment's daily decision workflow.

**Next three production steps:** (1) add the workbook upload and clear per-sheet validation feedback; (2) verify all AI-generated figures against the computed result and strengthen the farm-to-client shortage explanation; (3) add saved daily plans, access control, and operational monitoring if the prototype is adopted.

Production and Commercial remain responsible for approving any real-world plan.
