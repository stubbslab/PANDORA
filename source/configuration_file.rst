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

.. code-block:: yaml

   database:
     type: "pandora.database.db.PandoraDatabase"
     db_path: "/Users/pandora_ctrl/Desktop"
  
   monochromator:
     type: "pandora.commands.monochromator.MonochromatorController"
     usb_port: "/dev/tty.usbserial-FTDI1CB2"
     baudrate: 9600
     # model: "Acton_SP2150"

   labjack:
     ip_address: "169.254.84.89"
     timeout: 2
     shutter: "FIO00"
     flipmount1: "FIO1"
     flipmount2: "FIO2"
     flipmount3: "FIO3"

