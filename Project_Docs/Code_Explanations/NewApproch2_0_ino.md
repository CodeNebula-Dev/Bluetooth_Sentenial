# Explanation: `NewApproch2.0.ino`

## Purpose
`NewApproch2.0.ino` is the alternative **Hold-Open Mode** firmware. It is best suited for environments like offices or workshops where the door should stay unlocked as long as the authorized user is physically inside the room.

## Logic & Flow
- **Continuous Presence Detection**: Scans for the authorized UUID periodically without aggressively sleeping.
- **Persistent Unlocking**: Instead of pulsing the relay, the code holds `GPIO 4` `HIGH` as long as the phone's beacon is detected within the RSSI threshold.
- **Grace Period (Timeout)**: Unlike the pulse logic, when the user walks out of range, the lock doesn't instantly engage to prevent lockouts on minor signal drops. Instead, a 10-second timeout begins. If the beacon is not seen again before the timer expires, the relay drops `LOW`.

## Role in the System
Provides an alternative usability profile for users who value presence-based seamless access without having to re-authenticate or rush through a door before it locks.
