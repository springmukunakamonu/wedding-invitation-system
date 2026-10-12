let scanner = null;
let currentToken = null;
let currentGuestId = null;
let checkinMode = "qr";
let processingScan = false;

const startButton = document.getElementById("start-camera");
const stopButton = document.getElementById("stop-camera");
const scannerStatus = document.getElementById("scanner-status");
const cameraNotice = document.getElementById("camera-notice");
const resultPanel = document.getElementById("result");
const countPanel = document.getElementById("count-panel");
const countInput = document.getElementById("people-count");
const confirmButton = document.getElementById("confirm-checkin");

function setScannerStatus(message) {
  scannerStatus.textContent = message;
}

function showCameraNotice(message) {
  cameraNotice.textContent = message;
  cameraNotice.classList.remove("hidden");
}

function showResult(title, detail, status) {
  resultPanel.replaceChildren();
  resultPanel.className = `checkin-result ${status}`;

  const heading = document.createElement("h3");
  heading.textContent = title;
  resultPanel.appendChild(heading);

  if (detail) {
    const text = document.createElement("p");
    text.textContent = detail;
    resultPanel.appendChild(text);
  }
}

async function stopCamera() {
  if (!scanner) return;

  try {
    if (scanner.isScanning) await scanner.stop();
    scanner.clear();
  } catch (error) {
    console.error("Could not stop the camera scanner.", error);
  } finally {
    scanner = null;
    startButton.classList.remove("hidden");
    stopButton.classList.add("hidden");
  }
}

async function handleScan(decodedText) {
  if (processingScan) return;
  processingScan = true;
  currentToken = decodedText.trim();
  checkinMode = "qr";
  countPanel.classList.add("hidden");
  resultPanel.classList.add("hidden");
  setScannerStatus("Invitation found. Checking guest details…");
  await stopCamera();

  try {
    const response = await fetch("/api/checkin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: currentToken, people_count: 0 })
    });
    const data = await response.json();

    if (!response.ok && data.status !== "invalid") {
      throw new Error(data.message || "Could not check this invitation.");
    }

    if (data.status === "valid") {
      currentGuestId = data.guest_id;
      prepareCount(data.allowed_count);
      showResult(data.guest_name, `Allowed: ${data.allowed_count} · ${data.category}`, "ok");
      setScannerStatus("Guest found. Confirm the number of people arriving.");
    } else if (data.status === "used") {
      showResult("Already checked in", `${data.guest_name} checked in at ${data.checked_in_at} (${data.people_count} people).`, "warn");
      setScannerStatus("This invitation has already been used.");
    } else {
      showResult("Invitation not recognized", data.message || "Check the QR code and try again.", "error");
      setScannerStatus("Scan another invitation or find the guest manually.");
    }
  } catch (error) {
    showResult("Could not check invitation", error.message, "error");
    setScannerStatus("Check your connection and try again.");
  } finally {
    processingScan = false;
  }
}

function prepareCount(maxCount) {
  document.getElementById("max-count").textContent = maxCount;
  countInput.max = maxCount;
  countInput.value = 1;
  countPanel.classList.remove("hidden");
}

async function startCamera() {
  cameraNotice.classList.add("hidden");

  if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showCameraNotice("Camera access requires a secure HTTPS address. Open this check-in page using your HTTPS website, or use guest search below. If using a phone on the same Wi-Fi as the computer, the site still needs HTTPS.");
    setScannerStatus("Camera unavailable on this connection.");
    return;
  }

  if (typeof Html5Qrcode === "undefined") {
    showCameraNotice("The scanner could not load. Check your internet connection, then reload this page.");
    setScannerStatus("Scanner library unavailable.");
    return;
  }

  startButton.disabled = true;
  setScannerStatus("Requesting camera access…");
  try {
    scanner = new Html5Qrcode("reader");
    await scanner.start(
      { facingMode: "environment" },
      {
        fps: 10,
        qrbox: (width, height) => {
          const size = Math.floor(Math.min(width, height, 320) * 0.8);
          return { width: size, height: size };
        },
        aspectRatio: 1
      },
      handleScan,
      () => {}
    );
    startButton.classList.add("hidden");
    stopButton.classList.remove("hidden");
    setScannerStatus("Camera is on. Point it at the guest’s invitation QR code.");
  } catch (error) {
    scanner = null;
    const message = error && error.name === "NotAllowedError"
      ? "Camera permission was denied. Allow camera access in your browser settings, then try again."
      : "Could not start the camera. Check that your browser has camera permission and that no other app is using it.";
    showCameraNotice(message);
    setScannerStatus("Camera did not start.");
  } finally {
    startButton.disabled = false;
  }
}

