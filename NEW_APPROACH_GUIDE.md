# New Approach Guide: Turning your Phone into a Key

For the **Secure Connection** method (`NewApproach.ino`), your phone must broadcast a specific **Service UUID**. 
This makes your phone act like a Beacon that the ESP32 searches for.

## 1. Get the App
Download **nRF Connect for Mobile** (Free).
- [Android Play Store](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp)
- [iOS App Store](https://apps.apple.com/us/app/nrf-connect-for-mobile/id1054362403)

## 2. Generate Your Secret Key (UUID)
You need a unique ID.
1.  Go to [uuidgenerator.net](https://www.uuidgenerator.net/)
2.  Copy the Version 4 UUID. 
    *   *Example: `12345678-1234-1234-1234-1234567890ab`*
3.  **Paste this into your Firmware** (`NewApproach.ino` line 24).

## 3. Set Up the "Advertiser" (The Beacon)
Open **nRF Connect** on your phone.

### Android
1.  Tap **ADVERTISER** tab.
2.  Tap **+** to add a new packet.
3.  **Display Name**: "MyDigitalKey"
4.  **Add Record** -> **Service UUID**.
5.  Paste your UUID here.
6.  Save & Switch the slider to **ON**.

### iOS
1.  Tap **Advertiser** tab.
2.  Tap **+**.
3.  Name: "MyDigitalKey".
4.  Tap **Add Service**.
5.  Paste your UUID.
6.  Save & Toggle **Switch ON**.

## 4. How it Works
1.  Your phone is now silently shouting *"I am Service 1234..."*.
2.  The ESP32 is listening specifically for that ID.
3.  When you walk up, ESP32 sees it -> Connects -> Unlocks.
4.  The ESP32 immediately disconnects to reset security.
