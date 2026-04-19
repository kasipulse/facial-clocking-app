from fastapi import FastAPI, UploadFile, File
from datetime import datetime

app = FastAPI()

logs = []

@app.get("/")
def home():
    return {"msg": "API running"}

@app.post("/clock")
async def clock(file: UploadFile = File(...)):
    time = str(datetime.now())

    data = {
        "name": file.filename,
        "time": time
    }

    logs.append(data)

    return data

@app.get("/logs")
def get_logs():
    return logs