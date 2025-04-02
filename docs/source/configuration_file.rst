Configuration file
==================

.. _configuration_file:

The configuration file is a YAML file that contains the configuration for the
PandoraBox. It is used to specify the subsystems that are available, their
configuration, and the default values for the subsystems.

The configuration file is loaded when the PandoraBox is initialized. The
configuration file is specified as a command line argument when running the
PandoraBox.

An example configuration file is shown below:

.. literalinclude:: ../../default.yaml
   :language: yaml

.. .. code-block:: yaml

..   # Configuration file for the Pandora system
..   # This file contains the default settings for the system components
..   # and their parameters.
..   database:
..     type: "pandora.database.db.PandoraDatabase"
..     root: "/Users/pandora_ctrl/Documents/pandoraData/"

..   monochromator:
..     type: "pandora.controller.monochromator.MonochromatorController"
..     usb_port: "/dev/tty.usbserial-FTDI1CB2"
..     baudrate: 9600
..     # model: "Acton_SP2150"

..   labjack:
..     ip_address: "169.254.84.89"
..     timeout: 2
..     flipShutter: "FIO00"
..     flipSpecMount: "FIO1"
..     flipOrderBlockFilter: "FIO2"
..     flipOD2First: "FIO3"
..     flipOD2Second: "FIO4"
..     flipPD2: "FIO5"
..     flipQuarterWavePlate: "FIO6"
..     flipPD3: "FIO7"
    
..     # Changes to the logic of the flip signals
..     # Default is low signal on the beam, high out of the beam
..     flipSpecMountInvertLogic: False
..     flipOrderBlockFilterInvertLogic: False
..     flipOD2FirstInvertLogic: False
..     flipOD2SecondInvertLogic: False
..     flipPD3InvertLogic: False
..     flipQuarterWavePlateInvertLogic: True
..     flipPD2InvertLogic: True

..   keysights:
..     type: "pandora.controller.keysight.KeysightController"
..     # Each Keysight device with its own IP address
..     K1:
..       name: "k1"
..       keysight_ip: "169.254.5.2"
..       timeout_ms: 25000
..       settings:
..         mode: "CURR"
..         rang: 'AUTO'
..         nplc: 10.
..         nsamples: 50
..         delay: 0.
..         interval: 2e-3
..     K2:
..       name: "k2"
..       keysight_ip: "169.254.124.255"
..       timeout_ms: 25000
..       settings:
..         mode: "CURR"
..         rang: 'AUTO'
..         nplc: 10.
..         nsamples: 50
..         delay: 0.
..         interval: 2e-3

..   zaber_stages:
..     type: "pandora.controller.zaberstages.zaberController"
..     Z1: # ND Filter
..       ip_address: "140.247.113.250"
..       # ND filters map
..       # The numbers refers to the zaber position in mm
..       slot_map: {'ND20': 7, 
..                 'ND15': 46.37, 
..                 'ND10': 79.57, 
..                 'ND05': 113.57, 
..                 'CLEAR': 148.77}
..       device: 0
..       axis_id: 1
..       # Zaber speed in mm/sec
..       speed_mm_per_sec: 10
..       name: "nd-filter"
..     Z2: # Focus SN: 132383 FW: 7.41.17786 
..       ip_address: "140.247.113.251"
..       device: 0
..       axis_id: 1
..       speed_mm_per_sec: 10
..       # The focus position is given in mm
..       # the focus position is very sensitive to positional changes
..       slot_map: {'FOCUS': 50.8}
..       name: "focus"
..     Z3: # Pinhole Mask
..       ip_address: "140.247.113.252"
..       # Pinhole mask map
..       # The numbers refers to the zaber position in mm
..       # The pinhole mask is a 4-position wheel with the following configuration:
..       # 1. 50 um pinhole (P50um)
..       # 2. 100 um pinhole (P100um)
..       # We do not have clear
..       slot_map: {
..                 'P200UM': 14.02,
..                 'P100UM': 45.94,
..                 'CLEAR': 50.8,
..                 }
..       device: 0
..       axis_id: 1
..       speed_mm_per_sec: 10
..       name: "pinhole-mask"

..   spectrograph:
..     type: "pandora.controller.stellarnet.SpectrographController"
..     inttime: 1 # ms
..     scan_avg: 10
..     xtiming: 1 # 1/2 or 3 (low/mid or high resolution) 
..     smooth: 1

..   logging:
..     level: "INFO"
..     logfile: "./pandora.log"
