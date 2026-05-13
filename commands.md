# 🔒 Ghost Lock — Terminal Commands

## Step 1: Find Your Device MAC Address
```bash
python3 scanner.py
```

---

## Step 2: Run the Simulations

### Ghost Protocol v3 — Hold-Open Mode (`simulation_newapproach2.py`)
This is the **main simulation** for the Ghost Lock. It connects, checks RSSI to verify you're actually close, unlocks, then goes stealth.
```bash
python3 simulation_newapproach2.py --device "9c-82-81-8b-25-fc"
```

**With custom RSSI threshold** (default is -70, use -60 for closer range, -80 for longer range):
```bash
python3 simulation_newapproach2.py --device "9c-82-81-8b-25-fc" --rssi -60
```

---

### Secure Pulse Mode (`simulation_new.py`)
Connects, verifies RSSI, unlocks for 3 seconds, then locks and enters cooldown.
```bash
python3 simulation_new.py --device "9c-82-81-8b-25-fc"
```

**With custom RSSI threshold:**
```bash
python3 simulation_new.py --device "9c-82-81-8b-25-fc" --rssi -60
```

---

### Original Simulation (`simulation.py`)
Continuous RSSI monitoring mode — stays connected and watches signal strength in real-time.
```bash
python3 simulation.py --device "9c-82-81-8b-25-fc"
```

**Mock mode** (test without a real device — type RSSI values manually):
```bash
python3 simulation.py --mock
```

---

## Step 3: Raw Bluetooth Auto-Lock (`main.py`)
The **real deal** — actually locks/unlocks your Mac screen based on your phone's proximity.
```bash
python3 main.py --device "9c-82-81-8b-25-fc" --password "Dev@071006"
```

**With custom RSSI thresholds:**
```bash
python3 main.py --device "9c-82-81-8b-25-fc" --password "Dev@071006" --lock-rssi -75 --unlock-rssi -65
```

---

## ⚠️ Important Notes
- **Press `Ctrl + C`** to stop any script
- Make sure your **iQOO 7 Bluetooth is ON** before running
- Grant **Terminal → System Settings → Privacy → Bluetooth** permission
- Grant **Terminal → System Settings → Privacy → Accessibility** permission (for `main.py`)
- RSSI values: **-30 = very close**, **-70 = moderate**, **-90 = far away**
