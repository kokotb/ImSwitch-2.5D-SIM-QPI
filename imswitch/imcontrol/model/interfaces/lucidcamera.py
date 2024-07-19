import numpy as np

from imswitch.imcommon.model import initLogger
# from .pyicic import IC_ImagingControl
import time
from arena_api.system import system
from arena_api.buffer import *
import ctypes
import numpy as np
import cv2
from datetime import datetime
from arena_api.enums import PixelFormat
from arena_api.__future__.save import Writer
from datetime import datetime

class CameraTIS:
    def __init__(self, cameraNo):
        super().__init__()
        
        self.__logger = initLogger(self, tryInheritParent=True)
        
        device = []
        
        # cameraNo is a two digit number unique to our cams (LUCID)
        cameraNo_string = "{}".format(cameraNo)
        camerNo_num_digit = len(cameraNo_string)
        camera_found = False
        
        device_infos = None
        selected_index = None
        
        device_infos = system.device_infos

        for i in range(len(device_infos)):
            if cameraNo_string == device_infos[i]['serial'][-camerNo_num_digit:]:
                device_info = device_infos[i]
                serial_number =  device_info['serial']
                selected_index = i
                camera_found = True
                break

        if camera_found == True:
            device = system.create_device(device_infos=device_infos[selected_index])[0]
        else:
            raise Exception(f"Serial number {serial_number} cannot be found")
        
        # nodemap = device.nodemap
##Create object reference for found device        
        self.device = device
##Populate a reference to all device nodes. Some setting are in 'tl stream modemap'
        self.nodemap = device.nodemap
        tl_stream_nodemap = device.tl_stream_nodemap
        tl_stream_nodemap['StreamAutoNegotiatePacketSize'].value = True
        tl_stream_nodemap["StreamBufferHandlingMode"].value = "NewestOnly"
##Populate dict with desired node values/properties from camera
        self.nodes = self.nodemap.get_node(['Width', 'Height', 'PixelFormat', 
                                       'ExposureAuto','ExposureTime','DeviceStreamChannelPacketSize', 'OffsetX', 'OffsetY','Gamma',
                                       'Gain','AcquisitionFrameRateEnable','AcquisitionFrameRate','ADCBitDepth'])
##Create string referencing model name of cam =='ATX245S-M' for all cams
        self.model = device_info['serial']
