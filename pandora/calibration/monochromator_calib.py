import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, peak_widths
from scipy.optimize import curve_fit
from lmfit.models import VoigtModel
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d
from astropy.modeling.models import Gaussian1D, Polynomial1D
from astropy.modeling.fitting import LevMarLSQFitter

from lmfit.models import SkewedGaussianModel, PolynomialModel, SplitLorentzianModel
from lmfit.models import SplineModel, GaussianModel, LorentzianModel
import pandas as pd
import os

from pandora.calibration.hg2_lamp import hg2_lines_all as hg2_lines

# Define a simple Gaussian function with constant offset
def gauss(x, amp, mu, sigma, offset):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2) + offset

def parabola(x, a, b, c):
    """Parabolic function with vertex as a parameter."""
    return -((x - a) / b) ** 2 + c

def polyfit_to_vertex_form(coeffs):
    """
    Converts coefficients from np.polyfit (ax^2 + bx + c) to vertex form (-((x-a)/b)^2 + c).
    """
    a_poly, b_poly, c_poly = coeffs
    
    if a_poly >= 0:
        raise ValueError("Parabola does not have a peak (a must be negative for an inverted parabola).")
        # return np.nan, np.nan, np.nan
    
    a_new = -b_poly / (2 * a_poly)  # Vertex position
    b_new = 1 / np.sqrt(-a_poly)    # Width parameter
    c_new = c_poly - (b_poly ** 2) / (4 * a_poly)  # Peak intensity    
    return a_new, b_new, c_new


