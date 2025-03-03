import numpy as np
from scipy.signal import find_peaks
import matplotlib.pyplot as plt

class SpectrumCalibrator:
    """
    A class that takes in a measured (pixel/wavelength vs. intensity) spectrum,
    finds the most prominent emission lines, and performs a polynomial calibration
    fit to known spectral lines (e.g., from a Hg/Ar lamp).
    """
    def __init__(self, x_data, intensities, x_is_pixel=False):
        """
        Parameters
        ----------
        x_data : array-like
            The x-axis data. Can be pixel numbers or approximate wavelengths.
        intensities : array-like
            The measured intensities at each x_data point.
        x_is_pixel : bool, optional
            If True, x_data is treated as pixel indices (0, 1, 2, ...).
            If False, x_data is treated as nominal/approximate wavelengths.
        """
        self.x_data = np.asarray(x_data)
        self.intensities = np.asarray(intensities)
        self.x_is_pixel = x_is_pixel
        
        # These will be filled after finding peaks and calibrating
        self.peak_indices = None
        self.peak_x_positions = None
        self.peak_intensities = None
        self.calibration_coeffs = None
        
    def find_prominent_lines(self, height=None, distance=None, prominence=None):
        """
        Finds prominent peaks in the spectrum using scipy.signal.find_peaks.
        
        Parameters
        ----------
        height : float, optional
            Required height of peaks. If None, no minimum height is enforced.
        distance : int, optional
            Required minimal horizontal distance (in x_data steps) between peaks.
        prominence : float, optional
            Required prominence of peaks. If None, no minimum prominence is enforced.
        
        Returns
        -------
        peaks : ndarray
            Indices of found peaks in self.intensities.
        """
        # Use scipy.signal.find_peaks to locate peaks
        peaks, properties = find_peaks(self.intensities,
                                       height=height,
                                       distance=distance,
                                       prominence=prominence)
        
        # Store the results
        self.peak_indices = peaks
        self.peak_x_positions = self.x_data[peaks]
        self.peak_intensities = self.intensities[peaks]
        
        return peaks
    
    def match_peaks_to_known_lines(self, known_lines, match_tolerance=2.0):
        """
        Simple matching of found peaks to known lines (for demonstration).
        
        Parameters
        ----------
        known_lines : dict or list
            If dict, the keys are known wavelengths (float) and the values
            might be the element name (e.g., 'Hg' or 'Ar').
            If list, it should be a list of known wavelength floats.
        match_tolerance : float
            Maximum absolute difference in x-domain (pixel or nominal nm)
            within which a peak is considered a match to a known line.
            
        Returns
        -------
        matched_pairs : list of tuples
            List of (measured_x, true_wavelength).
        """
        if isinstance(known_lines, dict):
            true_wavelengths = np.array(list(known_lines.values()), dtype=float)
        else:
            true_wavelengths = np.array(known_lines, dtype=float)
        
        matched_pairs = []
        residual = []
        # For each known line, see if there's a measured peak close enough
        for wl in true_wavelengths:
            # Find the difference with all peak positions
            diffs = np.abs(self.peak_x_positions - wl)
            min_diff = np.min(diffs)
            if min_diff <= match_tolerance:
                # get index of the best match
                best_idx = np.argmin(diffs)
                matched_x = self.peak_x_positions[best_idx]
                matched_pairs.append((matched_x, wl))
                residual.append(min_diff)
        print(f"There are {len(matched_pairs)} pairs found with median residual {np.median(residual):0.2f} nm")
        self.matched_pairs = matched_pairs
        pass
    
    def fit_polynomial(self, matched_pairs=None, order=2):
        """
        Fits a polynomial of given order to the matched peak data.
        
        If x_is_pixel=True, we interpret matched_pairs as:
            matched_pairs[i] = (pixel_position, true_wavelength).
        If x_is_pixel=False, matched_pairs[i] = (measured_wavelength, true_wavelength).
        
        Parameters
        ----------
        matched_pairs : (optional) list of tuples
            Each tuple is (measured_x, true_wavelength).
        order : int
            Polynomial order (e.g., 1 = linear, 2 = quadratic, etc.).
            
        Returns
        -------
        coeffs : ndarray
            Polynomial coefficients in the order used by np.polyval (highest power last).
            That is: coeffs = [a_n, a_(n-1), ..., a_0].
        """
        if matched_pairs is None:
            if not hasattr(self, 'matched_pairs'):
                raise ValueError("No matched pairs provided and no previous matches found.")
            else:
                matched_pairs = self.matched_pairs

        # Convert matched_pairs to arrays
        measured_x = np.array([p[0] for p in matched_pairs], dtype=float)
        true_wl   = np.array([p[1] for p in matched_pairs], dtype=float)
        
        # Fit polynomial: we want to find W = f(X)
        # so that np.polyval(coeffs, X) ~ W
        coeffs = np.polyfit(measured_x, true_wl, deg=order)
        self.calibration_coeffs = coeffs
        return coeffs
    
    def apply_calibration(self, x_values):
        """
        Apply the previously fitted polynomial calibration to new x-values.
        
        Parameters
        ----------
        x_values : array-like
            Pixel or nominal wavelength values to calibrate.
            
        Returns
        -------
        calibrated_wavelengths : ndarray
            The calibrated wavelengths after applying the polynomial fit.
        """
        if self.calibration_coeffs is None:
            raise ValueError("No calibration has been performed yet. "
                             "Call fit_polynomial first.")
        return np.polyval(self.calibration_coeffs, x_values)
    
    def plot_calibration_fit(self):
        """
        Plots the calibration polynomial fit and the data (measured vs. true wavelengths).
        """
        if self.calibration_coeffs is None:
            raise ValueError("No calibration has been performed yet. "
                             "Call fit_polynomial first.")
        coefs = self.calibration_coeffs
        x_values = np.linspace(np.min(self.x_data), np.max(self.x_data), 100)
        y_values = np.polyval(coefs, x_values)
    
        # Convert matched_pairs to arrays
        matched_pairs = self.matched_pairs
        measured_x = np.array([p[0] for p in matched_pairs], dtype=float)
        true_wl   = np.array([p[1] for p in matched_pairs], dtype=float)
    
        eq_str = polynomial_string(coefs)
    
        fig, axs = plt.subplots(1, 2, figsize=(12, 5))
        ax1 = axs[0]
        ax1.scatter(true_wl, measured_x, color='firebrick', label='Data')
        ax1.plot(y_values, x_values, color='k', 
                 label='Fit Model\n' + eq_str)
        ax1.set_xlabel("True Wavelength (nm)")
        ax1.set_ylabel("Measured Wavelength (nm)")
        ax1.set_title("Calibration Fit")
        ax1.legend()
    
        ax2 = axs[1]
        residual = np.polyval(coefs, measured_x) - true_wl
        residual2 = measured_x-true_wl
        ax2.scatter(true_wl, residual2, color='firebrick', label='Not Corrected\n'+
                    f'RMS: {np.std(residual2):0.2g} nm')
        ax2.scatter(true_wl, residual, color='k', 
                    label=('Corrected\n' + f'RMS: {np.std(residual):0.2g} nm'))
        ax2.axhline(0, color='grey', ls='--', lw=2)
        ax2.set_xlabel("True Wavelength (nm)")
        ax2.set_ylabel("Residual (nm)")
        ax2.set_title("Residuals")
        ax2.legend()
        fig.tight_layout()
        plt.show()

    def plot_spectrum(self, show_peaks=True):
        """
        Simple helper to plot the spectrum, optionally highlighting found peaks.
        """
        plt.figure(figsize=(8, 4))
        plt.plot(self.x_data, self.intensities, label='Spectrum', color='k')
        
        if show_peaks and self.peak_indices is not None:
            plt.plot(self.peak_x_positions, self.peak_intensities, 'rx',
                     label='Detected peaks')
        
        plt.title("Measured Spectrum")
        plt.xlabel("Pixel" if self.x_is_pixel else "Wavelength (nm)")
        plt.ylabel("Intensity (a.u.)")
        plt.legend()
        plt.tight_layout()
        plt.show()

