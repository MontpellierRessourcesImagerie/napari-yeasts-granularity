import xarray as xr
import numpy as np
from scipy.stats import pearsonr
from .measure_operator import BaseMeasureOperator


class MeasureColocOperator(BaseMeasureOperator):

    name = "Measure colocalization"

    def __init__(self):
        super().__init__()
        self.secondary_image = None

    def set_secondary_image(self, secondary_image):
        if self.intensity_image is None:
            raise ValueError("Primary intensity image must be set before setting the secondary image.")
        if secondary_image.dims != self.intensity_image.dims:
            raise ValueError("Secondary image must have the same dimensions as the primary intensity image.")
        if secondary_image.shape != self.intensity_image.shape:
            raise ValueError("Secondary image must have the same shape as the primary intensity image.")
        self.secondary_image = secondary_image

    def _measure_objects_3D(self, labels_frame, intensity_frame, spacing, rows, t=0, nT=1):
        labels = np.unique(labels_frame)
        labels = labels[labels != 0]

        if self.secondary_image is None:
            raise ValueError("Secondary image has not been set. Please set it before running the operator.")

        secondary_frame = (
            self.secondary_image.values 
            if 'T' not in self.secondary_image.dims 
            else self.secondary_image.isel({'T': t}).values
        )
        
        for label in labels:
            mask = labels_frame == label
            values_a = intensity_frame[mask]
            values_b = secondary_frame[mask]
            line_idx = (label - 1) * nT + t
            r, p_value = pearsonr(values_a, values_b)
            rows[line_idx] = {
                'Pearson': r, 
                'P-value': p_value,
                'Label'  : int(label),
                'T'      : t
            }
        

if __name__ == "__main__":
    from .data_loader import DataLoader

    base_calib = {
        'T': 1.0,
        'Z': 0.3,
        'Y': 0.065,
        'X': 0.065
    }

    dl1 = DataLoader(group_size=3, group_index=1)
    dl1.set_base_calibration(base_calib)

    dl2 = DataLoader(group_size=3, group_index=2)
    dl2.set_base_calibration(base_calib)

    while dl1.next() and dl2.next():
        c1, c1_axes = dl1.load_image()
        calib = dl1.get_calibration(c1_axes)
        c2, c2_axes = dl2.load_image()

        c1_arr = xr.DataArray(c1, dims=list(c1_axes))
        c2_arr = xr.DataArray(c2, dims=list(c2_axes))
        labels, label_axes = dl1.load_labels()

        if labels is None or label_axes is None:
            print(f"Skipping measurement.")
            continue

        labels_arr = xr.DataArray(labels, dims=list(label_axes))

        op = MeasureColocOperator()
        op.set_input_data(labels_arr, c1_arr, calib)
        op.set_secondary_image(c2_arr)
        op.run()

        measurements = op.get_measurements()
        measurements_path = dl1.get_results_path("coloc")
        measurements.to_csv(measurements_path, index=False)