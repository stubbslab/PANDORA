#!/usr/bin/env python3
import pyvisa
import csv
import os
import time
import argparse
from datetime import datetime

###### Read Config File #######
script_dir = os.path.dirname(os.path.realpath(__file__))
config_filename = os.path.join(script_dir, "../../default.yaml")
def _load_config(config_file):
    # Parse a config file (JSON, YAML, etc.) with device parameters
    import yaml
    # get current working directory
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

configDefault = _load_config(config_file=config_filename)

def get_config_section(section, config=configDefault):
    return config.get(section, {})    
###############################

def start_acquisition(args):
    # Open VISA resource
    inst = initiate_keysight(args)

    # Clear status, errors, and any existing buffer
    inst.write('*CLS')
    inst.write(':ABOR')

    # 3) _Clear_ the trace buffer before you re‐configure it
    inst.write(':TRACe:CLEar')                        # ← clears out old points :contentReference[oaicite:0]{index=0}
    inst.write(':TRACe:FEED:CONTrol NEXT')             # ← set feed mode to “next” so you start fresh :contentReference[oaicite:1]{index=1}

    # Configure current measurement parameters
    inst.write(':SENS:FUNC "CURR"')
    inst.write(":SENS:CURR:RANG:AUTO OFF")
    inst.write(f':SENS:CURR:NPLC {args.nplc}')
    if args.rang0 is not None:
        inst.write(f':SENS:CURR:RANG {args.rang0}')

    # if args.autoRange:
    #     inst.write(':SENS:CURR:RANG:AUTO ON')

    # # Configure trace buffer depth
    # inst.write(f':TRAC:POIN {args.points}')

    # Set data format to ASCII and include status
    # inst.write(':FORMat:DATA ASCII')
    # inst.write(':FORMat:ELEM CURR,STAT')

    # Start continuous acquisition
    # inst.write(':INITiate:CONTinuous ON')
    inst.write('INP ON')

    print("Continuous acquisition started.")


def stop_acquisition(args):
    # Open VISA resource
    inst = initiate_keysight(args)

    # Stop continuous acquisition
    # inst.write(':INITiate:CONTinuous OFF')
    inst.write('INP OFF')
    # inst.query('*OPC?')        # wait for instrument to finish
    
    # Delay to ensure data is ready
    time.sleep(0.5)

    # 3) Figure out how many points you have
    float(inst.query('MEAS:CURR?')[0:-1])
    total = int(inst.query(':TRACe:DATA:COUNt?'))
    print(f"Total points: {total}")

    # 4) Retrieve in blocks
    block = 1000
    raw = []
    for i in range(1, total+1, block):
        j = min(i+block-1, total)
        raw.extend(inst.query(f':TRACe:DATA? {i},{j}').split(','))

    # Get per-point delay (seconds)
    delay = float(inst.query(':TRACe:DELay?'))

    # Prepare filename with timestamp
    fname = datetime.now().strftime("%m%d%Y-%H%M") + ".csv"

    # Write CSV: row, elapsed_time_s, current_A, status
    with open(fname, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["row", "elapsed_time_s", "current_A", "status"])
        for i in range(n):
            curr = float(raw[2*i])
            stat = int(raw[2*i+1])
            elapsed = i * delay
            writer.writerow([i+1, elapsed, curr, stat])

    print(f"Data saved to {fname}")

def initiate_keysight(args):
    name = args.name

    # Create an instance of the KeysightController
    _kconfig = get_config_section('keysights')
    if name not in _kconfig.keys():
        print(f"List of available keysight devices: {_kconfig.keys()}")
        raise ValueError(f"Keysight device {name} not found in config file.")

    # get the ip address of the keysight device
    ip_address = _kconfig[name]['keysight_ip']

    # Open the pyVISA resource
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(f'TCPIP0::{ip_address}::INSTR')

    inst.timeout = 100000 #Keysight timeout in milliseconds - needs to be high if n_pl_cycles is high
    return inst

if __name__ == "__main__":
    import pyvisa
    # ip_address = "169.254.124.255"
    ip_address = "169.254.5.2"
    nplc = 1

    # Create an instance of the KeysightController
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(f"TCPIP::{ip_address}::hislip0,4880::INSTR")
    inst.timeout = 100000 #Keysight timeout in milliseconds - needs to be high if n_pl_cycles is high

    # Check current power line frequency setting
    current_freq = inst.query(":SYST:LFREQ?")
    print(f"Current line frequency: {current_freq.strip()} Hz")

    # Set power line frequency explicitly to 60 Hz
    inst.write(":SYST:LFREQ 60")
    time.sleep(0.1)  # brief pause to ensure command is executed

    # Verify change
    new_freq = inst.query(":SYST:LFREQ?")
    print(f"Updated line frequency: {new_freq.strip()} Hz")

    inst.write('SENSe:FUNCtion:ON "CURR"')
    inst.write(":SENS:CURR:RANG:AUTO OFF")

    inst.write(':SENS:CURR:NPLC:AUTO OFF')
    inst.write(f':SENS:CURR:NPLC {nplc}')

    # Initiate the electrometer measurement
    # inst.write('INP ON')
    
    print(float(inst.query('MEAS:CURR?')[0:-1]))

    # # print power line frequency
    # print("Power line frequency:")
    # print(float(inst.read(':SYST:POWE:FREQ?')))