async function confirmCheckin() {
  const count = Number.parseInt(countInput.value, 10);
  const maxCount = Number.parseInt(countInput.max, 10);
  if (!Number.isInteger(count) || count < 1 || count > maxCount) {
    showResult("Check the headcount", `Enter a number from 1 to ${maxCount}.`, "error");
    return;
  }

  confirmButton.disabled = true;
  try {
    const endpoint = checkinMode === "qr"
      ? "/api/checkin"
      : `/api/manual-checkin/${currentGuestId}`;
    const payload = checkinMode === "qr"
      ? { token: currentToken, people_count: count }
      : { people_count: count };
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json();

    if (data.status === "ok") {
      showResult("Check-in complete", data.message, "ok");
      countPanel.classList.add("hidden");
      setScannerStatus("Ready for the next guest.");
    } else {
      showResult("Check-in not completed", data.message || "Please try again.", "error");
    }
  } catch (error) {
    showResult("Connection problem", "Could not save the check-in. Check your connection and try again.", "error");
  } finally {
    confirmButton.disabled = false;
  }
}

async function manualSearch(event) {
  event.preventDefault();
  const query = document.getElementById("manual-search").value.trim();
  const list = document.getElementById("manual-results");
  list.replaceChildren();
  if (!query) {
    addSearchMessage(list, "Enter a guest name or phone number to search.");
    return;
  }

  try {
    const response = await fetch(`/api/guests/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error("Guest search failed.");
    const guests = await response.json();
    if (guests.length === 0) {
      addSearchMessage(list, "No guests found. Try another name or phone number.");
      return;
    }

    guests.forEach(guest => {
      const item = document.createElement("li");
      const details = document.createElement("div");
      details.className = "manual-guest-details";
      const name = document.createElement("strong");
      name.textContent = guest.full_name;
      const phone = document.createElement("span");
      phone.textContent = `${guest.phone} · up to ${guest.allowed_count}`;
      details.append(name, phone);

      const button = document.createElement("button");
      button.type = "button";
      button.className = "manual-checkin-button";
      button.textContent = "Check in";
      button.addEventListener("click", () => selectManualGuest(guest));
      item.append(details, button);
      list.appendChild(item);
    });
  } catch (error) {
    addSearchMessage(list, "Could not search guests. Check your connection and try again.");
  }
}

function addSearchMessage(list, message) {
  const item = document.createElement("li");
  item.className = "manual-search-message";
  item.textContent = message;
  list.appendChild(item);
}

function selectManualGuest(guest) {
  currentGuestId = guest.id;
  currentToken = null;
  checkinMode = "manual";
  resultPanel.classList.add("hidden");
  prepareCount(guest.allowed_count);
  showResult(guest.full_name, `Manual check-in · Allowed: ${guest.allowed_count} · ${guest.category}`, "ok");
  setScannerStatus("Guest selected. Confirm the number of people arriving.");
  countPanel.scrollIntoView({ behavior: "smooth", block: "center" });
}

startButton.addEventListener("click", startCamera);
stopButton.addEventListener("click", async () => {
  await stopCamera();
  setScannerStatus("Camera is off.");
});
confirmButton.addEventListener("click", confirmCheckin);
document.getElementById("manual-search-form").addEventListener("submit", manualSearch);

if (!window.isSecureContext) {
  showCameraNotice("Camera access requires HTTPS. You can still search for guests and check them in manually.");
}
