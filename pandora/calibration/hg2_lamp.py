"""
Lines from the Ocean Hg2 lamp

This module also contains a function to create a fake spectrum.

"""
import numpy as np

# Fake spectrum for demonstration
hg2_lines = {
    "Hg01":  253.652,
    "Hg02":  296.728,
    "Hg03":  302.150,
    "Hg04":  313.155,
    "Hg05":  334.148,
    "Hg06":  365.015,
    "Hg07":  404.656,
    "Hg08":  435.835,
    "Hg09":  546.074,
    "Hg10":  576.961,
    "Hg11":  579.066,
    "Ar01":  696.543,
    "Ar02":  706.722,
    "Ar03":  714.704,
    "Ar04":  727.294,
    "Ar05":  738.398,
    "Ar06":  750.387,
    "Ar07":  763.511,
    "Ar08":  772.376,
    "Ar09":  794.818,
    "Ar10":  800.616,
    "Ar11":  811.531,
    "Ar12":  826.452,
    "Ar13":  842.465,
    "Ar14":  912.297,
    "Ar15":  922.450,
    "Ar16":  935.423,
    "Ar17":  949.743,
    "Ar18":  965.778,
}

hg2_line_strengths = {
    # Mercury lines
    "Hg01": 4096,  # ~253.652 nm (often saturated)
    "Hg02": 1024,  # ~296.728 nm
    "Hg03":  512,  # ~302.150 nm
    "Hg04": 4096,  # ~313.155 nm (very bright, often saturated)
    "Hg05": 1000,  # ~334.148 nm
    "Hg06":  512,  # ~365.015 nm (bright)
    "Hg07": 3072,  # ~404.656 nm (bright)
    "Hg08": 4096,  # ~435.835 nm (very strong)
    "Hg09": 3200,  # ~546.074 nm (strong but not always saturated)
    "Hg10": 1500,  # ~576.961 nm
    "Hg11": 1400,  # ~579.066 nm
    # Argon lines
    "Ar01": 800,   # ~696.543 nm
    "Ar02": 900,   # ~706.722 nm
    "Ar03": 700,   # ~714.704 nm
    "Ar04": 600,   # ~727.294 nm
    "Ar05": 500,   # ~738.398 nm
    "Ar06": 600,   # ~750.387 nm
    "Ar07": 700,   # ~763.511 nm
    "Ar08": 600,   # ~772.376 nm
    "Ar09": 500,   # ~794.818 nm
    "Ar10": 500,   # ~800.616 nm
    "Ar11": 400,   # ~811.531 nm
    "Ar12": 350,   # ~826.452 nm
    "Ar13": 300,   # ~842.465 nm
    "Ar14": 300,   # ~912.297 nm
    "Ar15": 250,   # ~922.450 nm
    "Ar16": 250,   # ~935.423 nm
    "Ar17": 200,   # ~949.743 nm
    "Ar18": 200,   # ~965.778 nm
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