class monoLineFinder:
    """
    Class to analyze a single peak in a spectrum (e.g. from a monochromator).
    It locates the main peak, estimates the background via a linear fit,
    and provides methods to visualize the result. Now also fits a Gaussian line.
    """
    
    def __init__(self, x_data, intensities,
                 distance=20, height=2500,
                 rel_height_bg=0.91, rel_height_peak=0.5):
        """
        Parameters
        ----------
        x_data : array-like
            Wavelength or pixel axis data. (E.g. 300 nm to 1100 nm)
        intensities : array-like
            Measured intensities at each wavelength.
        distance : float
            Minimum horizontal distance (in array indices) between peaks
            passed to find_peaks().
        height : float
            Minimum peak height passed to find_peaks().
        rel_height_bg : float
            'rel_height' passed to peak_widths() for identifying the background region.
            (Typically near 0.9 or 0.95.)
        rel_height_peak : float
            'rel_height' for the main peak half‐width measurement. Typically 0.5.
        """
        self.x_data = np.array(x_data)  # Keep indices for fits
        self.intensities = np.array(intensities, dtype=float)
        self.distance = distance
        self.height = height
        self.rel_height_bg = rel_height_bg
        self.rel_height_peak = rel_height_peak
        
        # Analysis results
        self.peaks = None
        self.peak_x_positions = None
        self.peak_intensities = None
        self.bg_poly = None       # (slope, intercept) from np.polyfit
        self.bg_xrange = None     # x values used for background modeling
        self.bg_vals = None       # background intensities from polyfit
        self.ilow = None
        self.ihigh = None
        self.dp = None
        self.dh = None
        self.found_peak_index = None  # single peak index if found

        # Gaussian fit results
        self.gauss_params = None  # (amp, center, sigma, offset)
        self.gauss_cov = None     # covariance matrix from curve_fit
        self.gauss_chisqr = None  # Chi-square for Gaussian fit

        # Additional centroid results
        self.parabola_vertex = None
        self.moment_center = None
        self.parabola_vertex_unc = None
        self.moment_center_unc = None
        self.parabola_chisqr = None
        self.y_fit = None
    
    def find_line(self, order=2):
        """
        1. Finds a single main peak via find_peaks()
        2. Gets the peak widths
        3. Identifies a window around the peak
        4. Fits a linear background to points below a certain threshold
        5. Stores relevant results in object attributes
        """
        # --- 1. Find peak(s) ---
        peaks, properties = find_peaks(
            self.intensities, height=self.height, distance=self.distance
        )
        # remove if the edges are the peaks
        peaks = peaks[(peaks > 0) & (peaks < self.intensities.size - 1)]

        if len(peaks) == 0:
            raise ValueError("No peaks found with the given 'height' and 'distance' constraints.")
            
        # We'll assume there's only one main peak. If multiple, pick the highest.
        main_peak_idx = peaks[np.argmax(self.intensities[peaks])]
        self.peaks = [main_peak_idx]
        
        # Store the single peak position and intensity
        self.peak_x_positions = self.x_data[main_peak_idx]
        self.peak_intensities = self.intensities[main_peak_idx]
        self.found_peak_index = main_peak_idx
        
        # --- 2. Get peak width at rel_height=0.5 ---
        results_half = peak_widths(
            self.intensities, [main_peak_idx], rel_height=self.rel_height_peak
        )
        self.dp = int(results_half[0])  # approximate half‐width in array indices
        
        # --- 3. Identify background region at rel_height_bg ~ 0.91 ---
        results_bg = peak_widths(
            self.intensities, [main_peak_idx], rel_height=self.rel_height_bg
        )
        # results_bg[1][0] is the intensity “height” at that fraction
        self.dh = results_bg[1][0]

        # We'll define a ±2.5*dp window around the peak for background fitting
        self.ilow = int(main_peak_idx - 2.0 * self.dp)
        self.ihigh = int(main_peak_idx + 2.0 * self.dp)
        self.ilow = max(self.ilow, 0)
        self.ihigh = min(self.ihigh, len(self.x_data))
        
        xwin = self.x_data[self.ilow : self.ihigh]
        ywin = self.intensities[self.ilow : self.ihigh]

        # Use only points below the threshold "dh" to fit the background
        mask = ywin < self.dh
        if not np.any(mask):
            # If everything is above dh, fallback to using them all
            mask = np.ones_like(xwin, dtype=bool)
        
        # --- 4. Fit linear background ---
        c = np.polyfit(xwin[mask], ywin[mask], order)  # slope, intercept
        self.bg_poly = c
        self.bg_xrange = xwin
        self.bg_vals = np.polyval(c, xwin)

        return main_peak_idx

    def check_saturation(self, th=65000):
        """Check if the peak intensity exceeds a certain threshold."""
        return self.peak_intensities > th
    
    def measure_parabola_vertex(self, nfwhm=1.5):
        """Computes the vertex of a parabolic fit within ±FWHM and its uncertainty."""
        peak_idx = self.found_peak_index
        fwhm_pts = self.dp  # approximate FWHM in array indices
        half_win = fwhm_pts*nfwhm/2
        p_low = int(np.round(max(peak_idx - half_win, 0),0))
        p_high = int(np.round(min(peak_idx + half_win, len(self.x_data)),0))

        self.x_para = self.x_data[p_low : p_high]
        y_para = self.intensities[p_low : p_high].copy()
        # y_para = y_para - np.polyval(self.bg_poly, self.x_para)  # Subtract background

        if len(self.x_para) < 3:
            return self.peak_x_positions, np.nan
        
        coeffs = np.polyfit(self.x_para, y_para, 2)
        p0 = polyfit_to_vertex_form(coeffs)
        popt, cov_matrix = curve_fit(parabola, self.x_para, y_para, p0=p0)
        vertex_x = popt[0]
        vertex_unc = np.sqrt(cov_matrix[0,0])

        # Compute chi-square
        y_fit = parabola(self.x_para,*popt)
        chisqr = np.std((y_para - y_fit) ** 2 / np.abs(y_fit))
        self.parabola_chisqr = chisqr
        self.y_fit = y_fit.copy()

        return vertex_x, vertex_unc

    def measure_moment_center(self):
        """Computes the center of mass (first moment) within ±2.5*FWHM and its uncertainty."""
        peak_idx = self.found_peak_index
        fwhm_pts = self.dp  # approximate FWHM in array indices

        wide_win = int(2.5 * fwhm_pts)
        m_low = max(peak_idx - wide_win, 0)
        m_high = min(peak_idx + wide_win, len(self.x_data))

        x_mom = self.x_data[m_low : m_high]
        y_mom = self.intensities[m_low : m_high].copy()
        y_mom -= np.polyval(self.bg_poly, x_mom)  # Subtract background

        total_flux = np.sum(y_mom)
        if total_flux == 0 or len(x_mom) == 0:
            return self.peak_x_positions, np.nan
        
        moment_center = np.sum(x_mom * y_mom) / total_flux
        variance = np.sum(y_mom * (x_mom - moment_center) ** 2) / total_flux
        moment_unc = np.sqrt(variance / len(x_mom))
        
        return moment_center, moment_unc
    
    def measure_gaussian_fit(self):
        """Fits a Gaussian to the peak and computes chi-square."""
        peak_idx = self.peak_x_positions
        i1, i2 = self.ilow, self.ihigh
        x_win = self.x_data[i1 : i2]
        y_win = self.intensities[i1 : i2].copy() - np.polyval(self.bg_poly, x_win)
                
        p0 = [max(y_win), peak_idx, self.dp / 2.3548, min(y_win)]
        popt, pcov = curve_fit(gauss, x_win, y_win, p0=p0, maxfev = 10000)
        self.gauss_params = popt
        self.gauss_cov = pcov
        
        y_fit = gauss(x_win, *popt)
        chisqr = np.sum((y_win - y_fit) ** 2 / np.abs(y_fit))
        self.gauss_chisqr = chisqr
        
        return popt, chisqr

    def fit_voigt_line(self):
        """
        Fits a Voigt profile to the spectral data (with optional background subtraction).
        Stores results in:
        - self.voigt_params (lmfit Parameters object)
        - self.voigt_result  (lmfit.ModelResult object)
        """
        if self.found_peak_index is None:
            raise ValueError("No peak found. Run find_line() first.")

        # 1) Choose window around peak
        i1, i2 = self.ilow, self.ihigh
        x_win = self.x_data[i1 : i2].astype(float)
        y_win = self.intensities[i1 : i2].astype(float)

        # 2) Subtract background if your class has a linear background fit
        if self.bg_poly is not None:
            y_win = y_win - np.polyval(self.bg_poly, x_win)

        # 3) Build the Voigt model
        voigt_model = VoigtModel(prefix='v_')

        # 4) Make initial parameter guesses
        # amplitude ~ peak height minus local background
        amp_guess = max(y_win) 
        center_guess = self.peak_x_positions
        # sigma_guess ~ FWHM guess / 2.355
        # gamma_guess ~ a fraction of sigma or a separate guess
        sigma_guess = max(self.dp / 2.355, 1.0)
        gamma_guess = sigma_guess  # or pick a different heuristic

        params = voigt_model.make_params(
            v_amplitude=amp_guess,
            v_center=center_guess,
            v_sigma=sigma_guess,
            v_gamma=gamma_guess,
            v_offset=0
        )

        # 5) Perform fit using lmfit
        self.voigt_result = voigt_model.fit(y_win, params, x=x_win)

        # 6) Store final parameter values for convenience
        self.voigt_params = self.voigt_result.params
        return self.voigt_params['v_center'].value, self.voigt_params['v_center'].stderr

    def measure_centroids(self, nfwhm=1.5):
        """Wrapper function to compute Gaussian fit, parabola vertex, and moment center."""
        self.parabola_vertex, self.parabola_vertex_unc = self.measure_parabola_vertex(nfwhm)
        self.moment_center, self.moment_center_unc = self.measure_moment_center()
        self.gauss_params, self.gauss_chisqr = self.measure_gaussian_fit()
        self.voigt_mean, self.voigt_mean_unc = self.fit_voigt_line()
        # centers = [self.parabola_vertex, self.moment_center, self.gauss_params[1]]
        # errors = [self.parabola_vertex_unc, self.moment_center_unc, np.sqrt(self.gauss_cov[1,1])]

        centers = [self.parabola_vertex, self.moment_center, self.voigt_mean]
        errors = [self.parabola_vertex_unc, self.moment_center_unc, self.voigt_mean_unc]
        return centers, errors
    
    
    def plot_line(self, commanded_wav=[None,None], ax=None):
        """
        Plot the data window around the main peak, the fitted background,
        and indicate the identified peak position.
        
        Parameters
        ----------
        commanded_wav : float or None
            If provided, draws a vertical dashed line for the 'commanded' wavelength.
        ax : matplotlib Axes object or None
            If None, create a new figure/axes; otherwise draw on the provided axes.
        """
        if self.found_peak_index is None:
            raise ValueError("Run find_line() before plotting.")

        if ax is None:
            fig, ax = plt.subplots(figsize=(6,4))

        # Window around the peak
        i1, i2 = self.ilow, self.ihigh
        xx = self.x_data[i1 : i2]
        yy = self.intensities[i1 : i2]

        # Fitted background
        bg = self.bg_vals

        ax.scatter(xx, yy, color='k', label='Line Data')
        ax.plot(xx, bg, color='firebrick', label='Background')
        ax.plot(xx, gauss(xx, *self.gauss_params)+bg, color='k', label='Gaussian Fit')
        
        if commanded_wav[0] is not None:
            ax.axvline(commanded_wav[1], ls='--', color='grey', label='Commanded wav')
            ax.set_title(r"Monochromator $\lambda=%i nm$"%commanded_wav[0])
        
        # Mark the main peak
        ax.plot(self.peak_x_positions, self.peak_intensities,
                'rx', markersize=8, label='Peak')
        
        # Mark the centroid positions
        ax.plot(self.parabola_vertex, self.peak_intensities, color='blue' ,marker='x', ls='--', label='Parabola Vertex')
        if self.y_fit is not None:
            ax.plot(self.x_para, self.y_fit, color='blue', ls='--')
        ax.plot(self.moment_center, self.peak_intensities, color='g', marker='x', ls='--', label='Moment Center')

        ax.legend()
        ax.set_xlabel("Pixels")
        ax.set_ylabel("Counts [ADU]")
        # ax.set_title("monoLineFinder Result")
        fig.tight_layout()
        return fig
    
