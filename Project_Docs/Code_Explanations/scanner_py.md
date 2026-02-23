# Explanation: `scanner.py`

## Purpose
`scanner.py` is a Python utility used primarily during **Phase 1 (Software Simulation)** to discover and list all nearby Bluetooth devices.

## Logic & Flow
- **macOS Bluetooth API**: It uses the `PyObjC` framework (`IOBluetooth`) to interact natively with the Mac's Bluetooth hardware.
- **Device Iteration**: It scans for paired or recently seen devices, fetches their friendly names, MAC addresses, and connection statuses, and displays them via standard output.

## Role in the System
It bridges the gap for users to easily figure out the MAC address of their target smartphone, which is a required step before running the main simulation scripts.
