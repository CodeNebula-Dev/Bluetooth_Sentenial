# Explanation: `StealthLock.ino`

## Purpose
`StealthLock.ino` is the legacy, early version of the Ghost Lock firmware. 

## Logic & Flow
- **MAC-Based Verification**: The locking logic in this version relies primarily on recognizing the MAC address of an approaching Bluetooth device.
- **Lack of Handshake**: It does not establish a two-way BLE connection handshake to verify the cryptographic identity.

## Role in the System
It serves as a reference for how the lock evolved but is **deprecated** for security reasons. Modern features and the full security suite (preventing MAC spoofing and replay attacks) are only present in the `NewApproach` files.
