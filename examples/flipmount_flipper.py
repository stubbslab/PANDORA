import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.states.flipmount_state import FlipMountState
from pandora.states.labjack_handler import LabJack
from pandora.utils.logger import initialize_central_logger  

# Initialize the logger
initialize_central_logger("../shutter.log", "INFO")

ip_address = "169.254.84.89"
labjack = LabJack(ip_address)
import time 

mydict = {
"flipShutter": "FIO00",
"flipSpecMount": "FIO1",
"flipOrderBlockFilter": "FIO2",
"flipOD2First": "FIO3",
"flipOD2Second": "FIO4",
"flipPD2": "FIO5",
"flipQuaterWavePlate": "FIO6",
"flipPD3": "FIO7",
}
# Initialize the shutter
for i, name in enumerate(mydict.keys()):
    print(10*"------")
    print(name)
    print(mydict[name])
    time.sleep(2)
    fm = FlipMountState(mydict[name], labjack=labjack)
    fm.deactivate()

    time.sleep(3)
    fm.activate()
    print(10*"------")
    
    input("Should we continue?")
    
# fm = FlipMountState(mydict["flipOD2Second"], labjack=labjack)
# fm.deactivate()