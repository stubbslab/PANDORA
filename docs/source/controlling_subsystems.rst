
Controlling Subsystems
======================

This section provides users with a clear understanding of how to control 
each subsystem of the PANDORA system.


.. _shutter:

Shutter
-------

Controlled via the ``ShutterState`` class, the **Shutter** subsystem
manages the light path by opening or closing the shutter. Connected through
the LabJack, it determines if lights enter the optical path or not.

.. code-block:: python

   # Example: Open the shutter
   pandora.open_shutter()

   # Example: Close the shutter
   pandora.close_shutter()

To check the connection please refer to the :ref:`LabJack Interface <labjack-interface>` section.

.. _monochromator:

Monochromator
-------------

The **Monochromator** subsystem is managed by the
``MonochromatorController``. It is responsible for tuning the system's
wavelength and ensuring the device starts in its home position (typically
400 nm). This subsystem plays a key role in wavelength
calibration.

To access from the main controller, use:

.. code-block:: python

   monochromator = pandora.monochromator

   # Example: Move to 500 nm
   monochromator.move_to_wavelength(500)

   # Example: Move to home position
   monochromator.go_home()

   # Example: Get current wavelength
   monochromator.get_current_wavelength()


.. _flip-mounts:

Flip Mounts
-----------

The **Flip Mounts** subsystem comprises multiple units (e.g., ``f1``,
``f2``, ``f3``), each handled by an instance of ``FlipMountState``.
These flip mounts are linked to specific LabJack ports and enable rapid
switching of optical paths—ensuring that only the desired signals reach
the detectors while others remain safely out of the light path.

.. code-block:: python

   # There are many flipmounts

   # Example: Activate flip mount 1 (IR blocking filter)
   f1 = pandora.flip_mounts.f1
   # Put on the optical path
   f1.activate()
   # Move out of the optical path
   f1.deactivate()

   # Example: Deactivate flip mount 2 (neutral density filter)
   f2 = pandora.flip_mounts.f2
   f2.activate()

.. _zaber-stages:

Zaber Stages
------------

The **Zaber Stage** subsystem, managed by the ``ZaberController``, is used
to position optical components (like neutral density filters) within the
light path. Precise control over this stage ensures accurate alignment
and optimal system configuration for various experimental setups.

.. _labjack-interface:

LabJack Interface
-----------------

The **LabJack** serves as the central digital I/O controller. It connects
directly with the shutter, flip mounts, and other peripherals, facilitating
coordinated control across all subsystems. Its integration is essential for
synchronizing the operation of hardware components throughout the PANDORA
system.

Keysight Electrometers
----------------------

Represented by instances of ``KeysightState`` (such as ``k1`` and ``k2``),
the **Keysight Electrometers** perform high-precision electrical
measurements. They are configured to monitor currents accurately during
exposures, whether in light or dark conditions, providing critical data
for the system's performance.
