#!/usr/bin/env python3
# coding: utf-8
"""
ioptron.py – Command‑line controller for iOptron HAZ‑series Alt‑Az mounts
===========================================================================

This script talks to an iOptron mount through the Go2Nova 8409 hand‑controller’s
USB‑to‑serial bridge (115 200‑8‑N‑1).  It supports three CLI sub‑commands:

* **status** – print current Alt/Az and basic system state
* **goto**   – slew to a specified Alt/Az
* **home**   – return to the mount’s mechanical zero (“home”) position


The system will not remember its home position across power cycles of both the remote controller AND the mount. If the remote controller is unplugged but the mount never loses power, there appears to be no problem. However, if the whole system is shut off, then you have a problem. 
There are two problems I have identified (or risks, rather): 
1. If a complete power loss occurs, the system on next startup will set whatever position it is at as the NEW ZENITH.
2. During the alignment wizard zenith homing procedure, the system will rotate a full 360 degrees no matter what, and point up to zenith which could rip out cables. After confirming data and time, it will then attempt to look at the sun. This could cause a crash.
So, if a power loss occurs that even exceeds the battery life of the HAZ71 mount, and full power is lost (e.g. if the remote controller loses power! This includes unplugging), zenith will need to be reacquired with the correct azimuth. 

If a power interrupt occurs with PANDORA's optical payload mounted, it is best to not use the alignment wizard, for you risk a problematic pointing that could cause a crash. After confirming date/time/location settings, it will attempt to point to an astronomical object for alignment confirmation, and it will not reliably set the azimuth position without this. If during the daytime (read: you input the time as being during sunup in your location and season), you run this wizard, it will point at the sun. If you try to abort mid-alignment (e.g. skip it), then python-based motion commands fail unless you park, then unpark the system. Crucially, the system will also attain an incorrect azimuth alignment. The setup wizard needs to point at an astronomical object and be confirmed in its pointing before it will function normally, namely setting the correct geomagnetic South. If you try to do the setup with a time set to nighttime, then it will (without asking you) slew to a bright star in the night sky, and will almost certainly perform a full circle rotation, which again implies a risk of cable loss. If you set a manual zenith position, Be advised that a rough alignment and manual zenith setting may mean that the altitude limit is no longer perfectly safe. This is the benefit of a proper setup wizard alignment: true alt az referencing.
In general, the wizard should be used when the user cares about very specifically knowing the true altitude and azimuth of PANDORA, and when it is safe to do so cable-wise. 
If a manual zenith position is input, it is advisable to slew down to the lowest altitude that is observed to be safe by eye, then go to Menu > Settings > Set Altitude Limit and input that New lowest altitude position. It's also good practice to just confirm this altitude limit is correctly set across power failures.
Check the saved parking position, too. It appears to be saved across full power cycles of the remote controller, but this is not totally clear. 

If using the setup wizard is not an option due to cable constraints, one should instead press the menu button until the menu appears, then the back button to return to the normal position pointing view (with RA/DEC, alt/az, etc) and then to point the system using the up/down/left/right arrow keys until Alt = 90, Az = 180 is roughly attained by manual adjustments. To lock this in as the new zenith position, go to menu, Zero Position, Set Zero Position. If this was successful, Az Al should show 180, 90. 


Additional debug: after zenith setting, the code may print "slew complete" too early. This seems to be remedied by running park, then unpark. 

Example
-------
$ python ioptron.py --port /dev/cu.PL2303G-USBtoUART110 status
$ python ioptron.py --port /dev/cu.PL2303G-USBtoUART110 goto 45 120 --track
$ python ioptron.py --port /dev/cu.PL2303G-USBtoUART110 home

Requires :  `pip install pyserial`
Documented : iOptron RS‑232 Command Language v3.10 (2021‑01‑04)
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

from builtins import TimeoutError

import serial


BAUDRATE = 115_200

# Software-enforced azimuth limits (degrees)
AZ_LOWER = 0.0
AZ_UPPER = 360.0


class IoptronMount:
    # ---------- parking API -------------------------------------------------------

    def park(self) -> None:
        """Move the mount to the stored parking position and block until parked."""
        print("Parking mount...")
        if self._cmd_single(":MP1#") != "1":
            raise RuntimeError("Park command failed")
        # Wait until movement stops (position-based)
        self.wait_for_stop(interval=0.2)

    def unpark(self) -> None:
        """Unpark the mount, allowing movements."""
        print("Unparking mount...")
        if self._cmd_single(":MP0#") != "1":
            raise RuntimeError("Unpark command failed")

    def set_park(self, alt_deg: float, az_deg: float) -> None:
        """Define a new parking position (saved in non-volatile memory)."""
        alt_str = self._format_altitude(alt_deg)
        az_str = self._format_azimuth(az_deg)
        if self._cmd_single(f":SPH{alt_str}#") != "1":
            raise RuntimeError("Failed to set park altitude")
        if self._cmd_single(f":SPA{az_str}#") != "1":
            raise RuntimeError("Failed to set park azimuth")
        print(f"Parking position set to Alt {alt_deg:.4f}°, Az {az_deg:.4f}°")

    def get_park(self) -> tuple[float, float]:
        """Retrieve the stored parking position in degrees."""
        rsp = self._cmd(":GPC#")  # TTTTTTTTTTTTTTTTT#
        if not rsp.endswith("#") or len(rsp) < 18:
            raise RuntimeError(f"Unexpected :GPC# response: {rsp!r}")
        data = rsp.strip("#")
        alt_units = int(data[0:8])
        az_units = int(data[8:17])
        return alt_units / 360_000.0, az_units / 360_000.0
    """Thin wrapper around the iOptron RS‑232 command set."""

    def __init__(self, port: str, baudrate: int = BAUDRATE, timeout: float = 2.0, monitor_enabled: bool = False) -> None:
        self.port_name = port
        self.monitor_enabled = monitor_enabled
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout,
                write_timeout=timeout,
            )
        except serial.SerialException as exc:
            sys.stderr.write(f"ERROR: could not open {port!r}: {exc}\n")
            raise SystemExit(1) from exc

        # Flush anything stale.
        self.ser.reset_input_buffer()

        # Optional handshake—identifies the mount model (may fail harmlessly).
        try:
            model_code = self._cmd(":MountInfo#")
            print(f"Connected to mount model code: {model_code.strip('#')}")
        except TimeoutError:
            print("WARNING: :MountInfo# timed‑out; continuing anyway.")

        # Ensure tracking is disabled by default (consume ack)
        try:
            self._cmd_single(":ST0#")
            print("Tracking disabled by default.")
        except TimeoutError:
            pass

    # ---------- low‑level helpers -------------------------------------------------

    def close(self) -> None:
        """Close the serial port (safe to call multiple times)."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    __del__ = close

    def _read_until_hash(self) -> str:
        """Read ASCII bytes until the terminating ‘#’. Raises TimeoutError if late."""
        buf = bytearray()
        start = time.monotonic()
        while True:
            b = self.ser.read(1)
            if not b:
                raise TimeoutError("Mount response timed‑out")
            if b == b"#":
                buf.append(ord("#"))
                return buf.decode("ascii")
            buf.append(b[0])
            if time.monotonic() - start > self.ser.timeout:
                raise TimeoutError("Mount response timed‑out")

    def _cmd(self, payload: str, expect_reply: bool = True) -> Optional[str]:
        """
        Send *payload* (must include trailing ‘#’ or it will be appended).  If
        *expect_reply* is True, return the response string (also ‘#’‑terminated).
        """
        if not payload.endswith("#"):
            payload += "#"
        if self.monitor_enabled:
            print(f"[RAW TX] {payload!r}")
        self.ser.write(payload.encode("ascii"))
        self.ser.flush()
        if expect_reply:
            resp = self._read_until_hash()
            if self.monitor_enabled:
                print(f"[RAW RX] {resp!r}")
            return resp
        return None

    def _cmd_single(self, payload: str) -> str:
        """
        Send *payload* (appends “#” if missing) and read exactly one reply byte.

        Several “set” commands (e.g. :Sa, :Sz, :MSS, :MH) acknowledge with a
        bare “1” or “0” rather than the usual hash‑terminated string.
        """
        if not payload.endswith("#"):
            payload += "#"
        if self.monitor_enabled:
            print(f"[RAW TX] {payload!r}")
        self.ser.write(payload.encode("ascii"))
        self.ser.flush()
        resp = self.ser.read(1)
        if self.monitor_enabled:
            print(f"[RAW RX] {resp!r}")
        if not resp:
            raise TimeoutError("Mount response timed‑out")
        return resp.decode("ascii")

    # ---------- formatting helpers -----------------------------------------------

    @staticmethod
    def _format_altitude(deg_alt: float) -> str:
        """Convert degrees to sTTTTTTTT (±0.01 arc‑sec units)."""
        if not -90.0 <= deg_alt <= 90.0:
            raise ValueError("Altitude must be in −90…+90°")
        units = int(round(deg_alt * 360_000))  # 1° = 3600″ = 360 000 centi‑arcsec
        sign = "+" if units >= 0 else "-"
        return f"{sign}{abs(units):08d}"

    @staticmethod
    def _format_azimuth(deg_az: float) -> str:
        """Convert degrees to TTTTTTTTT (0.01 arc‑sec units)."""
        deg_az = deg_az % 360.0
        units = int(round(deg_az * 360_000))
        return f"{units:09d}"

    # ---------- public high‑level API --------------------------------------------

    def goto_altaz(self, alt_deg: float, az_deg: float, track_after: bool = False) -> None:
        """
        Slew to the requested Alt/Az (degrees) and block until the mount reports
        the slew is finished.
        """
        alt_str = self._format_altitude(alt_deg)
        az_str = self._format_azimuth(az_deg)

        # Per RS‑232 spec “:Sa<sign><8‑digits>#” and “:Sz<9‑digits>#”
        if self._cmd_single(f":Sa{alt_str}#") != "1":
            raise RuntimeError("Failed to accept altitude target")
        if self._cmd_single(f":Sz{az_str}#") != "1":
            raise RuntimeError("Failed to accept azimuth target")

        print("Slewing...")
        time.sleep(0.1)  # Give firmware a moment before issuing :MSS#
        if self._cmd_single(":MSS#") != "1":
            raise RuntimeError("Mount refused slew (limit hit?)")

        if track_after:
            self._cmd(":ST1#")  # Resume tracking; MSS stops it.

        # Wait until motion finishes using status-based polling
        self.wait_for_slew_complete(interval=0.2)

    def goto_home(self) -> None:
        """Return to the mechanical zero (home) position."""
        print("Slewing to home...")
        if self._cmd_single(":MH#") != "1":
            raise RuntimeError("Mount failed to slew to home")

        # Wait until motion finishes using status-based polling
        self.wait_for_slew_complete(interval=0.2)
    def wait_for_slew_complete(self, interval: float = 0.2) -> None:
        """
        Poll system status every `interval` seconds until the mount stops slewing.
        """
        # Allow initial motion to begin
        time.sleep(interval)
        while True:
            # Query system status: code '2' = Slewing
            _, _, state = self.get_status()
            if state != "Slewing":
                break
            time.sleep(interval)
    def wait_for_stop(self, interval: float = 0.2, threshold: float = 0.0005) -> None:
        """
        Poll current Alt/Az every `interval` seconds and block until movement stops.
        Movement is considered stopped when changes in both Alt and Az are below `threshold` degrees.
        """
        # Initial delay to allow motion to begin
        time.sleep(interval)
        prev_alt, prev_az = self.get_altaz()
        while True:
            time.sleep(interval)
            alt, az = self.get_altaz()
            # If both axes change less than threshold, motion has stopped
            if abs(alt - prev_alt) < threshold and abs(az - prev_az) < threshold:
                break
            prev_alt, prev_az = alt, az

    def get_altaz(self) -> tuple[float, float]:
        """Return current Alt/Az in degrees."""
        rsp = self._cmd(":GAC#")  # sTTTTTTTTTTTTTTTTT#
        if len(rsp) != 19 or not rsp.endswith("#"):
            raise RuntimeError(f"Unexpected :GAC# response: {rsp!r}")

        sign = 1 if rsp[0] == "+" else -1
        alt_units = int(rsp[1:9])
        az_units = int(rsp[9:18])
        return sign * alt_units / 360_000.0, az_units / 360_000.0

    def get_status(self) -> tuple[float, float, str]:
        """
        Return the current altitude (degrees), azimuth (degrees), and
        system state ('Stopped', 'Tracking', 'Slewing', etc.).
        """
        # Get numeric Alt/Az
        alt, az = self.get_altaz()
        # Query extended status
        rsp = self._cmd(":GLS#")
        # 19th character (index 18) indicates system status per manual
        code = rsp[18]
        mapping = {
            "0": "Stopped (non-zero)",
            "1": "Tracking",
            "2": "Slewing",
            "3": "Auto-guiding",
            "6": "Parked",
            "7": "Stopped (home)",
        }
        state = mapping.get(code, "Unknown")
        return alt, az, state

    def is_parked(self) -> bool:
        """
        Return True if the mount is currently in the parked state.
        """
        _, _, state = self.get_status()
        return state == "Parked"

    def get_home(self) -> tuple[float, float]:
        """
        Slew the mount to its mechanical zero (‘home’), then return its Alt/Az.
        """
        # Slew to home and block until motion finishes
        self.goto_home()
        # Read actual home coordinates
        return self.get_altaz()

    def test_home(self, duration: float = 30.0) -> None:
        """
        Slew to home, then for `duration` seconds dump all bytes received
        with elapsed timestamps, to diagnose additional status messages.
        """
        print(f"Starting home-test for {duration:.1f}s...")
        # Ensure buffer is clear
        self.ser.reset_input_buffer()
        # Start slew
        self.goto_home()
        start = time.time()
        while True:
            elapsed = time.time() - start
            if elapsed > duration:
                print("\nHome-test duration complete.")
                break
            chunk = self.ser.read(128)
            if not chunk:
                continue
            for b in chunk:
                # Printable ASCII
                if 32 <= b < 127 and chr(b) not in {"\r", "\n"}:
                    out = chr(b)
                elif b in {10, 13}:
                    out = "\\n"
                else:
                    out = f"\\x{b:02x}"
                print(f"[{elapsed:6.2f}s] {out}", end="", flush=True)
        # After test, report final position
        alt, az = self.get_altaz()
        print(f"\nPost-test position: Alt {alt:.4f}°, Az {az:.4f}°")

    def calibrate(self) -> None:
        """
        Synchronize the mount’s internal coordinates to the current Alt/Az.
        Uses the :CM# RS-232 command to set commanded position to current position.
        """
        print("Calibrating mount (synchronizing current position)...")
        if self._cmd_single(":CM#") != "1":
            raise RuntimeError("Calibration command failed")
        print("Mount coordinates synchronized.")

    # Note: iOptron firmware refers to the built-in Zenith/Home as "zero" (Alt ≈90°, Az ≈180°),
    #       determined during the Assist Alignment Wizard via magnetic-south + zenith sensor.
    def reset_zero(self) -> None:
        """
        Set the current position as the new zenith reference position.
        """
        print("Resetting zero position to current Alt/Az...")
        if self._cmd_single(":SZP#") != "1":
            raise RuntimeError("Failed to set new zero position")
        print("Zero position updated.")

    def set_alt_limit(self, limit_deg: int) -> None:
        """
        Set the minimum altitude limit (applies to slewing and tracking).
        Uses the :SALsnn# RS-232 command, where s = sign and nn = degrees.
        """
        if not -89 <= limit_deg <= 89:
            raise ValueError("Altitude limit must be between -89 and 89 degrees")
        sign = "+" if limit_deg >= 0 else "-"
        nn = abs(limit_deg)
        limit_str = f"{sign}{nn:02d}"
        if self._cmd_single(f":SAL{limit_str}#") != "1":
            raise RuntimeError("Failed to set altitude limit")
        print(f"Altitude limit set to {limit_deg}°")

    def get_alt_limit(self) -> int:
        """
        Get the current altitude limit in degrees.
        Uses the :GAL# RS-232 command.
        """
        rsp = self._cmd(":GAL#")  # expects "snn#"
        if not rsp.endswith("#") or len(rsp) < 3:
            raise RuntimeError(f"Unexpected :GAL# response: {rsp!r}")
        sign = rsp[0]
        nn = int(rsp[1:3])
        return nn if sign == "+" else -nn

    def zero_and_park(self) -> None:
        """
        Set current position as the new zero/home and also define the same spot as park.
        """
        # Read current Alt/Az
        alt, az = self.get_altaz()
        # Reset zero
        print("Resetting zero to current position...")
        if self._cmd_single(":SZP#") != "1":
            raise RuntimeError("Failed to set new zero position")
        print("Zero position updated.")
        # Set park to this position
        print("Defining park position at current position...")
        alt_str = self._format_altitude(alt)
        az_str = self._format_azimuth(az)
        if self._cmd_single(f":SPH{alt_str}#") != "1":
            raise RuntimeError("Failed to set park altitude")
        if self._cmd_single(f":SPA{az_str}#") != "1":
            raise RuntimeError("Failed to set park azimuth")
        print(f"Park position set to Alt {alt:.4f}°, Az {az:.4f}°")

    def status(self) -> None:
        """Print current Alt/Az and basic system status."""
        alt, az, state = self.get_status()
        print(f"Altitude : {alt:8.4f}°")
        print(f"Azimuth  : {az:8.4f}°")
        print(f"System   : {state}")

    # Context-manager helpers
    def __enter__(self) -> "IoptronMount":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.close()


