# Project Phases

The **Ghost Lock** project is divided into two primary phases: Simulation and Hardware Deployment. This approach ensures all logic and anti-spoofing techniques are verified before involving physical electronics.

## Phase 1: Software Simulation (macOS)
Before committing to hardware components, the project focuses on software simulation on macOS using the built-in Bluetooth hardware.

### Objective Flow

```mermaid
sequenceDiagram
    participant User as Developer
    participant scan as scanner.py
    participant sim as simulation_new.py
    participant phone as Phone
    
    User->>scan: Run script
    scan->>scan: Inspect paired devices via PyObjC
    scan-->>User: Outputs Phone MAC Address
    User->>sim: Run with --device <MAC>
    
    loop Every Second
        sim->>phone: Check presence/connection
        alt User approaches (RSSI climbs)
            sim->>sim: Simulated UNLOCK!
        else User Leaves
            sim->>sim: Simulated LOCK!
        end
    end
```

### Key Milestones
- **Device Discovery**: Discover and identify the MAC.
- **Connection Logic Simulation**: Simulate locking and unlocking mechanisms checking for presence.
- **Cooldown Logic validation**: Observe edge cases in software before real hardware test.

---

## Phase 2: Hardware Implementation (ESP32)
The validated logic is ported to C++ to run on a cheap, power-efficient ESP32 microcontroller mapping software states to GPIO pins.

### Hardware Control Flow

```mermaid
graph LR
    A[ESP32 NimBLE Scanner] --> B{Phone Found?}
    B -->|Yes| C[Verify Handshake]
    B -->|No| A
    C -->|Pass| D[Set GPIO PIN HIGH]
    C -->|Fail| A
    
    subgraph Physical World
    D --> E[5V Relay Module Energizes]
    E --> F[12V Power connected to Solenoid]
    F --> G[Door Unlocks]
    end
```

### Key Milestones
- **Firmware Flashing**: Upload optimized C++ code (`NewApproach.ino`, `NewApproch2.0.ino`).
- **Hardware Integration**: Wire ESP32 to Relay and Relay to Solenoid Lock.
- **Deployment**: Final field tests.