class Hg2LampLineCharacterization:
    """
    Hg2LampLineCharacterization characterizes the lines of a Hg2 lamp spectrum.

    Parameters
    ----------
    name : str
        Name of the Hg2 lamp line (eg. "Ar07").
    exptime: int
        Exposure time in miliseconds to load the spectrum.
    peak : int
        peak of the line in pixels.
    window : int
        window around the peak in pixels.
    
    """
    def __init__(self, name, peak, exptime=10, window=10, outdir="./",
                 flat_field=True, is_dark=True):
        self.name = name
        self.exptime = int(exptime)
        self.peak = peak
        self.window = window
        self.flat_field = flat_field
        self.is_dark = is_dark

        self.centers = dict()
        self.errors = dict()
        self.rsquared = dict()
        self.wavelength = hg2_lines[name]

        # Get the absolute path to the directory of the current file (monochromator_calib.py)
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Navigate two directories up to reach TOPDIR
        root = os.path.abspath(os.path.join(current_dir, '..', '..'))

        # outfile
        self.fname = f"{outdir}/results/{self.name}.csv"

        # Dark and flat field
        self.darkfname = f'{root}/data/20250310T111722_20ms_dark.txt'
        self.flatfname = f'{root}/data/stellarnet-blackcomet-qe-curve.csv'

        # Load spectrum
        self.spec_dir = '/Users/esteves/Downloads/spectrometer_local/exptime/'
        self.timestamp = '20250311T153442'
        self.spec_fname = f"{self.spec_dir}/{self.timestamp}_{self.exptime}ms.txt"
        self.load_spectrum()

        # Crop spectrum
        self.crop_spectrum()

    def load_spectrum(self):
        data = np.genfromtxt(self.spec_fname)
        self.wav_all = data[:,0]
        self.pixel_all = np.arange(len(self.wav_all),dtype=int)
        self.counts_all = data[:,1]

        self.instrument_signature_removal()
        pass

    def instrument_signature_removal(self):
        """
        Remove the instrument signature from the spectrum.

        Dark subtraction and flat fielding.
        """
        if self.is_dark:
            # load dark
            if os.path.exists(self.darkfname):
                print("Dark subtraction")
                dd = np.genfromtxt(self.darkfname)
                wav0, dark0 = dd[:,0], dd[:,1]
                self.counts_all = self.counts_all - np.interp(self.wav_all, wav0, dark0)
            else:
                print(f"Dark file not found: {self.darkfname}")
        
        if self.flat_field:
            # load flat
            if os.path.exists(self.flatfname):
                print("Flat fielding")
                self.qe_curve = pd.read_csv(self.flatfname, comment="#")
                ## CCD quantum efficiency
                wav0, qe = self.qe_curve.wavelength.values, self.qe_curve.QE.values
                self.counts_all = self.counts_all / np.interp(self.wav_all, wav0, qe)
            else:
                print(f"Flat field file not found: {self.flatfname}")
        pass

    def crop_spectrum(self):
        self.ilow = int(max(self.peak - self.window, 0))
        self.ihigh = int(min(self.peak + self.window, len(self.wav_all)))

        self.wav = self.wav_all[self.ilow:self.ihigh]
        self.pixel = self.pixel_all[self.ilow:self.ihigh]
        self.counts = self.counts_all[self.ilow:self.ihigh]
        pass

    def line_finder(self):
        mono_finder = monoLineFinder(self.pixel, self.counts, height=2000, distance=20)
        mono_finder.find_line(order=3)
        return mono_finder

    def measure_centroids(self, length=9, polyorder=2):
        mono_finder = self.line_finder()
        centers, errors = mono_finder.measure_centroids()
        
        # add the peak_fwhm
        self.peak_fwhm = mono_finder.dp
        self.peak_height = mono_finder.peak_intensities

        # add peak instead of gaussian fit
        centers[-1] = mono_finder.peak_x_positions
        errors[-1] = 1.0

        # Measure the centroid using a Savitzky-Golay filter
        c, e = self.measure_savgol_centroids(length=length, polyorder=polyorder)
        centers.append(c)
        errors.append(e)

        # add the rsquared
        rsqr = [np.nan]*len(centers)
        
        # add to center and errors to the dictionary
        self.centers = dict(zip(['parabola_vertex', 'moment_center', 'peak','savgolFilter'], centers))
        self.errors = dict(zip(['parabola_vertex', 'moment_center', 'peak', 'savgolFilter'], errors))
        self.rsquared = dict(zip(['parabola_vertex', 'moment_center', 'peak','savgolFilter'], rsqr))
    
    def measure_savgol_centroids(self, length=7, polyorder=2):
        """
        Measure the centroids (first moment) of the smoothed line 
        using a Savitzky-Golay filter.

        Parameters
        ----------
        length : int
            The length of the filter window (i.e., the number of coefficients).
        polyorder : int
            The order of the polynomial used to fit the samples.
        
        Returns
        -------
        moment_center : float
            The centroid (first moment) of the smoothed line.
        moment_unc : float
            The uncertainty of the centroid
        
        """
        # apply the savgol filter
        y_smooth = savgol_filter(self.counts, length, polyorder)
        
        # make a fine grid for the interpolation (40 times the original pixel size, ~0.01nm)
        self.x_fine = np.linspace(self.pixel.min(), self.pixel.max(), 40*self.pixel.size) 
        f_interp = interp1d(self.pixel, y_smooth, kind='cubic')

        # interpolate the smoothed data
        self.y_fine = f_interp(self.x_fine)

        # get the peak of the smoothed data
        main_peak_idx = np.argmax(self.y_fine)

        # approximate number of points around peak
        # 2 FWHM points on each side
        half_width = 2*self.peak_fwhm*40  
        i_low = max(0, main_peak_idx - half_width)
        i_high = min(len(self.x_fine), main_peak_idx + half_width)
        x_mom = self.x_fine[i_low:i_high]
        y_mom = self.y_fine[i_low:i_high]

        total_flux = np.sum(y_mom)  # total flux
        moment_center = np.sum(x_mom * y_mom) / total_flux
        variance = np.sum(y_mom * (x_mom - moment_center) ** 2) / total_flux
        moment_unc = np.sqrt(variance / len(x_mom))
        return moment_center, moment_unc
    
    def fit_gauss_continuum(self, poly_degree=1, poly_init_vals=None):
        """
        Fit one Gaussian line + a polynomial continuum to (x, y) data using Astropy.
        Applies parameter bounds and attempts to retrieve uncertainties.
    
        Parameters
        ----------
        poly_degree : int, optional
            Degree of the polynomial continuum. Default is 1 (linear).
        poly_init_vals : list, optional
            Initial values for the polynomial coefficients [c0, c1, ...].
            If None, will default to zeros (except c0 might be near y[0]).
        """
    
        # Data
        x = self.pixel
        y = self.counts
    
        # Initial Gaussian guesses
        amp1 = self.peak_height
        mean1 = self.centers['peak']
        stddev1 = self.peak_fwhm / 2.355  # FWHM -> sigma
    
        # Define the Gaussian model
        g1 = Gaussian1D(amplitude=amp1, mean=mean1, stddev=stddev1)
    
        # ---- (1) Set Parameter Bounds ----
        # Lower & upper bounds for amplitude, mean, and stddev as an example
        # (Adjust as appropriate for your system)
        g1.amplitude.bounds = (100, 65e3)         # amplitude >= 0
        g1.mean.bounds = (x.min(), x.max())     # mean in the data range
        g1.stddev.bounds = (1., 15.)         # nonzero stddev
    
        # Define the polynomial (continuum) model
        if poly_init_vals is None:
            # If linear, e.g., [y[0], 0.0]
            if poly_degree == 1:
                c0_guess = float(y[0])
                c1_guess = 0.0
                poly_init_vals = [c0_guess, c1_guess]
            else:
                poly_init_vals = [0.0]*(poly_degree+1)
    
        poly_cont = Polynomial1D(degree=poly_degree)
        for i, val in enumerate(poly_init_vals):
            setattr(poly_cont, f'c{i}', val)
            # Optional: set polynomial bounds if needed:
            # poly_cont.c0.bounds = (0, None)  etc.
    
        # Combine Gaussian + polynomial
        model_init = g1 + poly_cont
    
        # ---- (2) Fit the data ----
        fitter = LevMarLSQFitter()
        best_fit = fitter(model_init, x, y, maxiter=1000)  # maxiter for safety    
        self.normal = best_fit  # store
        
        # Attempt to read parameter uncertainties
        # For a compound model, best_fit[0] corresponds to g1, best_fit[1] to poly.
        mean_val = best_fit[0].mean.value
        mean_err = get_params_uncertainty(fitter, best_fit, param_name='mean_0')

        # Keep the continuum parameters for later use
        self.continumm = [best_fit.c0_1.value, best_fit.c1_1.value]
        
        # # Plot for debugging
        x_fine = np.linspace(x.min(), x.max(), 500)
        y_fine = best_fit(x_fine)
    
        plt.figure(figsize=(8,5))
        plt.plot(x, y, 'bo', label='Data')
        plt.plot(x_fine, y_fine, 'r-', label='Best Fit')
        plt.title('Gaussian + Continuum Fit (Astropy)')
        plt.xlabel('Pixel')
        plt.ylabel('Counts')
        plt.legend()
        plt.show()
        # Return relevant param, param uncertainty
        return mean_val, mean_err

    def fit_lorentzian_knots(self, nsigma=3):
        """
        Fit one Lorentzian peak + a polynomial continuum to (x, y) data using lmfit and plot the result.

        """
        # take initial values
        p1 = self.peak_height
        m1 = self.centers['peak']
        fwhm1 = self.peak_fwhm / 2.355
        x = self.pixel
        y = self.counts
        
        # Define the model
        peak_model = SplitLorentzianModel(prefix='peak_')

        # Set initial parameter values
        params = model.make_params(
            peak_amplitude=p1, peak_center=m1, peak_sigma=fwhm1, peak_sigma_r=1.5*fwhm1
        )

        # Make sure the Gaussian parameters are within reasonable bounds
        params['peak_sigma'].min = 1.
        params['peak_sigma'].max = 10.
        params['peak_sigma_r'].min = 0.5
        params['peak_sigma_r'].max = 10.

        params['peak_amplitude'].min = 0        
        
        # Get the knots
        left = np.linspace(x.min(), m1-nsigma*fwhm1, 5)
        right = np.linspace(m1+nsigma*fwhm1, x.max(), 5)
        knot_xvals = np.append(left, right)
        bkg = SplineModel(prefix='bkg_', xknots=knot_xvals)
        params.update(bkg.guess(y, x))

        # Re-define model
        model = peak_model + bkg

        # Make sure the Gaussian parameters are within reasonable bounds
        params['peak_sigma'].min = 1.
        params['peak_sigma'].max = 10.
        params['peak_amplitude'].min = 0

        # Fit the composite model to the data
        result = model.fit(y, params, x=x)

        # Store the best-fit model and its parameters
        self.skewed_normal = result
        self.knot_xvals = knot_xvals

        # get the center and uncertainty
        mean = result.params['peak_center'].value
        mean_unc = result.params['peak_center'].stderr
        return mean, mean_unc
    
    def split_lorentzian_fit(self, nsigma=3, nknots=4):
        return self.fit_lmlfit_model(SplitLorentzianModel, nsigma=nsigma, nknots=nknots)
    
    def lorentzian_fit(self, nsigma=3, nknots=4):
        return self.fit_lmlfit_model(LorentzianModel, nsigma=nsigma, nknots=nknots)
    
    def skewed_gaussian_fit(self, nsigma=3, nknots=4):
        return self.fit_lmlfit_model(SkewedGaussianModel, nsigma=nsigma, nknots=nknots)

    def gaussian_fit(self, nsigma=3, nknots=4):
        return self.fit_lmlfit_model(GaussianModel, nsigma=nsigma, nknots=nknots)

    def voigt_fit(self, nsigma=3, nknots=4):
        return self.fit_lmlfit_model(VoigtModel, nsigma=nsigma, nknots=nknots)

    def get_bkg_model(self, model1, params, nsigma=3, nknots=4):
        m1 = self.centers['peak']
        sigma = self.peak_fwhm / 2.355
        x, y = self.pixel, self.counts

        # Get the knots
        left = np.linspace(x.min(), m1 - nsigma * sigma, nknots)
        right = np.linspace(m1 + nsigma * sigma, x.max(), nknots)
        knot_xvals = np.append(left, right)
        
        # Create Spline Model
        bkg = SplineModel(prefix='bkg_', xknots=knot_xvals, polyorder=3)

        # Define the full model (Model + Spline)
        model = model1 + bkg
        
        # Ensure background parameters are added
        params.update(bkg.guess(y, x))  # This correctly initializes the spline
        
        # Constrain the background model
        # Bakcground is always additive
        for name in params.keys():
            if "bkg_s" in name:
                i = int(name[-1])
                params[name].max = 1.1*np.interp(knot_xvals[i], x, y)
                params[name].min = 0.

        self.knot_xvals = knot_xvals
        return model, bkg, params
    
    def fit_lmlfit_model(self, funcmodel, nsigma=3, nknots=4):
        """
        Fit one Lorentzian peak + a polynomial continuum to (x, y) data using lmfit and plot the result.

        """
        # take initial values
        p1 = self.peak_height
        m1 = self.centers['peak']
        fwhm1 = self.peak_fwhm / 2.355
        x = self.pixel
        y = self.counts
        
        # Define the model
        peak_model = funcmodel(prefix='peak_')

        # Set initial parameter values
        params = peak_model.make_params(
            peak_amplitude=p1, peak_center=m1, peak_sigma=fwhm1,
        )
        params.update(peak_model.guess(y, x))
        
        # Set the background with constraints
        model, bkg, params = self.get_bkg_model(peak_model, params, nsigma, nknots)
        
        # Make sure the Gaussian parameters are within reasonable bounds
        params['peak_center'].min = x.min()
        params['peak_center'].max = x.max()
        params['peak_amplitude'].min = 0

        # Fit the composite model to the data
        result = model.fit(y, params, x=x)

        # get the center and uncertainty
        mean = result.params['peak_center'].value
        mean_unc = result.params['peak_center'].stderr
        if mean_unc is None:
            # print("Covariance matrix not computed. Re-running fit...")
            
            # Retrieve best-fit parameters
            params = result.params.copy()

            # Ensure all parameters are set to `vary=True` for refitting
            # for par_name in params:
            #     params[par_name].vary = True  # Allow all parameters to be adjusted

            # Re-run the fit, explicitly asking to compute covariance
            result = model.fit(y, params, x=x, calc_covar=True)

            # Re-check uncertainty
            mean_unc = result.params['peak_center'].stderr
            mean = result.params['peak_center'].value

        # Store the best-fit model and its parameters
        model_name = funcmodel.__name__.lower()
        setattr(self, model_name, result)

        return mean, mean_unc
    
    def fit_models(self, nsigma=3, nknots=4):
        functions = ['lorentzian_fit', 'skewed_gaussian_fit', 'gaussian_fit', 'voigt_fit', 'split_lorentzian_fit']
        methods = ['lorentzianModel','skewedGaussianModel','gaussianModel','voigtModel', 'splitLorentzianModel']
        for fun, method in zip(functions, methods):
            c, e = getattr(self, fun)(nsigma=nsigma, nknots=nknots)
            self.centers[method] = c
            self.errors[method] = e
            self.rsquared[method] = getattr(self, method.lower()).rsquared
        pass

    def plot_raw_line(self, fig=None):
        """
        Plot the raw line data with the identified peak position.
        """
        if fig is None:
            fig, ax = plt.subplots(figsize=(6,4))
        else:
            ax = fig.gca()
        ax.set_title(self.name+" Line - Raw Data \n"+r"$\lambda$ = %.2f nm"%self.wavelength)
        ax.plot(self.pixel, self.counts, 'k', label='%s Data'%self.name)
        ax.plot(self.pixel, self.counts, 'ko')
        ax.axvline(self.peak, color='r', ls='--', label='Peak')
        ax.set_xlabel("Pixels")
        ax.set_ylabel("Counts [ADU]")
        ax.legend()
        return fig

    def plot_zoom_out(self, fig=None, ntimes=3):
        """
        Plot the raw line data with the identified peak position.
        """
        if fig is None:
            fig, ax = plt.subplots(figsize=(6,4))
        else:
            ax = fig.gca()
        # take data within 30 nm of the peak
        ilow = int(max(self.peak - ntimes*self.window, 0))
        ihigh = int(min(self.peak + ntimes*self.window, len(self.wav_all)))

        wav = self.wav_all[ilow:ihigh]
        pixel = self.pixel_all[ilow:ihigh]
        counts = self.counts_all[ilow:ihigh]

        ax.set_title(self.name+" Line - Zoom out \n"+r"$\lambda$ = %.2f nm"%self.wavelength)
        ax.plot(wav, counts, 'k', label='%s Data'%self.name)
        ax.plot(wav, counts, 'ko')
        ax.axvline(self.wavelength, color='r', ls='--', label='Hg2 Line Center')
        ax.set_xlabel("wav [nm]")
        ax.set_ylabel("Counts [ADU]")
        ax.legend()
        return fig
    
    def plot_model_fit(self, method='gaussianModel', fig=None, ax=None):
        """
        Plot the raw line data with the identified peak position.
        """
        if fig is None:
            fig, ax = plt.subplots(figsize=(8,7))

        # plot data
        ax.scatter(self.pixel, self.counts, color='k', lw=2, label="Line " + self.name+" Spectrum")
        ax.plot(self.pixel, self.counts, color='k', lw=1)

        # plot best fit
        method_name = method.lower()
        out = getattr(self, method_name)
        rsqr = self.rsquared[method]
        comps = out.eval_components()

        ax.plot(self.pixel, out.best_fit, label=method + ' best fit\n'+f'Rsqr: {rsqr:0.5f}', color='r', lw=2)
        ax.plot(self.pixel, comps['peak_'], color='m', ls='--', label='line')
        ax.plot(self.pixel, comps['bkg_'], color='g', ls='--', label='continuum')
        ax.plot(self.knot_xvals, np.interp(self.knot_xvals, self.pixel, comps['bkg_']), 'gx', label='knots')
        ax.legend(fontsize=12)

        ax.set_xlabel("Pixels")
        ax.set_ylabel("Counts [ADU]")
        ax.legend()
        fig.tight_layout()
        return fig
    
    def compare_models(self):
        fig, axs = plt.subplots(2, 2, figsize=(12,10))
        methods = ['lorentzianModel','skewedGaussianModel','gaussianModel','voigtModel']
        for ax, method in zip(axs.ravel(), methods):
            self.plot_model_fit(method=method, fig=fig, ax=ax)
        return fig
    
    def plot_line_centers(self, window=5):
        fig, ax = plt.subplots(figsize=(8,7))
        ax.set_title("Line Centers " +self.name+ "\n"+r"$\lambda$ = %.2f nm"%self.wavelength)
        # I need to map 8 centers values with colors
        colors = ['r','g','b','m','c','y','k','orange','firebrick']
        for i, key in enumerate(self.centers.keys()):
            #lines with the center and error
            ax.errorbar(self.centers[key], self.peak_height*(1+2*i/100), xerr=self.errors[key], fmt='o', color=colors[i], label=key)
            # ax.errorbar(self.centers[key], yerr=self.errors[key], fmt='o', color=colors[i], label=key)

        il, ih = int(self.peak-window)-1, int(self.peak+window)+1
        ax.plot(self.pixel_all[il:ih], self.counts_all[il:ih], color='grey', marker='o')
        ax.plot(self.pixel_all[il:ih], self.counts_all[il:ih], color='grey', label=self.name)
        #ax.errorbar(self.centers.keys(), self.centers.values(), yerr=self.errors.values(), fmt='o')
        ax.set_xlim(self.peak-window, self.peak+window)
        ax.set_ylabel("Counts [ADU]")
        ax.set_xlabel("Pixel")
        ax.legend(fontsize=11, loc=3)
        return fig
    
    def build_results(self):
        """
        Build a single-row DataFrame with multi-level columns for the results of one measurement/run.
        Returns the new results DataFrame without saving to disk.
        """
        # Prepare a dict of (top_level, sub_level) -> value
        hier_data = {
            ('line_info', 'timestamp'):   self.timestamp,
            ('line_info', 'name'):        self.name,
            ('line_info', 'wavelength'):  self.wavelength,
            ('line_info', 'exptime'):     self.exptime,
            ('line_info', 'peak_height'): self.peak_height,
            ('line_info', 'fwhm'):        2.355 * self.gaussianmodel.params['peak_sigma']
        }

        # Add the fit results
        for method in self.centers.keys():
            hier_data[(method, 'center')]   = self.centers[method]
            hier_data[(method, 'error')]    = self.errors[method]
            hier_data[(method, 'rsquared')] = self.rsquared[method]

        # Convert this dictionary to a DataFrame with a single row (index=[0])
        df = pd.DataFrame(hier_data, index=[0])
        return df


    def save_results(self):
        """
        Save the current measurement's DataFrame (returned by build_results) to a CSV.
        If the CSV already exists, appends (concatenates) the new row(s).
        """
        # Build the new data you want to append
        df_new = self.build_results()
        print(f"Saving results to {self.fname}")
        if os.path.isfile(self.fname):
            # 1) Load existing file, specifying multi-level headers
            df_existing = pd.read_csv(self.fname, index_col=0, header=[0, 1])

            # 2) Concatenate old + new data
            df_all = pd.concat([df_existing, df_new], ignore_index=True)

            # 3) (Optional) remove duplicate rows based on all columns
            #    or you might want to remove duplicates based on line_info, etc.
            df_all.drop_duplicates(inplace=True)

            # 4) Write out
            df_all.to_csv(self.fname)
            return df_all

        else:
            # If file doesn't exist, just save df_new
            df_new.to_csv(self.fname)
            return df_new

