# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""Dataset definition class for PyBP GUI system.

"""

import re
import os
import nibabel as nib
import numpy as np

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from nkroi.algorithm import array2qimage as aq
from labelconfig import LabelConfig

threeD_fourD_flag = False
data = ''

class DoStack(QObject):
    """
    For Undo and Redo
    
    """
    stack_changed = pyqtSignal()

    def __init__(self):
        super(QObject, self).__init__()
        self._stack = []

    def push(self, v):
        self._stack.append(v)
        self.stack_changed.emit()

    def pop(self):
        t = self._stack.pop()
        self.stack_changed.emit()
        return t
    
    def stack_not_empty(self):
        if self._stack:
            return True
        else:
            return False

class VolumeDataset(object):
    """
    Base dataset in PyBP GUI system.
    
    """
    def __init__(self, source, label_config_center, name=None, header=None, 
                 view_min=None, view_max=None, alpha=255, colormap='gray'):
        """
        Create a dataset from an NiftiImage which has following 
        atributes:
        
        Parameters
        ----------
        source : Nifti file path or 3D numpy array
            Nifti dataset, specified either as a filename (single file 3D 
            image) or a 3D numpy array. When source is a numpy array,
            parameter header is required.
        label_config : label configuration
        name : name of the volume
            volume name.
        header : nifti1 header structure
            Nifti header structure.
        view_min : scalar or None
            The lower limitation of data value which can be seen.
        view_max : scalar
            The upper limitation of data value which can be seen.
        alpha: int number (0 - 255)
            alpha channel value, 0 indicates transparency. Default is 255.
        colormap : string
            The string can represents the colormap used for corresponding
            values, it can be 'gray', 'red2yellow', 'blue2green', 'ranbow'...

        Returns
        -------
        VolumeDataset

        """
        if isinstance(source, np.ndarray):
            self._data = np.rot90(source)
            if name == None:
                self._name = 'new_image'
            else:
                self._name = str(name)
            if not isinstance(header, nib.nifti1.Nifti1Header):
                raise ValueError("Parameter header must be specified!")
            elif header.get_data_shape() == source.shape:
                self._header = header
            elif len(header.get_data_shape())-1 == len(source.shape):
                self._header = header #added by zgf....
            else:
                raise ValueError("Data dimension does not match.")
        else:
            img = nib.load(source)
            # FIXME: only fit in Unix/Linux systems
            basename = os.path.basename(source.strip('/'))
            self._name = re.sub(r'(.*)\.nii(\.gz)?', r'\1', basename)

            #----------------------------------zgf-----------------------------------------------------------------
            global data,threeD_fourD_flag
            data = img.get_data()
            length = len(data.shape)
            if length == 3:
               self._data = np.rot90(data)
               threeD_fourD_flag = False
            elif length == 4:
                self._data = np.rot90(data[:,:,:,0])
                threeD_fourD_flag = True
            else:
                print 'error!'
            #----------------------------------zgf-----------------------------------------------------------------
            # self._data = np.rot90(data)
            self._header = img.get_header()

        if view_min == None:
            self._view_min = self._data.min()
        else:
            self._view_min = view_min

        if view_max == None:
            self._view_max = self._data.max()
        else:
            self._view_max = view_max

        self._alpha = alpha
        self._colormap = colormap
        self._rgba_list = range(self.get_data_shape()[2])
 
        # bool status for the item
        self._visible = True

        # define a dictionary 
        self.label_config_center = label_config_center
        self.label_config_center.single_roi_view_update.connect(self.update_single_roi)
        
        # undo redo stacks
        self.undo_stack = DoStack()
        self.redo_stack = DoStack()

        self.update_rgba()

    def get_data_shape(self):
        """
        Get shape of data.
        
        """
        return self._header.get_data_shape()

    def _rendering_factory(self):
        """
        Return a rendering factory according to the display setting.

        """
        def shadow(array):
            if not isinstance(self._colormap, LabelConfig):
                colormap = str(self._colormap)
            else:
                colormap = self._colormap.get_colormap()
            try:
                current_roi = self.label_config_center.get_drawing_value()
            except ValueError:
                current_roi = None
            return aq.array2qrgba(array, self._alpha, colormap,
                                  normalize=(self._view_min, self._view_max), roi=current_roi)
        return shadow

    def update_single_roi(self):
        if self._colormap == 'single ROI':
            self.update_rgba()
            self.label_config_center.single_roi_view_update_for_model.emit() 

    def update_rgba(self, index=None):
        """
        Create a range of qrgba array for display.
        
        """
        # return a rendering factory
        f = self._rendering_factory()

        if index == None:
            layer_list = [self._data[..., i] for i in 
                                range(self.get_data_shape()[2])]
            self._rgba_list = map(f, layer_list)
        else:
            self._rgba_list[index] = f(self._data[..., index])

    def set_alpha(self, alpha):
        """Set alpha value."""
        if isinstance(alpha, int):
            if alpha <= 255 and alpha >= 0:
                if self._alpha != alpha:
                    self._alpha = alpha
                    self.update_rgba()
        else:
            raise ValueError("Value must be an integer between 0 and 255.")

    def get_alpha(self):
        """Get alpha value."""
        return self._alpha

    def set_view_min(self, view_min):
        """Set lower limition of display range."""
        try:
            view_min = float(view_min)
            self._view_min = view_min
            self.update_rgba()
        except ValueError:
            print "view_min must be a number."

    def get_view_min(self):
        """Get lower limition of display range."""
        return self._view_min

    def set_view_max(self, view_max):
        """Set upper limition of display range."""
        try:
            view_max = float(view_max)
            self._view_max = view_max
            self.update_rgba()
        except ValueError:
            print"view_max must be a number."

    def get_view_max(self):
        """Get upper limition of display range."""
        return self._view_max
    
    def set_name(self, name):
        """Set item's name."""
        self._name = str(name)

    def get_name(self):
        """Get item's name."""
        return self._name

    def set_colormap(self, map_name):
        """Set item's colormap.

        """
        self._colormap = map_name

    def get_colormap(self):
        """Get item's colormap.

        """
        return self._colormap

    def set_visible(self, status):
        """Set visibility of the volume."""
        if isinstance(status, bool):
            if status:
                self._visible = True
            else:
                self._visible = False
        else:
            raise ValueError("Input must a bool.")

    def is_visible(self):
        """Query the status of visibility."""
        return self._visible

    def get_rgba(self, index):
        """Get rgba array based on the index of the layer."""
        return self._rgba_list[index]

    def set_voxel(self, x, y, z, value, ignore=True):
        """
        Set value of the voxel whose coordinate is (x, y, z).
        
        """
        try:
            orig_data = self._data[x, y, z]
            if np.any(orig_data != 0) and not ignore:
                force = QMessageBox.question(None, "Replace?", "Would you like to replace the original values?", QMessageBox.Yes, QMessageBox.No)
                if force == QMessageBox.No:
                    return
            self.undo_stack.push((x, y, z, self._data[x, y, z]))
            self._data[x, y, z] = value
            try:
                for z_ in range(min(z), max(z)+1):
                    self.update_rgba(z_)
            except TypeError:
                self.update_rgba(z)
        except:
            raise
            print "Input coordinates are invalid."

    def get_voxel_value(self, x, y, z):
        """
        Get value of the voxel whose coordinate is (x, y, z)

        """
        return self._data[x, y, z]

    def save2nifti(self, file_path):
        """Save to a nifti file."""
        data = np.rot90(self._data, 3)
        self._header['cal_max'] = data.max()
        self._header['cal_min'] = 0
        image = nib.nifti1.Nifti1Image(data, None, self._header)
        nib.nifti1.save(image, file_path)

    def get_label_config(self):
        return self.label_config_center

    def undo_stack_not_empty(self):
        return self.undo_stack.stack_not_empty()

    def redo_stack_not_empty(self):
        return self.redo_stack.stack_not_empty()

    def undo(self):
        if self.undo_stack:
            voxel_set = self.undo_stack.pop()
            self.set_voxel(*voxel_set, ignore=True)
            self.redo_stack.push(self.undo_stack.pop())
            return voxel_set[2]
        return None

    def redo(self):
        if self.redo_stack:
            voxel_set = self.redo_stack.pop()
            self.set_voxel(*voxel_set, ignore=True)
            return voxel_set[2]
        return None

    def connect_undo(self, slot):
        self.undo_stack.stack_changed.connect(slot)

    def connect_redo(self, slot):
        self.redo_stack.stack_changed.connect(slot)

    def get_header(self):
        return self._header

    def get_value(self, xyz):
        return self._data[xyz[0], xyz[1], xyz[2]]

    def get_lthr(self):
        return self._view_min

    def get_lthr_data(self):
        """
        return whole data which low-thresholded.

        """
        temp = self._data.copy()
        temp[temp < self._view_min] = 0
        return temp

    def get_lthr_raw_data(self):
        temp = self._data.copy()
        temp[temp < self._view_min] = 0
        return np.rot90(temp, 3)

    def get_raw_data(self):
        temp = self._data.copy()
        return np.rot90(temp, 3)

    def get_value_label(self, value):
        return self.label_config.get_index_label(value)

    def set_label(self, label_config):
        self.label_config = label_config

    def is_label_global(self):
        return self.label_config.is_global

    def get_roi_coords(self, roi):
        data = self._data
        return (data==roi).nonzero()

    def get_coord_val(self, x, y, z):
        return self._data[y, x, z]
