let currentToken = null;
let currentGuestId = null;

function showResult(html, cls = "") {
  const el = document.getElementById("result");
  el.className = "card " + cls;
  el.innerHTML = html;
}

async function onScanSuccess(decodedText) {
  // Avoid duplicate rapid scans of the same code
  if (decodedText === currentToken) return;
  currentToken = decodedText;

  const res = await fetch("/api/checkin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: decodedText, people_count: 0 })
  });
  const data = await res.json();

  if (data.status === "valid") {
    showResult(
      `<h3>✅ ${data.guest_name}</h3>
       <p>Allowed: ${data.allowed_count} person(s) — Category: ${data.category}</p>`,
      "ok"
    );
    currentGuestId = data.guest_id;
    document.getElementById("max-count").textContent = data.allowed_count;
    document.getElementById("count-panel").classList.remove("hidden");
    document.getElementById("people-count").max = data.allowed_count;
  } else if (data.status === "used") {
    showResult(
      `<h3>⚠️ Already Checked In</h3>
       <p>${data.guest_name} checked in at ${data.checked_in_at} (${data.people_count} person(s))</p>`,
      "warn"
    );
  } else {
    showResult(`<h3>❌ ${data.message}</h3>`, "error");
  }
}

async function confirmCheckin() {
  const count = parseInt(document.getElementById("people-count").value, 10);
  const res = await fetch("/api/checkin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: currentToken, people_count: count })
  });
  const data = await res.json();
  if (data.status === "ok") {
    showResult(`<h3>✅ ${data.message}</h3>`, "ok");
    document.getElementById("count-panel").classList.add("hidden");
  } else {
    showResult(`<h3>❌ ${data.message}</h3>`, "error");
  }
}

async function manualSearch() {
  const q = document.getElementById("manual-search").value;
  const res = await fetch(`/api/guests/search?q=${encodeURIComponent(q)}`);
  const data = await res.json();
  const ul = document.getElementById("manual-results");
  ul.innerHTML = "";
  data.forEach(g => {
    const li = document.createElement("li");
    li.innerHTML = `${g.full_name} — ${g.phone} (max ${g.allowed_count})
      <button onclick="manualCheckin(${g.id})">Check-In</button>`;
    ul.appendChild(li);
  });
}

async function manualCheckin(guestId) {
  const count = parseInt(prompt("How many people?", "1"), 10);
  if (!count || count < 1) return;
  const res = await fetch(`/api/manual-checkin/${guestId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ people_count: count })
  });
  const data = await res.json();
  alert(data.message);
}

// Initialize the QR scanner
const scanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: 250 });
scanner.render(onScanSuccess);