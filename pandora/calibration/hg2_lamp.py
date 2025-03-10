"""
Lines from the Ocean Hg2 lamp

This module also contains a function to create a fake spectrum.

"""
import numpy as np

# https://physics.nist.gov/PhysRefData/ASD/lines_form.html
# https://www.oceanoptics.com/wp-content/uploads/2024/07/Wavelength-Calibration-Products-v1.0_0724.pdf
# Fake spectrum for demonstration
# Dictionary of Hg/Ar lamp spectral lines (NIST reference),
# extended up to ~1100 nm for Ar lines.
hg2_lines = {
    # Mercury (Hg) lines
    "Hg01": 253.65200,
    "Hg02": 296.72840,
    "Hg03": 302.15060,
    "Hg04": 313.15560,
    "Hg05": 334.14820,
    "Hg06": 365.01520,
    "Hg07": 404.65650,
    "Hg08": 435.83430,
    "Hg09": 546.07350,
    "Hg10": 576.95980,
    "Hg11": 579.06630,

    # Argon (Ar) lines
    "Ar01":  696.54310,
    "Ar02":  706.72180,
    "Ar03":  714.70420,
    "Ar04":  727.29360,
    "Ar05":  738.39800,
    "Ar06":  750.38690,
    "Ar07":  763.51100,
    "Ar08":  772.37610,
    "Ar09":  794.81760,
    "Ar10":  800.61580,
    "Ar11":  811.53110,
    "Ar12":  826.45180,
    "Ar13":  842.46480,
    "Ar14":  912.29670,
    "Ar15":  922.44990,
    "Ar16":  935.42200,
    "Ar17":  949.74290,
    "Ar18":  965.77860,
    "Ar19":  978.45100,
    "Ar20": 1047.00000,
    "Ar21": 1066.66000,
    "Ar22": 1088.46000,
    "Ar23": 1090.65000,
}

# Approximate relative intensities (peak heights). Actual values
# depend on lamp conditions and spectrometer setup; use these
# as a rough guide only.
hg2_line_strengths = {
    # Mercury lines
    "Hg01": 4096,  # Often the strongest Hg line near 254 nm
    "Hg02": 1024,
    "Hg03":  900,
    "Hg04": 2048,
    "Hg05":  800,
    "Hg06": 3500,
    "Hg07": 3800,
    "Hg08": 4000,
    "Hg09": 3200,
    "Hg10": 1200,
    "Hg11": 1000,

    # Argon lines
    "Ar01":  600,
    "Ar02":  500,
    "Ar03":  400,
    "Ar04":  300,
    "Ar05":  300,
    "Ar06":  400,
    "Ar07":  500,
    "Ar08":  500,
    "Ar09":  400,
    "Ar10":  400,
    "Ar11":  300,
    "Ar12":  250,
    "Ar13":  200,
    "Ar14":  150,
    "Ar15":  150,
    "Ar16":  150,
    "Ar17":  150,
    "Ar18":  150,
    "Ar19":  100,
    "Ar20":   80,
    "Ar21":   80,
    "Ar22":   70,
    "Ar23":   70,
}


def create_fake_hg2_spectrum(
    wavemin=200.0, 
    wavemax=1100.0, 
    npoints=1024, 
    std_nm=1.5, 
    noise_std=10.0
):
    # 1. Create the wavelength array
    wavelengths = np.linspace(wavemin, wavemax, npoints)
    intensities = np.zeros_like(wavelengths)

    # Now add Gaussian peaks for each line:
    for line_label, amplitude in hg2_line_strengths.items():
        # Get the wavelength center from the parallel dictionary
        line_center = hg2_lines[line_label]  # in nm

        # Create a Gaussian profile
        # Gauss = amplitude * exp( - (x - center)^2 / (2 * sigma^2) )
        intensities += amplitude * np.exp(
            -0.5 * ((wavelengths - line_center) / std_nm)**2
        )

    # 3. Add random noise (baseline)
    #    We'll add a baseline offset of 0 plus some random normal noise with std = noise_std
    noise = np.random.normal(loc=0.0, scale=noise_std, size=len(wavelengths))
    intensities += noise

    # Ensure no negative intensities if that matters
    intensities = np.clip(intensities, 0, None)

    return wavelengths, intensities

if __name__ == "__main__":
    wav, spec = create_fake_hg2_spectrum()

    import matplotlib.pyplot as plt
    plt.plot(wav, spec, 'k')
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (arbitrary units)")
    plt.title('Fake Hg2 Lamp Spectrum')