from matplotlib import pyplot as plt
from scipy.signal import savgol_filter
from lmfit.models import SplineModel, GaussianModel
from scipy.optimize import fminbound
import numpy as np
# from lmfit

def gaussian(x, mu, A, sigma):
    """Single Gaussian function."""
    return A * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))

def sum_gaussians(x, means, amplitudes, sigma):
    """Sum of multiple Gaussians."""
    return sum(gaussian(x, mu, A, sigma) for mu, A in zip(means, amplitudes))

def find_max_gaussians(means, amplitudes, sigma):
    """Find the approximate max position and value of the sum Gaussians."""
    weights = [A * np.exp(-((mu - np.mean(means)) ** 2) / (2 * sigma ** 2)) for A, mu in zip(amplitudes, means)]
    #x_approx = sum(w * mu for w, mu in zip(weights, means)) / sum(weights)

    # Refine numerically in the range [min(mu) - 2σ, max(mu) + 2σ]
    x_opt = fminbound(lambda x: -sum_gaussians(x, means, amplitudes, sigma),
                      np.min(means) - 3 * sigma, np.max(means) + 3 * sigma)
    return x_opt, sum_gaussians(x_opt, means, amplitudes, sigma)

class deblendModel:
    """
    Model to deblend spectral lines of the Hg/Ar lamp.
    """
    def __init__(self, pixel, counts, centers, calibration=[1.,1.], weights=None):
        if weights is None:
            weights = [1.0] * len(centers)
    
        # wavelength pixel relation
        self.wav2pixel = np.poly1d(calibration)
        self.x = pixel
        self.counts = counts

        self.centers = centers
        self.weights = weights

        # centers pixels 
        self.centers_pixel = self.wav2pixel(centers)
        
        # Number of Gaussians
        self.ncomponents = len(centers)

        # Spectrum resolution
        self.sigma_nm = 1.3
        self.sigma_pixel = self.wav2pixel(self.centers[0] + self.sigma_nm) - self.wav2pixel(self.centers[0])

        # Initial guess for the peak center
        self.peak_center = self.centers_pixel[0]

        # Varying parameters
        self.vary_sigma = True
        self.vary_delta = True
        self.vary_weight = True
        self.free_blend_amplitude = False
        self.free_vary_sigma = False
        pass

    def pixel_center_guess(self, length=3, polyorder=2):
        """
        Finds the pixel center of the peak using the maximum 
        of the sum of the Gaussians in wavelength space.

        Use the distance from the peak center to the other peaks
        to estimate the pixel centers of the other peaks.

        Advatange: The pixel centers are less sensitive to the 
        wavelength calibration.
        """
        x_smooth = np.linspace(self.x.min(), self.x.max(), 10000)
        y_smooth = np.interp(x_smooth, self.x,savgol_filter(self.counts, length, polyorder))

        self.peak_center = x_smooth[np.argmax(y_smooth)]
        self.peak_height = np.max(y_smooth)

        x_max_3, f_max_3 = find_max_gaussians(self.centers, self.weights, self.sigma_nm)
        self.peak_guess = x_max_3
        self.normalization = f_max_3/self.peak_height

        deltas_nm = self.centers - x_max_3
        deltas_pixel = self.wav2pixel(self.centers+deltas_nm) - self.wav2pixel(self.centers)
        self.centers_pixel_guess = self.peak_center+deltas_pixel


    def fit(self, nsigma=3, nknots=3, npixels=3):
        # Improve the initial guess
        self.pixel_center_guess()
        self.y = self.counts.copy()*self.normalization

        # Create model and params
        model, params = self.make_model(nsigma, nknots)

        # Constrain the parameters
        params = self.constrain_params(params, npixels)

        result = model.fit(self.y, params, x=self.x)
        if result.errorbars is False:
            print("Re-running fit to compute error bars...")
            
            # Copy best-fit parameters
            params = result.params.copy()
            
            # Re-run the fit explicitly requesting covariance computation
            result = model.fit(self.y, params, x=self.x, calc_covar=True)

        self.result = result
        pass

    def constrain_params(self, params, npixels=3.0):
        # Make sure the Gaussian parameters are within reasonable bounds
        params['peak_center'].min = self.centers_pixel[0]-npixels
        params['peak_center'].max = self.centers_pixel[0]+npixels
        params['peak_amplitude'].min = self.weights[0]*0.1
        params['peak_amplitude'].max = self.weights[0]*10.0
        params['peak_sigma'].vary = self.vary_sigma
        params['peak_sigma'].min = self.sigma_pixel/5.
        params['peak_sigma'].max = 2*self.sigma_pixel

        # Constrain the blend parameters
        for i in range(1,self.ncomponents):            
            params['blend%i_center'%i].expr = 'peak_center + delta%i'%i

            if not self.free_vary_sigma:
                params['blend%i_sigma'%i].expr = 'peak_sigma'

            # Add aditional constraints
            delta = self.centers_pixel[i] - self.centers_pixel[0]
            weight = self.weights[i] / self.weights[0]

            params.add('delta%i'%i, value=delta, vary=self.vary_delta)
            if self.vary_delta:
                params['delta%i'%i].min = delta - npixels/2.
                params['delta%i'%i].max = delta + npixels/2.

            if self.free_blend_amplitude:
                params['blend%i_amplitude'%i].min = weight/5.
                params['blend%i_amplitude'%i].max = weight*5.

            else:
                params['blend%i_amplitude'%i].expr = 'peak_amplitude * weight%i'%i
                params.add('weight%i'%i, value=weight, vary=self.vary_weight)
                if self.vary_weight:
                    params['weight%i'%i].min = weight/2.0
                    params['weight%i'%i].max = weight*2.0
            
        return params

    def make_model(self, nsigma=3, nknots=3):
        # Create the model
        model = GaussianModel(prefix='peak_')

        for i in range(1,self.ncomponents):
            model += GaussianModel(prefix=f'blend{i}_')

        # Create the parameters
        params = model.make_params(
            peak_amplitude=self.weights[0],
            peak_center=self.centers_pixel[0],
            peak_sigma=self.sigma_pixel,
        )
        # Set initial parameter values
        for i in range(1, self.ncomponents):
            # Initialize each blend using the corresponding center and weight
            params.add(f'blend{i}_amplitude', value=self.weights[i])
            params.add(f'blend{i}_center', value=self.centers_pixel[i])
            params.add(f'blend{i}_sigma', value=self.sigma_pixel)
        
        model, params = self.make_bkg_model(model, params, nsigma, nknots)
        return model, params

    def make_bkg_model(self, model, params, nsigma=3, nknots=3):
        # get the knots
        left = np.linspace(self.x.min(), np.min(self.centers_pixel) - nsigma * self.sigma_pixel, nknots)
        right = np.linspace(np.max(self.centers_pixel) + nsigma * self.sigma_pixel, self.x.max(), nknots)
        knot_xvals = np.append(left, right)

        if self.ncomponents>2:
            deltas = np.diff(self.centers_pixel)
            w = np.where(np.abs(deltas)>2*self.sigma_pixel)[0]
            # middle = (self.centers_pixel[w+1] + self.centers_pixel[w])/2
            # knot_xvals = np.sort(np.append(knot_xvals, middle))
            # print(knot_xvals)

        self.xknots = knot_xvals
        # Create Spline Model
        bkg = SplineModel(prefix='bkg_', xknots=knot_xvals, polyorder=1)
        model+=bkg

        # Create the spline model   
        params = params.update(bkg.guess(self.y, self.x))  # This correctly initializes the spline
        for bname in params.keys():
            if "bkg_s" in bname:
                i = int(bname[-1])
                params[bname].max = 1.05*np.interp(knot_xvals[i], self.x, self.y)
                params[bname].min = 0.0
                
        return model, params
    
    def plot_fit(self, result=None):
        if result is None:
            result = self.result
        y = self.y
        x = self.x
        knot_xvals = self.xknots
        m1 = self.centers_pixel[0]
        
        plt.figure(figsize=(6,5))
        # Plot the fit
        comps = result.eval_components()
        plt.plot(x, y, 'ro', label='Data')
        plt.axvline(m1, color='r', label='P(wav=%.3f)'%self.centers[0])

        plt.plot(x, result.best_fit,'k', label='Blended Model\n'+ r'$R^2$ = %.5f'%result.rsquared)

        plt.plot(x, comps['peak_'], color='firebrick', ls='--',label='Ar Ref. Line')
        plt.axvline(result.params['peak_center'].value, color='firebrick', ls='--')

        for i in range(1,self.ncomponents):
            label = 'Blended Line %i'%i
            plt.plot(x, comps['blend%i_'%i], color='grey', ls='--',label=label)
            plt.axvline(result.params['blend%i_center'%i].value, color='grey', ls='--')

        plt.plot(x, comps['bkg_'], color='lightgrey', ls='--', label='Bkg')
        plt.plot(knot_xvals, np.interp(knot_xvals, x, comps['bkg_']), 'x', color='k')
        plt.legend()
