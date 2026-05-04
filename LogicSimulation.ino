/**
 * Ghost Lock v3.0 - LOGIC SIMULATION VIA SERIAL
 * 
 * Instructions:
 * 1. Run this in the Wokwi ESP32 Simulator.
 * 2. Open the "Serial Monitor" tab in Wokwi.
 * 3. Type the following commands to test the logic:
 *    - "near"  : Simulates your phone coming close (RSSI > Threshold).
 *    - "far"   : Simulates your phone moving away (RSSI Drops).
 *    - "spoof" : Simulates a fake phone trying to connect (Verification fails).
 */

#include <Arduino.h>

const int RELAY_PIN = 4;
const bool ACTIVE_STATE = HIGH; 

enum LockState { SECURE_LOCKED, VERIFYING, HOLD_OPEN_STEALTH };
LockState currentState = SECURE_LOCKED;
unsigned long lastSeenTime = 0;

// Auto-lock delay set to 10 seconds
const unsigned long AUTO_LOCK_DELAY = 10000;

bool isPhoneNear = false;

void setLockState(bool isOpen) {
  if (isOpen) {
    digitalWrite(RELAY_PIN, ACTIVE_STATE);
    Serial.println("  [DOOR UNLOCKED] - Relay HIGH");
  } else {
    digitalWrite(RELAY_PIN, !ACTIVE_STATE);
    Serial.println("  [DOOR LOCKED] - Relay LOW");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  
  Serial.println("\n=========================================");
  Serial.println("=== Ghost Lock v3 LOGIC SIMULATOR ===");
  Serial.println("=========================================");
  Serial.println("Commands:");
  Serial.println("  near  -> Walk up to the door");
  Serial.println("  far   -> Walk away from the door");
  Serial.println("  spoof -> Hacker tries to clone your UUID");
  Serial.println("=========================================\n");
  
  setLockState(false); 
}

void loop() {
  // --- Check Serial Inputs to Simulate BLE Events ---
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim(); // Remove whitespace/newlines
    
    if (cmd == "near") {
      isPhoneNear = true;
      if (currentState == SECURE_LOCKED) {
        Serial.println("\n>>> USER INPUT: 'near'");
        Serial.println("[BLE] Phone detected nearby! (RSSI strong)");
        currentState = VERIFYING;
      } else {
        Serial.println("\n>>> USER INPUT: 'near'");
        Serial.println("[BLE] Phone is still nearby (Heartbeat updated).");
      }
      lastSeenTime = millis();
    } 
    else if (cmd == "far") {
      Serial.println("\n>>> USER INPUT: 'far'");
      Serial.println("[BLE] Phone moved out of range (Signal lost).");
      isPhoneNear = false;
    }
    else if (cmd == "spoof") {
      Serial.println("\n>>> USER INPUT: 'spoof'");
      Serial.println("[BLE] Unknown device broadcasting your UUID!");
      if (currentState == SECURE_LOCKED) {
        currentState = VERIFYING;
        // Hack to make verification fail
        isPhoneNear = false; 
      }
    }
  }

  // --- STATE 2: VERIFICATION ---
  if (currentState == VERIFYING) {
    Serial.println("[LOGIC] Connecting to verify Identity Handshake...");
    delay(1000); // Simulate connection latency
    
    if (isPhoneNear) {
      Serial.println("[LOGIC] Identity Verified! You are authorized.");
      setLockState(true);
      Serial.println("[LOGIC] Disconnecting immediately (Stealth Mode Active).");
      currentState = HOLD_OPEN_STEALTH;
      lastSeenTime = millis();
    } else {
      Serial.println("[LOGIC] Verification Failed! (Could not establish secure connection)");
      Serial.println("[LOGIC] Remaining Locked.");
      currentState = SECURE_LOCKED;
    }
  }

  // --- STATE 3: HOLD OPEN (Stealth Monitoring) ---
  if (currentState == HOLD_OPEN_STEALTH) {
    // If phone is "near", we simulate receiving BLE advertisements continually
    if (isPhoneNear) {
       if (millis() - lastSeenTime > 1000) {
           lastSeenTime = millis();
       }
    }
    
    // The Exit Check: 10 seconds of no heartbeat
    if (millis() - lastSeenTime > AUTO_LOCK_DELAY) {
      Serial.println("\n[LOGIC] 10 Seconds passed without seeing User.");
      Serial.println("[LOGIC] Auto-Locking for security.");
      setLockState(false);
      currentState = SECURE_LOCKED;
    }
  }

  delay(50);
}
