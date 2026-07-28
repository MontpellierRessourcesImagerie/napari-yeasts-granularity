import pandas as pd
from abc import ABC, abstractmethod
import xarray as xr
import numpy as np
from tqdm import tqdm


class BaseMeasureOperator(ABC):

    def __init__(self):
        self.labeled_objects = None
        self.intensity_image = None
        self.calibration     = None
        self.measurements    = None
        self.control_img     = None

    def nTimes(self) -> int:
        if self.labeled_objects is None:
            raise ValueError("Labeled objects data has not been set.")
        if 'T' in self.labeled_objects.dims:
            return self.labeled_objects.sizes['T']
        else:
            return 1

    def hasTime(self) -> bool:
        if self.labeled_objects is None:
            raise ValueError("Labeled objects data has not been set.")
        return 'T' in self.labeled_objects.dims

    def set_input_data(self, labels: xr.DataArray, intensities: xr.DataArray, calib: tuple):
        if labels.dims != intensities.dims:
            raise ValueError("Labels and intensities must have the same dimensions.")
        if len(calib) != len(labels.dims):
            raise ValueError("Calibration tuple length must match the number of dimensions in the input data.")
        self.labeled_objects = labels
        self.intensity_image = intensities
        self.calibration = calib

    def _get_reshaped_data(self):
        if self.labeled_objects is None:
            raise ValueError("Labeled objects data has not been set.")
        if self.intensity_image is None:
            raise ValueError("Intensity image data has not been set.")
        if self.calibration is None:
            raise ValueError("Calibration data has not been set.")
        calib_dict = {ax: self.calibration[i] for i, ax in enumerate(self.labeled_objects.dims)}
        target_axes = [ax for ax in 'TZYX' if ax in self.labeled_objects.dims]
        label_map = self.labeled_objects.transpose(*target_axes, ...).values
        intensity_map = self.intensity_image.transpose(*target_axes, ...).values
        spacing = tuple([calib_dict[ax] for ax in target_axes])
        return label_map, intensity_map, spacing

    def get_measurements(self) -> pd.DataFrame:
        if self.measurements is None:
            raise ValueError("Measurements have not been computed. Please run the operator first.")
        m = self.measurements.copy()
        return m.sort_values(by=["Label", "T"]).reset_index(drop=True)

    @abstractmethod
    def _measure_objects_3D(self, labels_frame, intensity_frame, spacing, rows, t=0, nT=1):
        raise NotImplementedError("Subclasses must implement the _measure_objects_3D method.")

    def get_control(self) -> tuple[str, np.ndarray, str]|tuple[None, None, None]:
        return (None, None, None)

    def _measure_objects(self) -> pd.DataFrame|None:
        label_map, intensity_map, spacing = self._get_reshaped_data()
        # The label map is remapped by FindCellsOperator and  incomplete tracks are removed, 
        # so the labels indexing is dense and labels are present at all frames.
        nT = self.nTimes()
        nL = np.max(label_map)
        rows = [{} for _ in range(nL * nT)] 
        
        if self.hasTime():
            for t in tqdm(range(nT)):
                labels_frame = label_map[t]
                intensity_frame = intensity_map[t]
                self._measure_objects_3D(labels_frame, intensity_frame, spacing[1:], rows, t=t, nT=nT)
        else:
            self._measure_objects_3D(label_map, intensity_map, spacing, rows)

        res = pd.DataFrame(rows)
        if "Label" not in res.columns or "T" not in res.columns:
            return None
        res = res.sort_values(by=["Label", "T"]).reset_index(drop=True)
        return res

    def run(self):
        self.measurements = self._measure_objects()

