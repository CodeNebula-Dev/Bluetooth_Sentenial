# Mobile Test Guide: Validating the "Ghost Lock"

Since you have an old phone, you can use it to simulate the **ESP32's "Eyes"** (The Scanner).
This is the **best** way to find the perfect `RSSI_THRESHOLD` for your room before you build the real device.

## The Concepts
We have two ways to test. You cannot easily mix them (e.g. running script on Mac but using Phone as antenna). Pick the one that fits your goal:

### Test A: "Physics Check" (Best for Range)
*   **The Lock**: Your **Old Phone** (placed at the door).
*   **The Key**: Your **Main Phone**.
*   **The Brain**: Your Eyes (watching the graph).
*   **Goal**: Find the real-world signal strength (-dBm) at your door.

### Test B: "Logic Check" (Best for Code)
*   **The Lock**: Your **Mac** (sitting on desk).
*   **The Key**: Your **Main Phone** OR **Old Phone**.
*   **The Brain**: The Python Script (`simulation.py`).
*   **Goal**: Prove the code unlocks/locks effectively when signal changes.

---

## Method 1: The "Physics Check" (Using nRF Connect)
You don't need to write code. You need a "Scanner" app that shows raw numbers.
We recommend **nRF Connect for Mobile** (Free on Android & iOS).

1.  **Install** "nRF Connect" on your **Old Phone**.
2.  **Turn ON Bluetooth** on your **Main Phone** (The Key).
3.  Open nRF Connect on the Old Phone.

## Step 2: The "Graph" Test (The Visual Lock)
This tool has a "RSSI Graph" feature that mimics our Lock Logic.

1.  In nRF Connect, click **SCAN** (Top right).
2.  Look for your Main Phone (e.g., "iQOO 7").
    *   *Tip: Use the Filter bar to search for it so you only see your phone.*
3.  Tap on the **RSSI Graph** tab (or "Graph" icon).
    *   You will see a line chart moving in real-time.

## Step 3: Determining Your Thresholds
Now, act out the scenario:

1.  **"Present" (Unlocked)**:
    *   Place the Old Phone where the Lock will be (e.g., on the door handle).
    *   Stand where you typically sit/stand in the office.
    *   **Read the number**: Is it -60? -70?
    *   *Example: Let's say it hovers around -65 dBm.*

2.  **"Walking Away" (Locking)**:
    *   Walk out the door and go 5-10 meters away.
    *   Watch the line drop.
    *   **Read the number**: Is it -85? -90?
    *   *Example: It drops to -88 dBm.*

3.  **"Gone" (Disconnect)**:
    *   Walk far enough that the line stops or disappears.

## Step 4: Configuring the Firmware
Use your real data to tune the `StealthLock.ino` file.

*   If your "Inside" signal is **-65** and your "Outside" signal is **-85**:
*   Set the Threshold right in the middle: **-75**.

```cpp
// StealthLock.ino
const int RSSI_THRESHOLD = -75; // The "Sweet Spot"
```

## Why this is better than the Mac Simulation?
Your Old Phone has a dedicated Bluetooth radio and proper drivers (unlike the Mac, which was caching the value). This test gives you the **Physics Truth** of your environment. If it works here, it will work on the ESP32.

---

# Option B: Verify the Python Simulation (`simulation.py`)
If you want to test if the **Mac Script** works using your Old Phone (instead of your main phone):

1.  **Pair** the Old Phone to your Mac (System Settings -> Bluetooth).
2.  **Find its MAC Address**: 
    *   Run `python3 scanner.py` on your Mac.
    *   Look for the Old Phone's name. Copy its MAC.
3.  **Run the Simulation**:
    ```bash
    python3 simulation.py --device [OLD_PHONE_MAC]
    ```
4.  **The Test**:
    *   Leave the Mac on the table.
    *   Take the Old Phone and walk away (or turn off its Bluetooth).
    *   Verify the Mac screen says **[ACTION] <<< LOCKING**.
    *   Walk back (or turn on Bluetooth).
    *   Verify the Mac screen says **[ACTION] >>> UNLOCKING**.

This confirms the **Logic** (Disconnect = Lock) works with physical hardware.
