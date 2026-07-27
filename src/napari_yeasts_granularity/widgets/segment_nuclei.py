from napari_yeasts_texture.widgets.widget import Widget
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import napari
from napari.qt.threading import create_worker

from autooptions import Options

from napari_yeasts_texture.workers.segment_nuclei import NucleiSegmentation


class SegmentNucleiWidget(Widget):
    
    def __init__(self, viewer: "napari.viewer.Viewer"): # type: ignore
        super().__init__(l_type='grid', viewer=viewer)

    def getOptions(self):
        thresholds = NucleiSegmentation.get_thresholding_methods()
        options = Options("NapariYeastsTexture", "SegmentNuclei")
        options.addImage("Nuclei")
        options.addChoice("Method", value=thresholds[0], choices=thresholds)
        options.addFloat("Sigma", 2.0)
        options.addBool("Use log?", True)
        options.addBool("Kill borders?", True)
        options.addInt("Min size", 100)
        options.load()
        return options
    
    def getAnisotropy(self):
        layer_name = self.options.value("Nuclei")
        if layer_name not in self.viewer.layers:
            return None, 1.0
        layer = self.viewer.layers[layer_name]
        scale = layer.scale
        ani = 1.0
        if len(scale) ==  3:
            ani = scale[0] / scale[1]
        elif len(scale) == 4:
            ani = scale[1] / scale[2]
        return layer, ani

    def apply(self):
        layer, anisotropy = self.getAnisotropy()
        if layer is None:
            return
        sigma = self.options.value("Sigma")
        use_log = self.options.value("Use log?")
        kill_borders = self.options.value("Kill borders?")
        min_size = self.options.value("Min size")
        method = self.options.value("Method")

        self.operation = NucleiSegmentation()
        self.operation.set_input_image(layer.data)
        self.operation.set_anisotropy(anisotropy)
        self.operation.set_sigma(sigma)
        self.operation.set_use_log(use_log)
        self.operation.set_kill_borders(kill_borders)
        self.operation.set_min_size(min_size)
        self.operation.set_method(method)

        worker = create_worker(
            self.operation.run,
            _progress={
                'desc': 'Running nuclei segmentation...'
            }
        )
        worker.finished.connect(self.displayResult)
        worker.start()

    def displayResult(self):
        if self.operation.output_image is None:
            return
        layer_name = self.options.value("Nuclei")
        output_layer_name = f"{layer_name}_segmented"
        layer = self.viewer.layers[layer_name]

        if output_layer_name in self.viewer.layers:
            self.viewer.layers[output_layer_name].data = self.operation.output_image
        else:
            self.viewer.add_labels(
                self.operation.output_image, 
                name=output_layer_name,
                scale=layer.scale
            )