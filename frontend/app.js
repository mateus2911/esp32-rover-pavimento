const statusBadge = document.getElementById("ws-status");
const modeBadge = document.getElementById("mode-badge");
const motorReadout = document.getElementById("motor-readout");
const speedSlider = document.getElementById("speed-slider");
const speedValue = document.getElementById("speed-value");
const estopBtn = document.getElementById("btn-estop");
const snapBtn = document.getElementById("btn-snap");
const captureToggle = document.getElementById("toggle-capture");
const captureModeBadge = document.getElementById("capture-mode-badge");
const captureCount = document.getElementById("capture-count");
const captureStatus = document.getElementById("capture-status");

// Captura 3 imagens por segundo quando a chave estiver ativada (~333 ms)
const CAPTURE_RATE_HZ = 3;
const CAPTURE_INTERVAL_MS = 1000 / CAPTURE_RATE_HZ;

// Estado das teclas pressionadas no momento
const keysPressed = { w: false, a: false, s: false, d: false };
let captureIntervalId = null;
let isCapturing = false;

// Conexão WebSocket com o backend FastAPI
const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/control`);

ws.onopen = () => {
  statusBadge.textContent = "WS Conectado";
  statusBadge.className = "badge connected";
};

ws.onclose = () => {
  statusBadge.textContent = "WS Desconectado";
  statusBadge.className = "badge disconnected";
};

speedSlider.addEventListener("input", () => {
  speedValue.textContent = speedSlider.value;
});

function calculateMotorSpeeds(keys, maxSpeed) {
  const throttle = (keys.w ? maxSpeed : 0) - (keys.s ? maxSpeed : 0);
  const turn = (keys.d ? maxSpeed : 0) - (keys.a ? maxSpeed : 0);

  const clamp = (value) => Math.max(-255, Math.min(255, value));
  const left = clamp(throttle + turn);
  const right = clamp(throttle - turn);

  return { left: Math.round(left), right: Math.round(right) };
}

function sendCommand(left, right) {
  motorReadout.textContent = `L: ${left} | R: ${right}`;
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ left, right }));
  }
}

function triggerEmergencyStop() {
  for (const key of Object.keys(keysPressed)) {
    keysPressed[key] = false;
  }
  document.querySelectorAll(".btn-dir").forEach((btn) => {
    btn.classList.remove("active");
  });
  sendCommand(0, 0);
}

function formatPhotoCount(total) {
  return `${total} ${total === 1 ? "foto" : "fotos"}`;
}

async function refreshCaptureCount() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) return;
    const data = await response.json();
    captureCount.textContent = formatPhotoCount(data.total_captures ?? 0);

    if (data.mock_mode) {
      modeBadge.textContent = "Modo Simulação";
      modeBadge.className = "badge mode-sim";
    } else if (data.stream_connected && data.esp32_ws_connected) {
      modeBadge.textContent = "ESP32 Conectada";
      modeBadge.className = "badge mode-real-ok";
    } else {
      const cam = data.stream_connected ? "Câm OK" : "Sem Câm";
      const ws = data.esp32_ws_connected ? "Motores OK" : "Sem Motores";
      modeBadge.textContent = `ESP32 Real (${cam} | ${ws})`;
      modeBadge.className = "badge mode-real-wait";
    }
  } catch {
    // Silencioso caso o servidor esteja reiniciando
  }
}

async function requestCapture(prefixLabel) {
  if (isCapturing) return;
  isCapturing = true;

  try {
    const response = await fetch("/api/capture", { method: "POST" });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Erro ao capturar frame.");
    }
    captureCount.textContent = formatPhotoCount(data.total_captures);
    captureStatus.textContent = `${prefixLabel}: ${data.filename}`;
    captureStatus.className = "capture-status ok";
  } catch (err) {
    captureStatus.textContent = err.message || "Falha na captura.";
    captureStatus.className = "capture-status error";
  } finally {
    isCapturing = false;
  }
}

async function captureFrame() {
  if (!captureToggle.checked) return;
  await requestCapture("Capturando (3/s)");
}

async function captureSinglePhoto() {
  await requestCapture("Foto salva");
}

function updateCaptureLoop() {
  if (captureToggle.checked) {
    captureModeBadge.textContent = "GRAVANDO";
    captureModeBadge.className = "capture-badge on";
    if (captureIntervalId === null) {
      captureFrame();
      captureIntervalId = setInterval(captureFrame, CAPTURE_INTERVAL_MS);
    }
  } else {
    captureModeBadge.textContent = "DESLIGADA";
    captureModeBadge.className = "capture-badge off";
    if (captureIntervalId !== null) {
      clearInterval(captureIntervalId);
      captureIntervalId = null;
    }
    captureStatus.textContent = "Captura pausada. Ative a chave (ou pressione C) para retomar.";
    captureStatus.className = "capture-status";
  }
}

window.addEventListener("keydown", (e) => {
  const key = e.key.toLowerCase();
  if (e.code === "Space") {
    e.preventDefault();
    triggerEmergencyStop();
    return;
  }
  if (key === "f" && !e.repeat) {
    captureSinglePhoto();
    return;
  }
  if (key === "c" && !e.repeat) {
    captureToggle.checked = !captureToggle.checked;
    updateCaptureLoop();
    return;
  }
  if (key in keysPressed && !keysPressed[key]) {
    keysPressed[key] = true;
    document.querySelector(`[data-key="${key}"]`)?.classList.add("active");
  }
});

window.addEventListener("keyup", (e) => {
  const key = e.key.toLowerCase();
  if (key in keysPressed) {
    keysPressed[key] = false;
    document.querySelector(`[data-key="${key}"]`)?.classList.remove("active");
  }
});

document.querySelectorAll(".btn-dir").forEach((btn) => {
  const key = btn.dataset.key;
  btn.addEventListener("pointerdown", () => { keysPressed[key] = true; });
  btn.addEventListener("pointerup", () => { keysPressed[key] = false; });
  btn.addEventListener("pointerleave", () => { keysPressed[key] = false; });
  btn.addEventListener("pointercancel", () => { keysPressed[key] = false; });
});

window.addEventListener("blur", triggerEmergencyStop);
estopBtn.addEventListener("click", triggerEmergencyStop);
snapBtn.addEventListener("click", captureSinglePhoto);
captureToggle.addEventListener("change", updateCaptureLoop);

refreshCaptureCount();
setInterval(refreshCaptureCount, 2000);

setInterval(() => {
  const maxSpeed = Number(speedSlider.value);
  const { left, right } = calculateMotorSpeeds(keysPressed, maxSpeed);
  sendCommand(left, right);
}, 150);
