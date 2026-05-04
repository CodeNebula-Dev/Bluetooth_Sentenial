/**
 * Ghost Lock v3.0 - "Hold Open" Mode
 * Logic:
 * 1. Scan -> Connect -> Verify User (Security Check).
 * 2. Disconnect immediately (Stealth).
 * 3. KEEP RELAY HIGH (Door Unlocked) while user is detected.
 * 4. Lock ONLY when user is missing for >10 seconds.
 */

#include <Arduino.h>
#include <NimBLEDevice.h>
#include <vector>

// ================= USER CONFIGURATION =================

// 1. Authorized Users (Service UUIDs)
// Add a unique UUID for each person you want to give access to.
std::vector<NimBLEUUID> authorizedUUIDs = {
    NimBLEUUID("12345678-1234-1234-1234-1234567890ab"), // User 1 (Alice)
    NimBLEUUID("87654321-4321-4321-4321-ba0987654321")  // User 2 (Bob)
};

// 2. Signal Threshold (How close to UNLOCK)
const int RSSI_UNLOCK_THRESHOLD = -75;

// 3. Hardware Config
const int RELAY_PIN = 4;
// WARNING: Ensure your lock is rated for CONTINUOUS DUTY before using true!
const bool ACTIVE_STATE =
    HIGH; // Set to LOW if using a Relay Module that triggers on Low

// ======================================================

NimBLEScan *pBLEScan;
NimBLEClient *pClient;
bool deviceFound = false;
const NimBLEAdvertisedDevice *targetDevice;

enum LockState { SECURE_LOCKED, VERIFYING, HOLD_OPEN_STEALTH };
LockState currentState = SECURE_LOCKED;
unsigned long lastSeenTime = 0;

// Time to wait before locking after signal is lost (e.g., 10 seconds)
const unsigned long AUTO_LOCK_DELAY = 10000;

class MyAdvertisedDeviceCallbacks : public NimBLEScanCallbacks {
  void onResult(const NimBLEAdvertisedDevice *advertisedDevice) override {
    bool isAuthorized = false;
    for (int i = 0; i < authorizedUUIDs.size(); i++) {
      if (advertisedDevice->isAdvertisingService(authorizedUUIDs[i])) {
        isAuthorized = true;
        break;
      }
    }

    if (isAuthorized) {

      // Update Heartbeat (We see you!)
      lastSeenTime = millis();

      // LOGIC: If we are already holding open, just keep the timer updated.
      // If we are Locked, we need to check RSSI before verifying.
      if (currentState == SECURE_LOCKED) {
        if (advertisedDevice->getRSSI() > RSSI_UNLOCK_THRESHOLD) {
          // Signal is strong enough -> Initiate Verification
          Serial.println("Target in Range. Initiating Security Handshake...");
          targetDevice = advertisedDevice;
          deviceFound = true;
          NimBLEDevice::getScan()->stop();
        }
      }
    }
  }
};

void setLockState(bool isOpen) {
  if (isOpen) {
    digitalWrite(RELAY_PIN, ACTIVE_STATE);
    // Serial.println(" [DOOR HELD OPEN] ");
  } else {
    digitalWrite(RELAY_PIN, !ACTIVE_STATE);
    Serial.println(" [DOOR LOCKED] ");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n=== Ghost Lock v3: Hold-Open Mode ===");

  pinMode(RELAY_PIN, OUTPUT);
  setLockState(false); // Start Locked

  NimBLEDevice::init("");
  pBLEScan = NimBLEDevice::getScan();
  pBLEScan->setScanCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(false);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {

  // --- STATE 1: LOCKED & SCANNING ---
  if (currentState == SECURE_LOCKED) {
    if (deviceFound) {
      currentState = VERIFYING; // Found a candidate, go to verify
    } else if (!pBLEScan->isScanning()) {
      pBLEScan->start(1, false); // Scan for 1 second
    }
  }

  // --- STATE 2: VERIFICATION (The "Sentinel" Check) ---
  if (currentState == VERIFYING) {
    pClient = NimBLEDevice::createClient();

    // Connect to verify it's really you (Anti-Spoofing)
    if (pClient->connect(targetDevice)) {
      Serial.println("Identity Verified. Unlocking...");

      // UNLOCK THE DOOR
      setLockState(true);

      // Disconnect immediately to be Stealthy
      pClient->disconnect();

      currentState = HOLD_OPEN_STEALTH;
      lastSeenTime = millis(); // Reset timer
    } else {
      Serial.println("Verification Failed (Spoof attempt?). Remaining Locked.");
      currentState = SECURE_LOCKED;
    }

    NimBLEDevice::deleteClient(pClient); // Free memory
    deviceFound = false;
  }

  // --- STATE 3: HOLD OPEN (Stealth Monitoring) ---
  if (currentState == HOLD_OPEN_STEALTH) {
    // We are disconnected, but the Door is UNLOCKED.
    // We just keep scanning to make sure you are still nearby.

    if (!pBLEScan->isScanning()) {
      pBLEScan->start(1, false);
    }

    // THE EXIT CHECK
    // If we haven't seen your UUID for 10 seconds...
    if (millis() - lastSeenTime > AUTO_LOCK_DELAY) {
      Serial.println("User Left Range. Auto-Locking.");
      setLockState(false); // LOCK THE DOOR
      currentState = SECURE_LOCKED;
    }
  }

  delay(20);
}