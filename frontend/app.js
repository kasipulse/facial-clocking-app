const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const statusText = document.getElementById("status");
const button = document.getElementById("captureBtn");

let currentStream = null;
let useFrontCamera = true;

// -----------------------
// 🎥 START CAMERA
// -----------------------
async function startCamera() {
    try {
        // Stop previous stream if exists
        if (currentStream) {
            currentStream.getTracks().forEach(track => track.stop());
        }

        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: useFrontCamera ? "user" : "environment"
            }
        });

        video.srcObject = stream;
        currentStream = stream;

    } catch (err) {
        statusText.innerText = "Camera error ❌";
        console.log(err);
    }
}

// Start camera initially
startCamera();

// -----------------------
// 🔄 SWITCH CAMERA
// -----------------------
function switchCamera() {
    useFrontCamera = !useFrontCamera;
    startCamera();
}

// OPTIONAL: attach this to a button if you add one in HTML
// <button onclick="switchCamera()">Switch Camera</button>

// -----------------------
// 📸 CAPTURE + SEND
// -----------------------
button.onclick = async () => {

    statusText.innerText = "Processing...";

    const context = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    context.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {

        const formData = new FormData();
        formData.append("file", blob, "face.jpg");

        try {
            const response = await fetch("/identify/", {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            statusText.innerText =
                data.message ||
                data.status ||
                "No response from server";

        } catch (err) {
            statusText.innerText = "Server error ❌";
            console.log(err);
        }

    }, "image/jpeg");
};
