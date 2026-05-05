const AUTH_UUID = "12345678-1234-1234-1234-1234567890ab";

function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n));
}

// Deterministic RSSI model:
// rssi = base - 20*log10(distance)
// Tuned so:
// - ~2m => -61..-65 dBm
// - ~12m => -78..-85 dBm
function distanceToRssi(distanceM) {
  const d = Math.max(distanceM, 0.1);
  const base = -55.0; // approx at 1m
  const rssi = base - 20.0 * Math.log10(d);
  return Math.round(clamp(rssi, -110, -35));
}

function fmtSeconds(ms) {
  return `${(ms / 1000).toFixed(1)}s`;
}

class GhostLockEngineJS {
  constructor(cfg) {
    this.cfg = cfg;
    this.phone = { advertising: true, genuine: true, distanceM: 12 };
    this.reset();
  }

  reset(cfgOverrides = {}) {
    this.cfg = { ...this.cfg, ...cfgOverrides };

    this.nowMs = 0;
    this.lastSeenTimeMs = null;
    this.pulseEndMs = null;
    this.lockState =
      this.cfg.firmware === "pulse" ? "SCAN_FOR_TRIGGER" : "SECURE_LOCKED";
    this.doorUnlocked = false;
    this.verifying = false;

    // Relay input polarity: door unlocked iff we apply active polarity
    this.relayInputHigh = !this.cfg.activeStateHigh;
  }

  setPhone({ advertising, genuine, distanceM }) {
    if (typeof advertising === "boolean") this.phone.advertising = advertising;
    if (typeof genuine === "boolean") this.phone.genuine = genuine;
    if (typeof distanceM === "number") this.phone.distanceM = distanceM;
  }

  get rssi() {
    return distanceToRssi(this.phone.distanceM);
  }

  get phoneAuthorized() {
    // In this UI the phone always advertises the configured service UUID.
    return true;
  }

  get isVisible() {
    if (!this.phone.advertising) return false;
    if (!this.phoneAuthorized) return false;
    return this.rssi >= this.cfg.scanFloorRssi;
  }

  _log(onLog, msg) {
    onLog(`[${fmtSeconds(this.nowMs)}] ${msg}`);
  }

  _handshake(onLog) {
    // In your firmware: connect succeeds only for genuine BLE identity.
    if (this.phone.genuine) {
      this._log(onLog, "Identity Verified. Unlocking...");
      return true;
    }
    this._log(onLog, "Verification Failed (Spoof attempt?). Remaining Locked.");
    return false;
  }

