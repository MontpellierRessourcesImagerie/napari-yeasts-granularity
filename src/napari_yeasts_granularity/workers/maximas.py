import tifffile as tiff
import numpy as np
import pandas as pd
from pathlib import Path
from pprint import pprint

from scipy.ndimage import gaussian_filter, gaussian_laplace
from skimage.filters import threshold_li, threshold_otsu
from skimage.measure import label, regionprops
from skimage.morphology import remove_small_objects

from skimage import morphology as morph
from skimage import filters as filters

import numpy as np
from scipy.ndimage import gaussian_laplace
from skimage.feature import peak_local_max
from skimage.draw import disk


class MaximasFinder:
    def __init__(self):
        self.intensities = None
        self.nuclei = None
        self.log_response = None
        self.points = None
        self.sigma_xy = 2.0
        self.anisotropy = 1.0
        self.prominence = 2000.0

    def set_intensities(self, img):
        self.intensities = img

    def set_nuclei(self, img):
        self.nuclei = img

    def set_sigma_xy(self, sigma):
        self.sigma_xy = sigma

    def set_anisotropy(self, ani):
        self.anisotropy = ani

    def set_prominence(self, prominence):
        self.prominence = prominence
 
    def detect_spots_log(
        self,
        stack: np.ndarray,
        sigma_xy: float,
        anisotropy: float,
        prominence: float,
    ) -> np.ndarray:
    
        sigma_z = sigma_xy / anisotropy
        sigmas = (sigma_z, sigma_xy, sigma_xy)   # (z, y, x)
    
        stack_f = stack.astype(np.float64)
        log_response = gaussian_laplace(stack_f, sigma=sigmas) * (sigma_xy ** 2)
        tiff.imwrite("/tmp/log_response.tif", log_response.astype(np.float32))
    
        neg_log = -log_response
    
        coords = peak_local_max(
            neg_log,
            min_distance=2,
            threshold_abs=prominence,
            exclude_border=True,
        )
        
        self.output_image = neg_log
        return coords
    
    def search_maxima(self, spots_img, nuclei_img, sigma=2.0, ani=1.0):
        points = None
        if spots_img.ndim == 3:
            coordinates = self.detect_spots_log(
                spots_img, 
                sigma_xy=sigma, 
                anisotropy=ani, 
                prominence=self.prominence
            )
            points = np.array(coordinates)
        elif spots_img.ndim == 4:
            buffer = []
            for t in range(spots_img.shape[0]):
                print(f"  T:{t+1} / {spots_img.shape[0]}")
                coordinates = self.detect_spots_log(
                    spots_img[t], 
                    sigma_xy=sigma, 
                    anisotropy=ani, 
                    prominence=self.prominence
                )
                buffer.extend([(t, *coord) for coord in coordinates])
            points = np.array(buffer)
        else:
            raise ValueError(f"Unsupported image dimensions: {spots_img.ndim}")
        
        return points.astype(float)
    
    def run(self):
        if self.intensities is None:
            raise ValueError("Input image is not set.")
        self.points = self.search_maxima(
            self.intensities, 
            self.nuclei,
            sigma=self.sigma_xy, 
            ani=self.anisotropy
        )
    
