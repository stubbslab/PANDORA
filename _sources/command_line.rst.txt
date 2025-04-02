.. _pandora_box_command_line:

PB Command-Line Interface
=================================

This page provides usage instructions and examples for the PandoraBox command line (“pb”). These commands let you control PANDORA’s various subsystems—such as the shutter, monochromator, flip mounts, Keysight electrometers, spectrometer, and Zaber stages—individually.

Prerequisites: 
-------------------------------------------

Before running any ``pb`` command, configure your terminal:

.. code-block:: bash

   # Change directory to your PANDORA root folder
   cd ${HOME}/Documents/dev/versions/v1.0/PANDORA/

   # Add the pandora folder to your PYTHONPATH
   export PYTHONPATH="${PWD}:${PYTHONPATH}"

   # Create an alias so you can call pb anywhere
   alias pb="python ${HOME}/Documents/dev/versions/v1.0/PANDORA/pandora/commands/pb.py"

You will then be able to use the ``pb`` command from any directory in your terminal session.

Overview
------------------------------

To see all available commands and options, type:

.. code-block:: bash

   pb -h

The output lists all subcommands and general usage:

.. code-block:: text

   usage: pb.py [-h]
                {measure-pandora-throughput,set-wavelength,get-wavelength,
                 open-shutter,close-shutter,get-keysight-readout,
                 get-spectrometer-readout,flip,zaber}
                ...

   PandoraBox Command-Line Interface (commands)

   positional arguments:
     {measure-pandora-throughput,set-wavelength,get-wavelength,open-shutter,
      close-shutter,get-keysight-readout,get-spectrometer-readout,flip,zaber}
       measure-pandora-throughput    Measure throughput linking main beam flux
                                     to monitor diode flux.
       set-wavelength                Set the monochromator to a specific
                                     wavelength.
       get-wavelength                Get the current wavelength of the
                                     monochromator.
       open-shutter                  Open the shutter.
       close-shutter                 Close the shutter.
       get-keysight-readout          Get the readout from the Keysight
                                     electrometer.
       get-spectrometer-readout      Get the readout from the StellarNet
                                     spectrometer.
       flip                          Control flip mounts (on/off/state, or list
                                     mount names).
       zaber                         Control Zaber stages.

   options:
     -h, --help    show this help message and exit

Use ``pb <command> --help`` for additional details on each command’s options.

Shutter Commands
----------------

To control the shutter, you can open or close it:

.. code-block:: bash

   pb open-shutter
   pb close-shutter

You may also add ``--verbose`` for more detailed console output:

.. code-block:: bash

   pb open-shutter --verbose

Monochromator
---------------------------------

To set the monochromator to a specific wavelength (in nanometers):

.. code-block:: bash

   pb set-wavelength 500

To retrieve the current wavelength:

.. code-block:: bash

   pb get-wavelength

Flip Mounts
-----------

Flip mounts are controlled with the ``flip`` subcommand. You can turn a mount on or off or query its current state:

.. code-block:: bash

   pb flip (mount_name) --on
   pb flip (mount_name) --off
   pb flip (mount_name) --state

To list all flip mount names recognized by the system:

.. code-block:: bash

   pb flip --listNames

Example usage:

.. code-block:: bash

   pb flip pd2 --on
   pb flip second-order-filter --off

Keysight Electrometers
----------------------

Retrieve Keysight electrometer data with:

.. code-block:: bash

   pb get-keysight-readout <exptime> [--name K1|K2] [--rang0 <value>]
                                   [--nplc <int>] [--autoRange]
                                   [--verbose]

Where:

- ``exptime`` is the measurement duration (in seconds).
- ``--name K1`` or ``--name K2`` selects which Keysight electrometer (default: K1).
- ``--rang0 2e-9`` sets a specific measurement range.
- ``--autoRange`` automatically determines the optimum measurement range.
- ``--nplc 10`` sets the integration time in terms of line cycles (default = 10).
- ``--verbose`` prints additional console output.

Examples:

.. code-block:: bash

   pb get-keysight-readout 2 --rang0 2e-9
   pb get-keysight-readout 2 --name K2 --autoRange
   pb get-keysight-readout 2 --name K2 --rang0 2e-9 --verbose

Spectrometer
------------

Obtain a spectrometer reading, including exposure and other parameters:

.. code-block:: bash

   pb get-spectrometer-readout <exptime> [--scanavg <num_scans>]
                                         [--xtiming 1|2|3]
                                         [--is_plot] [--verbose]

Where:

- ``<exptime>`` is exposure time in milliseconds.
- ``--scanavg <num_scans>`` averages multiple scans.
- ``--xtiming <mode>`` sets the spectrometer resolution mode (default = 3, highest).
- ``--is_plot`` displays a plot of intensity (counts) vs. wavelength (nm).
- ``--verbose`` prints additional details.

Example:

.. code-block:: bash

   pb get-spectrometer-readout 20 --is_plot

Zaber Stages
------------

Use the ``zaber`` subcommand to query and move Zaber stages:

.. code-block:: bash

   pb zaber [-h] [--listZaberNames] [--listSlotTable]
            [--move <mm_position>] [--verbose]
            <controller_name> [slot]

**Positional Arguments**:

- ``controller_name``: The name of the Zaber controller (e.g., nd-filter, pinhole, focus).
- ``slot``: The slot name (e.g., home, clear, ND20, etc.) if not using ``--move``.

**Options**:

- ``--listZaberNames``: Lists all known Zaber controller names.
- ``--listSlotTable``: Lists the slot table for the specified controller.
- ``--move <mm_position>``: Moves to a specified position (in mm).
- ``--verbose``: Prints extra console output.

Examples:

- **List all Zaber controllers**:

  .. code-block:: bash

     pb zaber --listZaberNames

- **Move a Zaber stage to a named slot**:

  .. code-block:: bash

     pb zaber nd-filter clear

- **Return a Zaber stage to home**:

  .. code-block:: bash

     pb zaber nd-filter home

- **List slot table for a given controller**:

  .. code-block:: bash

     pb zaber nd-filter --listSlotTable

- **Move stage to a specific mm position**:

  .. code-block:: bash

     pb zaber nd-filter --move 20


Further Reading
---------------

For more details, refer back to the main documentation pages on subsystem control and the PANDORA API:

- :doc:`Controlling Subsystems <controlling_subsystems>`
- :doc:`PANDORA Controller API <api/modules>`

This command-line interface is a convenient way to script, automate, or quickly test your laboratory workflows without needing to write Python code in a separate file. For larger automation tasks, consider using the Python API directly.

.. note::

   If you encounter issues or need advanced troubleshooting, please refer to additional resources in the :doc:`configuration_file` and :doc:`database_access` documentation, or consult the upcoming “Installation” and “User Guides” sections.