##Sets ExposureAuto to Off on the camera. There is propably a better place to do this.
        self.nodes['ExposureAuto'].value = 'Off'
        self.nodes['AcquisitionFrameRateEnable'].value = True
        self.nodes['AcquisitionFrameRate'].value = 25.0


        
        # self.exposure = 100.1negotbuffer
        # self.gain = 0.0
        # self.gamma = 1
        self.SensorHeight = 4600
        self.SensorWidth = 5320
        self.shape = (self.SensorHeight,self.SensorWidth)
        
        # self.properties = {
        #     'image_height': self.nodes['Height'].value,
        #     'image_width': self.nodes['Width'].value,
        #     'subarray_vpos': self.nodes['OffsetX'].value,
        #     'subarray_hpos': self.nodes['OffsetY'].value,
        #     'exposure_time': self.nodes['ExposureTime'].min,
        #     'subarray_vsize': 512,
        #     'subarray_hsize': 512,
        #     'SensorHeight': 4600,
        #     'SensorWidth': 5320
        # }
        
        # print(device)

        # return device
        
    def create_device_from_serial_number(self, serial_number):
        
        device = []
        camera_found = False

        device_infos = None
        selected_index = None

        device_infos = system.device_infos
        for i in range(len(device_infos)):
            if serial_number == device_infos[i]['serial']:
                selected_index = i
                camera_found = True
                break

        if camera_found == True:
            device = system.create_device(device_infos=device_infos[selected_index])[0]
            # print(device)
        else:
            raise Exception(f"Serial number {serial_number} cannot be found")

        return device
    
    def start_live(self):
        # print("start_live1")
        # print(self.device)
        # print("start_live2")
        num_buffers = 500

        self.device.start_stream(num_buffers)

    def stop_live(self):
        print("stop_live")
        # print(self.device)
        self.device.stop_stream()

    def suspend_live(self):
        print("suspend_live")
        # print(self.device)
        self.device.stop_stream()
        
        # self.cam.suspend_live()  # suspend imaging into prepared state

    def prepare_live(self):
        print("prepare_live")
        self.device.start_stream()
        # self.cam.prepare_live()  # prepare prepared state for live imaging

    def grabFrame(self):
        # print("grab frame")
        # print(self.device)
        buffer = self.device.get_buffer()
        # print(self.device)
        # print(buffer)
        """
        Copy buffer and requeue to avoid running out of buffers
        """
        item = BufferFactory.copy(buffer)
        self.device.requeue_buffer(buffer)
        buffer_bytes_per_pixel = int(len(item.data)/(item.width * item.height))
        """
        Buffer data as cpointers can be accessed using buffer.pbytes
        """
        num_channels = 1
        prev_frame_time = 0
        array = (ctypes.c_ubyte * num_channels * item.width * item.height).from_address(ctypes.addressof(item.pbytes))
        
        """
        Create a reshaped NumPy array to display using OpenCV
        """
        frame = np.ndarray(buffer=array, dtype=np.uint8, shape=(item.height, item.width, buffer_bytes_per_pixel))
        # print(np.shape(frame))
        # print(buffer_bytes_per_pixel)
        width = item.width
        height = item.height
        depth = 0

        # fps = str(1/(curr_frame_time - prev_frame_time))
        
        # frame, width, height, depth = self.cam.get_image_data()
        # frame = np.array(frame, dtype='float64')
        # Check if below is giving the right dimensions out
        # TODO: do this smarter, as I can just take every 3rd value instead of creating a reshaped
        #       3D array and taking the first plane of that
        # frame = np.reshape(frame, (height, width, depth))[:, :, 0]
        frame = np.transpose(frame)
        frame = np.moveaxis(frame, 1 , 2)
        # self.device.stop_stream()
        """
            Destroy the copied item to prevent memory leaks
        """
        # BufferFactory.destroy(item)
        # time.sleep(.25)        
            
        return frame

    def setROI(self, hpos, vpos, hsize, vsize):
        hsize = max(hsize, 32)  # minimum ROI size (32 for Lucid cam)
        vsize = max(vsize, 32)  # minimum ROI size (32 for Lucid cam)
        print('setROI1')
        self.__logger.debug(
            f'{self.model}: setROI started with {hsize}x{vsize} at {hpos},{vpos}.'
        )
        #Replaces what si below
        if self.nodes['Width'].is_readable and self.nodes['Width'].is_writable:
            self.nodes['Width'].value = hsize
        if self.nodes['Height'].is_readable and self.nodes['Height'].is_writable:
            self.nodes['Height'].value = vsize
        if self.nodes['OffsetX'].is_readable and self.nodes['OffsetX'].is_writable:    
            self.nodes['OffsetX'].value = hpos
        if self.nodes['OffsetY'].is_readable and self.nodes['OffsetY'].is_writable:       
            self.nodes['OffsetY'].value = vpos
        
        #self.cam.frame_filter_set_parameter(self.roi_filter, 'Top'.encode('utf-8'), vpos)        # self.cam.frame_filter_set_parameter(self.roi_filter, 'Top', vpos)
        # self.cam.frame_filter_set_parameter(self.roi_filter, 'Left', hpos)
        # self.cam.frame_filter_set_parameter(self.roi_filter, 'Height', vsize)
        # self.cam.frame_filter_set_parameter(self.roi_filter, 'Width', hsize)
        top = self.nodes['OffsetY']
        left = self.nodes['OffsetX']
        hei = self.nodes['Height']
        wid = self.nodes['Width']
##Large string of ROI info that print during camera initialization
        # self.__logger.info(
        #     f'ROI set: w{wid} x h{hei} at l{left},t{top}'
        # )
