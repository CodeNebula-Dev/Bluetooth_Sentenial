# Comprehensive Project Documentation Bundle & Architectural Overview

Welcome to the **Ghost Lock - Stealth BLE Proximity Lock System**.

This `README.md` serves as the central hub for the project code analysis, architectural ideas, security logic flows, and overall documentation. The goal of this project is to build an invisible Bluetooth proximity lock that unlocks automatically when an authorized user's phone approaches and locks upon departure.

## The Idea & Core Analysis

### Why "Ghost Lock"?
Traditional smart locks are inherently visible; they advertise their BLE or WiFi networks, inviting scanners and potential attacks ("Here I am, try to pick my digital lock!"). 
**Ghost Lock flips this dynamic.** 
The lock itself acts as a **passive listener** (BLE Central Client), waiting in stealth mode for your smartphone to broadcast a specific, secret UUID. Because the lock doesn't advertise, it's virtually invisible to wardriving scanners. 

### Security & Anti-Spoofing
A classic vulnerability in proximity systems is "MAC Spoofing" – an attacker intercepts your phone's MAC address and clones it. We solve this through the **Sentinel Verification Handshake**:
1. The lock sees the MAC that claims to have the secret UUID.
2. The lock *challenges* the beacon by attempting to establish a full BLE connection.
3. If the connection drops or fails instantly (because a spoofer only copied the broadcast, not the actual cryptographic stack), the lock refuses to open.

## Overarching Project Logic Flow

Below is the abstract visual representation of the Ghost Lock architecture, connecting the physical layer, the firmware/software layer, and the access flow.

```mermaid
graph TD
    A([User Phone - BLE Broadcaster]) -.->|Broadcasts Secret UUID & MAC| B(Ghost Lock Listener)
    
    subgraph Software OR Hardware
    B --> C{Is UUID matched?}
    C -->|No| D[Ignore Device]
    C -->|Yes| E{Is RSSI > Threshold?}
    E -->|No| F[Ignore / Wait]
    E -->|Yes| G[Initiate Handshake Connection]
    
    G --> H{Connection Successful?}
    H -->|No: Clone Detected!| I[Lock Remains Closed - Abort]
    H -->|Yes: Genuine Identity| J[Unlock Command Issued]
    end
    
    subgraph Action
    J --> K[Trigger Lock UI / Physical Relay]
    K --> L[Wait For Timeout / Presence Lost]
    L --> M[Lock Door & Enter Cooldown]
    end
```

## How to use this folder

- **`Project_Phases.md`**: Outlines the simulation and hardware phases of the Ghost Lock project, heavily annotated with state machine diagrams.
- **`Code_Explanations/`**: Contains deeply analyzed markdown files for every important source file, complete with Logic Flow diagrams and the raw inline source code. 

## Folder Structure Summary

```mermaid
mindmap
  root((Ghost Lock Docs))
    Phases
      Phase 1: Mac Simulation
      Phase 2: ESP32 Hardware
    Python Scripts
      main.py
      scanner.py
      simulation.py
      simulation_new.py
    C++ Firmware
      NewApproach.ino
      NewApproch2.0.ino
      StealthLock.ino
```

Dive into the other files in this directory to see exact execution flows for every file!
