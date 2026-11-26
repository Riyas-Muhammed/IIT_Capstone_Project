import os
import uuid
import pandas as pd
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse

app = FastAPI(
    title="Employee Welfare Program",
    version="1.0"
)

#  uvicorn app:app --reload
@app.get("/home")
def testing():
    return{"message": "App is running"}

@app.post("/reimbursment")
def evaluate_file(file: UploadFile= File(...)):
    allowed_extensions = [".pdf"]
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        return {"error": "Please upload a pdf file"}    

    return {"message": "File uploaded succesfully"}