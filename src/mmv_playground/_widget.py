"""
tbd
"""
from typing import TYPE_CHECKING

import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_laplace
import itk
from skimage.morphology import white_tophat, disk
import napari
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    import napari


class IntensityNormalization(QGroupBox):
    # (15.11.2024)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Intensity normalization')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''          # layer[name]
        self.lower_percentage = 0.0
        self.upper_percentage = 95.0

        # layout and parameters for intensity normalization
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        self.lbl_lower = QLabel('lower percentage')
        vbox.addWidget(self.lbl_lower)
        sld_lower = QSlider(Qt.Horizontal)
        sld_lower.setRange(0, 500)
        sld_lower.setSingleStep(1)
        sld_lower.valueChanged.connect(self.lower_changed)
        vbox.addWidget(sld_lower)

        self.lbl_upper = QLabel('Upper percentage')
        vbox.addWidget(self.lbl_upper)
        sld_upper = QSlider(Qt.Horizontal)
        sld_upper.setRange(9500, 10000)
        sld_upper.setSingleStep(1)
        sld_upper.valueChanged.connect(self.upper_changed)
        vbox.addWidget(sld_upper)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.run_intensity_normalization)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.name = self.parent.layer_names[index]

    def lower_changed(self, value: int):
        # (19.11.2024)
        self.lower_percentage = float(value) / 100.0
        self.lbl_lower.setText('lower percentage: %.2f' % \
            (self.lower_percentage))

    def upper_changed(self, value: int):
        # (19.11.2024)
        self.upper_percentage = float(value) / 100.0
        self.lbl_upper.setText('upper percentage: %.2f' % \
            (self.upper_percentage))

    def run_intensity_normalization(self):
        # (22.11.2024)
        if self.name == '':
            self.image_changed(0)

        if any(layer.name == self.name for layer in self.viewer.layers):
            layer = self.viewer.layers[self.name]
            input_image = layer.data
        else:
            print('Error: The image %s don\'t exist!' % (self.name))
            return

        lower_v = np.percentile(input_image, self.lower_percentage)
        upper_v = np.percentile(input_image, self.upper_percentage)
        img = np.clip(input_image, lower_v, upper_v)
        output = (img - lower_v) / (upper_v - lower_v)
        self.viewer.add_image(output, name=self.name)


class Smoothing(QGroupBox):
    # (26.11.2024)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Smoothing')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''              # layer[name]
        self.method = 'Gaussian'    # smoothing method

        # vbox and parameters for smoothing
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        vbox.addWidget(QLabel('Smoothing method'))
        self.cbx_method = QComboBox()
        self.cbx_method.addItems(['Gaussian', 'edge-preserving'])
        self.cbx_method.currentIndexChanged.connect(self.method_changed)
        vbox.addWidget(self.cbx_method)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.run_smoothing)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.name = self.parent.layer_names[index]

    def method_changed(self, index: int):
        # (27.11.2024)
        if index == 0:
            self.method = 'Gaussian'
        elif index == 1:
            self.method = 'edge-preserving'
        else:
            self.method = 'unknown method'

    def run_smoothing(self):
        # (27.11.2024)
        if self.name == '':
            self.image_changed(0)

        if any(layer.name == self.name for layer in self.viewer.layers):
            layer = self.viewer.layers[self.name]
            input_image = layer.data
        else:
            print('Error: The image %s don\'t exist!' % (self.name))
            return

        if self.method == 'Gaussian':
            output = gaussian_filter(input_image, sigma=1.0)
        elif self.method == 'edge-preserving':
            itk_img = itk.GetImageFromArray(input_image.astype(np.float32))

            # set spacing
            itk_img.SetSpacing([1, 1])

            # define the filter
            gradientAnisotropicDiffusionFilter = \
                itk.GradientAnisotropicDiffusionImageFilter.New(itk_img)

            gradientAnisotropicDiffusionFilter.SetNumberOfIterations(10)
            gradientAnisotropicDiffusionFilter.SetTimeStep(0.125)
            gradientAnisotropicDiffusionFilter.SetConductanceParameter(1.2)
            gradientAnisotropicDiffusionFilter.Update()

            # run the filter
            itk_image_smooth = gradientAnisotropicDiffusionFilter.GetOutput()

            # extract the ouptut array
            output = itk.GetArrayFromImage(itk_image_smooth)
        else:
            print('Error: unknown method %s' % self.method)
            return

        self.viewer.add_image(output, name=self.name)


