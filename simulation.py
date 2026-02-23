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
