import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.states.shutter_state import ShutterState
from pandora.states.labjack_handler import LabJack
from pandora.utils.logger import initialize_central_logger  

# Initialize the logger
initialize_central_logger("../shutter.log", "INFO")

ip_address = "169.254.84.89"
labjack = LabJack(ip_address)

# Initialize the shutter
shutter = ShutterState(name="FIO0", labjack=labjack)
shutter.deactivate()
