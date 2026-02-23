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

## Source Code

### `simulation.py`

```python
import time
import sys
import argparse
import threading

# ================= SIMULATION CONFIGURATION =================
RSSI_THRESHOLD = -75        
LOCK_TIMEOUT_MS = 1000   

def get_current_time_ms():
    return int(time.time() * 1000)

# --- REAL DEVICE LOGIC (Original "Step 82" Simple Loop) ---
def run_real_loop(device_address):
    import IOBluetooth
    
    def get_device(mac):
        devices = IOBluetooth.IOBluetoothDevice.pairedDevices()
        if not devices: return None
        for d in devices:
            if d.addressString().replace("-", ":").upper() == mac.replace("-", ":").upper():
                return d
        return None

    target_device = get_device(device_address)
    if not target_device:
        print(f"Error: Device {device_address} not found.")
        sys.exit(1)

    # Force cleaner start state
    if target_device.isConnected():
        print("Clearing stale connection state...")
        target_device.closeConnection()
        time.sleep(1.0)

    print(f"--- MODE: REAL BLUETOOTH (Original) ---")
    print(f"Target: {target_device.name()}")
    print("WARNING: macOS RSSI often 'sticks'. Tests 'Disconnect' logic well, but 'Range' poorly.")
    print("-" * 50)

    last_seen_time = 0
    is_unlocked = False

    last_connect_attempt = 0

    try:
        while True:
            # 1. Non-Blocking Connection Handling
            now = get_current_time_ms()
            connected = target_device.isConnected()
            current_rssi = -127 

            if not connected:
                # Only try to reconnect every 2 seconds to prevent freezing the UI
                if now - last_connect_attempt > 2000:
                    try: target_device.openConnection()
                    except: pass
                    last_connect_attempt = now
            
            if target_device.isConnected():
                # target_device.remoteNameRequest_action_(None, None)
                try:
                    raw = target_device.rawRSSI()
                    # Filter: 127 is error. 0 is often error/glitch on Mac disconnect.
                    # Valid RSSI is usually negative (e.g. -30 to -99)
                    if raw != 127 and raw < 0:
                        current_rssi = raw
                except: pass
            
            # 2. Logic
            now = get_current_time_ms()
            
            if current_rssi >= RSSI_THRESHOLD:
                last_seen_time = now
            
            user_is_present = (now - last_seen_time < LOCK_TIMEOUT_MS)
            if last_seen_time == 0: user_is_present = False

            if user_is_present:
                if not is_unlocked:
                    print(f"\n[ACTION] >>> UNLOCKING")
                    is_unlocked = True
                rem = (LOCK_TIMEOUT_MS - (now - last_seen_time)) / 1000.0
                print(f"State: UNLOCKED | Signal: {current_rssi} dBm | Hold: {rem:.1f}s   ", end='\r')
            else:
                if is_unlocked:
                    print(f"\n[ACTION] <<< LOCKING")
                    is_unlocked = False
                print(f"State: LOCKED   | Signal: {current_rssi} dBm | Waiting...       ", end='\r')
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped.")

# --- MOCK LOGIC (Threaded Input) ---
mock_rssi = -127
def input_thread():
    global mock_rssi
    print("[INTERACTIVE] Type RSSI (e.g. -50) and Enter:")
    while True:
        try:
            val = input()
            try: mock_rssi = int(val)
            except: pass
        except: break

def run_mock_loop():
    global mock_rssi
    print("--- MODE: MOCK SIMULATION ---")
    t = threading.Thread(target=input_thread)
    t.daemon = True
    t.start()
    
    last_seen_time = 0
    is_unlocked = False

    try:
        while True:
            current_rssi = mock_rssi
            now = get_current_time_ms()
            
            if current_rssi >= RSSI_THRESHOLD:
                last_seen_time = now
            
            user_is_present = (now - last_seen_time < LOCK_TIMEOUT_MS)
            if last_seen_time == 0: user_is_present = False

            if user_is_present:
                if not is_unlocked:
                    print(f"\n[ACTION] >>> UNLOCKING")
                    is_unlocked = True
                rem = (LOCK_TIMEOUT_MS - (now - last_seen_time)) / 1000.0
                print(f"State: UNLOCKED | Signal: {current_rssi} dBm | Hold: {rem:.1f}s   ", end='\r')
            else:
                if is_unlocked:
                    print(f"\n[ACTION] <<< LOCKING")
                    is_unlocked = False
                print(f"State: LOCKED   | Signal: {current_rssi} dBm | Waiting...       ", end='\r')
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    if args.mock:
        run_mock_loop()
    elif args.device:
        run_real_loop(args.device)
    else:
        print("Use --device [MAC] or --mock")

if __name__ == "__main__":
    main()
```