def polynomial_string(coefs):
    """
    Given coefficients [a_n, ..., a_0], returns a string e.g.
    W = a_n*x^n + ... + a_0
    """
    order = len(coefs) - 1
    terms = []
    for i, c in enumerate(coefs):
        power = order - i
        if power > 1:
            terms.append(f"{c:.4g} x pixel^{power}")
        elif power == 1:
            terms.append(f"{c:.4g} x pixel")
        else:
            terms.append(f"{c:.4g}")
    return " + ".join(terms)

if __name__ == "__main__":
    from hg2_lamp import hg2_lines, create_fake_hg2_spectrum

    # 0. Load a fake spectrum
    wav, spec = create_fake_hg2_spectrum()

    # 1. Initialize the calibrator
    calibrator = SpectrumCalibrator(wav, spec, x_is_pixel=False)

    # 2. Find prominent peaks
    calibrator.find_prominent_lines(height=100, distance=1.5)

    # 3. Match found peaks to known lines
    matched = calibrator.match_peaks_to_known_lines(hg2_lines, match_tolerance=3.0)

    # X. Plot the spectrum and the peaks
    calibrator.plot_spectrum()

    # 4. Fit a polynomial (pixel -> wavelength)
    coeffs = calibrator.fit_polynomial(matched, order=2)
    print("Calibration polynomial coeffs:", coeffs)

    # 5. Apply calibration to all pixel values
    calibrated_wavelengths = calibrator.apply_calibration(wav)
    print("Calibrated wavelengths example:", calibrated_wavelengths[:10])

    # 6. Plot the calibration fit
    calibrator.plot_calibration_fit()

