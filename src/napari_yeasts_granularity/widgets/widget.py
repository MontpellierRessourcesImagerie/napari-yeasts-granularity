from abc import abstractmethod
from autooptions import OptionsWidget
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout
)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import napari
from napari.utils.notifications import show_info

class Widget(QWidget):
    def __init__(self, l_type, viewer: "napari.viewer.Viewer"): # type: ignore
        super().__init__()
        self.viewer     = viewer
        self.sameRowSet = set()
        self.options    = self.getOptions()
        self.operation  = None
        self.l_type     = l_type
        self.widget     = self.createLayout()

    def createLayout(self):
        widget = OptionsWidget(
            viewer=self.viewer, 
            options=self.options, 
            layout_type=self.l_type, 
            client=self,
            sameRowSet=self.sameRowSet
        )
        widget.addApplyButton(self.apply)
        layout = QVBoxLayout()
        layout.addWidget(widget)
        self.setLayout(layout)
        return widget

    @abstractmethod
    def getOptions(self):
        raise Exception("Abstract method getOptions of class Widget called!")
    
    def apply(self):
        show_info(f"Saved settings for: {self.options.applicationName}.{self.options.optionsName}")
    