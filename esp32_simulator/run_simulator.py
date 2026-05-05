#!/usr/bin/env python3
"""
Ghost Lock ESP32 Simulator

This simulates the *observable behavior* of the ESP32 firmware:
- BLE scanning callbacks
- connect/handshake verification success/failure (spoof vs real)
- relay output timing and door locked/unlocked state

It is not a CPU emulator; it models the firmware state machines closely enough
for hardware-style testing of thresholds, timers, and edge cases.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


DEFAULT_SERVICE_UUID = "12345678-1234-1234-1234-1234567890ab"


def now_wall_s() -> float:
    return time.time()


class SerialPrinter:
    """Mimic Arduino Serial prints (with simulated time prefix)."""

    def __init__(self, get_now_ms: Callable[[], int], out_stream=sys.stdout):
        self._get_now_ms = get_now_ms
        self._out = out_stream
        self._lock = threading.Lock()

    def println(self, msg: str) -> None:
        with self._lock:
            t_ms = self._get_now_ms()
            t_s = t_ms / 1000.0
            self._out.write(f"[{t_s:8.3f}s] {msg}\n")
            self._out.flush()


@dataclass
class AdvertisedDevice:
    service_uuid: str
    rssi: int
    phone_id: str
    genuine: bool

    def isAdvertisingService(self, uuid: str) -> bool:
        return self.service_uuid.lower() == uuid.lower()

    def getRSSI(self) -> int:
        return self.rssi


@dataclass
class SimPhone:
    phone_id: str
    service_uuid: str
    advertising: bool = False
    genuine: bool = True
    distance_m: float = 12.0
    manual_rssi: Optional[int] = None

    # These defaults are chosen so:
    # - near (2m) gives rssi around -61 to -65
    # - far (12m) gives rssi around -78 to -84
    rssi_near_distance_m: float = 2.0
    rssi_far_distance_m: float = 12.0

    def set_near(self) -> None:
        self.distance_m = self.rssi_near_distance_m
        self.manual_rssi = None

    def set_far(self) -> None:
        self.distance_m = self.rssi_far_distance_m
        self.manual_rssi = None

    def set_rssi(self, rssi: int) -> None:
        self.manual_rssi = int(rssi)

    def rssi_value(self) -> int:
        if self.manual_rssi is not None:
            return int(self.manual_rssi)

        # Simple log-distance style mapping (deterministic; add noise if desired).
        # rssi = base + (-20*log10(distance)) scaled.
        base = -55.0  # at 1m approx
        rssi = base - (20.0 * math.log10(max(self.distance_m, 0.1)))
        # Clamp to typical BLE-ish range
        rssi = max(-110.0, min(-35.0, rssi))
        return int(round(rssi))

    def advertise(self) -> Optional[AdvertisedDevice]:
        if not self.advertising:
            return None
        return AdvertisedDevice(
            service_uuid=self.service_uuid,
            rssi=self.rssi_value(),
            phone_id=self.phone_id,
            genuine=self.genuine,
        )


class FakeBleEnvironment:
    def __init__(self, phones: List[SimPhone]):
        self._phones = {p.phone_id: p for p in phones}

    def phone(self, phone_id: str) -> SimPhone:
        return self._phones[phone_id]

    def advertisements(self) -> List[AdvertisedDevice]:
        ads: List[AdvertisedDevice] = []
        for p in self._phones.values():
            dev = p.advertise()
            if dev is not None:
                ads.append(dev)
        return ads


class FakeScanner:
    """
    Models NimBLEScan start/stop behavior at a coarse level:
    - when started, it's scanning for `duration_ms`
    - during that window, we deliver advertisement callbacks
    """

    def __init__(self, printer: SerialPrinter):
        self._printer = printer
        self._cb: Optional[Callable[[AdvertisedDevice, int], None]] = None
        self._scanning_until_ms: int = 0

    def set_callbacks(self, cb: Callable[[AdvertisedDevice, int], None]) -> None:
        self._cb = cb

    def is_scanning(self, now_ms: int) -> bool:
        return now_ms < self._scanning_until_ms

    def start(self, duration_ms: int, now_ms: int) -> None:
        # In firmware: pBLEScan->start(1, false) (duration in seconds in API).
        # Here we accept duration_ms directly.
        self._scanning_until_ms = now_ms + duration_ms
        self._printer.println(f"Scanning started for {duration_ms}ms")

    def stop(self, now_ms: int) -> None:
        if self.is_scanning(now_ms):
            self._printer.println("Scanning stopped")
        self._scanning_until_ms = now_ms

    def deliver(self, ads: List[AdvertisedDevice], now_ms: int) -> None:
        if not self.is_scanning(now_ms):
            return
        if self._cb is None:
            return
        # Deliver all matching advertisements (firmware callbacks may be bursty).
        for ad in ads:
            self._cb(ad, now_ms)


class FakeBleClient:
    def __init__(self, printer: SerialPrinter):
        self._printer = printer
        self._connected: bool = False
        self._target: Optional[AdvertisedDevice] = None

    def connect(self, target: AdvertisedDevice) -> bool:
        # “Handshake” succeeds only for genuine devices in this simulator.
        self._connected = bool(target.genuine)
        self._target = target
        return self._connected

    def isConnected(self) -> bool:
        return self._connected

    def disconnect(self) -> None:
        if self._connected:
            self._printer.println("BLE disconnected (stealth)")
        self._connected = False
        self._target = None


class RelaySim:
    def __init__(self, printer: SerialPrinter, active_state_high: bool = True):
        self._printer = printer
        self._active_state = True if active_state_high else False
        self.input_pin_value: bool = False
        self.door_unlocked: bool = False

    def set_active_state_high(self, active_state_high: bool) -> None:
        self._active_state = True if active_state_high else False

    def digitalWrite_relay_in(self, value: bool, now_ms: int) -> None:
        self.input_pin_value = bool(value)
        unlocked = self.input_pin_value == self._active_state
        if unlocked != self.door_unlocked:
            self.door_unlocked = unlocked
            self._printer.println(
                " [DOOR UNLOCKED]" if self.door_unlocked else " [DOOR LOCKED]"
            )


class PulseFirmware:
    """
    Mirrors `NewApproach.ino` (Pulse mode).
    - relay HIGH for UNLOCK_TIME_MS on handshake success
    - then LOW
    - cooldown ends after 5000ms without seen target
    """

    def __init__(
        self,
        printer: SerialPrinter,
        scanner: FakeScanner,
        relay: RelaySim,
        authorized_uuids: List[str],
        rssi_threshold: int,
        unlock_time_ms: int,
        cooldown_wait_ms: int,
    ):
        self._printer = printer
        self._scanner = scanner
        self._relay = relay

        self._authorized = [u.lower() for u in authorized_uuids]
        self._rssi_threshold = int(rssi_threshold)
        self._unlock_time_ms = int(unlock_time_ms)
        self._cooldown_wait_ms = int(cooldown_wait_ms)

        self._state = "SCAN_FOR_TRIGGER"
        self._last_seen_time_ms: int = 0
        self._pulse_end_ms: Optional[int] = None

        # Bind callback for advertisement results.
        def on_result(ad: AdvertisedDevice, now_ms: int) -> None:
            self.on_result(ad, now_ms)

        self._scanner.set_callbacks(on_result)

        self._client_printer = printer

    def _is_authorized(self, ad: AdvertisedDevice) -> bool:
        return ad.service_uuid.lower() in self._authorized

    def on_result(self, ad: AdvertisedDevice, now_ms: int) -> None:
        if not self._is_authorized(ad):
            return

        # In firmware: if (advertisedDevice.getRSSI() < RSSI_THRESHOLD) return;
        if ad.getRSSI() < self._rssi_threshold:
            return

        self._last_seen_time_ms = now_ms

        if self._state == "SCAN_FOR_TRIGGER":
            self._printer.println(f"Target Found: {ad.phone_id} (RSSI {ad.getRSSI()} dBm)")
            self._scanner.stop(now_ms)

            # Perform handshake/verification.
            client = FakeBleClient(self._client_printer)
            if client.connect(ad) and client.isConnected():
                self._printer.println(">>> SECURE UNLOCK (Handshake Success)")
                self._relay.digitalWrite_relay_in(True, now_ms)

                self._pulse_end_ms = now_ms + self._unlock_time_ms
                self._state = "PULSING"
                # Disconnect immediately after verification (stealth).
                client.disconnect()
            else:
                self._printer.println("Connection Failed (Spoof/Unauthenticated). Remaining locked.")

        elif self._state == "COOLDOWN_WAIT_FOR_EXIT":
            # Heartbeat: last_seen_time updated above.
            pass

    def loop_step(self, now_ms: int) -> None:
        # Pulse relay timing.
        if self._state == "PULSING":
            if self._pulse_end_ms is not None and now_ms >= self._pulse_end_ms:
                self._relay.digitalWrite_relay_in(False, now_ms)
                self._pulse_end_ms = None
                self._state = "COOLDOWN_WAIT_FOR_EXIT"
                self._printer.println("[State] Entering Cooldown. Waiting for user to leave...")

        # Cooldown exit condition.
        if self._state == "COOLDOWN_WAIT_FOR_EXIT":
            if self._last_seen_time_ms != 0 and (now_ms - self._last_seen_time_ms) > self._cooldown_wait_ms:
                self._printer.println("[User Left] -> Cooldown Reset. Ready to Scan.")
                self._state = "SCAN_FOR_TRIGGER"

        # Ensure scanner is running in the scan state.
        # In the real firmware, scanning continues even during cooldown.
        if self._state in ("SCAN_FOR_TRIGGER", "COOLDOWN_WAIT_FOR_EXIT"):
            if not self._scanner.is_scanning(now_ms):
                # Firmware: pBLEScan->start(1, false)
                self._scanner.start(duration_ms=1000, now_ms=now_ms)


class HoldOpenFirmware:
    """
    Mirrors `NewApproch2.0.ino` / GhostLock v3 hold-open mode:
    - SECURE_LOCKED: scan until authorized UUID found with RSSI > threshold,
      then stop scan and verify via handshake (connect success required)
    - VERIFYING: attempt connect; on success unlock and go to HOLD_OPEN_STEALTH
    - HOLD_OPEN_STEALTH: keep door unlocked while authorized advertisements continue
      and auto-lock after AUTO_LOCK_DELAY since lastSeenTime update.

    Fidelity note:
    Your firmware updates `lastSeenTime` for any authorized UUID that appears,
    even if RSSI is below threshold (it only gates *deviceFound* on RSSI).
    This simulator keeps that exact behavior.
    """

    def __init__(
        self,
        printer: SerialPrinter,
        scanner: FakeScanner,
        relay: RelaySim,
        authorized_uuids: List[str],
        rssi_unlock_threshold: int,
        auto_lock_delay_ms: int,
        scan_window_ms: int = 1000,
    ):
        self._printer = printer
        self._scanner = scanner
        self._relay = relay

        self._authorized = [u.lower() for u in authorized_uuids]
        self._rssi_unlock_threshold = int(rssi_unlock_threshold)
        self._auto_lock_delay_ms = int(auto_lock_delay_ms)
        self._scan_window_ms = int(scan_window_ms)

        self._state = "SECURE_LOCKED"
        self._device_found: bool = False
        self._target_device: Optional[AdvertisedDevice] = None
        self._last_seen_time_ms: int = 0

        def on_result(ad: AdvertisedDevice, now_ms: int) -> None:
            self.on_result(ad, now_ms)

        self._scanner.set_callbacks(on_result)

    def _is_authorized(self, ad: AdvertisedDevice) -> bool:
        return ad.service_uuid.lower() in self._authorized

    def on_result(self, ad: AdvertisedDevice, now_ms: int) -> None:
        if not self._is_authorized(ad):
            return

        # Firmware: lastSeenTime is updated whenever authorized UUID appears.
        self._last_seen_time_ms = now_ms

        if self._state == "SECURE_LOCKED":
            # Firmware v2/v3 uses strict `>` check.
            if ad.getRSSI() > self._rssi_unlock_threshold:
                self._printer.println("Target in Range. Initiating Security Handshake...")
                self._target_device = ad
                self._device_found = True
                self._scanner.stop(now_ms)
            # else: authorized but too far; we only update lastSeenTime.

    def loop_step(self, now_ms: int) -> None:
        if self._state == "SECURE_LOCKED":
            if self._device_found:
                self._state = "VERIFYING"
                # Continue verification in next step(s).
            elif not self._scanner.is_scanning(now_ms):
                self._scanner.start(duration_ms=self._scan_window_ms, now_ms=now_ms)

        elif self._state == "VERIFYING":
            # Attempt handshake.
            if self._target_device is None:
                self._device_found = False
                self._state = "SECURE_LOCKED"
                return

            client = FakeBleClient(self._printer)
            if client.connect(self._target_device) and client.isConnected():
                self._printer.println("Identity Verified. Unlocking...")
                self._relay.digitalWrite_relay_in(True, now_ms)
                client.disconnect()

                self._state = "HOLD_OPEN_STEALTH"
                self._last_seen_time_ms = now_ms
            else:
                self._printer.println(
                    "Verification Failed (Spoof attempt?). Remaining Locked."
                )
                self._state = "SECURE_LOCKED"

            self._device_found = False
            self._target_device = None

        elif self._state == "HOLD_OPEN_STEALTH":
            # Keep scanning while unlocked (same behavior as firmware).
            if not self._scanner.is_scanning(now_ms):
                self._scanner.start(duration_ms=self._scan_window_ms, now_ms=now_ms)

            if (self._last_seen_time_ms != 0) and (now_ms - self._last_seen_time_ms) > self._auto_lock_delay_ms:
                self._printer.println("User Left Range. Auto-Locking.")
                self._relay.digitalWrite_relay_in(False, now_ms)
                self._state = "SECURE_LOCKED"


class InteractiveController:
    def __init__(self, on_cmd: Callable[[str], None], printer: SerialPrinter):
        self._on_cmd = on_cmd
        self._printer = printer
        self._stop = False

    def start(self) -> None:
        th = threading.Thread(target=self._loop, daemon=True)
        th.start()

    def _loop(self) -> None:
        help_text = (
            "Commands: near, far, real, spoof, on, off, rssi <val>, status, quit, help"
        )
        self._printer.println(help_text)
        while not self._stop:
            try:
                line = input("ghostlock-sim> ")
            except EOFError:
                self._stop = True
                return
            cmd = line.strip()
            if not cmd:
                continue
            self._on_cmd(cmd)
            if cmd in ("quit", "exit"):
                self._stop = True
                return


class Simulator:
    def __init__(
        self,
        firmware: str,
        authorized_uuids: List[str],
        active_state_high: bool,
        rssi_threshold: int,
        unlock_ms: int,
        cooldown_ms: int,
        auto_lock_delay_ms: int,
        tick_ms: int,
        realtime: bool,
        scenario_path: Optional[str],
        interactive: bool,
    ):
        self._firmware = firmware
        self._authorized_uuids = authorized_uuids
        self._rssi_threshold = rssi_threshold
        self._unlock_ms = unlock_ms
        self._cooldown_ms = cooldown_ms
        self._auto_lock_delay_ms = auto_lock_delay_ms
        self._tick_ms = tick_ms
        self._realtime = realtime
        self._scenario_path = scenario_path
        self._interactive = interactive

        self._now_ms = 0
        self._stop = False

        self._printer = SerialPrinter(get_now_ms=lambda: self._now_ms)
        self._scanner = FakeScanner(self._printer)
        self._relay = RelaySim(self._printer, active_state_high=active_state_high)

        # Single-phone environment for now (matches your current scripts & demos).
        self._phone = SimPhone(
            phone_id="phone-1",
            service_uuid=self._authorized_uuids[0] if self._authorized_uuids else DEFAULT_SERVICE_UUID,
            advertising=False,
            genuine=True,
            distance_m=12.0,
        )
        self._env = FakeBleEnvironment([self._phone])

        # Firmware init.
        if firmware == "pulse":
            self._fw = PulseFirmware(
                printer=self._printer,
                scanner=self._scanner,
                relay=self._relay,
                authorized_uuids=self._authorized_uuids,
                rssi_threshold=self._rssi_threshold,
                unlock_time_ms=self._unlock_ms,
                cooldown_wait_ms=self._cooldown_ms,
            )
        elif firmware == "hold-open":
            self._fw = HoldOpenFirmware(
                printer=self._printer,
                scanner=self._scanner,
                relay=self._relay,
                authorized_uuids=self._authorized_uuids,
                rssi_unlock_threshold=self._rssi_threshold,
                auto_lock_delay_ms=self._auto_lock_delay_ms,
                scan_window_ms=1000,
            )
        else:
            raise ValueError(f"Unknown firmware: {firmware}")

        self._scenario: Optional[Dict] = None
        self._scenario_events: List[Dict] = []
        self._next_event_idx: int = 0

        if self._scenario_path:
            self._load_scenario(self._scenario_path)

    def _load_scenario(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            self._scenario = json.load(f)
        initial = self._scenario.get("initial_phone") or {}
        if "advertising" in initial:
            self._phone.advertising = bool(initial["advertising"])
        if "genuine" in initial:
            self._phone.genuine = bool(initial["genuine"])
        if "distance_m" in initial and initial["distance_m"] is not None:
            self._phone.distance_m = float(initial["distance_m"])
        if "manual_rssi" in initial:
            self._phone.manual_rssi = initial["manual_rssi"]

        self._scenario_events = list(self._scenario.get("events") or [])
        self._scenario_events.sort(key=lambda e: e.get("t_ms", 0))
        self._next_event_idx = 0

        self._printer.println(f"Scenario loaded: {path}")

    def _apply_action(self, action: str, now_ms: int) -> None:
        action = action.strip().lower()

        # Phone state commands.
        if action == "near":
            self._phone.set_near()
            self._printer.println("Phone set: near")
        elif action == "far":
            self._phone.set_far()
            self._printer.println("Phone set: far")
        elif action == "real":
            self._phone.genuine = True
            self._printer.println("Phone set: real (handshake will succeed)")
        elif action == "spoof":
            self._phone.genuine = False
            self._printer.println("Phone set: spoof (handshake will fail)")
        elif action == "on":
            self._phone.advertising = True
            self._printer.println("Phone set: ON (advertising)")
        elif action == "off":
            self._phone.advertising = False
            self._printer.println("Phone set: OFF (stopped advertising)")
        elif action.startswith("rssi"):
            parts = action.split()
            if len(parts) != 2:
                self._printer.println("Usage: rssi <value>")
                return
            self._phone.set_rssi(int(parts[1]))
            self._printer.println(f"Phone set: manual RSSI={self._phone.manual_rssi} dBm")
        elif action == "status":
            self._printer.println(
                f"STATUS: advertising={self._phone.advertising} genuine={self._phone.genuine} "
                f"distance_m={self._phone.distance_m:.2f} manual_rssi={self._phone.manual_rssi} "
                f"rssi_now={self._phone.rssi_value()} door_unlocked={self._relay.door_unlocked}"
            )
        elif action in ("quit", "exit"):
            self._stop = True
            self._printer.println("Stopping simulator...")
        elif action == "help":
            self._printer.println("Commands: near, far, real, spoof, on, off, rssi <val>, status, quit, help")
        else:
            self._printer.println(f"Unknown command: {action} (try 'help')")

    def run(self, max_sim_time_ms: int = 60000) -> None:
        # Start interactive controller (optional).
        if self._interactive:
            ctrl = InteractiveController(on_cmd=lambda c: self._apply_action(c, self._now_ms), printer=self._printer)
            ctrl.start()

        # Main loop.
        self._printer.println(f"Booting Ghost Lock ESP32 Simulator ({self._firmware})")

        # Initialize relay/door state as locked.
        self._relay.digitalWrite_relay_in(False, self._now_ms)

        while not self._stop and self._now_ms <= max_sim_time_ms:
            # Deliver scheduled scenario events.
            while (
                self._scenario_events
                and self._next_event_idx < len(self._scenario_events)
                and self._scenario_events[self._next_event_idx].get("t_ms", 0) <= self._now_ms
            ):
                evt = self._scenario_events[self._next_event_idx]
                self._next_event_idx += 1
                action = evt.get("action")
                if action is not None:
                    self._apply_action(str(action), self._now_ms)

            # BLE scan callback delivery.
            ads = self._env.advertisements()
            self._scanner.deliver(ads, self._now_ms)

            # Firmware state machine step.
            self._fw.loop_step(self._now_ms)

            # Stop if scenario finished (non-interactive).
            if self._scenario_events and (self._next_event_idx >= len(self._scenario_events)) and not self._interactive:
                # Give one extra scan window to show end-state logs.
                if self._now_ms > (self._scenario_events[-1].get("t_ms", 0) + 3000):
                    break

            self._now_ms += self._tick_ms

            if self._realtime:
                time.sleep(self._tick_ms / 1000.0)
            else:
                # No sleep: run fast.
                pass


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--firmware", choices=["pulse", "hold-open"], default="hold-open")
    p.add_argument("--active-state", choices=["high", "low"], default="high", help="Relay active level")
    p.add_argument("--tick-ms", type=int, default=50)
    p.add_argument("--realtime", action="store_true", help="Sleep to run in real time")
    p.add_argument("--interactive", action="store_true", help="Accept commands in the terminal")
    p.add_argument("--scenario", help="Path to a scenario JSON file")
    p.add_argument(
        "--authorized-uuid",
        action="append",
        default=[DEFAULT_SERVICE_UUID],
        help="Authorized service UUID (can be specified multiple times).",
    )

    # Timing/threshold tuning (matches firmware constants)
    p.add_argument("--rssi-threshold", type=int, default=-75, help="RSSI threshold to trigger unlock (pulse uses >=, hold-open uses >).")
    p.add_argument("--unlock-ms", type=int, default=3000, help="Pulse unlock duration (milliseconds).")
    p.add_argument("--cooldown-ms", type=int, default=5000, help="Cooldown wait-to-exit timeout (milliseconds) in pulse mode.")
    p.add_argument("--auto-lock-delay-ms", type=int, default=10000, help="Hold-open auto-lock delay after lastSeenTime (milliseconds).")
    return p.parse_args(argv)


def main() -> None:
    args = parse_args(sys.argv[1:])

    active_state_high = args.active_state.lower() == "high"
    authorized_uuids = args.authorized_uuid

    sim = Simulator(
        firmware=args.firmware,
        authorized_uuids=authorized_uuids,
        active_state_high=active_state_high,
        rssi_threshold=args.rssi_threshold,
        unlock_ms=args.unlock_ms,
        cooldown_ms=args.cooldown_ms,
        auto_lock_delay_ms=args.auto_lock_delay_ms,
        tick_ms=args.tick_ms,
        realtime=bool(args.realtime or args.interactive),
        scenario_path=args.scenario,
        interactive=bool(args.interactive),
    )
    sim.run(max_sim_time_ms=90000)


if __name__ == "__main__":
    main()