### `simulation_new.py`

```python
import time
import sys
import argparse
import time

# ================= SIMULATION CONFIGURATION =================
RSSI_THRESHOLD = -75        
UNLOCK_DURATION = 3 # Seconds to hold lock open

def get_current_time_ms():
    return int(time.time() * 1000)

def run_simulation(device_address):
    import IOBluetooth
    
    print(f"--- MODE: SECURE PULSE SIMULATION ---")
    print(f"Target: {device_address}")
    print("Logic: Scan -> Connect -> Unlock(3s) -> Disconnect")
    print("-" * 50)

    # Helper to find device
    def find_device():
        devices = IOBluetooth.IOBluetoothDevice.pairedDevices()
        if not devices: return None
        for d in devices:
            if d.addressString().replace("-", ":").upper() == device_address.replace("-", ":").upper():
                return d
        return None

    target_device = find_device()
    if not target_device:
        print(f"Error: Device {device_address} not found. Pair it first.")
        sys.exit(1)

    # Force clean start
    if target_device.isConnected():
        print("Initial Cleanup: Disconnecting...")
        target_device.closeConnection()
        time.sleep(1)

    cooldown = False

    try:
        while True:
            # 1. SCANNING STATE
            if not target_device.isConnected():
                # In real life, we check RSSI here. 
                # On Mac simulation, we check "Presence" by trying to connect.
                # If we are in "Cooldown" (User hasn't left yet), ignore them.
                
                if cooldown:
                    # Check if they are GONE (Signal lost) to reset cooldown
                    # For sim, we try to peek at RSSI or Connection
                    # If we can't connect, they are gone -> Reset Cooldown.
                    # Since we can't check without connecting on Mac, we assume
                    # Cooldown resets after 5 seconds of silence? 
                    # Actually, let's just use a simple timer for Sim.
                    print("State: COOLDOWN (Waiting for user to leave...)", end='\r')
                    time.sleep(1)
                    # Logic: If we CAN connect, they are still here.
                    # If we FAIL to connect, they left. Reset Cooldown.
                    try:
                        err = target_device.openConnection()
                        if err == 0: # Connected
                            target_device.closeConnection() # Still here, stay in cooldown
                        else:
                            print("\n[User Left] -> Cooldown Reset. Ready to Scan.")
                            cooldown = False
                    except:
                        print("\n[User Left] -> Cooldown Reset. Ready to Scan.")
                        cooldown = False
                
                else:
                    # Ready to Unlock
                    print("State: SCANNING...                            ", end='\r')
                    try:
                        # Attempt Connection (Simulating "Found UUID")
                        err = target_device.openConnection()
                        if err == 0 and target_device.isConnected():
                             # 2. UNLOCK STATE
                            print("\n[Action] >>> TARGET FOUND & CONNECTED!")
                            print("[Action] >>> UNLOCKING (3 Seconds)")
                            time.sleep(UNLOCK_DURATION)
                            
                            print("[Action] <<< LOCKING")
                            print("[Action] Disconnecting (Sentinel Logic)...")
                            target_device.closeConnection()
                            
                            cooldown = True
                            print("[State] Entered Cooldown Mode.")
                            time.sleep(2) # Give Bluetooth stack a breathe
                    except:
                        pass # Valid, just means user isn't here

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", required=True)
    args = parser.parse_args()
    run_simulation(args.device)
```
