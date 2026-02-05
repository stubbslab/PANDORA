"""
IoptronController - iOptron HAZ-series Alt-Az telescope mount controller

This module provides a PANDORA-compatible controller for iOptron mounts
communicating through the Go2Nova 8409 hand-controller's USB-to-serial bridge.

Reference: iOptron RS-232 Command Language v3.10 (2021-01-04)

Safety Notes:
    - The system will not remember its home position across power cycles of both
      the remote controller AND the mount.
    - If a complete power loss occurs, the system on next startup will set
      whatever position it is at as the NEW ZENITH.
    - During the alignment wizard zenith homing procedure, the system will rotate
      a full 360 degrees, which could damage cables.
    - After power loss, zenith will need to be reacquired with the correct azimuth.
    - Check the altitude limit and parking position after power failures.
"""

import logging
import time
from typing import Optional, Tuple

import serial


class IoptronController:
    """Controller for iOptron HAZ-series Alt-Az telescope mounts.

    Args:
        port: Serial port device path (e.g., "/dev/cu.PL2303G-USBtoUART110")
        baudrate: Serial baudrate (default: 115200)
        timeout: Serial timeout in seconds (default: 2.0)
        monitor_enabled: If True, print raw TX/RX bytes for debugging
        name: Controller name for logging
        safety: Optional dict with safety parameters:
            - alt_limit_default: Default altitude limit in degrees
            - az_lower: Lower azimuth limit in degrees
            - az_upper: Upper azimuth limit in degrees
        type: Unused, for config file compatibility

    Example:
        mount = IoptronController(port="/dev/cu.PL2303G-USBtoUART110")
        mount.goto_altaz(45, 180)
        mount.park()
        mount.close()
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 2.0,
        monitor_enabled: bool = False,
        name: str = "ioptron",
        safety: Optional[dict] = None,
        type: Optional[str] = None,
    ) -> None:
        self.port_name = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.monitor_enabled = monitor_enabled
        self.name = name
        self.logger = logging.getLogger(f"pandora.mount.{name}")

        # Safety limits
        safety = safety or {}
        self.alt_limit_default = safety.get("alt_limit_default", 0)
        self.az_lower = safety.get("az_lower", 0.0)
        self.az_upper = safety.get("az_upper", 360.0)

        self.ser: Optional[serial.Serial] = None
        self._connect()

    # ---------- Connection Management -----------------------------------------

    def _connect(self) -> None:
        """Establish serial connection to the mount."""
        try:
            self.ser = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
        except serial.SerialException as exc:
            self.logger.error(f"Could not open {self.port_name!r}: {exc}")
            raise ConnectionError(
                f"Cannot connect to iOptron mount at {self.port_name}"
            ) from exc

        # Flush any stale data
        self.ser.reset_input_buffer()

        # Identify mount model (may fail harmlessly)
        try:
            model_code = self._cmd(":MountInfo#")
            self.logger.info(f"Connected to mount model code: {model_code.strip('#')}")
        except TimeoutError:
            self.logger.warning(":MountInfo# timed out; continuing anyway.")

        # Disable tracking by default
        try:
            self._cmd_single(":ST0#")
            self.logger.info("Tracking disabled by default.")
        except TimeoutError:
            pass

    def close(self) -> None:
        """Close the serial port connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.logger.info("Serial connection closed.")

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> "IoptronController":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---------- Low-Level Communication ---------------------------------------

    def _read_until_hash(self) -> str:
        """Read ASCII bytes until the terminating '#'."""
        buf = bytearray()
        start = time.monotonic()
        while True:
            b = self.ser.read(1)
            if not b:
                raise TimeoutError("Mount response timed out")
            if b == b"#":
                buf.append(ord("#"))
                return buf.decode("ascii")
            buf.append(b[0])
            if time.monotonic() - start > self.timeout:
                raise TimeoutError("Mount response timed out")

    def _cmd(self, payload: str, expect_reply: bool = True) -> Optional[str]:
        """Send a command and optionally read the response.

        Args:
            payload: Command string (will append '#' if missing)
            expect_reply: If True, wait for and return '#'-terminated response

        Returns:
            Response string if expect_reply is True, else None
        """
        if not payload.endswith("#"):
            payload += "#"
        if self.monitor_enabled:
            self.logger.debug(f"[RAW TX] {payload!r}")
        self.ser.write(payload.encode("ascii"))
        self.ser.flush()
        if expect_reply:
            resp = self._read_until_hash()
            if self.monitor_enabled:
                self.logger.debug(f"[RAW RX] {resp!r}")
            return resp
        return None

    def _cmd_single(self, payload: str) -> str:
        """Send a command and read exactly one reply byte.

        Several "set" commands acknowledge with a bare "1" or "0"
        rather than the usual hash-terminated string.

        Args:
            payload: Command string (will append '#' if missing)

        Returns:
            Single character response ("1" for success, "0" for failure)
        """
        if not payload.endswith("#"):
            payload += "#"
        if self.monitor_enabled:
            self.logger.debug(f"[RAW TX] {payload!r}")
        self.ser.write(payload.encode("ascii"))
        self.ser.flush()
        resp = self.ser.read(1)
        if self.monitor_enabled:
            self.logger.debug(f"[RAW RX] {resp!r}")
        if not resp:
            raise TimeoutError("Mount response timed out")
        return resp.decode("ascii")

    # ---------- Formatting Helpers --------------------------------------------

    @staticmethod
    def _format_altitude(deg_alt: float) -> str:
        """Convert degrees to sTTTTTTTT format (0.01 arc-sec units)."""
        if not -90.0 <= deg_alt <= 90.0:
            raise ValueError("Altitude must be in -90 to +90 degrees")
        units = int(round(deg_alt * 360_000))  # 1 deg = 3600 arcsec = 360000 centi-arcsec
        sign = "+" if units >= 0 else "-"
        return f"{sign}{abs(units):08d}"

    @staticmethod
    def _format_azimuth(deg_az: float) -> str:
        """Convert degrees to TTTTTTTTT format (0.01 arc-sec units)."""
        deg_az = deg_az % 360.0
        units = int(round(deg_az * 360_000))
        return f"{units:09d}"

    # ---------- High-Level API ------------------------------------------------

    def goto_altaz(
        self, alt_deg: float, az_deg: float, track_after: bool = False
    ) -> None:
        """Slew to the requested Alt/Az position.

        Args:
            alt_deg: Target altitude in degrees (-90 to +90)
            az_deg: Target azimuth in degrees (0 to 360)
            track_after: If True, enable tracking after slew

        Raises:
            RuntimeError: If mount refuses the command
            ValueError: If position is outside safety limits
        """
        # Safety checks
        if self.is_parked():
            raise RuntimeError("Mount is parked. Unpark before slewing.")

        alt_limit = self.get_alt_limit()
        if alt_deg < alt_limit:
            raise ValueError(
                f"Requested altitude {alt_deg:.4f} deg below limit {alt_limit} deg"
            )

        if not (self.az_lower <= az_deg <= self.az_upper):
            raise ValueError(
                f"Requested azimuth {az_deg:.4f} deg outside safe range "
                f"[{self.az_lower:.4f}, {self.az_upper:.4f}]"
            )

        alt_str = self._format_altitude(alt_deg)
        az_str = self._format_azimuth(az_deg)

        if self._cmd_single(f":Sa{alt_str}#") != "1":
            raise RuntimeError("Failed to accept altitude target")
        if self._cmd_single(f":Sz{az_str}#") != "1":
            raise RuntimeError("Failed to accept azimuth target")

        self.logger.info(f"Slewing to Alt={alt_deg:.4f}, Az={az_deg:.4f}...")
        time.sleep(0.1)  # Brief pause before issuing slew command

        if self._cmd_single(":MSS#") != "1":
            raise RuntimeError("Mount refused slew (limit hit?)")

        if track_after:
            self._cmd(":ST1#")

        # Wait for slew to complete
        self._wait_for_slew_complete()

        # Disable tracking after move unless explicitly requested
        if not track_after:
            self._cmd_single(":ST0#")
            self.logger.info("Tracking disabled.")

        self.logger.info("Slew complete.")

    def goto_home(self) -> None:
        """Slew to the mechanical zero (home/zenith) position."""
        self.logger.info("Slewing to home (zenith)...")
        if self._cmd_single(":MH#") != "1":
            raise RuntimeError("Mount failed to slew to home")

        self._wait_for_slew_complete()

        # Disable tracking after homing
        self._cmd_single(":ST0#")
        self.logger.info("Home position reached. Tracking disabled.")

    def park(self) -> None:
        """Move the mount to the stored parking position."""
        self.logger.info("Parking mount...")
        if self._cmd_single(":MP1#") != "1":
            raise RuntimeError("Park command failed")

        self._wait_for_stop()

        # Disable tracking after parking
        self._cmd_single(":ST0#")
        self.logger.info("Mount parked. Tracking disabled.")

    def unpark(self) -> None:
        """Unpark the mount, allowing movements."""
        self.logger.info("Unparking mount...")
        if self._cmd_single(":MP0#") != "1":
            raise RuntimeError("Unpark command failed")
        self.logger.info("Mount unparked.")

    def set_park(self, alt_deg: float, az_deg: float) -> None:
        """Define a new parking position (saved in non-volatile memory).

        Args:
            alt_deg: Altitude for park position in degrees
            az_deg: Azimuth for park position in degrees
        """
        alt_str = self._format_altitude(alt_deg)
        az_str = self._format_azimuth(az_deg)

        if self._cmd_single(f":SPH{alt_str}#") != "1":
            raise RuntimeError("Failed to set park altitude")
        if self._cmd_single(f":SPA{az_str}#") != "1":
            raise RuntimeError("Failed to set park azimuth")

        self.logger.info(
            f"Parking position set to Alt={alt_deg:.4f} deg, Az={az_deg:.4f} deg"
        )

    def get_park(self) -> Tuple[float, float]:
        """Retrieve the stored parking position.

        Returns:
            Tuple of (altitude_deg, azimuth_deg)
        """
        rsp = self._cmd(":GPC#")
        if not rsp.endswith("#") or len(rsp) < 18:
            raise RuntimeError(f"Unexpected :GPC# response: {rsp!r}")

        data = rsp.strip("#")
        alt_units = int(data[0:8])
        az_units = int(data[8:17])
        return alt_units / 360_000.0, az_units / 360_000.0

    def get_altaz(self) -> Tuple[float, float]:
        """Get the current Alt/Az position.

        Returns:
            Tuple of (altitude_deg, azimuth_deg)
        """
        rsp = self._cmd(":GAC#")
        if len(rsp) != 19 or not rsp.endswith("#"):
            raise RuntimeError(f"Unexpected :GAC# response: {rsp!r}")

        sign = 1 if rsp[0] == "+" else -1
        alt_units = int(rsp[1:9])
        az_units = int(rsp[9:18])
        return sign * alt_units / 360_000.0, az_units / 360_000.0

    def get_status(self) -> Tuple[float, float, str]:
        """Get current position and system state.

        Returns:
            Tuple of (altitude_deg, azimuth_deg, state_string)
        """
        alt, az = self.get_altaz()
        rsp = self._cmd(":GLS#")

        # 19th character (index 18) indicates system status
        code = rsp[18]
        state_mapping = {
            "0": "Stopped (non-zero)",
            "1": "Tracking",
            "2": "Slewing",
            "3": "Auto-guiding",
            "6": "Parked",
            "7": "Stopped (home)",
        }
        state = state_mapping.get(code, f"Unknown ({code})")
        return alt, az, state

    def is_parked(self) -> bool:
        """Check if the mount is currently parked."""
        _, _, state = self.get_status()
        return state == "Parked"

    def stop(self) -> None:
        """Emergency stop - immediately halt all motion."""
        self.logger.warning("Emergency stop commanded!")
        # Stop slewing with :Q#
        self._cmd(":Q#", expect_reply=False)
        # Also disable tracking
        self._cmd_single(":ST0#")
        self.logger.info("Mount stopped. Tracking disabled.")

    def set_alt_limit(self, deg: int) -> None:
        """Set the minimum altitude limit.

        Args:
            deg: Altitude limit in degrees (-89 to 89)
        """
        if not -89 <= deg <= 89:
            raise ValueError("Altitude limit must be between -89 and 89 degrees")

        sign = "+" if deg >= 0 else "-"
        limit_str = f"{sign}{abs(deg):02d}"

        if self._cmd_single(f":SAL{limit_str}#") != "1":
            raise RuntimeError("Failed to set altitude limit")

        self.logger.info(f"Altitude limit set to {deg} deg")

    def get_alt_limit(self) -> int:
        """Get the current altitude limit.

        Returns:
            Altitude limit in degrees
        """
        rsp = self._cmd(":GAL#")
        if not rsp.endswith("#") or len(rsp) < 3:
            raise RuntimeError(f"Unexpected :GAL# response: {rsp!r}")

        sign = rsp[0]
        nn = int(rsp[1:3])
        return nn if sign == "+" else -nn

    def enable_tracking(self, enabled: bool = True) -> None:
        """Enable or disable sidereal tracking.

        Args:
            enabled: If True, enable tracking; if False, disable
        """
        cmd = ":ST1#" if enabled else ":ST0#"
        self._cmd_single(cmd)
        state = "enabled" if enabled else "disabled"
        self.logger.info(f"Tracking {state}.")

    # ---------- Wait Helpers --------------------------------------------------

    def _wait_for_slew_complete(self, interval: float = 0.2) -> None:
        """Poll system status until slewing stops."""
        time.sleep(interval)  # Allow motion to begin
        while True:
            _, _, state = self.get_status()
            if state != "Slewing":
                break
            time.sleep(interval)

    def _wait_for_stop(self, interval: float = 0.2, threshold: float = 0.0005) -> None:
        """Poll position until movement stops.

        Motion is considered stopped when changes in both Alt and Az
        are below threshold degrees.
        """
        time.sleep(interval)  # Allow motion to begin
        prev_alt, prev_az = self.get_altaz()
        while True:
            time.sleep(interval)
            alt, az = self.get_altaz()
            if abs(alt - prev_alt) < threshold and abs(az - prev_az) < threshold:
                break
            prev_alt, prev_az = alt, az
