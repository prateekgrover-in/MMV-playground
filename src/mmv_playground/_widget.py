"""
tbd
"""
from typing import TYPE_CHECKING

import numpy as np
import napari
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    # QGridvbox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    import napari


class IntensityGroup(QGroupBox):
    # (15.11.2024)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Intensity normalization')
        self.setVisible(False)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.lower_percentage = 0.0
        self.upper_percentage = 100.0
        self.index = 0          # layer index

        # layout and parameters for intensity normalization
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Image'))
        self.image = QComboBox()
        self.image.addItems(parent.layer_names)
        self.image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.image)

        self.lbl_lower = QLabel('lower percentage')
        vbox.addWidget(self.lbl_lower)
        lower = QSlider(Qt.Horizontal)
        lower.setRange(0, 500)
        lower.setSingleStep(1)
        lower.valueChanged.connect(self.lower_changed)
        vbox.addWidget(lower)

        self.lbl_upper = QLabel('Upper percentage')
        vbox.addWidget(self.lbl_upper)
        upper = QSlider(Qt.Horizontal)
        upper.setRange(9500, 10000)
        upper.setSingleStep(1)
        upper.valueChanged.connect(self.upper_changed)
        vbox.addWidget(upper)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.function_run)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.index = index

    def lower_changed(self, value: int):
        # (19.11.2024)
        self.lower_percentage = value / 100.0
        self.lbl_lower.setText('lower percentage: %.2f' % \
            (self.lower_percentage))

    def upper_changed(self, value: int):
        # (19.11.2024)
        self.upper_percentage = value / 100.0
        self.lbl_upper.setText('upper percentage: %.2f' % \
            (self.upper_percentage))

    def function_run(self):
        name = self.parent.layer_names[self.index]

        if any(layer.name == name for layer in self.viewer.layers):
            layer = self.viewer.layers[name]
            input_image = layer.data
        else:
            print('Error: The image %s don\'t exist!' % (name))
            return

        lower_v = np.percentile(input_image, self.lower_percentage)
        upper_v = np.percentile(input_image, self.upper_percentage)
        img = np.clip(input_image, lower_v, upper_v)
        output = (img - lower_v) / (upper_v - lower_v)
        self.viewer.add_image(output, name='output')


class SmoothingWidget(QWidget):
    # (15.11.2024)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)

        # vbox and parameters for intensity normalization
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Smoothing'))
        button1 = QPushButton('Button 1')
        vbox.addWidget(button1)

        vbox.addWidget(QLabel('Parameter 1'))
        self.param1 = QLineEdit(self)
        vbox.addWidget(self.param1)


class mmv_playground(QWidget):
    # (15.11.2024)
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer

        # Load the names of the existing layers
        self.init_ready = False     # the widgets are not all defined
        self.layer_names = []       # define a list for the names
        self.find_layers(None)      # load layer names

        # Define a vbox for the main widget
        vbox1 = QVBoxLayout()
        self.setLayout(vbox1)

        # Define a scroll area inside the QVBoxvbox
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        vbox1.addWidget(scroll_area)

        # Define a group box inside the scroll area
        group_box = QGroupBox('MMV-Playground')
        vbox2 = QVBoxLayout()
        group_box.setLayout(vbox2)
        scroll_area.setWidget(group_box)        

        # Button intensity normalization
        btn_intensity = QPushButton('Intensity normalization')
        btn_intensity.setCheckable(True)
        btn_intensity.clicked.connect(self.toggle_intensity_group)
        vbox2.addWidget(btn_intensity)

        # Intensity normalization group
        self.intensity_group = IntensityGroup(self)
        vbox2.addWidget(self.intensity_group)

        # Button smoothing
        btn_smoothing = QPushButton('Smoothing')
        btn_smoothing.setCheckable(True)
        btn_smoothing.clicked.connect(self.toggle_smoothing_widget)
        vbox2.addWidget(btn_smoothing)

        # Smoothing widget
        self.smoothing_widget = SmoothingWidget(self)
        vbox2.addWidget(self.smoothing_widget)

        # Button background correction
        btn_background = QPushButton('Background correction')
        btn_background.setCheckable(True)
        # btn_background.clicked.connect(self.toggle_background_widget)
        vbox2.addWidget(btn_background)

        # Button spot-shape filter
        btn_spot_shape = QPushButton('Spot-shape filter')
        btn_spot_shape.setCheckable(True)
        # btn_spot_shape.clicked.connect(self.toggle_spot_shape_widget)
        vbox2.addWidget(btn_spot_shape)

        # Button filament-shape filter
        btn_filament = QPushButton('Filament-shape filter')
        btn_filament.setCheckable(True)
        # btn_filament.clicked.connect(self.toggle_filament_widget)
        vbox2.addWidget(btn_filament)

        # Button thresholding
        btn_thresholding = QPushButton('Thresholding')
        btn_thresholding.setCheckable(True)
        # btn_thresholding.clicked.connect(self.toggle_thresholding_widget)
        vbox2.addWidget(btn_thresholding)

        # Button topology-preserving thinning
        btn_topology = QPushButton('Topology-preserving thinning')
        btn_topology.setCheckable(True)
        # btn_topology.clicked.connect(self.toggle_smoothing_widget)
        vbox2.addWidget(btn_topology)

        # Create a list of layer names
        self.init_ready = True      # all widgets are defined
        self.viewer.layers.events.inserted.connect(self.find_layers)
        self.viewer.layers.events.inserted.connect(self.connect_rename)
        self.viewer.layers.events.removed.connect(self.find_layers)
        self.viewer.layers.events.moving.connect(self.find_layers)

        for layer in self.viewer.layers:
            layer.events.name.connect(self.find_layers)

    def toggle_intensity_group(self, checked: bool):
        # Switching the visibility of the intensity widget
        # (15.11.2024)
        if self.intensity_group.isVisible():
            self.intensity_group.setVisible(False)
        else:
            self.intensity_group.setVisible(True)

    def toggle_smoothing_widget(self, checked: bool):
        # Switching the visibility of the smoothing widget
        # (15.11.2024)
        if self.smoothing_widget.isVisible():
            self.smoothing_widget.setVisible(False)
        else:
            self.smoothing_widget.setVisible(True)

    def find_layers(self, event: napari.utils.events.event.Event):
        # (19.11.2024)
        lst = []
        for layer in self.viewer.layers:
            name = layer.name
            lst.append(name)
        self.layer_names = lst

        if self.init_ready:
            self.intensity_group.image.clear()
            self.intensity_group.image.addItems(lst)

    def connect_rename(self, event: napari.utils.events.event.Event):
        # (20.11.2024)
        event.value.events.name.connect(self.find_layers)
