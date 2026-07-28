import pandas as pd
import xarray as xr
from functools import reduce
from .measure_operator import BaseMeasureOperator


class MeasurementsManager:
    def __init__(self):
        self.measurements = []
        self.operators = []
        self.input_intensities = None
        self.input_labels = None
        self.input_calibration = None
        self.controls = {}

    def get_message(self):
        return f"Performing measurements with {len(self.operators)} operators."

    def get_controls(self):
        return self.controls

    def add_operator(self, operator_instance):
        if not issubclass(type(operator_instance), BaseMeasureOperator):
            raise ValueError("Operator must be an instance of BaseMeasureOperator.")
        operator_instance.set_input_data(
            self.input_labels, 
            self.input_intensities, 
            self.input_calibration
        )
        self.operators.append(operator_instance)

    def set_input_data(self, labels: xr.DataArray, intensities: xr.DataArray, calib: tuple):
        if labels.shape != intensities.shape:
            raise ValueError("Labels and intensities must have the same shape.")
        if len(calib) != labels.ndim:
            raise ValueError("Calibration tuple length must match the number of dimensions in the input data.")
        self.input_labels      = labels
        self.input_intensities = intensities
        self.input_calibration = calib

    def run(self):
        for op_instance in self.operators:
            print("Running operator:", type(op_instance).__name__)
            op_instance.run()
            key, control, what = op_instance.get_control()
            if control is not None:
                self.controls[key] = (control, what)
            self.measurements.append(op_instance.get_measurements())
        print("All operators have been executed.")

    def get_merged_measurements(self):
        if not self.measurements:
            return pd.DataFrame()
        return reduce(
            lambda left, right: pd.merge(left, right, on=["Label", "T"], how="outer"),
            self.measurements
        )


if __name__ == "__main__":
    from pathlib import Path
    import tifffile as tiff

    from .measure_intensities import MeasureIntensitiesOperator
    from .measure_shape_operator import MeasureShapeOperator
    from .measure_spots_operator import MeasureSpotsOperator

    folder_intensities = Path("/home/clement/Documents/projects/2292-yeasts-granularity/2026-05-11-tiff/Sen1 et Nhp6A/Sen1 et Nhp6A Avec Sel/Sen1 et Nhp6A Replicat 1/Position 2")
    folder_labels = Path("/media/clement/fae534f3-f6ab-41aa-9554-baf3f7b791731/yeasts-granularity/Sen1 et Nhp6A/Sen1 et Nhp6A Avec Sel/Sen1 et Nhp6A Replicat 1/Position 2")
    
    intensities_path = folder_intensities / "1 Sen1 + NaCl_005.tif"
    labels_path      = folder_labels      / "1 Sen1 + NaCl_005.tif"
    
    calib = (1.0, 0.3, 0.065, 0.065) # TZYX
    intensities = tiff.imread(intensities_path)
    labels = tiff.imread(labels_path)

    intensities_arr = xr.DataArray(
        intensities, 
        dims=('T', 'Z', 'Y', 'X'),
        attrs={a: s for a, s in zip(('T', 'Z', 'Y', 'X'), calib)}
    )
    labels_arr = xr.DataArray(
        labels, 
        dims=('T', 'Z', 'Y', 'X'),
        attrs={a: s for a, s in zip(('T', 'Z', 'Y', 'X'), calib)}
    )

    operator = MeasurementsManager()
    operator.set_input_data(labels_arr, intensities_arr, calib)

    mio = MeasureIntensitiesOperator()
    operator.add_operator(mio)

    mso = MeasureShapeOperator()
    operator.add_operator(mso)

    mst = MeasureSpotsOperator()
    mst.set_prominence(350.0)
    operator.add_operator(mst)

    operator.run()

    measurements = operator.get_merged_measurements()
    csv_path = "/home/clement/Desktop/1 Sen1 + NaCl_005_measurements.csv"
    measurements.to_csv(csv_path, index=False)