##


###Write values from JSON config to the camera
    def setPropertyValue(self, property_name, property_value):
        # Check if the property exists.
        if property_name == "gain": # min=0, max=48
            self.nodes['Gain'].value = property_value
        elif property_name == "gamma": # min=0.2, max=2.0
            self.nodes['Gamma'].value = property_value
        elif property_name == "pixel_format": 
            self.nodes['PixelFormat'].value = property_value
        elif property_name == "ADC_bit_depth": 
            self.nodes['ADCBitDepth'].value = property_value
        elif property_name == "exposureauto":
            self.nodes['ExposureAuto'].value = property_value
        elif property_name == "exposure": #min and max can change depending on other settings
            self.nodes['ExposureTime'].value = property_value 
        elif property_name == 'image_height':
            # self.shape = (self.shape[0], property_value)
            self.shape = (property_value, self.shape[1])
        elif property_name == 'image_width': 
            self.shape = (self.shape[0], property_value)
            # self.shape = (property_value, self.shape[1])
        elif property_name == 'buffer_mode':
            self.nodes['StreamBufferHandlingMode'].value = property_value
        else:
            self.__logger.warning(f'Property {property_name} does not exist')
            return False
        return property_value
###
###Get values from the camera and store as variable
    def getPropertyValue(self, property_name):
        # Check if the property exists.
        if property_name == "gain":
            property_value = self.nodes['Gain'].value
        elif property_name == "gamma":
            property_value = self.nodes['Gamma'].value
        elif property_name == "exposure":
            property_value = self.nodes['ExposureTime'].value
        elif property_name == "pixel_format":  #PixelFormat other than Mono8 breaks the display.
            property_value = self.nodes['PixelFormat'].value
        elif property_name == "ADC_bit_depth":
            property_value = self.nodes['ADCBitDepth'].value
        elif property_name == "exposureauto":
            property_value = self.nodes['ExposureAuto'].value
        elif property_name == "image_width":
            property_value = self.shape[1]
        elif property_name == "image_height":
            property_value = self.shape[0]
        else:
            self.__logger.warning(f'Property {property_name} does not exist')
            return False
        return property_value

    def openPropertiesGUI(self):
        pass
        # self.cam.show_property_dialog()

def setCamForAcquisition(self, buffer_size):
    # FIXME: Include that once onlien
    # Set triggers - tell it to wait for trigger.
    print('Triggers not set yet.')
    
    # Set buffers
    self.device.start_stream(buffer_size)
    
def grabFrameSet(self, buffer_size):
    # buffer_size = image number pulled from a cam
    
    buffer = self.device.get_buffer(buffer_size) 
    """
    Copy buffer and requeue to avoid running out of buffers
    """
    item = BufferFactory.copy(buffer)
    self.device.requeue_buffer(buffer)
    buffer_bytes_per_pixel = int(len(item.data)/(item.width * item.height)/buffer_size)
    """
    Buffer data as cpointers can be accessed using buffer.pbytes
    """
    num_channels = buffer_size
    prev_frame_time = 0
    array = (ctypes.c_ubyte * num_channels * item.width * item.height).from_address(ctypes.addressof(item.pbytes))
    
    """
    Create a reshaped NumPy array to display using OpenCV
    """
    # FIXME: check how I need to re-shape the data grabbed to bi output correctly
    sim_set = np.ndarray(buffer=array, dtype=np.uint16, shape=(item.height, item.width, buffer_bytes_per_pixel))
    # print(np.shape(frame))
    # print(buffer_bytes_per_pixel)
    
    # TODO: Remove this, kept just in case it would come in handy.
    # frame = np.transpose(frame)
    # frame = np.moveaxis(frame, 1 , 2)
    """
        Destroy the copied item to prevent memory leaks
    """
    # FIXME: Include this in the final version?
    # BufferFactory.destroy(item)
    
    return sim_set

# Copyright (C) 2020-2021 ImSwitch developers
# This file is part of ImSwitch.
#
# ImSwitch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ImSwitch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