def get_params_uncertainty(fitter, best_fit, param_name='mean_0'):
    cov_matrix = fitter.fit_info['param_cov']
    param_names = best_fit.param_names  # e.g. ['amplitude_0', 'mean_0', 'stddev_0', ...]
    idx = param_names.index(param_name)
    error = np.sqrt(cov_matrix[idx, idx])
    return error

# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_pdf import PdfPages

# peaks, vertex, cen = [], [], []
# heights = []
# trues = []

# # Create one PDF file that will collect all figures
# with PdfPages("monochromator_peaks_20250307T222525.pdf") as pdf:
#     for i in range(wav.size):
#         wavelength = wav[i]
#         f  = files[i]
#         x_data, intensities = read_file(f)
#         tp = wav2pixel(wavelength)

#         finder = monoLineFinder(x_data, intensities,
#                                 distance=20, height=2500,
#                                 rel_height_bg=0.91, rel_height_peak=0.5)
    
#         p = finder.find_line()
#         v, c = finder.measure_centroids()
#         popt, pcov = finder.fit_gaussian_line()
    
#         # This returns a matplotlib Figure
#         fig = finder.plot_line(commanded_wav=[wavelength, tp])

#         # Save the current figure to the PDF
#         pdf.savefig(fig)
        
#         # Good practice to close the figure so as not to clutter memory
#         plt.close(fig)
    
