from .measure_operator import BaseMeasureOperator
import xarray as xr
import numpy as np
from skimage.measure import regionprops
from scipy.ndimage import (
    gaussian_filter,
    grey_opening,
    uniform_filter
)
from skimage.morphology.extrema import h_maxima


class MeasureSpotsOperator(BaseMeasureOperator):

    name = "Count spots per nucleus"

    def __init__(self):
        super().__init__()
        self.prominence = MeasureSpotsOperator.get_default_prominence()
        self.coordinates_buffer = []

    @staticmethod
    def get_default_prominence():
        return 400.0

    def set_prominence(self, prominence):
        if prominence <= 0:
            raise ValueError("Prominence must be a positive value.")
        self.prominence = prominence

    def get_control(self):
        key = "spots"
        control = None
        if len(self.coordinates_buffer) == 1: # 3D no time
            control = self.coordinates_buffer[0]
        else: # 3D + time
            merged_coords = []
            for buffer_idx, coords_array in enumerate(self.coordinates_buffer):
                if coords_array.size > 0:
                    time_indices = np.full((coords_array.shape[0], 1), buffer_idx, dtype=coords_array.dtype)
                    merged_coords.append(np.hstack([time_indices, coords_array]))
            control = np.vstack(merged_coords) if merged_coords else np.empty((0, 4)) 
        return (key, control, 'points')

    def _preprocess_image_3D(self, image):
        image = gaussian_filter(
            image.astype(np.float32), 
            sigma=(0.0, 0.5, 0.5)
        )
        opened = grey_opening(
            image, 
            size=(0, 7, 7)
        )
        opened = np.minimum(
            opened, 
            image
        )
        recon = image - opened

        blurred = gaussian_filter(
            recon, 
            sigma=(0.5, 5.0, 5.0)
        )
        recon = recon - blurred
        recon = uniform_filter(
            recon, 
            size=(0, 3, 3)
        )

        return recon

    def _build_mean_stddev_maps_3D(self, image, labels):
        std_dev_img = np.zeros_like(image, dtype=np.float32)
        mean_img = np.zeros_like(image, dtype=np.float32)
        all_props = regionprops(
            labels,
            intensity_image=image
        )

        std_dict = np.zeros((np.max(labels) + 1,), dtype=np.float32)
        median_dict = np.zeros((np.max(labels) + 1,), dtype=np.float32)

        for region in all_props:
            label = int(region.label)
            median_intensity = np.median(region.image_intensity[region.image])
            std_dev_intensity = np.std(region.image_intensity[region.image])
            std_dict[label] = std_dev_intensity
            median_dict[label] = median_intensity

        std_dev_img = std_dict[labels]
        mean_img = median_dict[labels]
        return mean_img, std_dev_img

    def _find_spots_3D(self, image, labels):
        preprocessed = self._preprocess_image_3D(image)
        h_max = h_maxima(preprocessed, self.prominence)
        coordinates = np.where(h_max > 0)
        self.coordinates_buffer.append(np.column_stack(coordinates))
        cell_ids = labels[coordinates]
        unique_cell_ids, counts = np.unique(cell_ids[cell_ids > 0], return_counts=True)
        nCells = np.max(labels)
        counts_per_cell = np.zeros((nCells+1,), dtype=np.uint8)
        for cell_id, count in zip(unique_cell_ids, counts):
            counts_per_cell[cell_id] = count

        return counts_per_cell


    def _measure_objects_3D(self, labels_frame, intensity_frame, spacing, rows, t=0, nT=1):
        counts_per_cell = self._find_spots_3D(intensity_frame, labels_frame)
        for cell_id, n_spots in enumerate(counts_per_cell):
            if cell_id == 0:
                continue
            line_idx = (cell_id - 1) * nT + t
            rows[line_idx].update({
                "Label" : cell_id,
                "T" : t,
                "Num. spots" : n_spots
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

        op = MeasureSpotsOperator()
        op.set_input_data(labels_arr, image_arr, calib)
        op.run()

        measurements = op.get_measurements()
        measurements_path = dl.get_results_path("spots")
        measurements.to_csv(measurements_path, index=False)

        (_, ctrl, _) = op.get_control()
        print(ctrl.shape)
        print(ctrl[:5])