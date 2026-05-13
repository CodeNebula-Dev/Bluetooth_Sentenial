import time
import sys
import argparse

# ================= SIMULATION CONFIGURATION =================
UNLOCK_DURATION = 3  # Seconds to hold lock open
SCAN_INTERVAL = 2

def get_rssi_reading(device, retries=5):
    """Try multiple methods to get RSSI. Returns (rssi, method) or (None, None)."""
    for attempt in range(retries):
        try:
            try:
                device.remoteNameRequest_action_(None, None)
            except Exception:
                pass
            try:
                raw = device.rawRSSI()
                if raw != 127 and raw != 0 and raw < 0:
                    return (raw, "rawRSSI")
            except Exception:
                pass
            try:
                rssi = device.RSSI()
                if rssi != 127 and rssi != 0 and rssi < 0:
                    return (rssi, "RSSI")
            except Exception:
                pass
        except Exception:
            pass
        time.sleep(0.3)
    return (None, None)

def run_simulation(device_address):
    import IOBluetooth
    
    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║        Secure Pulse Mode Simulation             ║")
    print(f"╚══════════════════════════════════════════════════╝")
    print(f"Target: {device_address}")
    print(f"Logic: Scan -> Connect -> Verify -> Unlock({UNLOCK_DURATION}s) -> Disconnect -> Cooldown")
    print("-" * 55)

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

    device_name = target_device.name() or device_address
    print(f"Device Found: {device_name}")

    # Force clean start
    if target_device.isConnected():
        print("Initial Cleanup: Disconnecting...")
        target_device.closeConnection()
        time.sleep(1)

    cooldown = False
    rssi_available = None

    try:
        while True:
            if not target_device.isConnected():
                if cooldown:
                    # COOLDOWN: Wait for user to LEAVE before allowing next unlock
                    print("State: COOLDOWN ⏸ (Waiting for user to leave...)       ", end='\r')
                    time.sleep(SCAN_INTERVAL)
                    try:
                        err = target_device.openConnection()
                        if err == 0 and target_device.isConnected():
                            # Still connected — user hasn't left yet
                            target_device.closeConnection()
                        else:
                            # Can't connect — user left!
                            print(f"\n[User Left] -> Cooldown Reset. Ready to Scan.")
                            cooldown = False
                    except:
                        print(f"\n[User Left] -> Cooldown Reset. Ready to Scan.")
                        cooldown = False
                
                else:
                    # SCANNING: Look for device
                    print("State: SCANNING 🔍 ...                            ", end='\r')
                    try:
                        err = target_device.openConnection()
                        if err == 0 and target_device.isConnected():
                            # Connected! Verify proximity
                            time.sleep(1.0)
                            rssi, method = get_rssi_reading(target_device)
                            
                            if rssi is not None:
                                rssi_available = True
                                print(f"\n✓ Connected | RSSI: {rssi} dBm (via {method})")
                            else:
                                if rssi_available is None:
                                    print(f"\n⚠ RSSI unavailable (normal for Android). Using CONNECTION mode.")
                                    rssi_available = False
                                
                                if target_device.isConnected():
                                    print(f"\n✓ Connected to {device_name} (Connection-Based)")
                                else:
                                    time.sleep(SCAN_INTERVAL)
                                    continue
                            
                            # UNLOCK
                            print(f"[Action] >>> TARGET FOUND & VERIFIED!")
                            print(f"[Action] >>> UNLOCKING 🔓 ({UNLOCK_DURATION} Seconds)")
                            time.sleep(UNLOCK_DURATION)
                            
                            print("[Action] <<< LOCKING 🔒")
                            print("[Action] Disconnecting (Sentinel Logic)...")
                            target_device.closeConnection()
                            
                            cooldown = True
                            print("[State] Entered Cooldown Mode.")
                            time.sleep(2)
                    except:
                        pass  # User isn't here

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\nStopped.")
        if target_device and target_device.isConnected():
            target_device.closeConnection()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Secure Pulse Bluetooth Simulation")
    parser.add_argument("--device", required=True, help="MAC Address of Bluetooth device")
    args = parser.parse_args()
    run_simulation(args.device)