  tick(dtMs, onLog) {
    this.nowMs += dtMs;

    const rssiNow = this.rssi;
    const visibleNow = this.isVisible;

    // MODE: Pulse
    if (this.cfg.firmware === "pulse") {
      const phoneInRange = visibleNow && rssiNow >= this.cfg.rssiThreshold;

      // Pulse firmware heartbeat only updates when RSSI passes threshold.
      if (phoneInRange) {
        this.lastSeenTimeMs = this.nowMs;
      }

      if (this.lockState === "SCAN_FOR_TRIGGER") {
        if (phoneInRange) {
          this._log(onLog, `Target Found (RSSI ${rssiNow} dBm)`);

          const ok = this._handshake(onLog);
          if (ok) {
            this._log(onLog, ">>> SECURE UNLOCK (Handshake Success)");
            this.doorUnlocked = true;
            this.relayInputHigh = this.cfg.activeStateHigh;
            this.pulseEndMs = this.nowMs + this.cfg.unlockMs;
            this.lockState = "PULSING";
          }
        }
      } else if (this.lockState === "PULSING") {
        if (this.pulseEndMs !== null && this.nowMs >= this.pulseEndMs) {
          this.relayInputHigh = !this.cfg.activeStateHigh;
          this.doorUnlocked = false;
          this._log(onLog, "[Action] <<< LOCKING");
          this.pulseEndMs = null;
          this.lockState = "COOLDOWN_WAIT_FOR_EXIT";
        }
      } else if (this.lockState === "COOLDOWN_WAIT_FOR_EXIT") {
        if (
          this.lastSeenTimeMs !== null &&
          this.nowMs - this.lastSeenTimeMs > this.cfg.cooldownMs
        ) {
          this._log(onLog, "[User Left] -> Cooldown Reset. Ready to Scan.");
          this.lockState = "SCAN_FOR_TRIGGER";
        }
      }
    } else {
      // MODE: Hold-open
      if (!visibleNow) {
        // If we can't see the device in scans, heartbeat stops (so it will auto-lock).
      } else {
        // Hold-open firmware: update lastSeenTime whenever the authorized UUID appears in scans,
        // even if it's below the unlock threshold.
        this.lastSeenTimeMs = this.nowMs;
      }

      if (this.lockState === "SECURE_LOCKED") {
        if (visibleNow && rssiNow > this.cfg.rssiUnlockThreshold) {
          this._log(onLog, "Target in Range. Initiating Security Handshake...");
          this.lockState = "VERIFYING";
        }
      } else if (this.lockState === "VERIFYING") {
        const ok = this._handshake(onLog);
        if (ok) {
          this.doorUnlocked = true;
          this.relayInputHigh = this.cfg.activeStateHigh;
          this._log(onLog, "BLE disconnected (stealth)");
          this.lastSeenTimeMs = this.nowMs;
          this.lockState = "HOLD_OPEN_STEALTH";
        } else {
          this.doorUnlocked = false;
          this.relayInputHigh = !this.cfg.activeStateHigh;
          this.lockState = "SECURE_LOCKED";
        }
      } else if (this.lockState === "HOLD_OPEN_STEALTH") {
        if (
          this.lastSeenTimeMs !== null &&
          this.nowMs - this.lastSeenTimeMs > this.cfg.autoLockDelayMs
        ) {
          this._log(onLog, "User Left Range. Auto-Locking.");
          this.doorUnlocked = false;
          this.relayInputHigh = !this.cfg.activeStateHigh;
          this.lockState = "SECURE_LOCKED";
        }
      }
    }

    const lastSeenAgeMs =
      this.lastSeenTimeMs === null ? null : Math.max(0, this.nowMs - this.lastSeenTimeMs);

    return {
      nowMs: this.nowMs,
      rssi: rssiNow,
      isVisible: visibleNow,
      doorUnlocked: this.doorUnlocked,
      lockState: this.lockState,
      lastSeenAgeMs
    };
  }
}

const elArena = document.getElementById("arena");
const elPhone = document.getElementById("phone");
const elPhoneGlyph = document.getElementById("phoneGlyph");
const elDoorText = document.getElementById("doorText");
const elLockStateText = document.getElementById("lockStateText");
const elRssiText = document.getElementById("rssiText");
const elRssiBarInner = document.getElementById("rssiBarInner");
const elVisibleText = document.getElementById("visibleText");
const elDistanceSub = document.getElementById("distanceSub");
const elLastSeenAgeText = document.getElementById("lastSeenAgeText");
const elLogsBox = document.getElementById("logsBox");

const elBtnPulse = document.getElementById("btnPulse");
const elBtnHold = document.getElementById("btnHold");
const elBtnAdv = document.getElementById("btnAdv");
const elBtnGenuine = document.getElementById("btnGenuine");
const elBtnNear = document.getElementById("btnNear");
const elBtnFar = document.getElementById("btnFar");
const elBtnReset = document.getElementById("btnReset");
const elBtnClearLogs = document.getElementById("btnClearLogs");
const elDistanceSlider = document.getElementById("distanceSlider");
const elRssiThresholdInput = document.getElementById("rssiThresholdInput");
const elScanFloorInput = document.getElementById("scanFloorInput");

let cfg = {
  authorizedUuids: [AUTH_UUID],
  serviceUuid: AUTH_UUID,
  firmware: "hold-open",

  // Defaults match your firmware constants
  rssiThreshold: -75,
  rssiUnlockThreshold: -75,
  unlockMs: 3000,
  cooldownMs: 5000,
  autoLockDelayMs: 10000,

  activeStateHigh: true,
  scanFloorRssi: -100
};

let phone = { advertising: true, genuine: true, distanceM: 12.0 };

let engine = new GhostLockEngineJS(cfg);
engine.setPhone(phone);

