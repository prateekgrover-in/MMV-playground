"""
tbd
"""
from typing import TYPE_CHECKING

import itk
import napari
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, \
    gaussian_laplace
from aicssegmentation.core.vessel import vesselness2D
from skimage.filters import threshold_li, threshold_otsu, threshold_sauvola, \
    threshold_triangle
from skimage.morphology import disk, erosion, medial_axis, white_tophat
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

from stardist.models import StarDist2D

from stardist.data import test_image_nuclei_2d
from stardist.plot import render_label
from csbdeep.utils import normalize

from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
import os
import time
import threading
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
import torch.nn.functional as F
from skimage.segmentation import watershed
import torch
import segmentation_models_pytorch as smp
import numpy as np
from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox
from PIL import Image
import os


def remove_small_instances(segm: np.ndarray,
                           thres_small: int = 128,
                           mode: str = 'background'):
    """Remove small spurious instances.
    """
    assert mode in ['none',
                    'background',
                    'background_2d',
                    'neighbor',
                    'neighbor_2d']

    if mode == 'none':
        return segm

    if mode == 'background':
        return remove_small_objects(segm, thres_small)
    elif mode == 'background_2d':
        temp = [remove_small_objects(segm[i], thres_small)
                for i in range(segm.shape[0])]
        return np.stack(temp, axis=0)

    if mode == 'neighbor':
        return merge_small_objects(segm, thres_small, do_3d=True)
    elif mode == 'neighbor_2d':
        temp = [merge_small_objects(segm[i], thres_small)
                for i in range(segm.shape[0])]
        return np.stack(temp, axis=0)

def merge_small_objects(segm, thres_small, do_3d=False):
    struct = np.ones((1,3,3)) if do_3d else np.ones((3,3))
    indices, counts = np.unique(segm, return_counts=True)

    for i in range(len(indices)):
        idx = indices[i]
        if counts[i] < thres_small:
            temp = (segm == idx).astype(np.uint8)
            coord = bbox_ND(temp, relax=2)
            cropped = crop_ND(temp, coord)

            diff = dilation(cropped, struct) - cropped
            diff_segm = crop_ND(segm, coord)
            diff_segm[np.where(diff==0)]=0

            u, ct = np.unique(diff_segm, return_counts=True)
            if len(u) > 1 and u[0] == 0:
                u, ct = u[1:], ct[1:]

            segm[np.where(segm==idx)] = u[np.argmax(ct)]

    return segm

from scipy import ndimage
from skimage.measure import label
from skimage.transform import resize
from skimage.morphology import dilation
from skimage.segmentation import watershed
from skimage.morphology import remove_small_objects

def bcd_watershed(semantic, boundary, distance, thres1=0.9, thres2=0.8, thres3=0.85, thres4=0.5, thres5=0.0, thres_small=128,
                  scale_factors=(1.0, 1.0, 1.0), remove_small_mode='background', seed_thres=32, return_seed=False):
    r"""Convert binary foreground probability maps, instance contours and signed distance
    transform to instance masks via watershed segmentation algorithm.
    Note:
        This function uses the `skimage.segmentation.watershed <https://github.com/scikit-image/scikit-image/blob/master/skimage/segmentation/_watershed.py#L89>`_
        function that converts the input image into ``np.float64`` data type for processing. Therefore please make sure enough memory is allocated when handling large arrays.
    Args:
        volume (numpy.ndarray): foreground and contour probability of shape :math:`(C, Z, Y, X)`.
        thres1 (float): threshold of seeds. Default: 0.9
        thres2 (float): threshold of instance contours. Default: 0.8
        thres3 (float): threshold of foreground. Default: 0.85
        thres4 (float): threshold of signed distance for locating seeds. Default: 0.5
        thres5 (float): threshold of signed distance for foreground. Default: 0.0
        thres_small (int): size threshold of small objects to remove. Default: 128
        scale_factors (tuple): scale factors for resizing in :math:`(Z, Y, X)` order. Default: (1.0, 1.0, 1.0)
        remove_small_mode (str): ``'background'``, ``'neighbor'`` or ``'none'``. Default: ``'background'``
    """
    distance = (distance / 255.0) * 2.0 - 1.0
    seed_map = (semantic > int(255*thres1)) * (boundary < int(255*thres2)) * (distance > thres4)
    foreground = (semantic > int(255*thres3)) * (distance > thres5)
    seed = label(seed_map)
    #print(np.unique(seed), "seeds")
    seed = remove_small_objects(seed, seed_thres)
    segm = watershed(-semantic.astype(np.float64), seed, mask=foreground)
    segm = remove_small_instances(segm, thres_small, remove_small_mode)

    if not all(x==1.0 for x in scale_factors):
        target_size = (int(semantic.shape[0]*scale_factors[0]),
                       int(semantic.shape[1]*scale_factors[1]),
                       int(semantic.shape[2]*scale_factors[2]))
        segm = resize(segm, target_size, order=0, anti_aliasing=False, preserve_range=True)

    if not return_seed:
        return cast2dtype(segm)

    return cast2dtype(segm), seed

