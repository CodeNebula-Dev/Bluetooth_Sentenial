import time
import sys
import argparse
import threading

# ================= SIMULATION CONFIGURATION =================
RSSI_THRESHOLD = -70        
LOCK_TIMEOUT_MS = 5000   # 5 seconds grace period

def get_current_time_ms():
    return int(time.time() * 1000)

# --- REAL DEVICE LOGIC ---
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

    device_name = target_device.name() or device_address

    # Force cleaner start state
    if target_device.isConnected():
        print("Clearing stale connection state...")
        target_device.closeConnection()
        time.sleep(1.0)

    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║         Real Bluetooth Monitor Mode             ║")
    print(f"╚══════════════════════════════════════════════════╝")
    print(f"Target: {device_name}")
    print(f"Mode: Tries RSSI first, falls back to Connection-Based if RSSI unavailable")
    print("-" * 55)

    last_seen_time = 0
    is_unlocked = False
    last_connect_attempt = 0
    rssi_available = None  # None = unknown yet
    rssi_fail_count = 0

    try:
        while True:
            now = get_current_time_ms()
            connected = target_device.isConnected()
            current_rssi = -127 
            rssi_ok = False

            if not connected:
                # Try to reconnect every 2 seconds
                if now - last_connect_attempt > 2000:
                    try: target_device.openConnection()
                    except: pass
                    last_connect_attempt = now
            
            if target_device.isConnected():
                # Try to get RSSI
                try:
                    target_device.remoteNameRequest_action_(None, None)
                except Exception:
                    pass
                
                # Try rawRSSI
                try:
                    raw = target_device.rawRSSI()
                    if raw != 127 and raw != 0 and raw < 0:
                        current_rssi = raw
                        rssi_ok = True
                        rssi_available = True
                        rssi_fail_count = 0
                except: pass
                
                # Try RSSI() as fallback
                if not rssi_ok:
                    try:
                        alt = target_device.RSSI()
                        if alt != 127 and alt != 0 and alt < 0:
                            current_rssi = alt
                            rssi_ok = True
                            rssi_available = True
                            rssi_fail_count = 0
                    except: pass
                
                # If RSSI still unavailable — use connection as presence
                if not rssi_ok:
                    rssi_fail_count += 1
                    if rssi_fail_count > 20 and rssi_available is None:
                        # After ~2 seconds of failures, switch to connection mode
                        rssi_available = False
                        print(f"\n⚠ RSSI unavailable for {device_name}. Switching to CONNECTION-BASED mode.")
                    
                    if rssi_available == False:
                        # Connection = present. Treat as strong signal.
                        current_rssi = -40  # Fake "strong" RSSI to trigger unlock
                        rssi_ok = True
            
            # Logic
            now = get_current_time_ms()
            
            if rssi_ok and current_rssi >= RSSI_THRESHOLD:
                last_seen_time = now
            
            user_is_present = (now - last_seen_time < LOCK_TIMEOUT_MS)
            if last_seen_time == 0: user_is_present = False

            if user_is_present:
                if not is_unlocked:
                    print(f"\n[ACTION] >>> UNLOCKING 🔓")
                    is_unlocked = True
                rem = (LOCK_TIMEOUT_MS - (now - last_seen_time)) / 1000.0
                mode = "RSSI" if rssi_available else "CONN"
                if rssi_available == False:
                    print(f"State: UNLOCKED 🔓 | Mode: {mode} | Connected ✓ | Hold: {rem:.1f}s   ", end='\r')
                else:
                    print(f"State: UNLOCKED 🔓 | Signal: {current_rssi} dBm | Hold: {rem:.1f}s   ", end='\r')
            else:
                if is_unlocked:
                    print(f"\n[ACTION] <<< LOCKING 🔒")
                    is_unlocked = False
                if rssi_available == False:
                    conn_str = "Connected" if target_device.isConnected() else "Disconnected"
                    print(f"State: LOCKED 🔒  | Mode: CONN | {conn_str} | Waiting...       ", end='\r')
                else:
                    print(f"State: LOCKED 🔒  | Signal: {current_rssi} dBm | Waiting...       ", end='\r')
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nStopped.")

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
                    print(f"\n[ACTION] >>> UNLOCKING 🔓")
                    is_unlocked = True
                rem = (LOCK_TIMEOUT_MS - (now - last_seen_time)) / 1000.0
                print(f"State: UNLOCKED 🔓 | Signal: {current_rssi} dBm | Hold: {rem:.1f}s   ", end='\r')
            else:
                if is_unlocked:
                    print(f"\n[ACTION] <<< LOCKING 🔒")
                    is_unlocked = False
                print(f"State: LOCKED 🔒  | Signal: {current_rssi} dBm | Waiting...       ", end='\r')
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nStopped.")

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
