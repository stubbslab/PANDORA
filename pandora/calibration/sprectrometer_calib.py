import numpy as np
from scipy.signal import find_peaks, peak_widths
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt

class SpectrumCalibrator:
    """
    A class that takes in a spectrometer's *reported wavelengths* vs. intensities,
    but re-calibrates by treating the 'true' x-axis as pixel indices (0..N-1).
    The final polynomial maps: pixel -> true wavelength.
    """
    def __init__(self, reported_wavelengths, intensities, dark=None):
        """
        Parameters
        ----------
        reported_wavelengths : array-like
            The spectrometer-reported wavelengths for each detector element.
            (Often slightly off and needing re-calibration.)
        intensities : array-like
            The measured intensities at each element.
        """
        # Store the raw data
        self.reported_wavelengths = np.asarray(reported_wavelengths)
        self.intensities0 = np.asarray(intensities)
        self.intensities = np.copy(self.intensities0)
        if dark is not None:
            self.intensities = self.intensities - dark
            self.intensities = np.clip(self.intensities, 0, None)
        
        # Compute the noise level (median intensity in a noise region)
        # The Hg2 lamp has no lines in the 610-660 nm range
        noise_region = (reported_wavelengths>610) & (reported_wavelengths<660)
        self.noise = np.median(self.intensities[noise_region])
        self.intensities/= self.noise

        # Number of pixels in the detector
        self.num_pixels = len(self.reported_wavelengths)
        
        # For calibration, we treat x_data = pixel indices [0..N-1]
        self.x_data = np.arange(self.num_pixels, dtype=float)
        
        # Book-keeping for found peaks, fits, etc.
        self.peak_indices = None
        self.peak_x_positions = None   # in pixel space
        self.peak_intensities = None
        self.vertex_positions = None   # parabola-fitted peak positions in pixel space
        self.centroid_positions = None # centroid-fitted peak positions in pixel space
        self.peak_fwhm = None # in nm
        
        self.calibration_coeffs = None
        self.matched_pairs = None      # list of (peak_pixel, true_wavelength)
        self.matched_method = None
        self.matched_residual = None
    
    # def find_prominent_lines(self, height=None, distance=None, prominence=None):
    #     """
    #     Finds prominent peaks in the spectrum using scipy.signal.find_peaks.
    #     Returns the indices of the found peaks in self.intensities.
    #     """
    #     peaks, properties = find_peaks(self.intensities,
    #                                    height=height,
    #                                    distance=distance,
    #                                    prominence=prominence)
    #     self.peak_indices = peaks
    #     # The 'pixel' position of each peak
    #     self.peak_x_positions = self.x_data[peaks]
    #     self.peak_intensities = self.intensities[peaks]
        
    #     return peaks
    
    def find_prominent_lines(self, height=None, distance=None, prominence=None):
        """
        Finds peaks using scipy.signal.find_peaks and computes the FWHM (full width
        at half maximum) in the actual x-data domain (which may be non-uniform).
            
        Returns
        -------
        peaks : ndarray
            Indices of found peaks in `intensities`.
        peak_fwhm : ndarray
            The computed FWHM in the same units as `x_data`.
        """
        # 1. Find the peaks
        peaks, properties = find_peaks(self.intensities, height=height,
                                    distance=distance, prominence=prominence)

        # 2. Compute widths at half maximum
        #    This returns widths in *index space*, plus fractional left_ips and right_ips
        results_half = peak_widths(self.intensities, peaks, rel_height=0.5)
        
        widths_samples = results_half[0]  # widths in *sample indices*
        left_ips       = results_half[2]
        right_ips      = results_half[3]

        # 3. Make an interpolation function from index -> x_data
        #    We'll treat the array index as the independent variable, x_data as dependent
        f_interp = interp1d(self.x_data, self.reported_wavelengths, kind='linear')  
        # or kind='cubic' if you want more smoothness, but linear is often enough.

        # 4. FWHM in x_data space
        fwhm = f_interp(right_ips) - f_interp(left_ips)
        self.peak_fwhm = fwhm
        self.peak_indices = peaks

        self.peak_x_positions = self.x_data[peaks]
        self.peak_intensities = self.intensities[peaks]
        self.peak_intensities0 = self.intensities0[peaks]
        return peaks, fwhm
    
    def fit_parabola_to_peaks(self, peak_indices=None, num_points=10):
        """
        Fits a parabola near each peak to refine its position in pixel space.
        """
        if peak_indices is None:
            if self.peak_indices is None:
                raise ValueError("No peaks found yet. Run find_prominent_lines first.")
            peak_indices = self.peak_indices
        
        refined_peaks = []
        for idx in peak_indices:
            start = max(0, idx - num_points)
            end   = min(self.num_pixels, idx + num_points + 1)
            
            x_fit = self.x_data[start:end]
            y_fit = self.intensities[start:end]
            # 2nd order polynomial fit
            coeffs = np.polyfit(x_fit, y_fit, 2)
            a, b, c = coeffs
            # vertex of the parabola
            vertex_x = -b / (2*a)
            refined_peaks.append(vertex_x)
        
        self.vertex_positions = np.array(refined_peaks)
        return self.vertex_positions

    def measure_peak_centroids(self, peak_indices=None, num_points=10):
        """
        Measures peak centroids (in pixel space) by the center-of-mass
        of intensity in a small window around each peak.
        """
        if peak_indices is None:
            if self.peak_indices is None:
                raise ValueError("No peaks found yet. Run find_prominent_lines first.")
            peak_indices = self.peak_indices

        centroids = []
        for idx in peak_indices:
            start = max(0, idx - num_points)
            end   = min(self.num_pixels, idx + num_points + 1)
            
            pixel_window = self.x_data[start:end]
            intensity_window = self.intensities[start:end]
            
            # Center of mass
            csum = np.sum(intensity_window)
            if csum == 0:
                centroids.append(pixel_window[len(pixel_window)//2])  # fallback
            else:
                centroid = np.sum(pixel_window * intensity_window) / csum
                centroids.append(centroid)
        
        self.centroid_positions = np.array(centroids)
        return self.centroid_positions
    
    def remove_saturated_peaks(self, saturation_threshold=64800):
        """
        Removes any detected peaks that exceed the given saturation threshold.

        Parameters
        ----------
        saturation_threshold : float
            Intensity above which a peak is considered saturated.
            
        Returns
        -------
        remaining_peaks : ndarray
            Updated array of peak indices that are below the saturation threshold.
        """
        if self.peak_indices is None:
            raise ValueError("No peaks found. Run find_prominent_lines() first.")
        
        # Identify which peaks are below the threshold
        mask = self.peak_intensities0 < saturation_threshold
        
        # Filter out saturated peaks
        removed_count = np.sum(~mask)
        self.peak_indices = self.peak_indices[mask]
        self.peak_x_positions = self.peak_x_positions[mask]
        self.peak_intensities = self.peak_intensities[mask]
        self.peak_fwhm = self.peak_fwhm[mask]
        self.peak_intensities0 = self.peak_intensities0[mask]
        
        print(f"Removed {removed_count} saturated peaks. {len(self.peak_indices)} remain.")
        return self.peak_indices

    def remove_wide_peaks(self, fwhm_threshold=10.0):
        """
        Removes any detected peaks that exceed the given FWHM threshold.
        
        Parameters
        ----------
        fwhm_threshold : float
            Any peak with FWHM larger than this value will be removed.
            
        Returns
        -------
        remaining_peaks : ndarray
            Updated array of peak indices that have FWHM below the threshold.
            
        Notes
        -----
        - Requires that `find_prominent_lines()` (or another method) has populated
        `self.peak_indices` and `self.peak_fwhm`.
        - Adjust `fwhm_threshold` to match your expected peak width unit.
        (e.g., if x_data is in nm, then threshold is in nm.)
        """
        # Make sure we have peaks and associated FWHM
        if self.peak_indices is None or not hasattr(self, 'peak_fwhm'):
            raise ValueError(
                "No peaks found or no FWHM values. "
                "Run find_prominent_lines() (with FWHM calculation) first."
            )
        
        # Identify which peaks have FWHM below threshold
        mask = (self.peak_fwhm < fwhm_threshold)
        
        # Count how many are removed
        removed_count = np.sum(~mask)
        
        # Filter out wide peaks
        self.peak_indices      = self.peak_indices[mask]
        self.peak_x_positions = self.peak_x_positions[mask]
        self.peak_intensities = self.peak_intensities[mask]
        self.peak_fwhm        = self.peak_fwhm[mask]
        
        print(f"Removed {removed_count} wide peaks. {len(self.peak_indices)} remain.")
        return self.peak_indices

    def match_peaks_to_known_lines(self, known_lines, method="peak", match_tolerance=2.0):
        """
        Matches found peaks (in pixel space) to known lines (in nm) by
        first converting the known line wavelength -> 'expected pixel'
        via linear interpolation from the min/max reported wave.
        
        known_lines : dict or list
            If dict, the values are known line wavelengths in nm.
            If list, it should be the known line wavelengths in nm.
        method : "peak", "parabola", or "centroid"
            Which peak position array to use.
        match_tolerance : float
            Maximum difference in pixel space to be considered a match.
        """
        # Gather the known line wavelengths
        if isinstance(known_lines, dict):
            true_wavelengths = np.array(list(known_lines.values()), dtype=float)
        else:
            true_wavelengths = np.array(known_lines, dtype=float)

        # Choose which measured x positions to use
        if method == "peak":
            if self.peak_x_positions is None:
                raise ValueError("No peaks found yet. Run find_prominent_lines first.")
            measured_x = self.peak_x_positions
        elif method == "parabola":
            if self.vertex_positions is None:
                raise ValueError("No parabola-fitted positions. Run fit_parabola_to_peaks first.")
            measured_x = self.vertex_positions
        elif method == "centroid":
            if self.centroid_positions is None:
                raise ValueError("No centroid positions. Run measure_peak_centroids first.")
            measured_x = self.centroid_positions
        else:
            raise ValueError("Unknown method. Choose from 'peak', 'parabola', 'centroid'.")

        matched_pairs = []
        pixel_resids = []

        # For each known line wavelength, compute expected pixel
        for wl in true_wavelengths:
            expected_pixel = np.interp(wl, self.reported_wavelengths, self.x_data)
            diffs = np.abs(measured_x - expected_pixel)
            min_diff = np.min(diffs)
            print(wl, min_diff)
            if min_diff <= match_tolerance:
                best_idx = np.argmin(diffs)
                matched_pixel = measured_x[best_idx]
                matched_pairs.append((matched_pixel, wl))
                pixel_resids.append(min_diff)

        if len(pixel_resids) > 0:
            print(f"Matched {len(matched_pairs)} lines, median pixel residual = {np.median(pixel_resids):.3f}")
        else:
            print("No lines matched within tolerance.")
        
        self.matched_pairs = matched_pairs  # (pixel, known_wavelength)
        self.matched_method = method
        self.matched_residual = np.array(pixel_resids)
    
    def fit_polynomial(self, matched_pairs=None, order=2):
        """
        Fits a polynomial W = f(pixel) to matched data: (pixel, true_wavelength).
        """
        if matched_pairs is None:
            matched_pairs = self.matched_pairs
        if not matched_pairs:
            raise ValueError("No matched pairs found; cannot fit polynomial.")

        px = np.array([p[0] for p in matched_pairs], dtype=float)
        wl = np.array([p[1] for p in matched_pairs], dtype=float)

        coeffs = np.polyfit(px, wl, deg=order)
        self.calibration_coeffs = coeffs
        return coeffs
    
    def apply_calibration(self, pixel_values):
        """
        Evaluate the polynomial calibration to convert from pixel -> wavelength.
        """
        if self.calibration_coeffs is None:
            raise ValueError("No calibration has been performed yet.")
        return np.polyval(self.calibration_coeffs, pixel_values)
    
    def get_model_residual(self):
        """
        Returns the difference [f(pixel) - true_wavelength] for matched pairs.
        """
        if self.calibration_coeffs is None:
            raise ValueError("No calibration has been performed yet.")
        if not self.matched_pairs:
            raise ValueError("No matched pairs found.")

        px = np.array([p[0] for p in self.matched_pairs], dtype=float)
        wl = np.array([p[1] for p in self.matched_pairs], dtype=float)
        calibrated_wl = self.apply_calibration(px)
        return calibrated_wl - wl
    
    def plot_calibration_fit(self):
        """
        Plots pixel on X axis vs. wavelength on Y axis, showing:
          1) the matched points (pixel, line_wavelength)
          2) the fitted polynomial curve
          3) a histogram of residuals (nm)
        """
        if self.calibration_coeffs is None:
            raise ValueError("No calibration has been performed yet.")

        # Prepare data for plotting
        coefs = self.calibration_coeffs
        eq_str = polynomial_string(coefs)

        matched_pairs = self.matched_pairs
        px_meas = np.array([p[0] for p in matched_pairs], dtype=float)
        wl_true = np.array([p[1] for p in matched_pairs], dtype=float)

        # Generate a smooth pixel array & compute polynomial
        px_model = np.linspace(0, self.num_pixels - 1, 200)
        wl_model = self.apply_calibration(px_model)

        # Residuals in nm
        residuals = self.get_model_residual()
        residuals2 = np.interp(px_meas, self.x_data, self.reported_wavelengths) - wl_true

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Left plot: Pixel vs. Wavelength (fit + matched points)
        ax1.scatter(px_meas, wl_true, color='firebrick', label='Matched Lines')
        ax1.plot(px_model, wl_model, color='k', label='Calibration Fit\n' + eq_str)
        ax1.plot(px_model, np.interp(px_model, self.x_data, self.reported_wavelengths), color='grey', label='Spec Calibration', ls='--')
        ax1.set_xlabel("Pixel")
        ax1.set_ylabel("Wavelength (nm)")
        ax1.set_title("Pixel-to-Wavelength Fit")
        ax1.legend()

        # Right plot: histogram of residuals
        #ax2.hist(residuals, bins=12, color='grey', alpha=0.7, edgecolor='black')
        ax2.scatter(wl_true, residuals, color='firebrick', label='Hg2 Calibrated\n' + f'RMS: {np.std(residuals):0.2g} nm')
        ax2.scatter(wl_true, residuals2, color='k', label='Spec Calibrated\n'+f'RMS: {np.std(residuals2):0.2g} nm')
        ax2.axhline(0, ls='--', color='k')
        ax2.set_ylabel("Residual (nm)")
        ax2.set_xlabel("Wavelength (nm)")
        ax2.legend()
        ax2.set_title(f"Centroid Method: {self.matched_method}")
        # ax2.set_title(f"Residuals (RMS={np.std(residuals):.3f} nm)")

        fig.tight_layout()
        return fig
    
    def plot_spectrum(self, show_peaks=True, title="Measured Spectrum"):
        """
        Plots the raw spectrum in pixel space.
        """
        fig = plt.figure(figsize=(8, 4))
        plt.plot(self.x_data, self.intensities, label='Spectrum', color='k')

        if show_peaks and self.peak_indices is not None:
            plt.plot(self.peak_x_positions, self.peak_intensities, 'rx',
                     label='Detected peaks')
        
        # Mark centroid or parabola positions if available
        if self.centroid_positions is not None:
            plt.vlines(self.centroid_positions, 
                       0, np.interp(self.centroid_positions, self.x_data, self.intensities, left=0, right=0),
                       color='blue', ls='dotted', label='Centroids')
        
        if self.vertex_positions is not None:
            plt.vlines(self.vertex_positions,
                       0, np.interp(self.vertex_positions, self.x_data, self.intensities, left=0, right=0),
                       color='red', ls='dashed', label='Parabola Vertices')
        
        plt.title(title)
        plt.xlabel("Pixel")
        plt.ylabel("Intensity (a.u.)")
        plt.legend()
        plt.tight_layout()
        return fig

    def plot_method_comparasion(self, known_lines, order=2, match_tolerance=2.0):
        """
        Plot the residuals of the calibration for different methods.
        This is useful to compare the performance of different peak
        detection and fitting methods.
        1. peak method
        2. centroid method
        3. parabola method
        """
        # compare methods
        methods = ['peak','centroid','parabola']
        colors = ['k','firebrick','grey']
        residuals = []
        for m in methods:
            matched = self.match_peaks_to_known_lines(known_lines, method=m, match_tolerance=match_tolerance)
            coeffs = self.fit_polynomial(matched, order)
            residuals.append(self.get_model_residual())

        mybins = np.arange(-1.0, 1.15, 0.15)
        # plot residuals
        fig, axs = plt.subplots(1, 3, figsize=(12, 4), sharey='all')
        for i, m in enumerate(methods):
            std = np.std(residuals[i][np.abs(residuals[i])<1.0])
            axs[i].set_title(f"{m} method\nRMS: {std:0.2g} nm")
            axs[i].hist(residuals[i], bins=mybins, histtype='step', lw=3,
                        color=colors[i], label=f'{m} method')
            axs[i].axvline(0, color='k', ls='--', lw=2)
            axs[i].set_xlabel("Residual (nm)")
            axs[i].set_ylabel("Counts")
            axs[i].legend()
        fig.tight_layout()
        return fig


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
    calibrator = SpectrumCalibrator(wav, spec, x_is_pixel=True)

    # 2. Find prominent peaks
    calibrator.find_prominent_lines(height=1000, distance=1.5)
    calibrator.measure_peak_centroids(num_points=12)
    calibrator.fit_parabola_to_peaks(num_points=12)

    # 3. Match found peaks to known lines
    calibrator.match_peaks_to_known_lines(hg2_lines, method='parbola', match_tolerance=1.5)

    fig = calibrator.plot_spectrum(title='Frankenstein Hg2 Lamp Spectrum')
    fig.savefig('long_exposure_spectrum_peaks.png', dpi=120)

    # 4. Fit a polynomial (pixel -> wavelength)
    matched = calibrator.match_peaks_to_known_lines(hg2_lines, method='parabola', match_tolerance=3.5)
    coeffs = calibrator.fit_polynomial(matched, order=2)
    fig = calibrator.plot_calibration_fit()
    fig.savefig('long_exposure_calibration_fit_2nd_order.png', dpi=120)

    # 5. Apply calibration to all pixel values
    

    # 6. Plot the calibration fit
    calibrator.plot_calibration_fit()