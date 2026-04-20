from fastapi import FastAPI, UploadFile, File
import requests
import os

app = FastAPI()

AZURE_KEY = os.getenv("AZURE_FACE_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")

PERSON_GROUP_ID = "employees"


# Create person group (run once manually)
@app.get("/create-group/")
def create_group():
    url = f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}"
    
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY
    }

    body = {
        "name": "Employees"
    }

    r = requests.put(url, headers=headers, json=body)
    return r.json()


# Register employee
@app.post("/register/")
async def register(name: str, file: UploadFile = File(...)):
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY
    }

    # Create person
    person_res = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/persons",
        headers=headers,
        json={"name": name}
    ).json()

    person_id = person_res["personId"]

    # Add face
    image = await file.read()
    add_face = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/persons/{person_id}/persistedFaces",
        headers={**headers, "Content-Type": "application/octet-stream"},
        data=image
    ).json()

    # Train
    requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/persongroups/{PERSON_GROUP_ID}/train",
        headers=headers
    )

    return {"person_id": person_id}


# Clock in (identify)
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

    face_id = detect[0]["faceId"]

    # Identify
    identify = requests.post(
        f"{AZURE_ENDPOINT}/face/v1.0/identify",
        headers=headers,
        json={
            "personGroupId": PERSON_GROUP_ID,
            "faceIds": [face_id]
        }
    ).json()

    return identify