let logs = [];
function appendLog(line) {
  logs.push(line);
  if (logs.length > 200) logs = logs.slice(-200);

  // Fast incremental render
  const div = document.createElement("div");
  div.textContent = line;
  div.style.padding = "2px 0";
  div.style.fontFamily =
    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";
  div.style.fontSize = "12px";
  elLogsBox.appendChild(div);
  elLogsBox.scrollTop = elLogsBox.scrollHeight;
}

function clearLogs() {
  logs = [];
  elLogsBox.innerHTML = "No logs yet.";
}

function setDoorUI(isUnlocked, lockState) {
  elDoorText.textContent = isUnlocked ? "UNLOCKED" : "LOCKED";
  elDoorText.style.color = isUnlocked ? "var(--good)" : "var(--bad)";
  elLockStateText.textContent = lockState;
}

function setPhoneVisualFromDistance(distanceM) {
  const minDist = 0.5;
  const maxDist = 15;

  const rect = elArena.getBoundingClientRect();
  const lockX = rect.width * 0.18;
  const maxX = rect.width - 26;

  const d = clamp(distanceM, minDist, maxDist);
  const t = (d - minDist) / (maxDist - minDist);
  const x = lockX + clamp(t, 0, 1) * (maxX - lockX);

  elPhone.style.left = `${x}px`;
}

function updateRssiAndUI() {
  const rssi = distanceToRssi(phone.distanceM);
  const visible = phone.advertising && rssi >= cfg.scanFloorRssi;

  elRssiText.textContent = `${rssi} dBm`;
  elDistanceSub.textContent = `${phone.distanceM.toFixed(1)}m`;

  const pct = Math.round(((rssi - -110) / (-35 - -110)) * 100);
  elRssiBarInner.style.width = `${clamp(pct, 0, 100)}%`;
  elRssiBarInner.style.background = engine.doorUnlocked ? "var(--good)" : "var(--accent)";
  elVisibleText.textContent = `visible: ${visible ? "yes" : "no"}`;
}

function setFirmwareButtons() {
  elBtnPulse.style.background =
    cfg.firmware === "pulse" ? "rgba(96,165,250,0.30)" : "rgba(255,255,255,0.04)";
  elBtnHold.style.background =
    cfg.firmware === "hold-open" ? "rgba(96,165,250,0.30)" : "rgba(255,255,255,0.04)";
}

function setPhoneButtons() {
  elBtnAdv.textContent = `Phone: ${phone.advertising ? "ON" : "OFF"}`;
  elBtnAdv.style.background = phone.advertising
    ? "rgba(52, 211, 153, 0.20)"
    : "rgba(255,255,255,0.04)";

  elBtnGenuine.textContent = `Phone: ${phone.genuine ? "REAL" : "SPOOF"}`;
  elBtnGenuine.style.background = phone.genuine
    ? "rgba(52, 211, 153, 0.20)"
    : "rgba(251, 113, 133, 0.20)";

  // Visual feedback in the arena.
  elPhone.style.background = phone.genuine
    ? phone.advertising
      ? "rgba(52, 211, 153, 0.22)"
      : "rgba(255,255,255,0.10)"
    : phone.advertising
      ? "rgba(251, 113, 133, 0.22)"
      : "rgba(255,255,255,0.10)";

  elPhoneGlyph.textContent = phone.advertising ? "📱" : "—";
  elPhoneGlyph.style.opacity = phone.advertising ? "1" : "0.7";
}

function resetEngine(withLog = true) {
  // Keep phone state, reset firmware state machine + timers.
  engine.reset({
    firmware: cfg.firmware,
    rssiThreshold: cfg.rssiThreshold,
    rssiUnlockThreshold: cfg.rssiUnlockThreshold,
    unlockMs: cfg.unlockMs,
    cooldownMs: cfg.cooldownMs,
    autoLockDelayMs: cfg.autoLockDelayMs,
    activeStateHigh: cfg.activeStateHigh,
    scanFloorRssi: cfg.scanFloorRssi
  });
  engine.setPhone(phone);

  setFirmwareButtons();
  setPhoneButtons();
  updateRssiAndUI();
  elLastSeenAgeText.textContent = "lastSeenAge: —";

  if (withLog) {
    clearLogs();
    appendLog(`Booting Ghost Lock simulator (${cfg.firmware})...`);
  }

  setDoorUI(engine.doorUnlocked, engine.lockState);
}

