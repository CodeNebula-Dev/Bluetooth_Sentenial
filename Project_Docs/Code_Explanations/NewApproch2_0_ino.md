# Explanation: `NewApproch2.0.ino`

## Purpose
`NewApproch2.0.ino` is the alternative **Hold-Open Mode** firmware. It is best suited for environments like private server rooms or personal workshops where the door should stay unlocked continuously as long as the authorized user is physically inside the room or sitting near the door.

## Hold-Open Logic State Diagram

```mermaid
graph TD
    A[Idle Bluetooth Scan] --> B{UUID Spotted?}
    B -->|No| A
    B -->|Yes| C{RSSI > Threshold?}
    
    C -->|No| A
    C -->|Yes| D[Trigger GPIO 4 HIGH]
    
    D --> E[Record Last Seen Timestamp]
    E --> F[Continuous Mini-Scans]
    
    F --> G{UUID Still Visible above Threshold?}
    G -->|Yes| E
    
    G -->|No| H{Has 10-Second Grace Period Expired?}
    H -->|No| F
    
    H -->|Yes| I[Trigger GPIO 4 LOW | LOCK ENGAGED]
    I --> A
```

## Detailed Analysis
- **Continuous Presence Detection**: Scans for the authorized UUID periodically without aggressively sleeping. 
- **Persistent Unlocking**: Instead of pulsing the relay and shutting it down, the code physically holds the relay coil energized (keeping `GPIO 4` at `HIGH`) as long as the phone's beacon is detected within the RSSI threshold.
- **Grace Period Engine**: Bluetooth signals are inherently noisy and bounce off walls, causing intermittent signal drops (Micro-drops). When the phone disappears for a split second, the lock **does not lock you out**. Instead, a **10-second timeout** begins. If the beacon reappears, the timer resets. If the timer hits exactly 10 seconds of pure silence, only then does the lock re-engage.
