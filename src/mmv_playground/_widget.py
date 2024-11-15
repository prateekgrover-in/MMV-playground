"""
tbd
"""
from typing import TYPE_CHECKING

from qtpy.QtWidgets import (
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    import napari


class IntensityWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisibility(False)

        # Layout and parameters for intensity normalization
        vbox_layout = QVBoxLayout()
        self.setLayout(vbox_layout)

        button1 = QPushButton('Button 1')
        vbox_layout.addWidget(button1)

        vbox_layout.addWidget(QLabel('Parameter 1'))
        self.param11 = QLineEdit(self)
        vbox_layout.addWidget(self.param1)


class SmoothingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisibility(False)

        # Layout and parameters for intensity normalization
        vbox_layout = QVBoxLayout()
        self.setLayout(vbox_layout)

        button1 = QPushButton('Button 1')
        vbox_layout.addWidget(button1)

        vbox_layout.addWidget(QLabel('Parameter 1'))
        self.param11 = QLineEdit(self)
        vbox_layout.addWidget(self.param1)


class mmv_playground(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer

        # define a scroll area inside the main widget
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.addWidget(scroll_area)

        # define a group box inside the scroll area
        group_box = QGroupBox('MMV-Playground')
        vbox_layout = QVBoxLayout()
        group_box.setLayout(vbox_layout)
        scroll_area.setWidget(group_box)        

        # add widgets to the group box
        self.button1 = QPushButton('Intensity normalization')
        self.button1.clicked.connect(self.toggle_intensity_widget)
        vbox_layout.addWidget(self.button1)

        # Intensity widget
        self.intensity_widget = IntensityWidget(self)
        vbox_layout.addWidget(self.intensity_widget)

        self.button2 = QPushButton('Smoothing')
        self.button2.clicked.connect(self.toggle_smoothing_widget)
        vbox_layout.addWidget(self.button2)

        # Smoothing widget
        self.smoothing_widget = SmoothingWidget(self)
        vbox_layout.addWidget(self.smoothing_widget)

    def toggle_intensity_widget(self):
        # switching the visibility of the intensity widget
        if self.intensity_widget.isVisible():
            self.intensity_widget.setVisibility(False)
            self.button1.setText('Intensity normalization')
        else:
            self.intensity_widget.setVisibility(True)
            self.button1.setText('Hide intensity normalization')

    def toggle_smoothing_widget(self):
        # switching the visibility of the smoothing widget
        if self.smoothing_widget.isVisible():
            self.smoothing_widget.setVisibility(False)
            self.button2.setText('Smoothing')
        else:
            self.intensity_widget.setVisibility(True)
            self.button1.setText('Hide smoothing')