// --- Dragging ---
let dragging = false;
let arenaRectCache = null;

function clientXToDistance(clientX) {
  const rect = elArena.getBoundingClientRect();
  const lockX = rect.width * 0.18;
  const maxX = rect.width - 26;
  const minDist = 0.5;
  const maxDist = 15;

  const x = clamp(clientX - rect.left, lockX, maxX);
  const t = (x - lockX) / (maxX - lockX);
  const d = minDist + t * (maxDist - minDist);
  return Math.round(d * 10) / 10;
}

function bindArenaDrag() {
  elPhone.addEventListener("pointerdown", (e) => {
    dragging = true;
    elPhone.setPointerCapture(e.pointerId);
    phone.distanceM = clientXToDistance(e.clientX);
    elDistanceSlider.value = String(phone.distanceM);
    setPhoneVisualFromDistance(phone.distanceM);
    updateRssiAndUI();
  });

  elPhone.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    phone.distanceM = clientXToDistance(e.clientX);
    elDistanceSlider.value = String(phone.distanceM);
    setPhoneVisualFromDistance(phone.distanceM);
    updateRssiAndUI();
  });

  elPhone.addEventListener("pointerup", () => {
    dragging = false;
  });
}

// --- Button bindings ---
elBtnPulse.addEventListener("click", () => {
  cfg.firmware = "pulse";
  cfg.rssiUnlockThreshold = cfg.rssiThreshold;
  resetEngine(true);
});

elBtnHold.addEventListener("click", () => {
  cfg.firmware = "hold-open";
  cfg.rssiUnlockThreshold = cfg.rssiThreshold;
  resetEngine(true);
});

elBtnAdv.addEventListener("click", () => {
  phone.advertising = !phone.advertising;
  setPhoneButtons();
});

elBtnGenuine.addEventListener("click", () => {
  phone.genuine = !phone.genuine;
  setPhoneButtons();
});

elBtnNear.addEventListener("click", () => {
  phone.distanceM = 2.0;
  elDistanceSlider.value = "2";
  setPhoneVisualFromDistance(phone.distanceM);
  updateRssiAndUI();
});

elBtnFar.addEventListener("click", () => {
  phone.distanceM = 12.0;
  elDistanceSlider.value = "12";
  setPhoneVisualFromDistance(phone.distanceM);
  updateRssiAndUI();
});

elBtnReset.addEventListener("click", () => {
  resetEngine(true);
});

elBtnClearLogs.addEventListener("click", () => {
  clearLogs();
});

elDistanceSlider.addEventListener("input", (e) => {
  phone.distanceM = parseFloat(e.target.value);
  setPhoneVisualFromDistance(phone.distanceM);
  updateRssiAndUI();
});

elRssiThresholdInput.addEventListener("change", (e) => {
  cfg.rssiThreshold = parseInt(e.target.value || "-75", 10);
  cfg.rssiUnlockThreshold = cfg.rssiThreshold;
  resetEngine(false);
});

elScanFloorInput.addEventListener("change", (e) => {
  cfg.scanFloorRssi = parseInt(e.target.value || "-100", 10);
  resetEngine(false);
});

// Keep initial UI coherent
setFirmwareButtons();
setPhoneButtons();
setPhoneVisualFromDistance(phone.distanceM);
updateRssiAndUI();
setDoorUI(false, engine.lockState);
appendLog(`Booting Ghost Lock simulator (${cfg.firmware})...`);

bindArenaDrag();

// Main simulation loop
const tickMs = 50;
setInterval(() => {
  engine.setPhone(phone);

  const snap = engine.tick(tickMs, (line) => {
    // Only append from the engine when it produces logs.
    appendLog(line);
  });

  setDoorUI(snap.doorUnlocked, snap.lockState);
  updateRssiAndUI();

  elLastSeenAgeText.textContent =
    snap.lastSeenAgeMs === null ? "lastSeenAge: —" : `lastSeenAge: ${fmtSeconds(snap.lastSeenAgeMs)}`;
}, tickMs);

