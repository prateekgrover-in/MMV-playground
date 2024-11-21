"""
tbd
"""
from typing import TYPE_CHECKING

import napari
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    # QGridLayout,
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


class IntensityWidget(QWidget):
    # (15.11.2024)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.viewer = parent.viewer
        self.parent = parent
        self.lower = 0.0        # lower percentage
        self.upper = 90.0       # upper percentage
        self.index = 0          # layer index

        # Layout and parameters for intensity normalization
        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel('Intensity normalization'))

        layout.addWidget(QLabel('Image'))
        self.image = QComboBox()
        self.image.addItems(parent.layer_names)
        self.image.currentIndexChanged.connect(self.image_changed)
        layout.addWidget(self.image)

        self.lbl_lower = QLabel('Lower percentage')
        layout.addWidget(self.lbl_lower)
        lower = QSlider(Qt.Horizontal)
        lower.setRange(0, 500)
        lower.setSingleStep(1)
        lower.valueChanged.connect(self.lower_changed)
        layout.addWidget(lower)

        self.lbl_upper = QLabel('Upper percentage')
        layout.addWidget(self.lbl_upper)
        upper = QSlider(Qt.Horizontal)
        upper.setRange(9500, 10000)
        upper.setSingleStep(1)
        upper.valueChanged.connect(self.upper_changed)
        layout.addWidget(upper)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.function_run)
        layout.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.index = index

    def lower_changed(self, value: int):
        # (19.11.2024)
        self.lower = value / 100.0
        self.lbl_lower.setText('Lower percentage: %.2f' % (self.lower))

    def upper_changed(self, value: int):
        # (19.11.2024)
        self.upper = value / 100.0
        self.lbl_upper.setText('Upper percentage: %.2f' % (self.upper))

    def function_run(self):
        print('run')
        print('lower: %.2f, upper: %.2f' % (self.lower, self.upper))
        name = self.parent.layer_names[self.index]
        print('name: %s' % (name))

class SmoothingWidget(QWidget):
    # (15.11.2024)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)

        # Layout and parameters for intensity normalization
        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel('Smoothing'))
        button1 = QPushButton('Button 1')
        layout.addWidget(button1)

        layout.addWidget(QLabel('Parameter 1'))
        self.param1 = QLineEdit(self)
        layout.addWidget(self.param1)


class mmv_playground(QWidget):
    # (15.11.2024)
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer
        self.init_ready = False     # the widgets are not all defined
        self.layer_names = []
        self.find_layers(None)      # load layer names

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

        # Button intensity normalization
        btn_intensity = QPushButton('Intensity normalization')
        btn_intensity.setCheckable(True)
        btn_intensity.clicked.connect(self.toggle_intensity_widget)
        layout2.addWidget(btn_intensity)

        # Intensity normalization widget
        self.intensity_widget = IntensityWidget(self)
        layout2.addWidget(self.intensity_widget)

        # Button smoothing
        btn_smoothing = QPushButton('Smoothing')
        btn_smoothing.setCheckable(True)
        btn_smoothing.clicked.connect(self.toggle_smoothing_widget)
        layout2.addWidget(btn_smoothing)

        # Smoothing widget
        self.smoothing_widget = SmoothingWidget(self)
        layout2.addWidget(self.smoothing_widget)

        # Button background correction
        btn_background = QPushButton('Background correction')
        btn_background.setCheckable(True)
        # btn_background.clicked.connect(self.toggle_background_widget)
        layout2.addWidget(btn_background)

        # Button spot-shape filter
        btn_spot_shape = QPushButton('Spot-shape filter')
        btn_spot_shape.setCheckable(True)
        # btn_spot_shape.clicked.connect(self.toggle_spot_shape_widget)
        layout2.addWidget(btn_spot_shape)

        # Button filament-shape filter
        btn_filament = QPushButton('Filament-shape filter')
        btn_filament.setCheckable(True)
        # btn_filament.clicked.connect(self.toggle_filament_widget)
        layout2.addWidget(btn_filament)

        # Button thresholding
        btn_thresholding = QPushButton('Thresholding')
        btn_thresholding.setCheckable(True)
        # btn_thresholding.clicked.connect(self.toggle_thresholding_widget)
        layout2.addWidget(btn_thresholding)

        # Button topology-preserving thinning
        btn_topology = QPushButton('Topology-preserving thinning')
        btn_topology.setCheckable(True)
        # btn_topology.clicked.connect(self.toggle_smoothing_widget)
        layout2.addWidget(btn_topology)

        # Create a list of layer names
        self.init_ready = True      # all widgets are defined
        self.viewer.layers.events.inserted.connect(self.find_layers)
        self.viewer.layers.events.inserted.connect(self.connect_rename)
        self.viewer.layers.events.removed.connect(self.find_layers)
        self.viewer.layers.events.moving.connect(self.find_layers)

        for layer in self.viewer.layers:
            layer.events.name.connect(self.find_layers)

    def toggle_intensity_widget(self, checked: bool):
        # Switching the visibility of the intensity widget
        # (15.11.2024)
        if self.intensity_widget.isVisible():
            self.intensity_widget.setVisible(False)
        else:
            self.intensity_widget.setVisible(True)

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
            self.intensity_widget.image.clear()
            self.intensity_widget.image.addItems(lst)
        print(lst)

    def connect_rename(self, event: napari.utils.events.event.Event):
        # (20.11.2024)
        event.value.events.name.connect(self.find_layers)
