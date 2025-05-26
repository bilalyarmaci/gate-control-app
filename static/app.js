// DOM Elements
const fileInput = document.getElementById('fileInput');
const videoFileInput = document.getElementById('videoFileInput');
// Image mode
const canvasImage = document.getElementById('previewCanvasImage');
const ctxImage = canvasImage.getContext('2d');
const containerImage = document.getElementById('containerImage');
// Video mode
const canvasVideo = document.getElementById('previewCanvasVideo');
const ctxVideo = canvasVideo.getContext('2d');
const containerVideo = document.getElementById('containerVideo');
const statusDiv = document.getElementById('status');
const videoElement = document.getElementById('videoElement');
const cameraElement = document.getElementById('cameraElement');
const imageBtn = document.getElementById('imageBtn');
const videoBtn = document.getElementById('videoBtn');
const cameraBtn = document.getElementById('cameraBtn');
const stopVideo = document.getElementById('stopVideo');
const stopCamera = document.getElementById('stopCamera');
const processVideo = document.getElementById('processVideo');
const captureFrame = document.getElementById('captureFrame');
const autoProcess = document.getElementById('autoProcess');

// Manage allowed plates UI
const savePlatesBtn = document.getElementById('savePlatesBtn');
const allowedPlatesInput = document.getElementById('allowedPlatesInput');
savePlatesBtn.onclick = async () => {
    const plates = allowedPlatesInput.value
        .split(',')
        .map(p => p.trim())
        .filter(p => p);
    try {
        const resp = await fetch('/update_allowed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plates })
        });
        const result = await resp.json();
        if (result.status === 'success') {
            showToast('saved', 'Allowed plates updated successfully');
        } else {
            showToast('error', 'Failed to update allowed plates');
        }
    } catch (err) {
        showToast('error', 'Error saving plates: ' + err.message);
    }
};

// Stream handling
let videoStream = null;
let currentMode = 'image';
let processingInterval = null;

// Button handlers
imageBtn.onclick = () => switchMode('image');
videoBtn.onclick = () => switchMode('video');
cameraBtn.onclick = () => switchMode('camera');
stopVideo.onclick = stopVideoStream;
stopCamera.onclick = stopCameraStream;
processVideo.onclick = processVideoFrame;
captureFrame.onclick = captureCameraFrame;

// Auto processing toggle
autoProcess.onchange = function () {
    if (this.checked) {
        startContinuousProcessing();
    } else {
        stopContinuousProcessing();
    }
};

// File input handlers
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Clear the canvas before drawing a new image
    ctxImage.clearRect(0, 0, canvasImage.width, canvasImage.height);

    const img = new Image();
    img.onload = () => {
        // Set canvas size to match the natural image size
        canvasImage.width = img.naturalWidth;
        canvasImage.height = img.naturalHeight;

        // Draw the image at its natural size
        ctxImage.drawImage(img, 0, 0, img.naturalWidth, img.naturalHeight);

        // Send the image for detection
        sendForDetect(canvasImage, containerImage);
    };
    img.src = URL.createObjectURL(file);

    // Ensure the canvas is visible
    canvasImage.style.display = 'block';
});

videoFileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    statusDiv.classList.add('d-none');
    videoElement.src = URL.createObjectURL(file);

    // Show video controls
    document.getElementById('videoControls').classList.remove('d-none');

    // Enable auto-process checkbox for continuous processing
    document.getElementById('autoProcess').disabled = false;
});

function switchMode(mode) {
    currentMode = mode;
    stopVideoStream();
    stopCameraStream();
    stopContinuousProcessing();

    // Hide all input types
    document.getElementById('imageInput').classList.add('d-none');
    document.getElementById('videoInput').classList.add('d-none');
    document.getElementById('videoControls').classList.add('d-none');
    document.getElementById('cameraControls').classList.add('d-none');
    containerImage.classList.add('d-none');
    containerVideo.classList.add('d-none');

    switch (mode) {
        case 'image':
            document.getElementById('imageInput').classList.remove('d-none');
            containerImage.classList.remove('d-none');
            break;
        case 'video':
            document.getElementById('videoInput').classList.remove('d-none');
            containerVideo.classList.remove('d-none');
            break;
        case 'camera':
            document.getElementById('cameraControls').classList.remove('d-none');
            containerVideo.classList.remove('d-none');
            // startCamera(); // Removed as per instructions
            break;
    }
}

