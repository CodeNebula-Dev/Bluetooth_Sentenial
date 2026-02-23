# Explanation: `NewApproach.ino`

## Purpose
`NewApproach.ino` represents the primary **Pulse Mode** firmware for the ESP32 microcontroller in the Ghost Lock system. It's meant for situations where a brief, timed unlock is desired (e.g., a standard front door strike).

## Logic & Flow
- **BLE Server & Scanning**: Uses the `NimBLE` library, which is a lightweight alternative to the standard Arduino BLE library, to minimize memory usage and maximize connection reliability.
- **Whitelist Initialization**: Advertises the expected service UUID (the user's phone). It filters out all other Bluetooth traffic.
- **Handshake Enforcement**: Instead of just relying on the MAC address, the ESP32 briefly attempts to connect to the broadcasting device to verify its authenticity before unlocking.
- **Triggering Relay**: If authenticated and within the proper RSSI range, it sets the designated digital pin (`GPIO 4` by default) `HIGH` for a set duration (e.g., 3 seconds) before locking it back (`LOW`).
- **Cooldown**: Prevents retriggering indefinitely by requiring the phone UUID to disappear from the scan results for a set time limit before resetting to idle.

## Role in the System
It's the production-ready code that actually resides on the hardware acting directly with the electronic door strike.
