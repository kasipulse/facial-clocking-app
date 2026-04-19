from fastapi import FastAPI, UploadFile, File
from datetime import datetime
import os
from deepface import DeepFace
import shutil

app = FastAPI()

KNOWN_FACES_DIR = "faces"
TEMP_DIR = "temp"

os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

@app.get("/")
def home():
    return {"msg": "API running with face recognition"}

# ✅ Register a face
@app.post("/register")
async def register(name: str, file: UploadFile = File(...)):
    path = f"{KNOWN_FACES_DIR}/{name}.jpg"

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"status": f"{name} registered"}

# ✅ Clock (recognize face)
@app.post("/clock")
async def clock(file: UploadFile = File(...)):
    temp_path = f"{TEMP_DIR}/{file.filename}"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    for face in os.listdir(KNOWN_FACES_DIR):
        known_path = f"{KNOWN_FACES_DIR}/{face}"

        try:
            result = DeepFace.verify(temp_path, known_path)

            if result["verified"]:
                name = face.split(".")[0]

                return {
                    "status": "success",
                    "person": name,
                    "time": str(datetime.now())
                }

        except:
            continue

    return {"status": "unknown"}