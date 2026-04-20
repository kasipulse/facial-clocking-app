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
# 🚀 FASTAPI APP
# -----------------------

app = FastAPI()

PERSON_GROUP_ID = "employees"

# -----------------------
# 🧠 BRANDING (GLOBAL)
# -----------------------

BRANDED_BY = "Built by Mpho Mahlaba"

# -----------------------
# ❤️ HEALTH CHECK (Render fix)
# -----------------------

@app.get("/")
def health():
    return {
        "status": "running",
        "built_by": BRANDED_BY
    }

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

    try:
        r = requests.put(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
        return {
            "response": r.json(),
            "built_by": BRANDED_BY
        }
    except Exception as e:
        return {"error": str(e), "built_by": BRANDED_BY}

# -----------------------
# 👤 REGISTER EMPLOYEE
# -----------------------

@app.post("/register/")
async def register(name: str = Form(...), file: UploadFile = File(...)):
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY
    }

    try:
        # Create person
        person_res = requests.post(
            f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/persons",
            headers=headers,
            json={"name": name},
            timeout=REQUEST_TIMEOUT
        ).json()

        if "personId" not in person_res:
            return {"error": person_res, "built_by": BRANDED_BY}

        person_id = person_res["personId"]

        # Add face
        image = await file.read()

        requests.post(
            f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/persons/{person_id}/persistedFaces",
            headers={**headers, "Content-Type": "application/octet-stream"},
            data=image,
            timeout=REQUEST_TIMEOUT
        )

        # Train model
        requests.post(
            f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/train",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        # Save to Firebase
        db.collection("employees").add({
            "name": name,
            "person_id": person_id
        })

        return {
            "message": "Employee registered ✅",
            "person_id": person_id,
            "built_by": BRANDED_BY
        }

    except Exception as e:
        return {"error": str(e), "built_by": BRANDED_BY}

# -----------------------
# 🕒 IDENTIFY + CLOCK IN/OUT
# -----------------------

@app.post("/identify/")
async def identify(file: UploadFile = File(...)):
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY
    }

    try:
        image = await file.read()

        # Detect face
        detect_res = requests.post(
            f"{AZURE_ENDPOINT}/face/v1.0/detect",
            headers={**headers, "Content-Type": "application/octet-stream"},
            params={"returnFaceId": "true"},
            data=image,
            timeout=REQUEST_TIMEOUT
        )

        detect = detect_res.json()

        if not isinstance(detect, list) or len(detect) == 0:
            return {"status": "No face detected ❌", "built_by": BRANDED_BY}

        face_id = detect[0].get("faceId")

        if not face_id:
            return {"status": "Face detection failed ❌", "built_by": BRANDED_BY}

        # Identify person
        identify_res = requests.post(
            f"{AZURE_ENDPOINT}/face/v1.0/identify",
            headers=headers,
            json={
                "personGroupId": PERSON_GROUP_ID,
                "faceIds": [face_id]
            },
            timeout=REQUEST_TIMEOUT
        )

        identify_json = identify_res.json()

        if not isinstance(identify_json, list) or len(identify_json) == 0:
            return {"status": "Identification failed ❌", "built_by": BRANDED_BY}

        result = identify_json[0]

        if "candidates" not in result or len(result["candidates"]) == 0:
            return {"status": "Not recognized ❌", "built_by": BRANDED_BY}

        person_id = result["candidates"][0]["personId"]

        # Get employee
        employees = db.collection("employees")\
            .where("person_id", "==", person_id)\
            .limit(1)\
            .stream()

        employee_list = list(employees)

        if not employee_list:
            name = "Unknown"
        else:
            name = employee_list[0].to_dict().get("name", "Unknown")

        # Get last attendance
        records = db.collection("attendance")\
            .where("person_id", "==", person_id)\
            .order_by("timestamp", direction=firestore.Query.DESCENDING)\
            .limit(1)\
            .stream()

        last = list(records)

        if last and last[0].to_dict().get("status") == "IN":
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
            "person_id": person_id,
            "built_by": BRANDED_BY
        }

    except Exception as e:
        return {"error": str(e), "built_by": BRANDED_BY}

# -----------------------
# 📊 DASHBOARD API
# -----------------------

@app.get("/attendance/")
def get_attendance():
    records = db.collection("attendance")\
        .order_by("timestamp", direction=firestore.Query.DESCENDING)\
        .stream()

    return {
        "data": [r.to_dict() for r in records],
        "built_by": BRANDED_BY
    }
