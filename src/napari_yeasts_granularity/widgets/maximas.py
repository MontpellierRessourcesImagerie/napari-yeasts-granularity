from napari_yeasts_texture.widgets.widget import Widget
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import napari
from napari.qt.threading import create_worker

from autooptions import Options

from napari_yeasts_texture.workers.maximas import MaximasFinder

class MaximasFinderWidget(Widget):
    
    def __init__(self, viewer: "napari.viewer.Viewer"): # type: ignore
        super().__init__(l_type='grid', viewer=viewer)

    def getOptions(self):
        options = Options("NapariYeastsTexture", "Maximas")
        options.addLabels("Nuclei")
        options.addImage("Intensities")
        options.addFloat("Prominence", 2000.0)
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
        nuclei_layer, anisotropy = self.getAnisotropy()
        if nuclei_layer is None:
            return
        
        intensities_layer_name = self.options.value("Intensities")
        prominence = self.options.value("Prominence")

        if intensities_layer_name not in self.viewer.layers:
            return

        intensities_layer = self.viewer.layers[intensities_layer_name]

        self.operation = MaximasFinder()
        self.operation.set_intensities(intensities_layer.data)
        self.operation.set_nuclei(nuclei_layer.data)
        self.operation.set_prominence(prominence)
        self.operation.set_anisotropy(anisotropy)

        worker = create_worker(
            self.operation.run,
            _progress={
                'desc': 'Running maximas detection...'
            }
        )
        worker.finished.connect(self.displayResult)
        worker.start()

    def displayResult(self):
        points = self.operation.points
        if points is None or len(points) == 0:
            print("No maxima detected.")
            return
        int_name = self.options.value("Intensities")
        max_name = f"Maximas_{int_name}"
        if max_name in self.viewer.layers:
            self.viewer.layers[max_name].data = points
        else:
            self.viewer.add_points(
                points, 
                name=max_name, 
                size=5, 
                face_color='transparent', 
                border_color='red'
            )