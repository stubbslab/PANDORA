import logging
from zaber_motion import Library, Units
from zaber_motion.ascii import Connection
from pandora.utils.socket_helper import is_port_open

"""
This script provides a class to control a Zaber stage via serial communication.

The Zaber stage should be powered on and connected to the computer via a USB port.

The distances units reported here are all in milimiters. 

"""

MASK_MAP = {'ND05': 7,
            'ND10': 7+39.37,
            'ND15': 7+39.37+33.20,
            'ND20': 7+39.37+33.20+34,
            'CLEAR': 7+39.37+33.20+34+35.20,
            }

class ZaberController:
    def __init__(self, ip_address, device=0, axis_id=1, slot_map=MASK_MAP, speed_mm_per_sec=8.0, name='foo', type=None):
        """
        Initialize the ZaberController object.

        Parameters:
        - ip_address (str): The ip_address to connect to the zaber controller. 
        - device (int): device id of the Zaber device.
        - axis (int): axis of the Zaber device.
        - speed_mm_per_sec (float): The movement speed in mm/s (default is 8mm/s).

        """
        self.ip_address = ip_address
        self.connection = None
        self.device = device
        self.axis_id = axis_id
        self.axis = None
        self.speed_mm_per_sec = speed_mm_per_sec
        self.slot_map = slot_map
        self.position = 'UNKNOWN'
        self.timeout_ms = 2000

        # Set up logging
        self.logger = logging.getLogger(f"pandora.zaber.{name}")

        # Enable Zaber's device database
        Library.enable_device_db_store()

        self.initialize()

    def initialize(self):
        """
        Initialize the Zaber connection.
        
        Steps:
        1. Connect to the Zaber device.
        2. Set the speed of the Zaber device.
        3. Move to the home position.
        """
        self.connect()
        self.set_zaber_speed(self.speed_mm_per_sec)
        self.get_current_slot()
        # self.go_home()
        pass

    def connect(self):
        """
        Establish the serial connection to the Zaber device.
        """
        if not self._is_connected():
            if not is_port_open(self.ip_address, 55550, timeout=self.timeout_ms/1000):
                self.logger.error(f"Cannot reach {self.ip_address}:55550 within {self.timeout_ms/1000:.2f} sec. Aborting connection.")
                self.instrument = None
                raise ConnectionError(f"Cannot reach zaber stage with ip adress {self.ip_address}. Please check if the instrument is on")

            try:
                self.connection = Connection.open_tcp(self.ip_address, Connection.TCP_PORT_CHAIN)
                devices = self.connection.detect_devices()

                if not devices:
                    self.logger.error("No Zaber devices detected.")
                    self.close()
                    return

                self.device = devices[self.device]
                self.axis = self.device.get_axis(self.axis_id)

                # self.set_zaber_speed(self.speed_mm_per_sec)
                self.logger.info(f"Connected to Zaber device on {self.ip_address} with speed {self.speed_mm_per_sec} mm/s.")

            except Exception as e:
                self.logger.error(f"Error: Could not connect to Zaber device on {self.ip_address}. {e}")
                self.connection = None
                self.close()
        else:
            self.logger.warning("Warning: Zaber connection already established.")

    def _is_connected(self):
        """Check if the connection is active."""
        return self.connection is not None and self.axis is not None
    
    def close(self):
        """
        Close the serial connection to the Zaber device.
        """
        if self._is_connected():
            self.connection.close()
            self.logger.info("Zaber connection closed.")
        self.connection = None
        self.device = None
        self.axis = None

    def move_to_slot(self, mask_slot_name):
        """
        Move the Zaber stage to a predefined mask slot.

        Parameters:
        - mask_slot_name (str): The name of the mask slot (e.g., "OD05", "OD10", ...).
        """
        if mask_slot_name not in list(self.slot_map.keys()):
            self.logger.error(f"Invalid mask slot name: {mask_slot_name}. Must be one of {list(self.mask_positions.keys())}.")
            return
        
        if not self._is_connected():
            self.connect()

        target_position = float(self.slot_map[mask_slot_name])

        self.logger.info(f"Zaber stage set to move to slot {mask_slot_name}")
        self.logger.debug(f"The position set to move is {target_position:.2f} mm")
        self.axis.move_absolute(target_position, Units.LENGTH_MILLIMETRES, True)
        self.position = mask_slot_name
        self.logger.info(f"Moved to mask slot {mask_slot_name} at {target_position:0.2f} mm.")

    def move_zaber_axis(self, distance_mm):
        """
        Move the Zaber stage by a relative distance.

        Parameters:
        - distance_mm (float): The distance to move in millimeters.
        """
        # check if there's an existinging connection 
        if not self._is_connected():
            self.connect()

        self.axis.move_absolute(distance_mm, Units.LENGTH_MILLIMETRES, True)
        self.logger.info(f"Moved Zaber axis by {distance_mm} mm.")
        self.position = str(distance_mm)

    def go_home(self):
        """
        Move the Zaber stage to the home position.
        """
        self.connect()
        self.axis.home()
        self.position = 'HOME'
        self.logger.info("Homed the Zaber stage.")

    def set_zaber_speed(self, speed):
        # check if there's an existinging connection 
        if not self._is_connected():
            self.connect()

        # Set movement speed (mm/sec)
        self.axis.move_velocity(speed, Units.VELOCITY_MILLIMETRES_PER_SECOND)

    def get_current_slot(self):
        """
        Get the current mask slot of the Zaber stage.
        """
        if not self._is_connected():
            self.connect()

        # Get the current position in mm
        current_position = self.get_position_mm()

        # Find the closest slot within 0.1 mm
        closest_slot = "UNKNOWN"
        for slot_name, slot_position in self.slot_map.items():
            if abs(current_position - slot_position) < 0.1:
                closest_slot = slot_name
                break
        
        self.position = closest_slot
        self.logger.info(f"Current slot: {closest_slot}")
    
    def get_position_mm(self):
        """
        Get the current position of the Zaber stage in millimeters.
        """
        # check if there's an existinging connection 
        if not self._is_connected():
            self.connect()

        position = self.axis.get_position(Units.LENGTH_MILLIMETRES)
        self.logger.info(f"Current position: {position:.3f} mm")
        return position

if __name__ == "__main__":
    from utils.logger import initialize_central_logger     
    # Set up logging
    initialize_central_logger("../zaberstage-main.log", "INFO")

    # Create an instance of ZaberController
    zb = ZaberController("169.254.47.12", speed_mm_per_sec=12)

    # Start at home state
    # zb.go_home()

    # Move by 5mm
    # zb.move_zaber_axis(20.0)

    # Move back by 2mm
    # zb.move_zaber_axis(-10.0)

    # Move to a predefined mask slot
    zb.move_to_slot(mask_slot_name="CLEAR")

    # Get the current position
    position = zb.get_position_mm()

    # Close the connection when done
    zb.close()
