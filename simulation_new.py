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
