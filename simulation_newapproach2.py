import time
import sys
import argparse

# ================= SIMULATION CONFIGURATION =================
AUTO_LOCK_DELAY = 10  # Seconds to wait before locking after signal is lost
SCAN_INTERVAL = 2     # Seconds between scan attempts

def get_rssi_reading(device, retries=5):
    """
    Try HARD to get an RSSI reading from a connected device.
    macOS is notoriously bad at returning RSSI for Android devices 
    because they enter Bluetooth "Sniff Mode" to save power.
    
    We try multiple methods:
    1. rawRSSI() — the standard way
    2. RSSI() — sometimes returns a different value
    3. Poke the device with remoteNameRequest to wake the radio
    
    Returns: (rssi_value, method_used) or (None, None) if no reading.
    """
    for attempt in range(retries):
        try:
            # Poke the device to wake it from Sniff Mode
            try:
                device.remoteNameRequest_action_(None, None)
            except Exception:
                pass
            
            # Method 1: rawRSSI
            try:
                raw = device.rawRSSI()
                if raw != 127 and raw != 0 and raw < 0:
                    return (raw, "rawRSSI")
            except Exception:
                pass
            
            # Method 2: RSSI (different API, sometimes works when rawRSSI doesn't)
            try:
                rssi = device.RSSI()
                if rssi != 127 and rssi != 0 and rssi < 0:
                    return (rssi, "RSSI")
            except Exception:
                pass
                
        except Exception:
            pass
        time.sleep(0.3)  # Brief wait before retry
    
    return (None, None)


def run_simulation(device_address):
    import IOBluetooth
    
    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║     Ghost Lock v3: Hold-Open Mode Simulation    ║")
    print(f"╚══════════════════════════════════════════════════╝")
    print(f"Target: {device_address}")
    print(f"Auto-Lock Delay: {AUTO_LOCK_DELAY}s after device disconnects/leaves")
    print(f"Logic: Scan -> Connect -> Verify -> Disconnect -> HOLD OPEN -> Auto-Lock")
    print("-" * 55)

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

    device_name = target_device.name() or device_address
    print(f"Device Found: {device_name}")

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
    rssi_available = None  # None = unknown, True/False after first check

    try:
        while True:
            # --- STATE 1: LOCKED & SCANNING ---
            if current_state == SECURE_LOCKED:
                print(f"State: SECURE_LOCKED 🔒 - Scanning for {device_name}...            ", end='\r')
                
                # Try to connect
                was_already_connected = target_device.isConnected()
                if not was_already_connected:
                    try:
                        err = target_device.openConnection()
                        if err != 0:
                            time.sleep(SCAN_INTERVAL)
                            continue
                        # Wait for connection to fully establish
                        time.sleep(1.5)
                        if not target_device.isConnected():
                            time.sleep(SCAN_INTERVAL)
                            continue
                    except Exception:
                        time.sleep(SCAN_INTERVAL)
                        continue
                
                # We're connected! Try to get RSSI
                rssi, method = get_rssi_reading(target_device)
                
                if rssi is not None:
                    rssi_available = True
                    print(f"\n✓ Connected | RSSI: {rssi} dBm (via {method})")
                    print("Signal verified — Initiating Security Handshake...")
                    current_state = VERIFYING
                else:
                    # RSSI unavailable — this is NORMAL for most Android phones on macOS
                    if rssi_available is None:
                        print(f"\n⚠ RSSI unavailable (normal for Android). Using CONNECTION-BASED mode.")
                        rssi_available = False
                    
                    if target_device.isConnected():
                        # Device IS connected — treat connection as proof of presence
                        print(f"\n✓ Connected to {device_name} (Connection-Based Verification)")
                        current_state = VERIFYING
                    else:
                        time.sleep(SCAN_INTERVAL)
                        continue

            # --- STATE 2: VERIFICATION ---
            elif current_state == VERIFYING:
                print(f"Identity Verified. Unlocking... 🔓 [DOOR HELD OPEN]")
                
                # Disconnect to be stealthy
                print("Disconnecting (Stealth Mode)...")
                target_device.closeConnection()
                
                current_state = HOLD_OPEN_STEALTH
                last_seen_time = time.time()
                time.sleep(2)  # Give Bluetooth stack a breather

            # --- STATE 3: HOLD OPEN (Stealth Monitoring) ---
            elif current_state == HOLD_OPEN_STEALTH:
                time_since_last_seen = time.time() - last_seen_time
                remaining = max(0, AUTO_LOCK_DELAY - time_since_last_seen)
                print(f"State: HOLD_OPEN 🔓 | Last seen: {int(time_since_last_seen)}s ago | Lock in: {int(remaining)}s     ", end='\r')
                
                # Ping: try connecting to see if device is still nearby
                try:
                    err = target_device.openConnection()
                    if err == 0:
                        time.sleep(0.5)
                        if target_device.isConnected():
                            # Device is still here!
                            last_seen_time = time.time()
                        target_device.closeConnection()
                except Exception:
                    pass  # Device not seen

                # THE EXIT CHECK
                if time.time() - last_seen_time > AUTO_LOCK_DELAY:
                    print(f"\n🔒 User Left Range (> {AUTO_LOCK_DELAY}s). Auto-Locking. [DOOR LOCKED]")
                    current_state = SECURE_LOCKED
                
                time.sleep(SCAN_INTERVAL)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nSimulation Stopped.")
        if target_device and target_device.isConnected():
            target_device.closeConnection()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Ghost Lock v3 (NewApproch2.0.ino) on macOS")
    parser.add_argument("--device", required=True, help="MAC Address of the target Bluetooth device (e.g., 9c-82-81-8b-25-fc)")
    parser.add_argument("--timeout", type=int, default=10, help="Seconds before auto-locking after signal lost (default: 10)")
    args = parser.parse_args()
    
    AUTO_LOCK_DELAY = args.timeout
    run_simulation(args.device)
