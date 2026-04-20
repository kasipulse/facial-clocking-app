const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const result = document.getElementById("result");
const button = document.getElementById("capture");

// -----------------------
// 🌐 BACKEND URL (UPDATE HERE IF NEEDED)
// -----------------------

const API_URL = "https://facial-clocking-app.onrender.com";

// -----------------------
// 📷 START CAMERA
// -----------------------

navigator.mediaDevices.getUserMedia({ video: true })
.then(stream => {
    video.srcObject = stream;
})
.catch(err => {
    console.log("Camera error:", err);
    result.innerText = "Camera not allowed ❌";
});

// -----------------------
// 📡 CAPTURE + SEND IMAGE
// -----------------------

button.onclick = async () => {

    result.innerText = "Processing... ⏳";

    const context = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    context.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {

        if (!blob) {
            result.innerText = "Capture failed ❌";
            return;
        }

        const formData = new FormData();
        formData.append("file", blob, "face.jpg");

        try {
            const response = await fetch(`${API_URL}/identify/`, {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                result.innerText = "Server error ❌";
                return;
            }

            const data = await response.json();

            // -----------------------
            // ⚡ SHOW RESULT
            // -----------------------

            if (data.message) {
                result.innerText = "✅ " + data.message;
                result.style.color = "lightgreen";
            } 
            else if (data.status) {
                result.innerText = "❌ " + data.status;
                result.style.color = "orange";
            } 
            else {
                result.innerText = "Unknown response ❌";
                result.style.color = "red";
            }

        } catch (err) {
            console.log(err);
            result.innerText = "Network error ❌";
            result.style.color = "red";
        }

    }, "image/jpeg");
};
