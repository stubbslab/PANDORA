.. _wavelength_scans:

Wavelength Scan Measurements
============================

.. warning::

   These measurement commands are **under construction**. The interface and behavior may change in future releases. Please report any issues or suggestions.

This page documents the automated wavelength scan measurement commands available in PANDORA. These commands coordinate the monochromator, electrometers, shutter, and other subsystems to perform systematic measurements across a wavelength range.

Overview
--------

PANDORA provides several wavelength scan commands for different measurement scenarios:

.. list-table:: Wavelength Scan Commands
   :header-rows: 1
   :widths: 30 70

   * - Command
     - Description
   * - ``measure-pandora-throughput``
     - Basic throughput measurement (current mode)
   * - ``measure-pandora-throughput-beta``
     - Enhanced throughput with dark measurements
   * - ``measure-pandora-tput-final``
     - Production-ready scan with overflow handling
   * - ``measure-pandora-charge``
     - Charge accumulation measurement (coulomb mode)


Throughput Measurements
-----------------------

The throughput commands measure the ratio of main beam flux to monitor diode flux across wavelengths using current mode on the Keysight electrometers.

**Basic Throughput Scan**

.. note::

   This command is under construction and may have limited functionality.

.. code-block:: bash

   pb measure-pandora-throughput <exptime> <lambda0> <lambdaEnd> [options]

**Arguments:**

- ``exptime``: Exposure time per measurement point (seconds)
- ``lambda0``: Start wavelength (nm)
- ``lambdaEnd``: End wavelength (nm)

**Options:**

- ``--step <nm>``: Wavelength step size (default: 1 nm)
- ``--ndFilter <name>``: ND filter to use (ND05, ND10, ND15, ND20, CLEAR)
- ``--nrepeats <n>``: Number of repeats per wavelength (default: 5)
- ``--verbose``: Enable verbose output

**Example:**

.. code-block:: bash

   # Scan from 400-700 nm with 5 nm steps, 2 second exposures
   pb measure-pandora-throughput 2 400 700 --step 5 --ndFilter ND10 --nrepeats 10


**Enhanced Throughput Scan (Beta)**

.. note::

   This command is under construction. The beta version includes additional features being tested.

.. code-block:: bash

   pb measure-pandora-throughput-beta <exptime> <lambda0> <lambdaEnd> [options]

Additional options over the basic version:

- ``--darktime <s>``: Dark measurement time between light measurements
- ``--flip <name>``: Flip mount to activate before measurement (e.g., flipPD2)

**Example:**

.. code-block:: bash

   # Scan with dark measurements between each point
   pb measure-pandora-throughput-beta 1 400 700 --step 5 --darktime 0.5 --nrepeats 50


**Production Throughput Scan (Final)**

.. note::

   This command is under construction but represents the most robust implementation with automatic overflow handling.

This version includes automatic handling of range overflows and proper dark measurements when the electrometer range changes.

.. code-block:: bash

   pb measure-pandora-tput-final <exptime> <lambda0> <lambdaEnd> [options]

**Options:**

- ``--step <nm>``: Wavelength step size (default: 1 nm)
- ``--ndFilter <name>``: ND filter on Zaber stage
- ``--nrepeats <n>``: Repeats per wavelength (only successful measurements counted)
- ``--darktime <s>``: Dark block time (defaults to exptime if not specified)
- ``--verbose``: Enable verbose logging

**Features:**

- Automatic dark measurement before/after range changes
- Automatic retry of failed light measurements due to overflow
- Only counts successful measurements toward repeat count

**Example:**

.. code-block:: bash

   # Production scan from 350-750 nm
   pb measure-pandora-tput-final 0.5 350 750 --step 2 --ndFilter CLEAR --nrepeats 100 --verbose


Charge Measurements
-------------------

.. note::

   This command is under construction. Charge mode measurement is experimental.

The charge measurement command uses the B2985B/B2987B electrometer in coulomb meter mode to measure accumulated charge vs wavelength. This mode integrates current over time using a feedback capacitor, which can provide better signal-to-noise for certain applications.

.. code-block:: bash

   pb measure-pandora-charge <exptime> <lambda0> <lambdaEnd> [options]

**Arguments:**

- ``exptime``: Integration time per measurement (seconds)
- ``lambda0``: Start wavelength (nm)
- ``lambdaEnd``: End wavelength (nm)

**Options:**

- ``--step <nm>``: Wavelength step size (default: 1 nm)
- ``--nrepeats <n>``: Number of repeats per wavelength (default: 100)
- ``--darktime <s>``: Dark exposure time (defaults to exptime)
- ``--discharge``: Discharge capacitor before each acquisition (default: enabled)
- ``--no-discharge``: Skip discharge for continuous charge accumulation
- ``--verbose``: Enable verbose output

**Example:**

.. code-block:: bash

   # Charge measurement scan from 400-600 nm
   pb measure-pandora-charge 1.0 400 600 --step 5 --nrepeats 50 --verbose

   # Without discharging between measurements (continuous accumulation)
   pb measure-pandora-charge 1.0 400 600 --step 5 --no-discharge

**Charge Mode Notes:**

- The feedback capacitor is automatically discharged (zeroed) before each measurement unless ``--no-discharge`` is specified
- Available charge ranges: 2 nC, 20 nC, 200 nC, 2 µC
- Auto-discharge can be configured to automatically reset the integrator when approaching range limits


Data Output
-----------

All wavelength scan commands save measurement data to the PANDORA database. The output includes:

- Timestamps for each measurement
- Wavelength values
- Electrometer readings (current or charge)
- Dark measurements (where applicable)
- Metadata (ND filter, repeat count, etc.)

See :doc:`Database Access <database_access>` for information on retrieving and analyzing measurement data.


Best Practices
--------------

1. **Warm-up**: Allow electrometers to warm up for at least 30 minutes before precision measurements.

2. **Dark measurements**: Use the ``--darktime`` option to interleave dark measurements for background subtraction.

3. **Range selection**: For throughput scans, the auto-range feature adjusts the electrometer range automatically. For charge measurements, select an appropriate fixed range based on expected signal levels.

4. **ND filters**: Use appropriate ND filters to keep signals within the optimal measurement range, especially at wavelengths with high source intensity.

5. **Repeat counts**: Higher repeat counts improve statistical precision. Use ``--nrepeats 100`` or more for production measurements.


Troubleshooting
---------------

**Overflow errors**: If you see overflow errors, try:

- Using a less sensitive range (higher ``--rang0`` value)
- Adding ND filters to reduce signal intensity
- Using ``measure-pandora-tput-final`` which handles overflows automatically

**Slow scans**: Reduce ``--nrepeats`` or increase ``--step`` for faster exploratory scans.

**Noisy data**: Increase ``--nplc`` for longer integration times, or increase ``--nrepeats`` for better averaging.


See Also
--------

- :doc:`Command Line Interface <command_line>` - General CLI documentation
- :doc:`Controlling Subsystems <controlling_subsystems>` - Direct subsystem control
- :doc:`Configuration File <configuration_file>` - System configuration options
