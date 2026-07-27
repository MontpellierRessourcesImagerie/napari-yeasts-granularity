import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.filters import threshold_li, threshold_otsu
from skimage.measure import label
from skimage.morphology import remove_small_objects
from skimage import filters as filters
from .trackpy_tracker import TrackpyTracker

class NucleiSegmentation:

    thresholding_methods = {
        "Otsu"  : threshold_otsu,
        "Li"    : threshold_li,
        "Mean"  : np.mean,
        "Median": np.median
    }

    def __init__(self):
        self.input_image = None
        self.output_image = None
        self.sigma = 2.0
        self.use_log = True
        self.kill_borders = True
        self.min_size = 100
        self.method = "Otsu"
        self.anisotropy = 1.0

    def set_input_image(self, img):
        self.input_image = img

    def set_anisotropy(self, ani):
        self.anisotropy = ani

    def set_sigma(self, sigma):
        self.sigma = sigma

    def set_use_log(self, use_log):
        self.use_log = use_log

    def set_kill_borders(self, kill_borders):
        self.kill_borders = kill_borders

    def set_min_size(self, min_size):
        self.min_size = min_size

    def set_method(self, method):
        if method not in self.thresholding_methods:
            raise ValueError(f"Unknown thresholding method: {method}")
        self.method = method

    @staticmethod
    def get_thresholding_methods():
        return list(NucleiSegmentation.thresholding_methods.keys())

    @staticmethod
    def remap_labels(label_image):
        _, inverse = np.unique(label_image, return_inverse=True)
        relabeled = inverse.reshape(label_image.shape)
        return relabeled

    def _segment_nuclei(self, img, sigma=2.0, ani=1.0):
        s_yx = sigma
        s_z = sigma / ani
        sigmas = (s_z, s_yx, s_yx)
        blurred = gaussian_filter(img, sigmas)
        if self.use_log:
            blurred = np.log(blurred + 1.0)
        threshold_func = self.thresholding_methods[self.method]
        t = threshold_func(blurred)
        labels = label(blurred > t)
        filtered = remove_small_objects(labels, max_size=self.min_size)
        return NucleiSegmentation.remap_labels(filtered).astype(np.uint16)

    def segment_nuclei(self, img, sigma=2.0, ani=1.0):
        img = img.astype(np.float32)
        if img.ndim == 3:
            return self._segment_nuclei(img, sigma=sigma, ani=ani)
        elif img.ndim == 4:
            buffer = np.zeros_like(img, dtype=np.uint16)
            for t in range(img.shape[0]):
                buffer[t] = self._segment_nuclei(img[t], sigma=sigma, ani=ani)
            return buffer
        else:
            raise ValueError(f"Unsupported image dimensions: {img.ndim}")
        
    def run(self):
        if self.input_image is None:
            raise ValueError("Input image is not set.")
        self.output_image = self.segment_nuclei(
            self.input_image, 
            sigma=self.sigma, 
            ani=self.anisotropy
        )