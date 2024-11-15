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
        self.setVisible(False)

        # Layout and parameters for intensity normalization
        layout = QVBoxLayout()
        self.setLayout(layout)

        button1 = QPushButton('Button 1')
        layout.addWidget(button1)

        layout.addWidget(QLabel('Parameter 1'))
        self.param1 = QLineEdit(self)
        layout.addWidget(self.param1)


class SmoothingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)

        # Layout and parameters for intensity normalization
        layout = QVBoxLayout()
        self.setLayout(layout)

        button1 = QPushButton('Button 1')
        layout.addWidget(button1)

        layout.addWidget(QLabel('Parameter 1'))
        self.param1 = QLineEdit(self)
        layout.addWidget(self.param1)


class mmv_playground(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer

        # Define a layout for the main widget
        layout1 = QVBoxLayout()
        self.setLayout(layout1)

        # Define a scroll area inside the QVBoxLayout
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        layout1.addWidget(scroll_area)

        # Define a group box inside the scroll area
        group_box = QGroupBox('MMV-Playground')
        layout2 = QVBoxLayout()
        group_box.setLayout(layout2)
        scroll_area.setWidget(group_box)        

        # Add widgets to the group box
        # Button 'intensity normalization'
        self.btn_intensity = QPushButton('Intensity normalization')
        self.btn_intensity.clicked.connect(self.toggle_intensity_widget)
        layout2.addWidget(self.btn_intensity)

        # Intensity widget
        self.intensity_widget = IntensityWidget(self)
        layout2.addWidget(self.intensity_widget)

        # Button smoothing
        self.btn_smoothing = QPushButton('Smoothing')
        self.btn_smoothing.clicked.connect(self.toggle_smoothing_widget)
        layout2.addWidget(self.btn_smoothing)

        # Smoothing widget
        self.smoothing_widget = SmoothingWidget(self)
        layout2.addWidget(self.smoothing_widget)

    def toggle_intensity_widget(self):
        # Switching the visibility of the intensity widget
        if self.intensity_widget.isVisible():
            self.intensity_widget.setVisible(False)
            self.btn_intensity.setText('Intensity normalization')
        else:
            self.intensity_widget.setVisible(True)
            self.btn_intensity.setText('Hide intensity normalization')

    def toggle_smoothing_widget(self):
        # Switching the visibility of the smoothing widget
        if self.smoothing_widget.isVisible():
            self.smoothing_widget.setVisible(False)
            self.btn_smoothing.setText('Smoothing')
        else:
            self.smoothing_widget.setVisible(True)
            self.btn_smoothing.setText('Hide smoothing')
