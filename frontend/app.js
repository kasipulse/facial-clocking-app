const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const result = document.getElementById("result");

const API_URL = "https://facial-clocking-app.onrender.com";

// -----------------------
// 📷 START CAMERA
// -----------------------

navigator.mediaDevices.getUserMedia({ video: true })
.then(stream => {
    video.srcObject = stream;
})
.catch(err => {
    result.innerText = "Camera error ❌";
});

// -----------------------
// ⚡ AUTO CLOCK FUNCTION
// -----------------------

async function sendFrame() {

    const context = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    context.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {

        if (!blob) return;

        const formData = new FormData();
        formData.append("file", blob, "face.jpg");

        try {
            const res = await fetch(`${API_URL}/identify/`, {
                method: "POST",
                body: formData
            });

            const data = await res.json();

            if (data.message) {
                result.innerText = "✅ " + data.message;
                result.style.color = "lightgreen";
            } else {
                result.innerText = data.status || "Scanning...";
                result.style.color = "orange";
            }

        } catch (err) {
            result.innerText = "Server error ❌";
        }

    }, "image/jpeg");
}

// -----------------------
// 🔁 RUN EVERY 5 SECONDS
// -----------------------

setInterval(sendFrame, 5000);
