.. Pandora Documentation documentation master file, created by
   sphinx-quickstart on Thu Feb 20 17:24:21 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Pandora
=================================================

.. toctree::
   :maxdepth: 1
   :caption: Contents

   command_line
   wavelength_scans
   controlling_subsystems
   configuration_file
   database_access

Overview
--------

Welcome to the PANDORA project documentation. PANDORA is a versatile instrument
control system that orchestrates multiple laboratory subsystems—such as the
monochromator, shutter, flip mounts, Keysight electrometers, and Zaber stages—
to provide a unified, automated workflow. This documentation offers a
high-level introduction, installation guidance, quick-start examples, and
detailed API references.

How to Install
--------------

Installation instructions are under development. Please check back soon for
a comprehensive guide on setup, configuration, and dependency management.

Command Line Interface
----------------------

The PANDORA project includes a command-line interface (CLI) for quick access to
common functionalities. This allows you to control subsystems, set parameters,
and perform measurements without writing a full Python script.

To use the CLI, simply run the ``pb`` command followed by the desired action. For example:

.. code-block:: bash

  # Set the monochromator to 500 nm
  pb set-wavelength 500

  # Open the shutter
  pb open-shutter

  # Get 1 second electrometer readout
  pb get-keysight-readout 1 --name K2 --nplc 10 --autoRange

  # Get a spectrum plot
  pb get-spectrometer-readout 50 --is_plot

  # Close the shutter
  pb close-shutter

This command will set the monochromator to 500 nm, open the shutter, move a flip mount named "pd2" into the beam, and acquire a short spectrometer reading (50 ms) while plotting the result.

Please refer to the :doc:`Command Line Interface <command_line>` documentation for a full list of commands and options.


Quick Start
-----------

Kickstart your experience with PANDORA using this minimal example:

.. code-block:: python

   from pandora_controller import PandoraBox
   pandora = PandoraBox()
   pandora.initialize_subsystems()

.. code-block:: text
  
   Hello, world!

.. .. program-output:: python ../examples/iniatite.py
..    :caption: Example Output
..    :name: example-output

Upon initialization, the subsystems assume their default safe states:

- **Monochromator:** go to home state (400 nm).
- **Shutter:** Closed, blocking the light path.
- **Flip Mounts:** Not on the optical path.
- **Keysight Electrometers:** On standby.
- **Zaber Stages:** At home (off light path).

Once the subsystems are initialized, you can control them individually
or in combination to suit your experimental needs.

For more details on controlling the hardware, see the :doc:`Controlling Subsystems <controlling_subsystems>`.


API Reference
-------------

For a detailed breakdown of classes, methods, and usage examples, please
refer to the `PANDORA Controller API Documentation <api/module.md>`_.

Additional Resources
--------------------

- **User Guides:** Comprehensive tutorials and operational tips will be added soon.
- **Troubleshooting:** Find common issues and their solutions.
- **Contributing:** Learn how to contribute improvements to PANDORA and its documentation.

Happy experimenting with PANDORA!

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