async function populateCameraDropdown() {
    try {
        // Request camera permission to populate device labels
        const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
        tempStream.getTracks().forEach(track => track.stop());

        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');

        const cameraSelect = document.getElementById('cameraSelect');
        cameraSelect.innerHTML = '<option value="" disabled selected>Select a camera</option>';

        videoDevices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.textContent = device.label || `Camera ${cameraSelect.length}`;
            cameraSelect.appendChild(option);
        });

        document.getElementById('cameraSelection').classList.remove('d-none');
    } catch (err) {
        console.error('Error populating camera dropdown:', err);
        showToast('error', 'Failed to load camera devices.');
    }
}

async function startCamera() {
    try {
        const cameraSelect = document.getElementById('cameraSelect');
        const selectedDeviceId = cameraSelect.value;

        if (!selectedDeviceId) {
            showToast('error', 'Please select a camera.');
            return;
        }

        // Stop any existing video stream
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
        }

        // Start the selected camera
        videoStream = await navigator.mediaDevices.getUserMedia({
            video: { deviceId: { exact: selectedDeviceId } }
        });

        cameraElement.srcObject = videoStream;
        showToast('info', 'Camera started. Click "Capture Frame" to detect objects.');
    } catch (err) {
        console.error('Camera error:', err);
        showToast('error', 'Failed to start camera: ' + err.message);
    }
}

// Populate the camera dropdown when the page loads
window.addEventListener('load', populateCameraDropdown);

// Add cameraSelect change event to startCamera, at root level
document.getElementById('cameraSelect').addEventListener('change', startCamera);

function stopVideoStream() {
    if (videoElement.src) {
        videoElement.src = '';
        videoElement.load();
    }
    stopContinuousProcessing();
}

function stopCameraStream() {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
    if (cameraElement.srcObject) {
        cameraElement.srcObject = null;
    }
}

function startContinuousProcessing() {
    // Clear any existing interval
    stopContinuousProcessing();

    // Process frames at regular intervals (e.g., every 1000ms)
    processingInterval = setInterval(() => {
        if (videoElement.paused || videoElement.ended) {
            stopContinuousProcessing();
            return;
        }

        // Resize the canvas to a smaller resolution for faster processing
        const targetWidth = 320; // Adjust as needed
        const targetHeight = (videoElement.videoHeight / videoElement.videoWidth) * targetWidth;
        canvasVideo.width = targetWidth;
        canvasVideo.height = targetHeight;

        // Draw the resized frame on the canvas
        ctxVideo.drawImage(videoElement, 0, 0, targetWidth, targetHeight);

        // Send the resized frame for detection
        sendForDetect(canvasVideo, containerVideo);
    }, 1000); // Adjust interval as needed (e.g., 1000ms = 1 second)

    showStatus('Continuous processing started', 'info');
}

function stopContinuousProcessing() {
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
}

function processVideoFrame() {
    if (!videoElement.src) {
        showStatus('Please select a video file first', 'warning');
        return;
    }

    // Capture current frame from video
    canvasVideo.width = videoElement.videoWidth || 640;
    canvasVideo.height = videoElement.videoHeight || 480;

    ctxVideo.drawImage(videoElement, 0, 0, canvasVideo.width, canvasVideo.height);
    sendForDetect(canvasVideo, containerVideo);
}

function captureCameraFrame() {
    if (!cameraElement.srcObject) {
        showStatus('Camera not active', 'warning');
        return;
    }

    // Capture current frame from camera
    canvasVideo.width = cameraElement.videoWidth || 640;
    canvasVideo.height = cameraElement.videoHeight || 480;

    ctxVideo.drawImage(cameraElement, 0, 0, canvasVideo.width, canvasVideo.height);
    sendForDetect(canvasVideo, containerVideo);
}

function showToast(action, plateText) {
    const toastContainer = document.getElementById('toastContainer');
    const toastElement = toastContainer.querySelector('.toast');
    const toastTitle = document.getElementById('toastTitle');
    const toastBody = document.getElementById('toastBody');

    // Set toast content based on action
    switch (action) {
        case "allowed":
            toastTitle.textContent = 'Access Granted';
            toastBody.textContent = `Truck allowed: ${plateText}`;
            toastElement.classList.add('bg-success', 'text-white');
            break;
        case "denied":
            toastTitle.textContent = 'Access Denied';
            toastBody.textContent = `Truck not authorized: ${plateText || 'Unknown plate'}`;
            toastElement.classList.add('bg-danger', 'text-white');
            break;
        case "error":
            toastTitle.textContent = 'Error';
            toastBody.textContent = 'No objects detected.';
            toastElement.classList.add('bg-danger', 'text-white');
            break;
        case "buzz":
            toastTitle.textContent = 'Alert';
            toastBody.textContent = 'Vehicle detected. Not a truck.';
            toastElement.classList.add('bg-warning', 'text-dark');
            break;
        case "saved":
            toastTitle.textContent = 'Success';
            toastBody.textContent = 'Allowed plates updated successfully.';
            toastElement.classList.add('bg-info', 'text-white');
            break;
    }

    // Show the toast
    const toast = new bootstrap.Toast(toastElement);
    toast.show();

    // Reset toast classes after hiding
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'text-white', 'text-dark');
    });
}

