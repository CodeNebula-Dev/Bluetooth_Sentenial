## ESP32 Simulator (Ghost Lock)

This folder contains a **local, offline** simulator that models:

- ESP32 firmware logic for **Pulse** and **Hold-Open** modes
- Fake BLE scanning + “connect/handshake” verification (spoof vs real)
- Relay + “door” output states (so you can test timing without hardware)

It does **not** emulate the ESP32 CPU or real NimBLE; instead it simulates the **observable behavior** your firmware implements (state machine, thresholds, timers, and relay/lock outputs).

### Run (interactive)

Pulse mode:

```bash
python3 run_simulator.py --firmware pulse --interactive
```

Hold-open mode:

```bash
python3 run_simulator.py --firmware hold-open --interactive
```

In the prompt, try:

- `near` / `far`
- `real` / `spoof`
- `on` / `off`
- `rssi -60`
- `status`

### Run (scripted scenario)

```bash
python3 run_simulator.py --firmware hold-open --scenario scenarios/default_hold_open.json
```

### Notes / Fidelity

- Pulse: unlocks for a fixed duration, then enters cooldown until “user left” timeout.
- Hold-open: keeps the door unlocked while the user is “seen”; auto-locks after missing for `AUTO_LOCK_DELAY`.
- The simulator uses the same threshold semantics as your firmware:
  - Pulse checks `rssi >= RSSI_THRESHOLD`
  - Hold-open checks `rssi > RSSI_UNLOCK_THRESHOLD`

