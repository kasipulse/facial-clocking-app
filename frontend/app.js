const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const result = document.getElementById("result");
const button = document.getElementById("capture");

// Start camera
navigator.mediaDevices.getUserMedia({ video: true })
.then(stream => {
    video.srcObject = stream;
})
.catch(err => {
    console.log("Camera error:", err);
});

// Capture + send
button.onclick = async () => {
    const context = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    context.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append("file", blob, "face.jpg");

        result.innerText = "Processing...";

        try {
            const response = await fetch("https://facial-clocking-app.onrender.com/identify/", {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            result.innerText = data.message || data.status || "Error";
        } catch (err) {
            result.innerText = "Server error";
            console.log(err);
        }

    }, "image/jpeg");
};
