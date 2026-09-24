from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from app.engine.validators import validate_data, read_and_validate_reference_prices
from app.engine.allocation import run_allocation_engine
from app.engine.assistant import ask_assistant, is_configured
from dotenv import load_dotenv
load_dotenv()
# print("GROQ_API_KEY loaded:", bool(os.environ.get("GROQ_API_KEY")))
from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI(title="API Planification Daily Apple Export - Atlas Fresh")
SEED_PATH = os.path.join(os.path.dirname(__file__), "data", "seed.xlsx")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifiez ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/plan/seed")
async def generate_plan_from_seed():
    try:
        farms_df, clients_df, station_df = validate_data(SEED_PATH)
        ref_prices = read_and_validate_reference_prices(SEED_PATH)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

    result = run_allocation_engine(farms_df, clients_df, station_df, ref_prices)
    return {
        "status": "success",
        "farms": farms_df.to_dict(orient="records"),
        "clients": clients_df.to_dict(orient="records"),
        **result,
    }

@app.post("/api/plan")
async def generate_plan(file: UploadFile = File(...)):
    temp_filename = f"temp_{file.filename}"
    try:
        # Save temp file
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. Validation & Parsing des DataFrames
        try:
            farms_df, clients_df, station_df = validate_data(temp_filename)
            ref_prices = read_and_validate_reference_prices(temp_filename)
        except ValueError as val_err:
            raise HTTPException(status_code=400, detail=str(val_err))

        # 2. Exécution du moteur d'allocation unique
        result = run_allocation_engine(farms_df, clients_df, station_df, ref_prices)
        return {
            "status": "success",
            "farms": farms_df.to_dict(orient="records"),
            "clients": clients_df.to_dict(orient="records"),
            **result,
        }

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.post("/api/assistant")
async def assistant_endpoint(payload: dict):
    question_id = payload.get("question")
    if not is_configured():
        raise HTTPException(status_code=501, detail="No AI model configured.")
    try:
        result = ask_assistant(question_id, payload)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # provider failure or the model mentioned an ID that doesn't exist in the plan
        raise HTTPException(status_code=502, detail=str(e))
 
