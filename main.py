from fastapi import FastAPI, UploadFile, File
from datetime import datetime
import os
import shutil
from deepface import DeepFace

app = FastAPI()

KNOWN_FACES_DIR = "faces"
TEMP_DIR = "temp"

os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# 🧠 In-memory storage (for now)
attendance_log = []

@app.get("/")
def home():
    return {"msg": "API running with attendance"}

# ✅ Register employee
@app.post("/register")
async def register(employee_id: str, file: UploadFile = File(...)):
    path = f"{KNOWN_FACES_DIR}/{employee_id}.jpg"

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"status": f"{employee_id} registered"}

# ✅ Clock in/out
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
                employee_id = face.split(".")[0]
                now = datetime.now()

                # 🔥 Prevent duplicate clock-ins (within 5 min)
                for record in attendance_log:
                    if record["employee_id"] == employee_id:
                        last_time = datetime.fromisoformat(record["time"])
                        diff = (now - last_time).seconds

                        if diff < 300:
                            return {
                                "status": "duplicate",
                                "message": "Already clocked recently"
                            }

                # ✅ Save attendance
                entry = {
                    "employee_id": employee_id,
                    "time": now.isoformat(),
                    "status": "clocked"
                }

                attendance_log.append(entry)

                return {
                    "status": "success",
                    "employee_id": employee_id,
                    "time": entry["time"]
                }

        except:
            continue

    return {"status": "unknown"}

# ✅ View attendance
@app.get("/attendance")
def get_attendance():
    return attendance_log