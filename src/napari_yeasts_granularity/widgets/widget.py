from abc import abstractmethod
from autooptions import OptionsWidget
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout
)
from napari.qt.threading import create_worker

class Widget(QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer     = viewer
        self.sameRowSet = set()
        self.options    = self.getOptions()
        self.operator   = None
        self.widget     = self.createLayout()

    def createLayout(self):
        widget = OptionsWidget(
            viewer=self.viewer, 
            options=self.options, 
            layout_type='grid', 
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

    @abstractmethod
    def create_operator(self):
        raise Exception("Abstract method create_operator of class Widget called!")
    
    def apply(self):
        self.operator = self.create_operator()
        if self.operator is None:
            return
        worker = create_worker(
            self.operator.run,
            _progress={
                "desc": self.operator.get_message()
            },
        )
        
        worker.finished.connect(self.displayResult)
        worker.start()

    @abstractmethod
    def displayResult(self, *args):
        raise Exception("Abstract method displayResult of class Widget called!")
    