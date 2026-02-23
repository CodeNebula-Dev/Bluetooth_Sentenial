# Explanation: `simulation.py` & `simulation_new.py`

## Purpose
These two files act as the testing ground for the proximity-based locking logic without requiring the ESP32 hardware to be wired up. They simulate the exact state machines that later run on the microcontroller unit.

## Logic & Flow
- **Scanning State**: Uses Bluetooth APIs to passively scan for a specified target device based on RSSI (signal strength) thresholds.
- **Handshake & Verification**: Attempts a connection to verify that the device is mathematically authorized, preventing basic cloning attacks.
- **Cooldown & Lock Release State Mache**:
  - `simulation_new.py` typically implements the **Pulse Mode** (Unlock briefly, lock, then ignore until user leaves and returns).
  - Handles timeout counting to avoid rapid locking/unlocking cycles near the threshold edge.

## Role in the System
They provide a safe, iterative way to develop and debug logic. Issues like RSSI bounce, connection delays, or state-machine deadlocks can be observed via print statements before porting the validated logic to C++.
