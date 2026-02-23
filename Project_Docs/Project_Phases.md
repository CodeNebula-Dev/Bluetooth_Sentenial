# Project Phases

The **Ghost Lock** project is divided into two primary phases: Simulation and Hardware Deployment.

## Phase 1: Software Simulation (macOS)
Before committing to hardware components, the project focuses on software simulation on macOS using the built-in Bluetooth hardware.

### Objectives
- **Device Discovery**: Write scripts (e.g., `scanner.py`) to discover and identify the MAC address of the target smartphone.
- **Connection Logic Simulation**: Simulate the locking and unlocking mechanism (via `simulation_new.py` or `simulation.py`) by checking for the target device's presence and simulating a BLE handshake.
- **Cooldown Logic**: Implement state machines that prevent the lock from repeatedly triggering when the user is hovering at the edge of the detection limit (cooldown mode).

## Phase 2: Hardware Implementation (ESP32)
Once the logic is validated in the software simulation, the project moves to actual physical deployment using an ESP32 microcontroller, a 5V relay, and a 12V solenoid lock.

### Objectives
- **Firmware Flashing**: Upload optimized C++ code (`NewApproach.ino`, `NewApproch2.0.ino`) using the Arduino IDE.
- **Hardware Integration**: Wire the ESP32 to a 5V relay module that correctly switches the 12V power supply for the physical lock terminal.
- **Deployment & Calibration**: Mount the module, set the correct RSSI threshold calibration for the space, and perform real-world anti-spoofing tests.
