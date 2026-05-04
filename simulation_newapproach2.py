import time
import sys
import argparse
import time

# ================= SIMULATION CONFIGURATION =================
AUTO_LOCK_DELAY = 10 # Seconds to wait before locking after signal is lost

def get_current_time_ms():
    return int(time.time() * 1000)

def run_simulation(device_address):
    import IOBluetooth
    
    print(f"=== Ghost Lock v3: Hold-Open Mode Simulation ===")
    print(f"Target: {device_address}")
    print("Logic: Scan -> Connect -> Verify -> Disconnect -> HOLD OPEN -> Auto-Lock (10s)")
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
        print(f"Error: Device {device_address} not found. Pair it first on this Mac.")
        sys.exit(1)

    # Force clean start
    if target_device.isConnected():
        print("Initial Cleanup: Disconnecting...")
        target_device.closeConnection()
        time.sleep(1)

    # State Machine
    SECURE_LOCKED = 0
    VERIFYING = 1
    HOLD_OPEN_STEALTH = 2

    current_state = SECURE_LOCKED
    last_seen_time = 0

    try:
        while True:
            # --- STATE 1: LOCKED & SCANNING ---
            if current_state == SECURE_LOCKED:
                print("State: SECURE_LOCKED - Scanning...                            ", end='\r')
                
                # Try to connect as a proxy for RSSI check / discovery
                try:
                    err = target_device.openConnection()
                    if err == 0 and target_device.isConnected():
                        print("\nTarget in Range. Initiating Security Handshake...")
                        current_state = VERIFYING
                    else:
                        time.sleep(1) # simulate scan interval
                except Exception as e:
                     time.sleep(1) # simulate scan interval

            # --- STATE 2: VERIFICATION (The "Sentinel" Check) ---
            elif current_state == VERIFYING:
                # In this sim, if we made it here, connection was successful
                print("Identity Verified. Unlocking... [DOOR HELD OPEN]")
                
                # Disconnect immediately to be Stealthy
                print("Disconnecting (Stealth Mode)...")
                target_device.closeConnection()
                
                current_state = HOLD_OPEN_STEALTH
                last_seen_time = time.time() # seconds
                time.sleep(2) # Give Bluetooth stack a breather

            # --- STATE 3: HOLD OPEN (Stealth Monitoring) ---
            elif current_state == HOLD_OPEN_STEALTH:
                time_since_last_seen = time.time() - last_seen_time
                print(f"State: HOLD_OPEN_STEALTH - Monitoring... (Last seen: {int(time_since_last_seen)}s ago)", end='\r')
                
                # Try connecting to see if device is still around
                try:
                    err = target_device.openConnection()
                    if err == 0:
                        # Device is still here! Update heartbeat.
                        last_seen_time = time.time()
                        target_device.closeConnection() # Disconnect to remain stealthy
                    else:
                        pass # Device not seen this ping
                except Exception as e:
                    pass # Device not seen this ping

                # THE EXIT CHECK
                if time.time() - last_seen_time > AUTO_LOCK_DELAY:
                    print(f"\nUser Left Range (> {AUTO_LOCK_DELAY}s). Auto-Locking. [DOOR LOCKED]")
                    current_state = SECURE_LOCKED
                
                time.sleep(1) # Poll every 1 second

            time.sleep(0.1) # Tiny sleep for CPU

    except KeyboardInterrupt:
        print("\nSimulation Stopped.")
        if target_device and target_device.isConnected():
            target_device.closeConnection()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Ghost Lock v3 (NewApproch2.0.ino) on macOS")
    parser.add_argument("--device", required=True, help="MAC Address of the target Bluetooth device (e.g., AA:BB:CC:DD:EE:FF)")
    args = parser.parse_args()
    run_simulation(args.device)