class BackgroundCorrection(QGroupBox):
    # (28.11.2024)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Background correction')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''              # layer[name]
        self.kernel_size = 0

        # vbox and parameters for smoothing
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        self.lbl_kernel_size = QLabel('Kernel size')
        vbox.addWidget(self.lbl_kernel_size)
        sld_kernel_size = QSlider(Qt.Horizontal)
        sld_kernel_size.setRange(0, 100)
        sld_kernel_size.setSingleStep(1)
        sld_kernel_size.valueChanged.connect(self.kernel_size_changed)
        vbox.addWidget(sld_kernel_size)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.run_background_correction)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.name = self.parent.layer_names[index]

    def kernel_size_changed(self, value: int):
        # (28.11.2024)
        self.kernel_size = value
        self.lbl_kernel_size.setText('Kernel size: %d' % (value))

    def run_background_correction(self):
        # (28.11.2024)
        if self.name == '':
            self.image_changed(0)

        if any(layer.name == self.name for layer in self.viewer.layers):
            layer = self.viewer.layers[self.name]
            input_image = layer.data
        else:
            print('Error: The image %s don\'t exist!' % (self.name))
            return

        output = white_tophat(input_image, disk(self.kernel_size))
        self.viewer.add_image(output, name=self.name)


class SpotShapeFilter(QGroupBox):
    # (04.12.2024)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('spot-shape filter')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''              # layer[name]
        self.sigma = 0.5

        # vbox and parameters for smoothing
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        self.lbl_sigma = QLabel('sigma')
        vbox.addWidget(self.lbl_sigma)
        sld_sigma = QSlider(Qt.Horizontal)
        sld_sigma.setRange(1, 20)
        # sld_sigma.setSingleStep(1)
        sld_sigma.valueChanged.connect(self.sigma_changed)
        vbox.addWidget(sld_sigma)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.run_spot_shape_filter)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.name = self.parent.layer_names[index]

    def sigma_changed(self, value: int):
        # (28.11.2024)
        self.sigma = float(value) * 0.5
        self.lbl_sigma.setText('sigma: %.1f' % (self.sigma))

    def run_spot_shape_filter(self):
        # (28.11.2024)
        if self.name == '':
            self.image_changed(0)

        if any(layer.name == self.name for layer in self.viewer.layers):
            layer = self.viewer.layers[self.name]
            input_image = layer.data
        else:
            print('Error: The image %s don\'t exist!' % (self.name))
            return

        output = -1.0 * (self.sigma**2) * gaussian_laplace(input_image, \
            self.sigma)
        self.viewer.add_image(output, name=self.name)


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
        self.btn_intensity = QPushButton('Intensity normalization')
        self.btn_intensity.setCheckable(True)
        self.btn_intensity.clicked.connect(self.toggle_intensity_normalization)
        vbox2.addWidget(self.btn_intensity)

        # Intensity normalization
        self.intensity_normalization = IntensityNormalization(self)
        vbox2.addWidget(self.intensity_normalization)

        # Button smoothing
        self.btn_smoothing = QPushButton('Smoothing')
        self.btn_smoothing.setCheckable(True)
        self.btn_smoothing.clicked.connect(self.toggle_smoothing)
        vbox2.addWidget(self.btn_smoothing)

        # Smoothing
        self.smoothing = Smoothing(self)
        vbox2.addWidget(self.smoothing)

        # Button background correction
        self.btn_background = QPushButton('Background correction')
        self.btn_background.setCheckable(True)
        self.btn_background.clicked.connect(self.toggle_background_correction)
        vbox2.addWidget(self.btn_background)

        # Background correction
        self.background_correction = BackgroundCorrection(self)
        vbox2.addWidget(self.background_correction)

        # Button spot-shape filter
        self.btn_spot_shape = QPushButton('spot-shape filter')
        self.btn_spot_shape.setCheckable(True)
        self.btn_spot_shape.clicked.connect(self.toggle_spot_shape_filter)
        vbox2.addWidget(self.btn_spot_shape)

        # spot-shape filter
        self.spot_shape_filter = SpotShapeFilter(self)
        vbox2.addWidget(self.spot_shape_filter)

        # Button filament-shape filter
        self.btn_filament = QPushButton('Filament-shape filter')
        self.btn_filament.setCheckable(True)
        # self.btn_filament.clicked.connect(self.toggle_filament_group)
        vbox2.addWidget(self.btn_filament)

        # Button thresholding
        self.btn_thresholding = QPushButton('Thresholding')
        self.btn_thresholding.setCheckable(True)
        # self.btn_thresholding.clicked.connect(self.toggle_thresholding_group)
        vbox2.addWidget(self.btn_thresholding)

        # Button topology-preserving thinning
        self.btn_topology = QPushButton('Topology-preserving thinning')
        self.btn_topology.setCheckable(True)
        # self.btn_topology.clicked.connect(self.toggle_topology_group)
        vbox2.addWidget(self.btn_topology)

        # Create a list of layer names
        self.init_ready = True      # all widgets are defined
        self.viewer.layers.events.inserted.connect(self.find_layers)
        self.viewer.layers.events.inserted.connect(self.connect_rename)
        self.viewer.layers.events.removed.connect(self.find_layers)
        self.viewer.layers.events.moving.connect(self.find_layers)

        for layer in self.viewer.layers:
            layer.events.name.connect(self.find_layers)

    def toggle_intensity_normalization(self, checked: bool):
        # Switching the visibility of the intensity normalization
        # (15.11.2024)
        if self.intensity_normalization.isVisible():
            self.intensity_normalization.setVisible(False)
            self.btn_intensity.setText('Intensity normalization')
        else:
            self.intensity_normalization.setVisible(True)
            self.btn_intensity.setText('Hide intensity normalization')

    def toggle_smoothing(self, checked: bool):
        # Switching the visibility of the smoothing
        # (15.11.2024)
        if self.smoothing.isVisible():
            self.smoothing.setVisible(False)
            self.btn_smoothing.setText('Smoothing')
        else:
            self.smoothing.setVisible(True)
            self.btn_smoothing.setText('Hide smoothing')

    def toggle_background_correction(self, checked: bool):
        # Switching the visibility of the background correction
        # (28.11.2024)
        if self.background_correction.isVisible():
            self.background_correction.setVisible(False)
            self.btn_background.setText('Background correction')
        else:
            self.background_correction.setVisible(True)
            self.btn_background.setText('Hide background correction')

    def toggle_spot_shape_filter(self, checked: bool):
        # Switching the visibility of the spot-shape filter
        # (04.12.2024)
        if self.spot_shape_filter.isVisible():
            self.spot_shape_filter.setVisible(False)
            self.btn_spot_shape.setText('spot-shape filter')
        else:
            self.spot_shape_filter.setVisible(True)
            self.btn_spot_shape.setText('Hide spot-shape filter')

    def find_layers(self, event: napari.utils.events.event.Event):
        # (19.11.2024)
        lst = []
        for layer in self.viewer.layers:
            name = layer.name
            lst.append(name)
        self.layer_names = lst

        if self.init_ready:
            self.intensity_normalization.cbx_image.clear()
            self.intensity_normalization.cbx_image.addItems(lst)
            self.smoothing.cbx_image.clear()
            self.smoothing.cbx_image.addItems(lst)
            self.background_correction.cbx_image.clear()
            self.background_correction.cbx_image.addItems(lst)
            self.spot_shape_filter.cbx_image.clear()
            self.spot_shape_filter.cbx_image.addItems(lst)

    def connect_rename(self, event: napari.utils.events.event.Event):
        # (20.11.2024)
        event.value.events.name.connect(self.find_layers)
