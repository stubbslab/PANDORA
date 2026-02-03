import numpy as np
import matplotlib.pyplot as plt
import time

import os

script_dir = os.path.dirname(os.path.realpath(__file__))
config_filename = os.path.join(script_dir, "../default.yaml")

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


def _initialize_logger(verbose=True):
    from pandora.utils.logger import initialize_central_logger
    # Setup and return a logger instance for the Pandora class
    logging_config = get_config_section('logging')
    logger = initialize_central_logger(logging_config['logfile'], logging_config['level'], verbose)
    return logger
    
def test_nplc_effect(keysight_device, nplc_values=[0.1, 0.3, 0.5, 1, 3, 5, 8, 10], nsamples=100, rang0=None):
    """
    Test whether increasing NPLC reduces measurement noise.

    Args:
        keysight_device (Keysight): An instance of the Keysight class.
        nplc_values (list): List of NPLC values to test.
        nsamples (int): Number of samples to acquire per test.

    Returns:
        list of (nplc, stddev, mean) tuples
            Each tuple contains the NPLC value, noise standard deviation, and mean current.
    """
    noise_results = []

    for nplc in nplc_values:
        print(f"\n--- Testing NPLC = {nplc} ---")
        keysight_device.set_nplc(nplc)
        keysight_device.set_nsamples(nsamples)
        keysight_device.set_delay(0)
        keysight_device.set_mode('CURR')
        if rang0 is not None:
            keysight_device.set_rang(f'{rang0}')
        else:
            keysight_device.auto_scale()

        keysight_device.on()
        keysight_device.acquire()
        data = keysight_device.read_data()
        keysight_device.off()

        readings = data['CURR']
        stddev = np.std(readings)
        mean = np.mean(readings)

        print(f"Mean = {mean:.3e} A, StdDev = {stddev:.3e} A")
        noise_results.append((nplc, stddev, mean))

        time.sleep(1)

    return noise_results


def plot_noise_vs_nplc(results, fig=None, axs=None):
    """
    Plot noise standard deviation and mean current vs. NPLC setting.

    Args:
        results (list of (nplc, stddev, mean)): Output from test_nplc_effect.
    """
    nplc_vals, std_vals, mean_vals = zip(*results)

    if fig is None or axs is None:
        fig, axs = plt.subplots(2, 1, figsize=(8, 8), sharex=True)
    else:
        # in case caller passed a single Axes
        fig.clf()
        axs = fig.subplots(2, 1, sharex=True)

    # --- StdDev panel ---
    axs[0].plot(nplc_vals, std_vals, marker='o')
    axs[0].set_xscale('log')
    axs[0].set_yscale('log')
    axs[0].set_ylabel('Noise StdDev (A)')
    axs[0].set_title('Noise vs. NPLC')
    axs[0].grid(True, which='both', ls='--', alpha=0.5)

    # --- Mean panel ---
    axs[1].plot(nplc_vals, mean_vals, marker='s', color='tab:red')
    axs[1].set_xscale('log')
    # often means can be positive/negative; use symlog if sign flip else log
    if np.all(np.array(mean_vals) > 0):
        axs[1].set_yscale('log')
    elif np.all(np.array(mean_vals) < 0):
        axs[1].set_yscale('log')
    else:
        axs[1].set_yscale('symlog', linthresh=1e-15)
    axs[1].set_ylabel('Mean Current (A)')
    axs[1].set_xlabel('NPLC')
    axs[1].grid(True, which='both', ls='--', alpha=0.5)

    fig.tight_layout()
    return fig, axs

if __name__ == '__main__':
    print("Initializing Keysight Electrometer...")
    from pandora.controller.keysight import KeysightController

    # wait time after changing settings before acquiring data
    wait_time = 3  # seconds
    verbose = True
    name = 'K2'
    nSteps = 1
    rang0 = 2e-11  # 2e-11 A range
    # rang0 = None
    nSamples = 100
    # rang0 = None  # Auto range

    # Initialize the logger
    _initialize_logger(verbose)

    # Create an instance of the KeysightController
    _kconfig = get_config_section('keysights')
    if name not in _kconfig.keys():
        print(f"List of available keysight devices: {_kconfig.keys()}")
        raise ValueError(f"Keysight device {name} not found in config file.")

    kconfig = get_config_section(name, config=_kconfig)
    keysight = KeysightController(**kconfig)

    fig, axs = None, None
    for i in range(nSteps):
        print(f"Step {i+1}/{nSteps}: Setting range to {rang0} A")
        # Run the test
        results = test_nplc_effect(keysight, nplc_values=[0.1, 0.3, 0.5, 1, 3, 5, 8, 10], nsamples=nSamples, rang0=rang0)

        # Plot the result
        fig, axs = plot_noise_vs_nplc(results, fig, axs)

    plt.show()