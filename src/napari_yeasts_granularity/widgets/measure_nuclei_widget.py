from napari_yeasts_granularity.widgets.widget import Widget
from napari_yeasts_granularity import (
    MeasureIntensitiesOperator,
    MeasureShapeOperator,
    MeasureSpotsOperator,
    MeasurementsManager,
)
from napari_yeasts_granularity.bridge import NapariBridge
from autooptions import Options
from napari.utils.notifications import show_info, show_warning


class MeasureNucleiWidget(Widget):

    opt_nuclei = "Nuclei"
    opt_intensities = "Intensities"
    opt_use_intensities = "Use intensities?"
    opt_use_shape = "Use shape?"
    opt_use_spots = "Use spots?"
    opt_prominence = "Min. prominence"

    def __init__(self, viewer: "napari.viewer.Viewer"):  # type: ignore
        super().__init__(viewer)

    def getOptions(self):
        options = Options("NapariYeastsGranularity", "MeasureNucleiWidget")
        options.addImage(self.opt_intensities)
        options.addLabels(self.opt_nuclei)
        options.addBool(self.opt_use_intensities, value=True)
        options.addBool(self.opt_use_shape, value=True)
        options.addBool(self.opt_use_spots, value=True)
        options.addFloat(self.opt_prominence, value=MeasureSpotsOperator.get_default_prominence())
        options.load()
        return options

    def create_operator(self):
        nuclei_layer_name = self.options.value(self.opt_nuclei)
        intensities_layer_name = self.options.value(self.opt_intensities)

        op = MeasurementsManager()
        input_intensities, scale = NapariBridge.get_image_as_xarray(
            self.viewer, 
            intensities_layer_name
        )
        input_labels, scale = NapariBridge.get_labels_as_xarray(
            self.viewer, 
            nuclei_layer_name
        )
        calib = scale
        op.set_input_data(input_labels, input_intensities, calib)

        use_intensities = self.options.value(self.opt_use_intensities)
        use_shape = self.options.value(self.opt_use_shape)
        use_spots = self.options.value(self.opt_use_spots)
        prominence = self.options.value(self.opt_prominence)

        if use_intensities:
            mio = MeasureIntensitiesOperator()
            op.add_operator(mio)
        if use_shape:
            mso = MeasureShapeOperator()
            op.add_operator(mso)
        if use_spots:
            mso = MeasureSpotsOperator()
            mso.set_prominence(prominence)
            op.add_operator(mso)

        return op

    def displayResult(self):
        if self.operator is None:
            show_warning("No operator available to display results.")
            return

        controls = self.operator.get_controls()
        dataframe = self.operator.get_merged_measurements()

        nuclei_layer_name = self.options.value(self.opt_nuclei)
        nuclei_layer = self.viewer.layers[nuclei_layer_name]

        nuclei_layer.features = dataframe

        for key, (control, what) in controls.items():
            if what == 'points':
                self.viewer.add_points(
                    control, 
                    name=f"{key} controls", 
                    face_color="transparent", 
                    border_color="red",
                    scale=nuclei_layer.scale
                )
            else:
                show_warning(f"Unknown control type '{what}' for key '{key}'.")


if __name__ == "__main__":
    import napari
    import tifffile as tiff
    from pathlib import Path

    viewer = napari.Viewer()
    widget = MeasureNucleiWidget(viewer)
    viewer.window.add_dock_widget(widget, area="right")

    folder_labels = "/media/clement/fae534f3-f6ab-41aa-9554-baf3f7b791731/yeasts-granularity/Sen1 et Nhp6A/Sen1 et Nhp6A Avec Sel/Sen1 et Nhp6A Replicat 1/Position 2"
    folder_intensities = "/home/clement/Documents/projects/2292-yeasts-granularity/2026-05-11-tiff/Sen1 et Nhp6A/Sen1 et Nhp6A Avec Sel/Sen1 et Nhp6A Replicat 1/Position 2"

    folder_labels = Path(folder_labels)
    folder_intensities = Path(folder_intensities)
    name = "1 Sen1 + NaCl_005.tif"

    intensities_path = folder_intensities / name
    labels_path = folder_labels / name

    labels = tiff.imread(labels_path)
    intensities = tiff.imread(intensities_path)

    viewer.add_image(
        intensities, 
        name="Intensities", 
        scale=(1.0, 0.3, 0.065, 0.065),
        axis_labels=["T", "Z", "Y", "X"]
    )
    viewer.add_labels(
        labels, 
        name="Nuclei", 
        scale=(1.0, 0.3, 0.065, 0.065),
        axis_labels=["T", "Z", "Y", "X"]
    )

    napari.run()