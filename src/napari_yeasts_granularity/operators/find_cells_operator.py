import pandas as pd
import xarray as xr
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.filters import threshold_otsu
from skimage.measure import label
from skimage.morphology import remove_small_objects
from skimage import filters as filters
from .trackpy_tracker import TrackpyTracker


class FindCellsOperator:

    def __init__(self):
        self.input_image    = None
        self.gaussian_sigma = self.default_gaussian_sigma()
        self.use_log        = self.default_use_log()
        self.log_factor     = self.default_log_factor()
        self.kill_borders   = self.default_kill_borders() # on all axes
        self.min_obj_size   = self.default_min_obj_size() # in voxels
        self.objects_diam   = self.default_objects_diam() # physical unit
        self.calibration    = None
        self.output_nuclei  = None

    def get_anisotropy(self) -> float:
        """
        Given the provided axes and calibration, computes the anisotropy factor betwen the XY vs Z axis.
        If the image is 2D, the anisotropy is 1.0.
        """
        if self.calibration is None:
            raise ValueError("Calibration must be set before getting anisotropy.")
        if self.input_image is None:
            raise ValueError("Input image must be set before getting anisotropy.")
        axes = self.input_image.dims
        if 'Z' not in axes:
            return 1.0
        if 'X' not in axes or 'Y' not in axes:
            raise ValueError("Input image must have 'X' and 'Y' axes.")
        z_index = axes.index('Z')
        z_size  = self.calibration[z_index]
        x_index = axes.index('X')
        xy_size = self.calibration[x_index]
        return z_size / xy_size
    
    @staticmethod
    def default_log_factor() -> float:
        return 2.0
    
    @staticmethod
    def default_objects_diam() -> float:
        return 1.7
    
    @staticmethod
    def default_min_obj_size() -> int:
        return 100 # in voxels

    @staticmethod
    def default_kill_borders() -> bool:
        return True

    @staticmethod
    def default_use_log() -> bool:
        return True

    @staticmethod
    def default_gaussian_sigma() -> float:
        return 1.0
    
    @staticmethod
    def remap_labels(label_image) -> np.ndarray:
        _, inverse = np.unique(label_image, return_inverse=True)
        relabeled = inverse.reshape(label_image.shape)
        return relabeled

    def get_message(self):
        return "Segmenting and tracking nuclei..."
    
    def set_input_image(self, image, axes='TZYX'):
        if image.ndim != len(axes):
            raise ValueError(f"Image dimensions {image.ndim} do not match axes length {len(axes)}")
        self.input_image = xr.DataArray(image, dims=list(axes))

    def set_input_image_xarray(self, image: xr.DataArray):
        if not isinstance(image, xr.DataArray):
            raise TypeError("Input image must be an xarray DataArray.")
        self.input_image = image

    def set_calibration(self, calibration: tuple):
        self.calibration = calibration
    
    def set_use_log(self, use_log: bool):
        self.use_log = use_log

    def set_gaussian_sigma(self, sigma: float):
        self.gaussian_sigma = sigma

    def set_kill_borders(self, kill: bool):
        self.kill_borders = kill

    def set_min_obj_size(self, size: int):
        self.min_obj_size = size

    def set_objects_diam(self, diam: float):
        self.objects_diam = diam

    def _identify_border_labels_frame(self, frame) -> set:
        border_labels = set()
        border_labels.update(np.unique(frame[0, :, :]))
        border_labels.update(np.unique(frame[-1, :, :]))
        border_labels.update(np.unique(frame[:, 0, :]))
        border_labels.update(np.unique(frame[:, -1, :]))
        border_labels.update(np.unique(frame[:, :, 0]))
        border_labels.update(np.unique(frame[:, :, -1]))
        return border_labels
    
    def _identify_border_labels(self, label_image) -> set:
        border_labels = set()
        if 'T' in label_image.dims:
            for t in range(label_image.sizes['T']):
                frame = label_image.isel({'T': t}).values
                border_labels.update(self._identify_border_labels_frame(frame))
        else:
            frame = label_image.values
            border_labels.update(self._identify_border_labels_frame(frame))
        return border_labels
    
    def _kill_borders(self, label_image) -> xr.DataArray:
        border_labels = self._identify_border_labels(label_image)
        mask = np.isin(label_image, list(border_labels), invert=True)
        return xr.DataArray(label_image * mask, dims=label_image.dims)

    def get_calibration_as_dict(self) -> dict:
        if self.calibration is None:
            raise ValueError("Calibration has not been set.")
        if self.input_image is None:
            raise ValueError("Input image must be set before getting calibration.")
        return {axis: calib for axis, calib in zip(self.input_image.dims, self.calibration)}
    
    def _prefilter(self, image_tzyx, anisotropy) -> np.ndarray:
        sigmas = [0.0 for _ in range(image_tzyx.ndim)]
        if 'Z' in image_tzyx.dims:
            z_index = image_tzyx.dims.index('Z')
            sigmas[z_index] = self.gaussian_sigma / anisotropy
        yx_indices = [image_tzyx.dims.index(dim) for dim in ['Y', 'X']]
        for idx in yx_indices:
            sigmas[idx] = self.gaussian_sigma
        return gaussian_filter(image_tzyx, sigma=sigmas)
    
    def _segment_nuclei_3d(self, prefiltered) -> np.ndarray:
        image = prefiltered - prefiltered.min()
        image = image / image.max()
        if self.use_log:
            image = np.log(self.log_factor * image + 1.0)
        t = threshold_otsu(image)
        image = label(image > t)
        image = remove_small_objects(image, max_size=self.min_obj_size)
        return self.remap_labels(image).astype(np.uint16)
    
    def _segment_nuclei_nd(self, img) -> np.ndarray:
        img = img.astype(np.float32)
        if img.ndim == 3:
            return self._segment_nuclei_3d(img)
        elif img.ndim == 4:
            buffer = np.zeros_like(img, dtype=np.uint16)
            for t in range(img.shape[0]):
                buffer[t] = self._segment_nuclei_3d(img[t])
            return buffer
        else:
            raise ValueError(f"Unsupported image dimensions: {img.ndim}")
        
    def _track_nuclei(self, labeled_nuclei) -> xr.DataArray:
        tracker = TrackpyTracker()
        tracker.initFromLabels(labeled_nuclei, self.get_calibration_as_dict())
        tracker.setSearchingDistance(self.objects_diam)
        tracker.setMemory(1)
        tracker.setRemoveIncompleteTracks(True)
        tracker.run()
        return tracker.relabelWithTracks(labeled_nuclei)
    
    def set_log_factor(self, factor: float):
        if factor < 1.0:
            raise ValueError("Log factor must be greater than or equal to 1.0.")
        self.log_factor = factor
    
    def get_output_nuclei(self) -> xr.DataArray:
        if self.output_nuclei is None:
            raise ValueError("Output nuclei have not been generated yet. Please run the operator first.")
        return self.output_nuclei

    def run(self):
        if self.input_image is None:
            raise ValueError("Input image must be set before running the operator.")
        
        if self.calibration is None:
            raise ValueError("Calibration must be set before running the operator.")
        
        target_axes = list([a for a in 'TZYX' if a in self.input_image.dims])
        anisotropy  = self.get_anisotropy()
        prefiltered = self._prefilter(
            self.input_image.transpose(*target_axes),
            anisotropy
        )
        labeled_nuclei = xr.DataArray(
            self._segment_nuclei_nd(prefiltered), 
            dims=target_axes
        )
        tracked_nuclei = (
            self._track_nuclei(labeled_nuclei)
            if 'T' in labeled_nuclei.dims
            else labeled_nuclei
        )
        if self.kill_borders:
            tracked_nuclei = self._kill_borders(tracked_nuclei)
        
        tracked_nuclei.values = self.remap_labels(tracked_nuclei.values)
        self.output_nuclei = tracked_nuclei.transpose(*self.input_image.dims)
        self.output_nuclei.attrs = self.input_image.attrs


if __name__ == "__main__":
    from .data_loader import DataLoader

    dl = DataLoader(group_size=3, group_index=1)
    dl.set_base_calibration({
        'T': 1.0,
        'Z': 0.3,
        'Y': 0.065,
        'X': 0.065
    })
    while dl.next():
        image, image_axes = dl.load_image()
        calib = dl.get_calibration(image_axes)

        op = FindCellsOperator()
        op.set_input_image(image, axes=image_axes)
        op.set_calibration(calib)
        op.run()

        dl.save_labels(op.get_output_nuclei().values)