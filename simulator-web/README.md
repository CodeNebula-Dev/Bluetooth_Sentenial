## ESP32 Simulator Web UI (static)

This is a lightweight browser UI (no build tools) for your Ghost Lock simulator:

- Drag the phone to change distance (RSSI changes automatically)
- Toggle `Phone: ON/OFF`
- Toggle `Phone: REAL/SPOOF` (handshake success vs failure)
- Switch `Pulse` vs `Hold-Open` firmware logic
- See relay/door state and serial-like logs in real time

### Run

From this folder:

```bash
cd "simulator-web"
python3 -m http.server 8080
```

Open:
`http://localhost:8080`