#         # Collect numeric data for later usage
#         peaks.append(p)
#         vertex.append(v)
#         cen.append(c)
#         trues.append(tp)
#         heights.append(finder.peak_intensities)

# # Convert to arrays if desired
# peaks = np.array(peaks)
# vertex = np.array(vertex)
# cen = np.array(cen)
# trues = np.array(trues)
# heights = np.array(heights)

# linesDf = initialize_line_dataframe()
# for line_name, line_wavelength in hg2_lines.items():
#     print(f"{line_name}: {line_wavelength}")
#     df = pd.read_csv(f"./results/{timestamp}_{line_name}.csv", index_col=1)
#     height = lineDf.peak_height.values
#     ix = np.nanargmin(np.abs(height-40e3))
#     line = lineDf.iloc[ix].copy()
#     linesDf = pd.concat(linesDf,line, ignore_index=True)

import numpy as np
import pandas as pd
import os
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

def quadratic(x, a, b, c):
    return a*x**2 + b*x + c

def quadratic_inv(w, a, b, c):
    disc = b**2 - 4 * c * (a - w)
    x_pred = (-b + np.sqrt(disc)) / (2 * c)
    return x_pred

class WaveLengthCalibrationModel:
    def __init__(self, lines, outdir='.'):
        self.lines = lines
        self.fname_loc = outdir + "/results/{name}.csv"
        self.params = dict()
        self.covparams = dict()
        self.residuals = dict()
        self.values = dict()
        self.errors = dict()
        self.prediction = dict()
        self.rmse = dict()

        # Put your wavelength array
        self.wav = np.array(list(self.lines.values()))
    
    def load_lines(self):
        dfs = []
        for name, peak in self.lines.items():
            fname = self.fname_loc.format(name=name)
            if os.path.isfile(fname):
                line = pd.read_csv(fname, index_col=0, header=[0, 1])
                # This returns a Series with multi-level index = columns
                row_series = line.iloc[-1]            
                # Convert Series -> DataFrame (1 row) with multi-level columns
                row_df = row_series.to_frame().T
                # Rename the row index so it becomes e.g. "Hg_line" etc.
                row_df.index = [name]
                dfs.append(row_df)
            else:
                continue
        self.df = pd.concat(dfs)
        pass
        
    def fit(self, method='gaussianModel'):
        centers = self.df[method]['center'].values.astype(float)
        errors = self.df[method]['error'].values.astype(float)
        wav = self.df['line_info']['wavelength'].values.astype(float)
        # print(wav.size)
        
        p0 = np.polyfit(centers, wav, 2)
        # Fit a quadratic (pixel -> wavelength)
        popt, pcov = curve_fit(
            quadratic, centers, wav, absolute_sigma=True,
            p0=p0
        )
        self.params[method] = popt
        self.covparams[method] = np.sqrt(np.diag(pcov))
        
        # residual = measured wavelength - fitted wavelength
        fitted_wav = quadratic(centers, *popt)
        self.residuals[method] = wav - fitted_wav
        
        # We'll store the *pixel positions* in self.values
        self.values[method] = centers
        self.errors[method] = errors
        self.prediction[method] = fitted_wav
        
        # Compute standard deviation of residuals (RMSE)
        self.rmse[method] = np.sqrt(np.mean(self.residuals[method]**2))
    
    def plot_residuals(self, method='gaussianModel', ax=None, color='k'):
        # Quick reference
        residuals = self.residuals[method]
        pp = self.values[method]
        pp_unc = self.errors[method]
        pp_unc[np.isnan(pp_unc)] = 1.0
        
        names = list(self.df.index.values)

        # Unpack best-fit params
        a_fit, b_fit, c_fit = self.params[method]
        
        # Propagation of error from pixel->wavelength
        # derivative of f(x) = 2a*x + b, so:
        #    dW = |(2a * x + b)| * dx
        # I'm dividing by 2. not sure if that's your intention;
        # adjust if needed
        ww_unc = np.abs(2*a_fit*pp + b_fit) * pp_unc
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))

        # Scatter + errorbars
        ax.scatter(pp, residuals, color=color, marker='o', label="Residuals")
        ax.errorbar(pp, residuals, yerr=ww_unc, fmt='o', color=color)
        
        # Zero residual line
        ax.axhline(0, color='red', linestyle='--', linewidth=1)

        # Annotate each point
        for i, txt in enumerate(names):
            ax.annotate(
                txt,
                (pp[i], residuals[i] + ww_unc[i] * 1.05),
                textcoords="offset points",
                xytext=(5,5),
                ha='center'
            )

        ax.set_xlabel("Pixel Position")
        ax.set_ylabel("Residuals (nm)")
        ax.set_title(f"Residuals of Wavelength Fit ({method})")
        ax.legend()
        ax.grid(True)

    def fit_all_methods(self):
        methods = [
            'peak', 'parabola_vertex', 'moment_center', 'savgolFilter',
            'lorentzianModel','skewedGaussianModel','gaussianModel',
            'voigtModel','splitLorentzianModel'
        ]
        for method in methods:
            print(method)
            self.fit(method)

    def print_all_rmse(self):
        """
        Prints the RMSE for each method in self.rmse.
        """
        print("=== RMSE for each method ===")
        for method, rmse_val in self.rmse.items():
            print(f"{method:25s} -> {rmse_val:.4f} nm")
    
    def plot_all_rmse(self):
        """
        Plots a simple bar chart of the RMSE for each method.
        """
        methods = list(self.rmse.keys())
        rmse_values = [self.rmse[m] for m in methods]

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(methods, rmse_values)
        
        # Make the x-axis labels readable
        ax.set_xticks(range(len(methods)))
        ax.set_xticklabels(methods, rotation=45, ha='right')
        
        ax.set_ylabel("RMSE (nm)")
        ax.set_title("Comparison of RMSE for Each Method")
        ax.grid(True)
        plt.tight_layout()
        plt.show()