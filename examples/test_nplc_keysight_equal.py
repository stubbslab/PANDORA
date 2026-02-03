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
    
def test_nplc_effect(
    keysight_device,
    nplc_values=[0.1, 0.3, 0.5, 1, 3, 5, 8, 10],
    *,
    base_nplc: float = 10.0,
    base_samples: int = 100,
    rang0=None,
):
    """
    Return list of (nplc, sigma, nsamples) tuples.

    Measure noise versus NPLC while keeping the *total integration time*
    identical for every test run.

    The reference time budget is  (base_nplc × base_samples / line‑freq).
    For a given test NPLC (nplc_i) we use

        nsamples_i = round(base_nplc * base_samples / nplc_i)

    so that  nsamples_i × nplc_i  is constant.
    """
    noise_results = []

    # constant product that preserves time budget
    k_time = base_nplc * base_samples

    for nplc in nplc_values:
        nsamples = max(1, int(round(k_time / nplc)))

        print(f"\n--- NPLC = {nplc}  |  nsamples = {nsamples} ---")
        keysight_device.set_nplc(nplc)
        keysight_device.set_nsamples(nsamples)
        keysight_device.set_delay(0)
        keysight_device.set_mode("CURR")

        if rang0 is not None:
            keysight_device.set_rang(f"{rang0}")
        else:
            keysight_device.auto_scale()

        keysight_device.on()
        keysight_device.acquire()

        # --- wait for acquisition to finish (same time budget for every NPLC) ---
        line_freq = 60.0  # Hz; change to 50.0 if your mains is 50 Hz
        wait_time = nsamples * nplc / line_freq + 0.5  # +0.5 s cushion
        time.sleep(wait_time)
        # ------------------------------------------------------------------------

        data = keysight_device.read_data()
        keysight_device.off()

        readings = data["CURR"]
        mean = float(np.mean(readings))
        stddev = float(np.std(readings))

        print(f"Mean = {mean:.3e} A, StdDev = {stddev:.3e} A")
        noise_results.append((nplc, stddev, nsamples))

        time.sleep(1)  # brief pause between runs

    return noise_results


def plot_noise_vs_nplc(results, fig=None, axs=None):
    """
    Plot noise standard deviation vs. NPLC setting.

    Args:
        results (list of (nplc, stddev)): Output from test_nplc_effect.
    """
    nplc_vals, std_vals, n_vals = zip(*results)
    err_vals = [s * np.sqrt(2.0 / (n - 1)) for s, n in zip(std_vals, n_vals)]

    if fig is None or axs is None:
        fig, axs = plt.subplots(figsize=(8, 5))

    axs.errorbar(nplc_vals, std_vals, yerr=err_vals, marker='o', linestyle='-')
    axs.set_xscale('log')
    axs.set_yscale('log')
    axs.set_xlabel('NPLC (log scale)')
    axs.set_ylabel('Noise StdDev (A) ±1σ err (log scale)')
    axs.set_title('Measurement Noise vs. NPLC')
    axs.grid(True, which='both', ls='--', alpha=0.5)
    return fig, axs

if __name__ == '__main__':
    print("Initializing Keysight Electrometer...")
    from pandora.controller.keysight import KeysightController

    # wait time after changing settings before acquiring data
    wait_time = 3  # seconds
    verbose = True
    name = 'K2'
    nSteps = 1
    rang0 = 2e-11  # 2e-11 A range for photodiode
    # rang0 = None
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
        results = test_nplc_effect(
            keysight,
            nplc_values=[0.1, 0.3, 0.5, 1, 3, 5, 8, 10],
            base_nplc=10,
            base_samples=100,
            rang0=rang0,
        )

        # Plot the result
        fig, axs = plot_noise_vs_nplc(results, fig, axs)

    plt.show()