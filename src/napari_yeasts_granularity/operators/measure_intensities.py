from .measure_operator import BaseMeasureOperator
import xarray as xr
from skimage.measure import regionprops
import numpy as np
from scipy.ndimage import gaussian_filter


class MeasureIntensitiesOperator(BaseMeasureOperator):

    name = "Measure intensities"

    def __init__(self):
        super().__init__()
        self.dog_sigmas = (1.0, 4.0)
        self.metric_functions = {
            ""   : self._get_original_data,
            "DoG": self._get_dog_data
        }

    def get_calibrated_sigma(self, sigma, calib):
        if len(calib) == 2:
            return (sigma, sigma)
        else:
            ani = calib[0] / calib[1]
            return (sigma / ani, sigma, sigma)
        
    def _get_original_data(self, data, spacing):
        return data.copy()
    
    def _get_dog_data(self, data, spacing):
        s1, s2 = self.dog_sigmas
        s1 = self.get_calibrated_sigma(s1, spacing)
        s2 = self.get_calibrated_sigma(s2, spacing)
        g1 = gaussian_filter(data.astype(np.float32), sigma=s1)
        g2 = gaussian_filter(data.astype(np.float32), sigma=s2)
        dog = g1 - g2
        return dog
    
    @staticmethod
    def as_key(key, what):
        if what == "":
            return key
        else:
            return f"{key} ({what})"

    def _measure_objects_3D(self, labels_frame, intensity_frame, spacing, rows, t=0, nT=1):
        for metric_name, metric_func in self.metric_functions.items():
            metric_data = metric_func(intensity_frame, spacing)
            
            all_props = regionprops(
                labels_frame, 
                intensity_image=metric_data, 
                spacing=spacing
            )

            for region in all_props:
                label = int(region.label)

                if int(label) == 0:
                    continue  # Skip background

                line_idx = (label - 1) * nT + t
                values = region.image_intensity[region.image]
                mean_int = float(np.mean(values))
                std_int = float(np.std(values))
                sorted = np.sort(values)
                q1 = np.percentile(sorted, 25)
                q3 = np.percentile(sorted, 75)
                iqr = q3 - q1
                rows[line_idx].update({
                    "Label" : label,
                    "T" : t,
                    self.as_key("Mean", metric_name) : mean_int,
                    self.as_key("Std. Dev.", metric_name): std_int,
                    self.as_key("Q1", metric_name) : q1,
                    self.as_key("Q3", metric_name) : q3,
                    self.as_key("IQR", metric_name) : iqr
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

        op = MeasureIntensitiesOperator()
        op.set_input_data(labels_arr, image_arr, calib)
        op.run()

        measurements = op.get_measurements()
        measurements_path = dl.get_results_path("intensities")
        measurements.to_csv(measurements_path, index=False)