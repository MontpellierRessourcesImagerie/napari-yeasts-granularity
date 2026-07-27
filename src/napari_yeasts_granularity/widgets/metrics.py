from napari_yeasts_texture.widgets.widget import Widget
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import napari

from autooptions import Options


class MetricsWidget(Widget):
    
    def __init__(self, viewer: "napari.viewer.Viewer"): # type: ignore
        super().__init__(l_type='grid', viewer=viewer)

    def getOptions(self):
        options = Options("NapariYeastsTexture", "Metrics")
        options.addLabels("Nuclei")
        options.addImage("Intensities")
        options.addBool("Q3-Q1 (img)", True)
        options.addBool("Q3-Q1 (LoG)", True)
        options.addBool("Std.Dev. (img)", True)
        options.addBool("Std.Dev. (LoG)", True)
        options.addBool("Hessian (img)", True)
        options.load()
        return options