# ---------- CLI -----------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Command‑line controller for iOptron HAZ‑series Alt‑Az mounts (angles in degrees)"
    )
    p.add_argument(
        "-p",
        "--port",
        default="/dev/cu.PL2303G-USBtoUART110",
        help="Serial device (default: %(default)s)",
    )
    p.add_argument(
        "--monitor",
        "-m",
        action="store_true",
        help="Show raw TX/RX bytes during operations",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    s_goto = sub.add_parser("goto", help="Slew to the specified Alt/Az")
    s_goto.add_argument("altitude", type=float, help="Altitude (degrees; -90 to +90)")
    s_goto.add_argument("azimuth", type=float, help="Azimuth (degrees; 0 to 360)")
    s_goto.add_argument(
        "--track",
        action="store_true",
        help="Resume tracking after slew (MSS stops tracking)",
    )
    s_goto.add_argument(
        "--status",
        action="store_true",
        help="Print mount status after the slew completes",
    )

    sub.add_parser("zenith", help="Return to zenith (factory zero) position")
    sub.add_parser("park", help="Move to the stored parking position")
    sub.add_parser("unpark", help="Unpark the mount (allow movements)")
    s_set = sub.add_parser("set-park", help="Define a new parking position")
    s_set.add_argument("altitude", type=float, help="Altitude for park position (degrees)")
    s_set.add_argument("azimuth", type=float, help="Azimuth for park position (degrees)")

    sub.add_parser("get-park", help="Show the stored parking position")
    sub.add_parser("get-position", help="Show current Alt/Az position")
    sub.add_parser("set-zenith", help="Set current position as the new zenith reference")
    s_alt_set = sub.add_parser(
        "set-alt-limit",
        help="Set the minimum altitude limit (degrees, -89…89)"
    )
    s_alt_set.add_argument(
        "limit",
        type=int,
        help="Altitude limit in degrees (-89…89)"
    )
    sub.add_parser(
        "get-alt-limit",
        help="Show the currently set altitude limit"
    )
    s_az_lim = sub.add_parser(
        "set-az-limits",
        help="Set software-enforced azimuth limits (degrees, 0…360)"
    )
    s_az_lim.add_argument(
        "lower",
        type=float,
        help="Lower azimuth limit (0…360)"
    )
    s_az_lim.add_argument(
        "upper",
        type=float,
        help="Upper azimuth limit (0…360)"
    )
    sub.add_parser("status", help="Show current Alt/Az and state")

    return p


def main() -> None:  # noqa: D103
    parser = _build_parser()
    # Allow --monitor/-m anywhere: extract and remove from argv
    monitor_enabled = False
    import sys
    filtered = [sys.argv[0]]
    for arg in sys.argv[1:]:
        if arg in ("--monitor", "-m"):
            monitor_enabled = True
        else:
            filtered.append(arg)
    sys.argv[:] = filtered

    args = parser.parse_args()

    # Software-enforced azimuth limits
    az_lower = AZ_LOWER
    az_upper = AZ_UPPER

    with IoptronMount(args.port, monitor_enabled=monitor_enabled) as mount:
        if args.cmd == "goto":
            # Enforce software-configured altitude limit
            # (removes static [0°, 90°] check)
            # Enforce safe azimuth range [az_lower, az_upper]
            if not (az_lower <= args.azimuth <= az_upper):
                sys.exit(f"ERROR: Requested azimuth {args.azimuth:.4f}° outside safe range [{az_lower:.4f}°, {az_upper:.4f}°].")

            # Check parked state
            if mount.is_parked():
                sys.exit("ERROR: Mount is currently parked. Please unpark before slewing.")
            # Enforce software-configured altitude limit
            try:
                alt_limit = mount.get_alt_limit()
            except Exception as e:
                sys.exit(f"ERROR: Unable to read altitude limit: {e}")
            if args.altitude < alt_limit:
                sys.exit(f"ERROR: Requested altitude {args.altitude:.4f}° below configured limit of {alt_limit:.4f}°.")
            mount.goto_altaz(args.altitude, args.azimuth, track_after=args.track)
            print("Mount reports slew complete.")
            if getattr(args, "status", False):
                mount.status()
            # Disable tracking after move (unless user explicitly tracking)
            if not args.track:
                mount._cmd_single(":ST0#")  # consume ack
                print("Tracking disabled.")
        elif args.cmd == "zenith":
            mount.goto_home()
            print("Zenith position reached.")
            mount._cmd_single(":ST0#")  # consume ack
            print("Tracking disabled.")
        elif args.cmd == "park":
            mount.park()
            print("Mount parked.")
            mount._cmd_single(":ST0#")  # consume ack
            print("Tracking disabled.")
        elif args.cmd == "unpark":
            mount.unpark()
            print("Mount unparked.")
        elif args.cmd == "set-park":
            # Confirm and move then set park
            print("WARNING: telescope will move to specified position and update park. Collisions are possible.")
            mount.goto_altaz(args.altitude, args.azimuth)
            mount.set_park(args.altitude, args.azimuth)            
            # resp = input(
            #     f"Move to Alt {args.altitude:.4f}°, Az {args.azimuth:.4f}° and set as park? [y/N]: "
            # )
            # if resp.lower() == 'y':
            #     mount.goto_altaz(args.altitude, args.azimuth)
            #     mount.set_park(args.altitude, args.azimuth)
            #     print(f"Park position set to Alt {args.altitude:.4f}°, Az {args.azimuth:.4f}°")
            # else:
            #     print("Operation aborted.")

        elif args.cmd == "get-park":
            alt, az = mount.get_park()
            print(f"Stored park position: Alt {alt:.4f}°, Az {az:.4f}°")
        elif args.cmd == "get-position":
            alt, az = mount.get_altaz()
            print(f"Current position: Alt {alt:.4f}°, Az {az:.4f}°")
        elif args.cmd == "set-zenith":
            print("WARNING: YOU ARE OFFSETTING THE SYSTEM'S ZENITH REFERENCE POSITION!")
            resp = input("Confirm set current position as new zenith reference? [y/N]: ")
            if resp.lower() == 'y':
                mount.reset_zero()
                print("Zenith reference updated.")
            else:
                print("Operation aborted.")
        elif args.cmd == "set-alt-limit":
            print("WARNING: setting an altitude limit can prevent slewing below this angle; collisions may still occur above it.")
            resp = input(f"Set altitude limit to {args.limit}°? [y/N]: ")
            if resp.lower() == 'y':
                mount.set_alt_limit(args.limit)
            else:
                print("Operation aborted.")
        elif args.cmd == "get-alt-limit":
            lim = mount.get_alt_limit()
            print(f"Current altitude limit: {lim}°")
        elif args.cmd == "status":
            mount.status()
        elif args.cmd == "set-az-limits":
            print("WARNING: This enforces a software azimuth limit for future slews.")
            resp = input(f"Set azimuth limits to [{args.lower:.4f}°, {args.upper:.4f}°]? [y/N]: ")
            if resp.lower() == 'y':
                # Validate logical range
                if not (0.0 <= args.lower < args.upper <= 360.0):
                    sys.exit("ERROR: Limits must satisfy 0 ≤ lower < upper ≤ 360.")
                az_lower = args.lower
                az_upper = args.upper
                print(f"Azimuth limits set to [{az_lower:.4f}°, {az_upper:.4f}°]")
            else:
                print("Operation aborted.")
        else:  # pragma: no cover – argparse guarantees we never hit this.
            sys.exit("Unknown command")


if __name__ == "__main__":
    main()
