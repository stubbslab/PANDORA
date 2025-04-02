import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.states.flipmount_state import FlipMountState
from pandora.states.labjack_handler import LabJack
from pandora.utils.logger import initialize_central_logger  

# Initialize the logger
initialize_central_logger("../shutter.log", "DEBUG", verbose=True)

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

def shall_we_go():
    answer = str(input("Should we continue (y/n)?"))
    if answer == "n":
        print("Exiting...")
        exit()

value = int(input("Enter the labjack port number (e.g. 0): "))
name = "FIO0%i"%value

# Initialize the flipMount
print(10*"------")
print(10*"------")
print(f"Activating {mydict[name]} with labjack port {name}")
fm = FlipMountState(name, labjack=labjack)

# Check the state
s = fm.get_state()
print(f"Current state: {s.value}")
shall_we_go()

# Check the high signal
time.sleep(1)
print(f"Sending high signal to {name}")
fm.labjack.send_high_signal(name)
shall_we_go()

# Check the high signal
time.sleep(1)
print(f"Sending low signal to {name}")
fm.labjack.send_low_signal(name)
shall_we_go()

# Check the square signal
time.sleep(1)
print(f"Sending square signal to {name}")
fm.labjack.send_binary_signal(name, wait_time_ms=50)
shall_we_go()

# Check flipMount activate function
time.sleep(1)
print(f"Check flipMount activate function: {name}")
fm.activate()
shall_we_go()

# Check flipMount deactivate function
time.sleep(1)
print(f"Check flipMount deactivate function: {name}")
fm.deactivate()

print("The test is complete.")
print(10*"------")