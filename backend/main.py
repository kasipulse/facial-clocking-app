import os
import json
import requests
from fastapi import FastAPI, UploadFile, File, Form
import firebase_admin
from firebase_admin import credentials, firestore

# -----------------------
# 🔐 ENV VARIABLES
# -----------------------

AZURE_KEY = os.getenv("AZURE_FACE_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")
FIREBASE_KEY = os.getenv("FIREBASE_KEY")

if not AZURE_KEY or not AZURE_ENDPOINT:
    raise ValueError("Missing Azure credentials")

if not FIREBASE_KEY:
    raise ValueError("Missing Firebase key")

# -----------------------
# 🔥 FIREBASE SETUP
# -----------------------

firebase_json = json.loads(FIREBASE_KEY)
cred = credentials.Certificate(firebase_json)
firebase_admin.initialize_app(cred)
db = firestore.client()

# -----------------------
# 🚀 FASTAPI APP
# -----------------------

app = FastAPI()

PERSON_GROUP_ID = "employees"

# -----------------------
# 🧱 CREATE GROUP (run once)
# -----------------------

@app.get("/create-group/")
def create_group():
    url = f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}"

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY
    }

    body = {"name": "Employees"}

    r = requests.put(url, headers=headers, json=body)
    return r.json()


# -----------------------
# 👤 REGISTER EMPLOYEE
# -----------------------

@app.post("/register/")
async def register(name: str = Form(...), file: UploadFile = File(...)):
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY
    }

    # Create person
    person_res = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/persons",
        headers=headers,
        json={"name": name}
    ).json()

    if "personId" not in person_res:
        return {"error": person_res}

    person_id = person_res["personId"]

    # Add face
    image = await file.read()
    add_face = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/persons/{person_id}/persistedFaces",
        headers={**headers, "Content-Type": "application/octet-stream"},
        data=image
    ).json()

    # Train model
    requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/train",
        headers=headers
    )

    # Save to Firebase
    db.collection("employees").add({
        "name": name,
        "person_id": person_id
    })

    return {
        "message": "Employee registered ✅",
        "person_id": person_id
    }


# -----------------------
# 🕒 IDENTIFY + CLOCK IN/OUT
# -----------------------

@app.post("/identify/")
async def identify(file: UploadFile = File(...)):
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY
    }

    image = await file.read()

    # Detect face
    detect = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/detect",
        headers={**headers, "Content-Type": "application/octet-stream"},
        params={"returnFaceId": "true"},
        data=image
    ).json()

    if not detect:
        return {"status": "No face detected ❌"}

    face_id = detect[0]["faceId"]

    # Identify person
    identify_res = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/identify",
        headers=headers,
        json={
            "personGroupId": PERSON_GROUP_ID,
            "faceIds": [face_id]
        }
    ).json()

    result = identify_res[0]

    if not result["candidates"]:
        return {"status": "Not recognized ❌"}

    person_id = result["candidates"][0]["personId"]

    # Get employee name
    employees = db.collection("employees")\
        .where("person_id", "==", person_id)\
        .limit(1)\
        .stream()

    employee = list(employees)
    name = employee[0].to_dict()["name"] if employee else "Unknown"

    # Toggle IN / OUT
    records = db.collection("attendance")\
        .where("person_id", "==", person_id)\
        .order_by("timestamp", direction=firestore.Query.DESCENDING)\
        .limit(1)\
        .stream()

    last = list(records)

    if last and last[0].to_dict()["status"] == "IN":
        status = "OUT"
    else:
        status = "IN"

    # Save attendance
    db.collection("attendance").add({
        "person_id": person_id,
        "name": name,
        "status": status,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    return {
        "message": f"{name} clocked {status} ✅",
        "person_id": person_id
    }


# -----------------------
# 📊 SIMPLE DASHBOARD API
# -----------------------

@app.get("/attendance/")
def get_attendance():
    records = db.collection("attendance")\
        .order_by("timestamp", direction=firestore.Query.DESCENDING)\
        .stream()

    data = [r.to_dict() for r in records]

    return data
