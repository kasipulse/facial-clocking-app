import os
import json
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import firebase_admin
from firebase_admin import credentials, firestore

# -----------------------
# 🔐 ENV VARIABLES
# -----------------------

AZURE_KEY = os.getenv("AZURE_FACE_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")
FIREBASE_KEY = os.getenv("FIREBASE_KEY")

REQUEST_TIMEOUT = 10

if not AZURE_KEY or not AZURE_ENDPOINT:
    raise ValueError("Missing Azure credentials")

if not FIREBASE_KEY:
    raise ValueError("Missing Firebase key")

# -----------------------
# 🔥 FIREBASE SETUP
# -----------------------

firebase_json = json.loads(FIREBASE_KEY)
cred = credentials.Certificate(firebase_json)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -----------------------
# 🚀 APP
# -----------------------

app = FastAPI()

PERSON_GROUP_ID = "employees"

BRANDED_BY = "Built by Mpho Mahlaba"

# -----------------------
# 🌐 FRONTEND STATIC FILES
# -----------------------

app.mount("/static", StaticFiles(directory="frontend"), name="static")

# -----------------------
# 🏠 FRONTEND ROUTES
# -----------------------

@app.get("/")
def home():
    return FileResponse("frontend/index.html")

@app.get("/dashboard")
def dashboard():
    return FileResponse("frontend/dashboard.html")

# -----------------------
# ❤️ HEALTH CHECK
# -----------------------

@app.get("/health")
def health():
    return {"status": "running", "built_by": BRANDED_BY}

# -----------------------
# 🧱 CREATE GROUP
# -----------------------

@app.get("/create-group/")
def create_group():
    url = f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}"

    headers = {"Ocp-Apim-Subscription-Key": AZURE_KEY}

    body = {"name": "Employees"}

    r = requests.put(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)

    return {"response": r.json(), "built_by": BRANDED_BY}

# -----------------------
# 👤 REGISTER
# -----------------------

@app.post("/register/")
async def register(name: str = Form(...), file: UploadFile = File(...)):

    headers = {"Ocp-Apim-Subscription-Key": AZURE_KEY}

    image = await file.read()

    person_res = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/persons",
        headers=headers,
        json={"name": name},
        timeout=REQUEST_TIMEOUT
    ).json()

    if "personId" not in person_res:
        return {"error": person_res}

    person_id = person_res["personId"]

    requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/persons/{person_id}/persistedFaces",
        headers={**headers, "Content-Type": "application/octet-stream"},
        data=image,
        timeout=REQUEST_TIMEOUT
    )

    requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/train",
        headers=headers,
        timeout=REQUEST_TIMEOUT
    )

    db.collection("employees").add({
        "name": name,
        "person_id": person_id
    })

    return {"message": "Employee registered ✅", "person_id": person_id}

# -----------------------
# 🕒 IDENTIFY (CLOCK IN/OUT)
# -----------------------

@app.post("/identify/")
async def identify(file: UploadFile = File(...)):

    headers = {"Ocp-Apim-Subscription-Key": AZURE_KEY}

    image = await file.read()

    detect = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/detect",
        headers={**headers, "Content-Type": "application/octet-stream"},
        params={"returnFaceId": "true"},
        data=image,
        timeout=REQUEST_TIMEOUT
    ).json()

    if not detect:
        return {"status": "No face detected ❌"}

    face_id = detect[0]["faceId"]

    identify_res = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/identify",
        headers=headers,
        json={
            "personGroupId": PERSON_GROUP_ID,
            "faceIds": [face_id]
        },
        timeout=REQUEST_TIMEOUT
    ).json()

    if not identify_res or not identify_res[0]["candidates"]:
        return {"status": "Not recognized ❌"}

    person_id = identify_res[0]["candidates"][0]["personId"]

    employee = db.collection("employees")\
        .where("person_id", "==", person_id)\
        .limit(1)\
        .stream()

    employee_list = list(employee)

    name = employee_list[0].to_dict()["name"] if employee_list else "Unknown"

    records = db.collection("attendance")\
        .where("person_id", "==", person_id)\
        .order_by("timestamp", direction=firestore.Query.DESCENDING)\
        .limit(1)\
        .stream()

    last = list(records)

    status = "OUT" if last and last[0].to_dict()["status"] == "IN" else "IN"

    db.collection("attendance").add({
        "person_id": person_id,
        "name": name,
        "status": status,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    return {
        "message": f"{name} clocked {status} ✅",
        "built_by": BRANDED_BY
    }

# -----------------------
# 📊 DASHBOARD API (FIXED)
# -----------------------

@app.get("/attendance/")
def get_attendance():

    records = db.collection("attendance")\
        .order_by("timestamp", direction=firestore.Query.DESCENDING)\
        .stream()

    data = [r.to_dict() for r in records]

    return {
        "data": data,
        "built_by": BRANDED_BY
    }
