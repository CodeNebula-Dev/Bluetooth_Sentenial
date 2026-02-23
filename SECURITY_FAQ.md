# Security FAQ & "New Approach" Logic

## 1. Is the Lock Visible to others?
**NO.**
- **Technically**: The ESP32 is acting as a **BLE Client** (Observer). It is like a person listening to the radio. It does not broadcast its own name. If you scan for Bluetooth devices near the lock, **you will see nothing**.
- **Exception**: It is only "visible" for the split second it connects to you, and even then, it doesn't broadcast a name, it just initiates a connection.

## 2. Can someone with the same MAC address open it?
**NO.** (This is the big upgrade).
- **Old Way**: Checked MAC Address. Spoofable.
- **New Way**: checks **Connection**. 
    - Even if a hacker sets their MAC address to `AA:BB:CC...` (Matching yours), they cannot complete the **Bluetooth Handshake** without the encryption keys (if paired) or simply because the ESP32 is looking for a specific **128-bit Service UUID**, not just a MAC.
    - Accidental opening is impossible. Deliberate hacking is extremely difficult.

## 3. How does it know to Lock?
It is a **Pulse System**.
1.  **Unlock**: You arrive -> It fires the relay for **3 Seconds**.
2.  **Auto-Lock**: After 3 seconds, it turns off the relay automatically.
3.  **Disconnect**: It immediately disconnects your phone.

## 4. How does it know I left? (The "Cooldown")
To prevent it from unlocking 100 times while you sit at your desk:
1.  After unlocking once, it enters **"Cooldown Mode"**.
2.  It keeps scanning. If it *sees* your phone is still there, it **DOES NOTHING**.
3.  It only resets to "Ready" when it scans for **5 Seconds** and **DOES NOT see you**.
4.  This ensures it only unlocks when you **arrive**, not while you **stay**.
