// Ghost Digital Lock - Presence Mode
// Logic: Unlocks and holds open while trusted device is near.

#include <Arduino.h>
#include <BLEAdvertisedDevice.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEUtils.h>
#include <vector>

// ================= USER CONFIGURATION =================

// Authorized Devices
std::vector<String> whitelist = {
    "12:34:56:78:9A:BC",
};

// RSSI Threshold (dBm)
// Must be stronger than this to be considered "Present"
const int RSSI_THRESHOLD = -75;

// Timing Configuration
const int RELAY_PIN = 4;
const unsigned long LOCK_TIMEOUT_MS =
    1000; // 1 Second of silence before locking

// ======================================================

// State Variables
unsigned long lastSeenTime = 0;
bool isUnlocked = false;

BLEScan *pBLEScan;

class MyAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    int rssi = advertisedDevice.getRSSI();

    // Filter weak signals immediately
    if (rssi < RSSI_THRESHOLD)
      return;

    String deviceMac = advertisedDevice.getAddress().toString();
    deviceMac.toUpperCase();

    for (const auto &trustedMac : whitelist) {
      if (deviceMac == trustedMac) {
        // Trusted device is HERE and STRONG.
        // Update the "Heartbeat" timestamp
        lastSeenTime = millis();

        Serial.print("Presence Detected: ");
        Serial.print(deviceMac);
        Serial.print(" [RSSI ");
        Serial.print(rssi);
        Serial.println("]");
        break;
      }
    }
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("\n=== Ghost Lock: Presence Mode ===");

  pinMode(RELAY_PIN, OUTPUT);
  // Default State: LOCKED
  digitalWrite(RELAY_PIN, LOW);

  BLEDevice::init("");
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(false);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {
  // 1. Run Scan (Heartbeat Check)
  // Scan for a short burst. Callbacks will update 'lastSeenTime' if user is
  // found.
  pBLEScan->start(0.5, false); // Scan for 500ms
  pBLEScan->clearResults();

  // 2. Logic Check
  unsigned long now = millis();
  bool userIsPresent = (now - lastSeenTime < LOCK_TIMEOUT_MS);

  // If system just started (lastSeenTime is 0), wait for first detection?
  // No, lock defaults to closed. If user appears, it opens.
  // One edge case: millis() wraps over 50 days, but acceptable for hobby.

  if (userIsPresent && lastSeenTime != 0) {
    // User is here. Ensure door is UNLOCKED.
    if (!isUnlocked) {
      Serial.println(">> OPENING DOOR (User Present)");
      digitalWrite(RELAY_PIN, HIGH);
      isUnlocked = true;
    }
  } else {
    // User is gone (Timeout expired). Ensure door is LOCKED.
    if (isUnlocked) {
      Serial.println("<< LOCKING DOOR (User Left)");
      digitalWrite(RELAY_PIN, LOW);
      isUnlocked = false;
    }
  }
}