// Replace modal logic with toast in sendForDetect
async function sendForDetect(canvas, container) {
    try {
        const dataUrl = canvas.toDataURL('image/jpeg');
        const resp = await fetch('/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: dataUrl })
        });

        const data = await resp.json();

        console.log('Detection response:', data); // Debugging log

        if (data.error) {
            showStatus(data.error, 'danger');
            return;
        }

        // Draw detections
        console.log('Detections:', data.detections); // Debugging log
        drawBBoxes(data.detections, container);

        // Show status
        if (data.status) {
            showStatus(data.status, 'info');
        }

        // Show toast based on Arduino action
        if (data.action) {
            showToast(data.action, data.plate_text);
        }
    } catch (err) {
        console.error('Detection error:', err);
        showStatus('Detection failed: ' + err.message, 'danger');
    }
}

// Update the box drawing function
function drawBBoxes(dets, containerTarget) {
    // Clear existing boxes
    Array.from(containerTarget.querySelectorAll('.bbox')).forEach(el => el.remove());

    // Calculate scale between natural and displayed image size
    const scaleX = containerTarget.clientWidth / containerTarget.querySelector('canvas').width;
    const scaleY = containerTarget.clientHeight / containerTarget.querySelector('canvas').height;

    // Draw new boxes
    dets.forEach(d => {
        const [x1, y1, x2, y2] = d.box;
        const div = document.createElement('div');
        div.className = 'bbox';

        // Scale coordinates to match displayed size
        const scaledX = x1 * scaleX;
        const scaledY = y1 * scaleY;
        const scaledWidth = (x2 - x1) * scaleX;
        const scaledHeight = (y2 - y1) * scaleY;

        // Apply scaled dimensions
        div.style.left = `${scaledX}px`;
        div.style.top = `${scaledY}px`;
        div.style.width = `${scaledWidth}px`;
        div.style.height = `${scaledHeight}px`;

        // Set color based on class
        div.style.borderWidth = '3px';
        div.style.borderStyle = 'solid';
        div.style.borderColor = d.class === 'truck' ? '#ff0000' :
            d.class === 'license_plate' ? '#00ff00' :
                d.class === 'car' ? '#ffc107' : '#ffff00';

        // Add label
        const label = document.createElement('div');
        label.className = 'bbox-label';
        label.textContent = `${d.class} (${(d.conf * 100).toFixed(1)}%)`;

        // Add OCR text if available
        if (d.ocr_text) {
            label.textContent += ` - ${d.ocr_text}`;
        }

        div.appendChild(label);
        containerTarget.appendChild(div);
    });

    // Debugging log to verify bounding box positions
    console.log('Bounding boxes drawn:', dets);
}

function showDetectionDetails(detections) {
    const detailsContainer = document.getElementById('detection-details');
    const detectionList = document.getElementById('detection-list');

    if (!detections || detections.length === 0) {
        detailsContainer.classList.add('d-none');
        return;
    }

    // Clear previous details
    detectionList.innerHTML = '';

    // Create detailed items for each detection
    detections.forEach((detection, index) => {
        const item = document.createElement('div');
        item.className = `detection-item ${detection.class}`;

        let content = `
            <strong>${detection.class.toUpperCase()} #${index + 1}</strong><br>
            Confidence: ${(detection.conf * 100).toFixed(1)}%<br>
            Coordinates: [${detection.box.map(coord => Math.round(coord)).join(', ')}]
        `;

        // Add OCR text if available
        if (detection.ocr_text) {
            content += `<br><strong>OCR Result:</strong> "${detection.ocr_text}"`;
        }

        item.innerHTML = content;
        detectionList.appendChild(item);
    });

    // Show the details container
    detailsContainer.classList.remove('d-none');
}

function showStatus(message, type) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `alert alert-${type}`;
    status.classList.remove('d-none');
}