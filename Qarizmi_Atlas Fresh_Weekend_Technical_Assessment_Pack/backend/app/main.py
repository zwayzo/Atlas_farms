from fastapi import FastAPI, UploadFile, File, HTTPException
import shutil
import os
from app.engine.validators import validate_data
from app.engine.allocation import run_allocation_engine
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from app.engine.validators import validate_data
from app.engine.allocation import run_allocation_engine

app = FastAPI(title="API Planification Daily Apple Export - Atlas Fresh")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifiez ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        except ValueError as val_err:
            raise HTTPException(status_code=400, detail=str(val_err))

        # 2. Exécution du moteur d'allocation unique
        result = run_allocation_engine(farms_df, clients_df, station_df)

        return {
            "status": "success",
            **result
        }

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)