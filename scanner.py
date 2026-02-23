import time
import sys
import Cocoa
import IOBluetooth

def scan_devices():
    print("Scanning for paired/known Bluetooth devices...")
    print("Note: This script finds devices that your Mac already knows about (paired).")
    print("-" * 60)
    print(f"{'Name':<30} | {'MAC Address':<20} | {'RSSI':<10} | {'Connected'}")
    print("-" * 60)

    devices = IOBluetooth.IOBluetoothDevice.pairedDevices()

    if not devices:
        print("No paired devices found using IOBluetooth.")
        return

    found_any = False
    
    for device in devices:
        name = device.name() or "Unknown"
        address = device.addressString()
        is_connected = device.isConnected()
        
        rssi = "N/A"
        if is_connected:
            raw_rssi = device.rawRSSI()
            if raw_rssi == 127:
                rssi = "N/A"
            else:
                rssi = str(raw_rssi)

        print(f"{name:<30} | {address:<20} | {rssi:<10} | {is_connected}")
        found_any = True

    print("-" * 60)
    print("Tip: If RSSI is 'N/A', make sure the device is CONNECTED to this Mac.")

if __name__ == "__main__":
    scan_devices()