#@title
# !pip install csbdeep
import numpy as np

from numba import jit
from tqdm import tqdm
from scipy.optimize import linear_sum_assignment
from collections import namedtuple
from csbdeep.utils import _raise

matching_criteria = dict()

def label_are_sequential(y):
    """ returns true if y has only sequential labels from 1... """
    labels = np.unique(y)
    return (set(labels)-{0}) == set(range(1,1+labels.max()))


def is_array_of_integers(y):
    return isinstance(y,np.ndarray) and np.issubdtype(y.dtype, np.integer)


def _check_label_array(y, name=None, check_sequential=False):
    err = ValueError("{label} must be an array of {integers}.".format(
        label = 'labels' if name is None else name,
        integers = ('sequential ' if check_sequential else '') + 'non-negative integers',
    ))
    is_array_of_integers(y) or _raise(err)
    if len(y) == 0:
        return True
    if check_sequential:
        label_are_sequential(y) or _raise(err)
    else:
        y.min() >= 0 or _raise(err)
    return True

class GoogleDriveUploader(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Finetuning Model')
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: lightgray; border-radius: 10px;}')
        
        self.parent = parent
        self.drive_folder_id = "1zJFdZEdmsTVFNPQUMcV3jVcwU4WBsxc-"  # Change this to your Drive folder ID
        
        # Layout
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        # Input field for dataset path
        vbox.addWidget(QLabel('Dataset Folder Path:'))
        self.dataset_path_input = QLineEdit()
        vbox.addWidget(self.dataset_path_input)

        # Upload button
        self.btn_upload = QPushButton('Finetune Model')
        self.btn_upload.clicked.connect(self.start_upload)
        vbox.addWidget(self.btn_upload)

    def authenticate_drive(self):
        """Authenticate Google Drive API."""
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(
            "C:/Users/grover01/Desktop/celldynamicsplatform-debdeefdc0a9.json",
            scopes=SCOPES
        )
        return build('drive', 'v3', credentials=creds)

    def get_folder_id(self, parent_folder_id, folder_name):
        """Check if a folder exists in Google Drive, and return its ID. If not, create it."""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents"
        response = self.drive_service.files().list(q=query, fields="files(id)").execute()

        if response.get('files'):
            return response['files'][0]['id']

        # Create the folder if it does not exist
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
        return folder['id']

    def upload_file(self, file_path, parent_folder_id):
        """Upload a single file to Google Drive."""
        file_metadata = {'name': os.path.basename(file_path), 'parents': [parent_folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"✅ Uploaded: {file_path} (ID: {file.get('id')})")

    def upload_folder(self, local_folder, drive_parent_folder_id):
        """Recursively upload a local folder (including subfolders) to Google Drive."""
        for root, dirs, files in os.walk(local_folder):
            # Create subfolder inside Google Drive (if needed)
            relative_path = os.path.relpath(root, local_folder)
            if relative_path == ".":
                current_drive_folder_id = drive_parent_folder_id
            else:
                current_drive_folder_id = self.get_folder_id(drive_parent_folder_id, relative_path)

            # Upload files in the current folder
            for file in files:
                file_path = os.path.join(root, file)
                self.upload_file(file_path, current_drive_folder_id)

        print(f"\n📂 All files from '{local_folder}' uploaded to Google Drive (ID: {drive_parent_folder_id})")

        # Create and upload "done.txt" checkpoint file
        done_file_path = os.path.join(local_folder, "done.txt")
        with open(done_file_path, "w") as f:
            f.write("Upload completed successfully.\n")

        self.upload_file(done_file_path, drive_parent_folder_id)
        print("✅ Uploaded checkpoint: done.txt")

    def start_upload(self):
        """Start the dataset upload process in a separate thread."""
        dataset_path = self.dataset_path_input.text().strip()
        if not dataset_path or not os.path.exists(dataset_path):
            QMessageBox.warning(self, "Error", "Invalid dataset path! Please enter a valid folder.")
            return
        
        self.btn_upload.setEnabled(False)
        threading.Thread(target=self.upload_process, args=(dataset_path,), daemon=True).start()

    def upload_process(self, dataset_path):
        """Handles the dataset upload process."""
        try:
            self.drive_service = self.authenticate_drive()
            self.upload_folder(dataset_path, self.drive_folder_id)
            QMessageBox.information(self, "Success", "Dataset uploaded successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Upload Failed", f"Error: {str(e)}")
        finally:
            self.btn_upload.setEnabled(True)

class UNetSegmentation(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('U-Net Segmentation')
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: lightblue; border-radius: 10px;}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''  # Selected image layer
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = 'C:/Users/grover01/Desktop/cell_segmentation_unet.pth'  # Change this path as needed
        self.target_size = (256, 256)  # U-Net input size

        # Layout
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        # Image selection dropdown
        vbox.addWidget(QLabel('Select Image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        # Run segmentation button
        btn_run = QPushButton('Run U-Net Segmentation')
        btn_run.clicked.connect(self.run_unet_segmentation)
        vbox.addWidget(btn_run)

        # Load U-Net model
        self.load_model()

    def load_model(self):
        """Load the pre-trained U-Net model."""
        try:
            self.model = smp.Unet(
                encoder_name="resnet34",
                encoder_weights="imagenet",
                in_channels=1,
                classes=1,
            ).to(self.device)
            
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            self.model.eval()
            print(f"✅ U-Net model loaded successfully on {self.device}")
        except Exception as e:
            QMessageBox.critical(self, "Model Error", f"Failed to load U-Net model!\n{str(e)}")

    def image_changed(self, index: int):
        """Update the selected image layer."""
        self.name = self.parent.layer_names[index]

    def preprocess_image(self, image):
        """Resize and preprocess the image for U-Net segmentation."""
        original_size = image.shape  # Save original size for upsampling
        img = Image.fromarray(image).convert("L")  # Convert to grayscale
        img = img.resize(self.target_size, Image.BILINEAR)  # Resize to (256,256)
        img = np.array(img).astype(np.float32) / 255.0  # Normalize

        # Convert to tensor and send to device
        img_tensor = torch.tensor(img).unsqueeze(0).unsqueeze(0).to(self.device)

        return img_tensor, original_size

    def run_unet_segmentation(self):
        """Run U-Net segmentation on the selected image."""
        if self.name == '':
            self.image_changed(0)  # Select first layer if none chosen

        # Get image data from Napari
        if any(layer.name == self.name for layer in self.viewer.layers):
            layer = self.viewer.layers[self.name]
            input_image = layer.data
        else:
            QMessageBox.warning(self, "Error", f"Image {self.name} does not exist!")
            return

        # Preprocess image (resize to 256x256)
        input_tensor, original_size = self.preprocess_image(input_image)

        # Run prediction
        with torch.no_grad():
            output = self.model(input_tensor)

        # Resize the output back to the original size
        predicted_mask = F.interpolate(output, size=original_size, mode="bilinear", align_corners=False)
        predicted_mask = predicted_mask.squeeze().cpu().numpy()
        predicted_mask = (predicted_mask - np.min(predicted_mask))
        predicted_mask = predicted_mask/np.max(predicted_mask)
        
        semantic = predicted_mask
        seed_map = (predicted_mask > 0.9)
        foreground = (predicted_mask > 0.75)
        seed = label(seed_map)
        
        # seed = remove_small_objects(seed, 32)
        segm = watershed(-semantic.astype(np.float64), seed, mask=foreground)
        # segm = remove_small_instances(segm, 128, 'background')
        result = segm

        # Add segmentation result to Napari
        self.viewer.add_image(result, name=f"{self.name}_mask", colormap='gray')
        print("✅ Segmentation completed!")


class StardistSegmentation(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Stardist Segmentation')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''          # layer.name
        self.method = 'Stardist'

        # layout and parameters for intensity normalization
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        vbox.addWidget(QLabel('Segmentation method'))
        self.cbx_method = QComboBox()
        self.cbx_method.addItems(['Versatile (fluorescent nuclei)', 'DSB 2018 (from StarDist 2D Paper)'])
        self.cbx_method.currentIndexChanged.connect(self.method_changed)
        vbox.addWidget(self.cbx_method)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.run_stardist_segmentation)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        self.name = self.parent.layer_names[index]

    def method_changed(self, index: int):
        if index == 0:
            self.method = 'Versatile (fluorescent nuclei)'
        elif index == 1:
            self.method = 'DSB 2018 (from StarDist 2D Paper)'
        else:
            self.method = 'unknown method'

    def run_stardist_segmentation(self):
        if self.name == '':
            self.image_changed(0)

        if any(layer.name == self.name for layer in self.viewer.layers):
            layer = self.viewer.layers[self.name]
            input_image = layer.data
        else:
            print('Error: The image %s don\'t exist!' % (self.name))
            return

        if (self.method == 'Versatile (fluorescent nuclei)'):
            model = StarDist2D.from_pretrained('2D_versatile_fluo')
        elif (self.method == 'DSB 2018 (from StarDist 2D Paper)'):
            model = StarDist2D.from_pretrained('2D_paper_dsb2018')
        else:
            model = StarDist2D.from_pretrained('2D_paper_dsb2018')   
        labels, _ = model.predict_instances(normalize(input_image))
        self.viewer.add_image(render_label(labels, img=input_image), name=self.name)

class IntensityNormalization(QGroupBox):
    # (15.11.2024) Function 1
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Intensity normalization')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''          # layer.name
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

        self.lbl_lower_percentage = QLabel('lower percentage: 0.00')
        vbox.addWidget(self.lbl_lower_percentage)
        sld_lower_percentage = QSlider(Qt.Horizontal)
        sld_lower_percentage.setRange(0, 500)
        sld_lower_percentage.valueChanged.connect(self.lower_changed)
        vbox.addWidget(sld_lower_percentage)

        self.lbl_upper_percentage = QLabel('Upper percentage: 95.00')
        vbox.addWidget(self.lbl_upper_percentage)
        sld_upper_percentage = QSlider(Qt.Horizontal)
        sld_upper_percentage.setRange(9500, 10000)
        sld_upper_percentage.valueChanged.connect(self.upper_changed)
        vbox.addWidget(sld_upper_percentage)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.run_intensity_normalization)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.name = self.parent.layer_names[index]

    def lower_changed(self, value: int):
        # (19.11.2024)
        self.lower_percentage = float(value) / 100.0
        self.lbl_lower_percentage.setText('lower percentage: %.2f' % \
            (self.lower_percentage))

    def upper_changed(self, value: int):
        # (19.11.2024)
        self.upper_percentage = float(value) / 100.0
        self.lbl_upper_percentage.setText('upper percentage: %.2f' % \
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
    # (26.11.2024) Function 2
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Smoothing')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''              # layer.name
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
    # (28.11.2024) Function 3
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Background correction')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''              # layer.name
        self.kernel_size = 1

        # vbox and parameters for background correction
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        self.lbl_kernel_size = QLabel('Kernel size: 1')
        vbox.addWidget(self.lbl_kernel_size)
        sld_kernel_size = QSlider(Qt.Horizontal)
        sld_kernel_size.setRange(1, 100)
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
    # (04.12.2024) Function 4
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('spot-shape filter')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''              # layer.name
        self.sigma = 0.5

        # vbox and parameters for spot-shape filter
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        self.lbl_sigma = QLabel('sigma: 0.5')
        vbox.addWidget(self.lbl_sigma)
        sld_sigma = QSlider(Qt.Horizontal)
        sld_sigma.setRange(1, 20)
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


class FilamentShapeFilter(QGroupBox):
    # (05.12.2024) Function 5
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('filament-shape filter')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''              # layer.name
        self.sigma = 0.25

        # vbox and parameters for filament-shape filter
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        self.lbl_sigma = QLabel('sigma: 0.25')
        vbox.addWidget(self.lbl_sigma)
        sld_sigma = QSlider(Qt.Horizontal)
        sld_sigma.setRange(1, 20)
        sld_sigma.valueChanged.connect(self.sigma_changed)
        vbox.addWidget(sld_sigma)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.run_filament_shape_filter)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.name = self.parent.layer_names[index]

    def sigma_changed(self, value: int):
        # (28.11.2024)
        self.sigma = float(value) * 0.25
        self.lbl_sigma.setText('sigma: %.2f' % (self.sigma))

    def run_filament_shape_filter(self):
        # (06.12.2024)
        if self.name == '':
            self.image_changed(0)

        if any(layer.name == self.name for layer in self.viewer.layers):
            layer = self.viewer.layers[self.name]
            input_image = layer.data
        else:
            print('Error: The image %s don\'t exist!' % (self.name))
            return

        output = vesselness2D(input_image, sigmas=[self.sigma])
        self.viewer.add_image(output, name=self.name)


class Thresholding(QGroupBox):
    # (06.12.2024) Function 6
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Thresholding')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''              # layer.name
        self.method = 'Otsu'

        # vbox and parameters for thresholding
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        vbox.addWidget(QLabel('Threshold method'))
        self.cbx_method = QComboBox()
        self.cbx_method.addItems(['Otsu', 'Li', 'Triangle', 'Sauvola'])
        self.cbx_method.currentIndexChanged.connect(self.method_changed)
        vbox.addWidget(self.cbx_method)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.run_thresholding)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.name = self.parent.layer_names[index]

    def method_changed(self, index: int):
        # (09.12.2024)
        if index == 0:
            self.method = 'Otsu'
        elif index == 1:
            self.method = 'Li'
        elif index == 2:
            self.method = 'Triangle'
        elif index == 3:
            self.method = 'Sauvola'
        else:
            self.method = 'unknown method'

    def run_thresholding(self):
        # (09.12.2024)
        if self.name == '':
            self.image_changed(0)

        if any(layer.name == self.name for layer in self.viewer.layers):
            layer = self.viewer.layers[self.name]
            input_image = layer.data
        else:
            print('Error: The image %s don\'t exist!' % (self.name))
            return

        if self.method == 'Otsu':
            t_otsu = threshold_otsu(input_image)
            output = input_image > t_otsu
        if self.method == 'Li':
            t_li = threshold_li(input_image)
            output = input_image > t_li
        if self.method == 'Triangle':
            t_tri = threshold_triangle(input_image)
            output = input_image > t_tri
        if self.method == 'Sauvola':
            t_local = threshold_sauvola(input_image)
            output = input_image > t_local

        self.viewer.add_image(output, name=self.name)


class TopologyPreservingThinning(QGroupBox):
    # (09.12.2024) Function 7
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('Topology-preserving thinning')
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QGroupBox {background-color: blue; ' \
            'border-radius: 10px}')
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ''              # layer.name
        self.min_thickness = 0.5
        self.thin = 1

        # vbox and parameters for thresholding
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel('Image'))
        self.cbx_image = QComboBox()
        self.cbx_image.addItems(parent.layer_names)
        self.cbx_image.currentIndexChanged.connect(self.image_changed)
        vbox.addWidget(self.cbx_image)

        self.lbl_min_thickness = QLabel('minimum thickness: 0.5')
        vbox.addWidget(self.lbl_min_thickness)
        sld_min_thickness = QSlider(Qt.Horizontal)
        sld_min_thickness.setRange(1, 10)
        sld_min_thickness.valueChanged.connect(self.min_thickness_changed)
        vbox.addWidget(sld_min_thickness)

        self.lbl_thin = QLabel('thin: 1')
        vbox.addWidget(self.lbl_thin)
        sld_thin = QSlider(Qt.Horizontal)
        sld_thin.setRange(1, 5)
        sld_thin.valueChanged.connect(self.thin_changed)
        vbox.addWidget(sld_thin)

        btn_run = QPushButton('run')
        btn_run.clicked.connect(self.run_topology_preserving_thinning)
        vbox.addWidget(btn_run)

    def image_changed(self, index: int):
        # (19.11.2024)
        self.name = self.parent.layer_names[index]

    def min_thickness_changed(self, value: int):
        # (10.12.2024)
        self.min_thickness = float(value) * 0.5
        self.lbl_min_thickness.setText('minimum thickness: %.1f' % \
            (self.min_thickness))

    def thin_changed(self, value: int):
        # (10.12.2024)
        self.thin = value
        self.lbl_thin.setText('thin: %d' % (self.thin))

    def run_topology_preserving_thinning(self):
        # (10.12.2024)
        if self.name == '':
            self.image_changed(0)

        if any(layer.name == self.name for layer in self.viewer.layers):
            layer = self.viewer.layers[self.name]
            input_image = layer.data
        else:
            print('Error: The image %s don\'t exist!' % (self.name))
            return

        output = input_image > 0
        safe_zone = np.zeros_like(output)
        ctl = medial_axis(output > 0)
        dist = distance_transform_edt(ctl == 0)
        safe_zone = dist > self.min_thickness + 1e-5

        rm_candidate = np.logical_xor(output, erosion(output, disk(self.thin)))
        output[np.logical_and(safe_zone, rm_candidate)] = 0

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

        self.btn_unet_segmentation = QPushButton('UNet Segmentation')
        self.btn_unet_segmentation.setCheckable(True)
        self.btn_unet_segmentation.clicked.connect(self.toggle_unet_segmentation)
        vbox2.addWidget(self.btn_unet_segmentation)

        # Stardist normalization
        self.unet_segmentation = UNetSegmentation(self)
        vbox2.addWidget(self.unet_segmentation)
        
        self.btn_google_drive_uploader = QPushButton('Finetuning Model')
        self.btn_google_drive_uploader.setCheckable(True)
        self.btn_google_drive_uploader.clicked.connect(self.toggle_google_drive_uploader)
        vbox2.addWidget(self.btn_google_drive_uploader)

        self.google_drive_uploader = GoogleDriveUploader(self)
        vbox2.addWidget(self.google_drive_uploader)
        
        # Button stardist segmentation
        self.btn_stardist_segmentation = QPushButton('Stardist Segmentation')
        self.btn_stardist_segmentation.setCheckable(True)
        self.btn_stardist_segmentation.clicked.connect(self.toggle_stardist_segmentation)
        vbox2.addWidget(self.btn_stardist_segmentation)

        # Stardist normalization
        self.stardist_segmentation = StardistSegmentation(self)
        vbox2.addWidget(self.stardist_segmentation)

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
        self.btn_filament_shape = QPushButton('Filament-shape filter')
        self.btn_filament_shape.setCheckable(True)
        self.btn_filament_shape.clicked.connect(self.toggle_filament_shape_filter)
        vbox2.addWidget(self.btn_filament_shape)

        # filament-shape filter
        self.filament_shape_filter = FilamentShapeFilter(self)
        vbox2.addWidget(self.filament_shape_filter)

        # Button thresholding
        self.btn_thresholding = QPushButton('Thresholding')
        self.btn_thresholding.setCheckable(True)
        self.btn_thresholding.clicked.connect(self.toggle_thresholding)
        vbox2.addWidget(self.btn_thresholding)

        # Thresholding
        self.thresholding = Thresholding(self)
        vbox2.addWidget(self.thresholding)

        # Button topology-preserving thinning
        self.btn_topology_preserving = QPushButton('Topology-preserving thinning')
        self.btn_topology_preserving.setCheckable(True)
        self.btn_topology_preserving.clicked.connect( \
            self.toggle_topology_preserving_thinning)
        vbox2.addWidget(self.btn_topology_preserving)

        # Topology-preserving thinning
        self.topology_preserving_thinning = TopologyPreservingThinning(self)
        vbox2.addWidget(self.topology_preserving_thinning)

        # Create a list of layer names
        self.init_ready = True      # all widgets are defined
        self.viewer.layers.events.inserted.connect(self.find_layers)
        self.viewer.layers.events.inserted.connect(self.connect_rename)
        self.viewer.layers.events.removed.connect(self.find_layers)
        self.viewer.layers.events.moving.connect(self.find_layers)

        for layer in self.viewer.layers:
            layer.events.name.connect(self.find_layers)

    def toggle_google_drive_uploader(self, checked: bool):
        if self.google_drive_uploader.isVisible():
            self.google_drive_uploader.setVisible(False)
            self.btn_google_drive_uploader.setText('Finetuning Model')
        else:
            self.google_drive_uploader.setVisible(True)
            self.btn_google_drive_uploader.setText('Hide Finetuning Model')

    def toggle_unet_segmentation(self, checked: bool):
        if self.unet_segmentation.isVisible():
            self.unet_segmentation.setVisible(False)
            self.btn_unet_segmentation.setText('UNet Segmentation')
        else:
            self.unet_segmentation.setVisible(True)
            self.btn_unet_segmentation.setText('Hide UNet Segmentation')
            
    def toggle_stardist_segmentation(self, checked: bool):
        # Switching the visibility of the intensity normalization
        # (15.11.2024)
        if self.stardist_segmentation.isVisible():
            self.stardist_segmentation.setVisible(False)
            self.btn_stardist_segmentation.setText('Stardist Segmentation')
        else:
            self.stardist_segmentation.setVisible(True)
            self.btn_stardist_segmentation.setText('Hide stardist segmentation')
            
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

    def toggle_filament_shape_filter(self, checked: bool):
        # Switching the visibility of the filament-shape filter
        # (05.12.2024)
        if self.filament_shape_filter.isVisible():
            self.filament_shape_filter.setVisible(False)
            self.btn_filament_shape.setText('filament-shape filter')
        else:
            self.filament_shape_filter.setVisible(True)
            self.btn_filament_shape.setText('Hide filament-shape filter')

    def toggle_thresholding(self, checked: bool):
        # Switching the visibility of the thresholding
        # (05.12.2024)
        if self.thresholding.isVisible():
            self.thresholding.setVisible(False)
            self.btn_thresholding.setText('Thresholding')
        else:
            self.thresholding.setVisible(True)
            self.btn_thresholding.setText('Hide thresholding')

    def toggle_topology_preserving_thinning(self, checked: bool):
        # Switching the visibility of the topology-preserving thinning
        # (09.12.2024)
        if self.topology_preserving_thinning.isVisible():
            self.topology_preserving_thinning.setVisible(False)
            self.btn_topology_preserving.setText('Topology-preserving thinning')
        else:
            self.topology_preserving_thinning.setVisible(True)
            self.btn_topology_preserving.setText('Hide topology-preserving thinning')

    def find_layers(self, event: napari.utils.events.event.Event):
        # (19.11.2024)
        lst = []
        for layer in self.viewer.layers:
            name = layer.name
            lst.append(name)
        self.layer_names = lst

        if self.init_ready:
            self.unet_segmentation.cbx_image.clear()
            self.unet_segmentation.cbx_image.addItems(lst)
            self.stardist_segmentation.cbx_image.clear()
            self.stardist_segmentation.cbx_image.addItems(lst)
            self.intensity_normalization.cbx_image.clear()
            self.intensity_normalization.cbx_image.addItems(lst)
            self.smoothing.cbx_image.clear()
            self.smoothing.cbx_image.addItems(lst)
            self.background_correction.cbx_image.clear()
            self.background_correction.cbx_image.addItems(lst)
            self.spot_shape_filter.cbx_image.clear()
            self.spot_shape_filter.cbx_image.addItems(lst)
            self.filament_shape_filter.cbx_image.clear()
            self.filament_shape_filter.cbx_image.addItems(lst)
            self.thresholding.cbx_image.clear()
            self.thresholding.cbx_image.addItems(lst)
            self.topology_preserving_thinning.cbx_image.clear()
            self.topology_preserving_thinning.cbx_image.addItems(lst)

    def connect_rename(self, event: napari.utils.events.event.Event):
        # (20.11.2024)
        event.value.events.name.connect(self.find_layers)
