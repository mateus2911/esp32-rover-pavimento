const speedSlider = document.getElementById("speed-slider");
const speedValue = document.getElementById("speed-value");
const pwmLeftEl = document.getElementById("pwm-left");
const pwmRightEl = document.getElementById("pwm-right");
const detectionsList = document.getElementById("detections-list");
const btnToggleAi = document.getElementById("btn-toggle-ai");
const btnSnapshot = document.getElementById("btn-snapshot");
const btnStop = document.getElementById("btn-stop");
const snapshotFeedback = document.getElementById("snapshot-feedback");

const pressedKeys = new Set();
let activeButtonDir = null;
let ws = null;

function connectControlWs() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${location.host}/ws/control`);
  ws.onclose = () => {
    setTimeout(connectControlWs, 1000);
  };
}

function sendDrive(left, right) {
  pwmLeftEl.textContent = left;
  pwmRightEl.textContent = right;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ left, right }));
  }
}

function computeCommand() {
  const maxPwm = Math.round((Number(speedSlider.value) / 100) * 255);

  let forward = 0;
  let turn = 0;

  if (pressedKeys.has("w") || pressedKeys.has("arrowup") || activeButtonDir === "forward") {
    forward += 1;
  }
  if (pressedKeys.has("s") || pressedKeys.has("arrowdown") || activeButtonDir === "backward") {
    forward -= 1;
  }
  if (pressedKeys.has("a") || pressedKeys.has("arrowleft") || activeButtonDir === "left") {
    turn -= 1;
  }
  if (pressedKeys.has("d") || pressedKeys.has("arrowright") || activeButtonDir === "right") {
    turn += 1;
  }

  let left = (forward + turn) * maxPwm;
  let right = (forward - turn) * maxPwm;

  left = Math.max(-255, Math.min(255, left));
  right = Math.max(-255, Math.min(255, right));
  return { left, right };
}

function pushCurrentDrive() {
  const { left, right } = computeCommand();
  sendDrive(left, right);
}

async function triggerEmergencyStop() {
  pressedKeys.clear();
  activeButtonDir = null;
  sendDrive(0, 0);
  await fetch("/api/emergency_stop", { method: "POST" });
}

speedSlider.addEventListener("input", () => {
  speedValue.textContent = `${speedSlider.value}%`;
});

window.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if (key === " ") {
    event.preventDefault();
    triggerEmergencyStop();
    return;
  }
  if (["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright"].includes(key)) {
    event.preventDefault();
    pressedKeys.add(key);
    pushCurrentDrive();
  }
});

window.addEventListener("keyup", (event) => {
  const key = event.key.toLowerCase();
  if (pressedKeys.delete(key)) {
    pushCurrentDrive();
  }
});

window.addEventListener("blur", () => {
  triggerEmergencyStop();
});

document.querySelectorAll(".pad-btn[data-dir]").forEach((btn) => {
  const dir = btn.dataset.dir;
  const start = (e) => {
    e.preventDefault();
    activeButtonDir = dir;
    btn.classList.add("active");
    pushCurrentDrive();
  };
  const end = () => {
    activeButtonDir = null;
    btn.classList.remove("active");
    pushCurrentDrive();
  };
  btn.addEventListener("mousedown", start);
  btn.addEventListener("touchstart", start);
  btn.addEventListener("mouseup", end);
  btn.addEventListener("mouseleave", end);
  btn.addEventListener("touchend", end);
});

btnStop.addEventListener("click", triggerEmergencyStop);

btnToggleAi.addEventListener("click", async () => {
  const res = await fetch("/api/ai/toggle", { method: "POST" });
  const data = await res.json();
  btnToggleAi.textContent = data.ai_enabled ? "IA: Ligada" : "IA: Desligada";
});

btnSnapshot.addEventListener("click", async () => {
  const res = await fetch("/api/snapshot", { method: "POST" });
  const data = await res.json();
  if (data.ok) {
    snapshotFeedback.textContent = `Frame salvo em: ${data.path}`;
  } else {
    snapshotFeedback.textContent = `Erro ao salvar frame: ${data.error || "desconhecido"}`;
  }
});

async function pollStatus() {
  try {
    const res = await fetch("/api/status");
    const status = await res.json();

    const modeEl = document.getElementById("badge-mode");
    modeEl.textContent = status.mock_mode ? "SIMULAÇÃO" : "ESP32 REAL";
    modeEl.className = `badge ${status.mock_mode ? "badge-warn" : "badge-ok"}`;

    document.getElementById("badge-detector").textContent = `IA: ${status.detector_backend}`;
    document.getElementById("status-stream").textContent = `Stream: ${status.stream_connected ? "OK" : "OFF"}`;
    document.getElementById("status-esp").textContent = `ESP32: ${status.esp32_connected ? "OK" : "OFF"}`;
    document.getElementById("status-fps").textContent = `FPS: ${status.fps.toFixed(1)}`;
    btnToggleAi.textContent = status.ai_enabled ? "IA: Ligada" : "IA: Desligada";

    if (!status.detections.length) {
      detectionsList.innerHTML = '<li class="empty">Nenhuma falha detectada no frame atual.</li>';
    } else {
      detectionsList.innerHTML = status.detections
        .map(
          (d) =>
            `<li><span>${d.label}</span><strong>${Math.round(d.confidence * 100)}%</strong></li>`
        )
        .join("");
    }
  } catch {
    // Ignora falhas momentâneas de polling
  }
}

// Keepalive contínuo enquanto uma tecla/botão estiver ativo para satisfazer o failsafe da ESP32
setInterval(() => {
  if (pressedKeys.size > 0 || activeButtonDir !== null) {
    pushCurrentDrive();
  }
}, 120);

setInterval(pollStatus, 500);
connectControlWs();
pollStatus();
