/**
 * Ghost Lock v2 - Secure Connection Mode
 * Architecture: BLE Central (Client) using NimBLE
 *
 * LOGIC:
 * 1. Silent Scan: Looks for a specific SERVICE_UUID.
 * 2. Connect: Attempts to handshake with the phone.
 * 3. Sentinel: If connected (security check passed), Unlock for 3s.
 * 4. Disconnect: Drop connection.
 * 5. Cooldown: Wait for user to LEAVE (signal loss) before scanning again.
 */

#include <Arduino.h>
#include <NimBLEDevice.h>

// ================= USER CONFIGURATION =================

// The Service UUID your Phone is advertising
// Generate a new one here: https://www.uuidgenerator.net/
static NimBLEUUID serviceUUID("12345678-1234-1234-1234-1234567890ab");

// RSSI Threshold to attempt connection
const int RSSI_THRESHOLD = -75;

// Hardware Config
const int RELAY_PIN = 4;
const int UNLOCK_TIME_MS = 3000;

// ======================================================

NimBLEScan *pBLEScan;
NimBLEClient *pClient;

// State Machine
enum LockState { SCAN_FOR_TRIGGER, COOLDOWN_WAIT_FOR_EXIT };
LockState currentState = SCAN_FOR_TRIGGER;
unsigned long lastSeenTime = 0;

void pulseRelay() {
  Serial.println(">>> SECURE UNLOCK (3s)");
  digitalWrite(RELAY_PIN, HIGH);
  delay(UNLOCK_TIME_MS);
  digitalWrite(RELAY_PIN, LOW);
  Serial.println("<<< LOCKED");
}

class MyAdvertisedDeviceCallbacks : public NimBLEAdvertisedDeviceCallbacks {
  void onResult(NimBLEAdvertisedDevice *advertisedDevice) {
    // Filter weak signals
    if (advertisedDevice.getRSSI() < RSSI_THRESHOLD)
      return;

    // Check for our Target
    if (advertisedDevice.isAdvertisingService(serviceUUID)) {
      // Update Heartbeat
      lastSeenTime = millis();

      // LOGIC SPLIT
      if (currentState == SCAN_FOR_TRIGGER) {
        Serial.print("Target Found: ");
        Serial.println(advertisedDevice.toString().c_str());

        // Stop scan to connect
        NimBLEDevice::getScan()->stop();

        pClient = NimBLEDevice::createClient();
        if (pClient->connect(advertisedDevice)) {
          if (pClient->isConnected()) {
            pulseRelay(); // UNLOCK
            pClient->disconnect();

            // Switch to COOLDOWN
            currentState = COOLDOWN_WAIT_FOR_EXIT;
            Serial.println(
                "[State] Entering Cooldown. Waiting for user to leave...");
          }
        } else {
          Serial.println("Connection Failed.");
        }
      } else if (currentState == COOLDOWN_WAIT_FOR_EXIT) {
        // We are in cooldown, and we just saw the user.
        // Reset the "User Left" timer implicitly by updating lastSeenTime.
        Serial.print("."); // Heartbeat print
      }
    }
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("\n=== Ghost Lock v2: Secure Sentinel ===");

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  NimBLEDevice::init("");

  pBLEScan = NimBLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(false);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {
  // Continuous Scanning logic
  if (!pBLEScan->isScanning()) {
    pBLEScan->start(1, false); // Short 1s scans
  }

  // Cooldown Logic: Check if user has left
  if (currentState == COOLDOWN_WAIT_FOR_EXIT) {
    // If we haven't seen the user for 5 seconds...
    if (millis() - lastSeenTime > 5000) {
      Serial.println("\n[User Left] -> Cooldown Reset. Ready to Scan.");
      currentState = SCAN_FOR_TRIGGER;
    }
  }

  delay(10);
}
