from .measure_operator import BaseMeasureOperator
import xarray as xr
from skimage.measure import regionprops
import numpy as np


class MeasureShapeOperator(BaseMeasureOperator):

    name = "Measure shapes"

    def _measure_objects_3D(self, labels_frame, intensity_frame, spacing, rows, t=0, nT=1):
        all_props = regionprops(
            labels_frame, 
            intensity_image=intensity_frame, 
            spacing=spacing
        )
        nL = np.max(labels_frame)

        for region in all_props:
            label = int(region.label)
            volume = region.area
            solidity = region.solidity
            line_idx = (label - 1) * nT + t
            rows[line_idx].update({
                "Label" : label,
                "T" : t,
                "Volume" : volume,
                "Solidity" : solidity,
                "Sphericity": region.equivalent_diameter / region.major_axis_length if region.major_axis_length > 0 else np.nan
            })

    
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
        labels, label_axes = dl.load_labels()
        calib = dl.get_calibration(image_axes)

        if labels is None or label_axes is None:
            print(f"Skipping measurement.")
            continue

        image_arr = xr.DataArray(image, dims=list(image_axes))
        labels_arr = xr.DataArray(labels, dims=list(label_axes))

        op = MeasureShapeOperator()
        op.set_input_data(labels_arr, image_arr, calib)
        op.run()

        measurements = op.get_measurements()
        measurements_path = dl.get_results_path("shapes")
        measurements.to_csv(measurements_path, index=False)