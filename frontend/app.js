const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const statusText = document.getElementById("status");
const button = document.getElementById("captureBtn");

// Start camera
navigator.mediaDevices.getUserMedia({ video: true })
.then(stream => {
    video.srcObject = stream;
})
.catch(err => {
    statusText.innerText = "Camera error ❌";
    console.log(err);
});

// Capture + send
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
