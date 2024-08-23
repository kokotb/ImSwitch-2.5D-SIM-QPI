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
        
        device_infos = system.device_infos #CTNOTE How long does this step take? It gathers all camera info every loop. Can reduce time by 2/3.

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
        
##Create object reference for found device        
        self.device = device

##Populate a reference to all device nodes. Some settings are in 'tl stream modemap'
        self.nodemap = device.nodemap
        self.tl_stream_nodemap = device.tl_stream_nodemap
        # self.tl_stream_nodemap["StreamBufferHandlingMode"].value = "NewestOnly" #move to somewhere in liveview

##Create list with all possible wanted node names from camera
        self.propNodeNames = ['ExposureTime','ExposureAuto', 'Gain','Gamma','AcquisitionFrameRateEnable','AcquisitionFrameRate',
                           'ADCBitDepth', 'WidthMax', 'HeightMax','TriggerSource','TriggerMode', 'PixelFormat','DeviceStreamChannelPacketSize']
        self.roiNodeNames = ['OffsetX', 'OffsetY', 'Width', 'Height']

# Get nodes from camera. These are the lists called to change actual cam values
        self.propNodes = self.nodemap.get_node(self.propNodeNames)
        self.roiNodes = self.nodemap.get_node(self.roiNodeNames)

        self.SensorHeight = 4600
        self.SensorWidth = 5320
        self.model = device_info['serial']

        # Get all current cam parameters
        # self.propNodeValues = {}
        # for node_name in self.node_names:
        #     if node_name in self.node_names_dict:
        #         # print(self.getPropertyValue(self.node_names_dict[node_name]))
        #         self.parameters[self.node_names_dict[node_name]] = self.getPropertyValue(self.node_names_dict[node_name])
        
        # self.exposure = 100.1negotbuffer
        # self.gain = 0.0
        # self.gamma = 1
        # self.SensorHeight = self.parameters['sensor_height']
        # self.SensorWidth = self.parameters['sensor_width']
        # Setting image shape to full sensor
        # self.shape = (self.SensorHeight,self.SensorWidth)


    def start_live(self):
        # print("start_live1")
        # print(self.device)
        # print("start_live2")
        num_buffers = 500
        self.device.start_stream(num_buffers)

    def start_liveSIM(self, num_buffers):
        self.device.start_stream(num_buffers)

    def stop_live(self):
        self.__logger.info("stop_live")
        self.device.stop_stream()

    def suspend_live(self):
        self.__logger.info("suspend_live")
        # print(self.device)
        self.device.stop_stream()
        
        # self.cam.suspend_live()  # suspend imaging into prepared state

    def prepare_live(self):
        self.__logger.info("prepare_live")
        self.device.start_stream()
        # self.cam.prepare_live()  # prepare prepared state for live imaging

    # def toggleTrigger(self):

    def grabFrame(self):
        buffer_type = "Mono8"
        # print('grabframe')
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

        # if buffer_type == "Mono16":
        #     # FIXME: Include this in live view also? Now is hardcoded...
        #     # Development only done for Mono8 at this point for live view
        #     """
        #     Mono12/Mono16 buffer data as cpointers can be cast to (uint16, c_ushort)
        #     """
        #     array = ctypes.cast(item.pdata, ctypes.POINTER(ctypes.c_ushort))
        #     array = np.ctypeslib.as_array(array, (item.height, item.width))
        #     frame = array

        #     """
        #         Destroy the copied item to prevent memory leaks
        #     """
        #     # BufferFactory.destroy(item)
        if buffer_type == "Mono8":
            
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
            # width = item.width
            # height = item.height
            # depth = 0

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
            
            # time.sleep(.25)     
        else:
            self.__logger.warning("Unsupported data type! Mono16 and Mono8 currently supported")
            frame = None
        # BufferFactory.destroy(item)
        return frame
    
    def forceValidROI(self, hpos, vpos, hsize, vsize):

        #OffsetX(hpos) and Width(hsize) must be in multiples of 8, with Width minimum >=32.
        #OffsetY(vpos) and Height(hsize) must be even, with Height minimum >=32.
        xmod = 8
        ymod = 2
        integer, decimal = divmod(hpos/xmod,1)
        if decimal < 0.5:
            hpos_new = int(xmod*integer)
        else:
            hpos_new = int(xmod*(integer+1))
        integer, decimal = divmod(vpos/ymod,1)
        if decimal < 0.5:
            vpos_new = int(ymod*integer)
        else:
            vpos_new = int(ymod*(integer+1))

        integer, decimal = divmod(hsize/xmod,1)
        if decimal < 0.5:
            hsize_new = int(xmod*integer)
        else:
            hsize_new = int(xmod*(integer+1))
        integer, decimal = divmod(vsize/ymod,1)
        if decimal < 0.5:
            vsize_new = int(ymod*integer)
        else:
            vsize_new = int(ymod*(integer+1))
        
        hsize_new = max(hsize_new, 32)  # minimum ROI size (32 for Lucid cam)
        vsize_new = max(vsize_new, 32)  # minimum ROI size (32 for Lucid cam)




        return hpos_new, vpos_new, hsize_new, vsize_new

    def setROI(self, hpos, vpos, hsize, vsize):
        # v-vertical, h-horizontal

        hsize_max = self.SensorWidth
        vsize_max = self.SensorHeight
        hpos_new, vpos_new, hsize_new, vsize_new = self.forceValidROI(hpos, vpos, hsize, vsize)

        # Get current image size
        hsize_old = self.getROIValue("Width")
        vsize_old = self.getROIValue("Height")
        
# Adjust image size if target size at target offset sets us over the cam border
        if hsize_new > hsize_max - abs(hpos_new):
            hsize_set = int(hsize_max - abs(hpos_new))
        else:
            hsize_set = hsize_new
        if vsize_new > vsize_max - abs(vpos_new):
            vsize_set = int(vsize_max - abs(vpos_new))
        else:
            vsize_set = vsize_new
        # Issue a warning to a user that this happend
        if hsize_new > hsize_max - abs(hpos_new) or vsize_new > vsize_max - abs(vpos_new):
            self.__logger.warning(
                    f'{self.model}: Image size or position out of bounds!\nImage cropped {hsize_new}x{vsize_new} to {hsize_set}x{vsize_set} at {hpos_new},{vpos_new}.'
                    )
##########################


# Check wheter we are shrinking or enrlarging an image, this sets whether to move the image first 
# and then set the size or shrink the image first and then move the image
        if hsize_set < hsize_old:
            # Shrink first then move, if moving sets us of the cam at current image size, cam will
            # not accept that
            self.setROIValue("Width", hsize_set)
            self.setROIValue("OffsetX", hpos_new)
        else:
            # Move first then enlarge, if larger size is of the cam size at current location cam
            # will not accept that
            self.setROIValue("OffsetX", hpos_new)
            self.setROIValue("Width", hsize_set)
        # Do the same for the other axis
        if vsize_set < vsize_old:
            self.setROIValue("Height", vsize_set)
            self.setROIValue("OffsetY", vpos_new)
        else:
            self.setROIValue("OffsetY", vpos_new)
            self.setROIValue("Height", vsize_set)
#####################

        top = self.roiNodes['OffsetY'].value
        left = self.roiNodes['OffsetX'].value
        hei = self.roiNodes['Height'].value
        wid = self.roiNodes['Width'].value
##Large string of ROI info that print during camera initialization
        self.__logger.info(
            f'ROI set: {wid}x{hei} at ({left},{top})'
        )

        return left, top, wid, hei
##


###Write values from JSON config to the camera
    def setPropertyValue(self, property_name, property_value):
        if property_name == 'StreamBufferHandlingMode': #Needed as this property is under tl_steam, not regular nodemap.
            sbhmValueOld = self.getPropertyValue(property_name)
            if sbhmValueOld == property_value:
                pass
            else:
                self.tl_stream_nodemap["StreamBufferHandlingMode"].value = property_value

        elif property_name == 'ADCBitDepth': #Checking to see if ADCBitDepth needs to be changed, as setting it takes a whole second. If it doesn't need to be changed, just pass.
            adcValueOld = self.getPropertyValue(property_name)
            if adcValueOld == property_value:
                pass
            else:
                 self.propNodes[property_name].value = property_value

        elif property_name == 'AcquisitionFrameRate' and self.propNodes[property_name].is_writable: #Needed as 'AcquisitionFrameRate' commonly fails to set as the acceptable values change depending on other property values.
             maxAcqFrameRate = self.propNodes[property_name].max
             if maxAcqFrameRate >= property_value:
                  pass
             else:
                  property_value = int(maxAcqFrameRate)
             self.propNodes[property_name].value = property_value
            
        elif self.propNodes[property_name].is_writable:
                self.propNodes[property_name].value = property_value  

        elif self.propNodes[property_name].is_readable:
                self.__logger.debug(f"Property {property_name} is not writable! Setting parameter from cam.")
                property_value = self.getPropertyValue(property_name)

        else:
            self.__logger.debug(f"Property {property_name} is not readable nor writable! Property not set!")

            property_value = None

        self.__logger.debug(f"Set {property_name} {property_value} on {self.model}")
        return property_value
    
    # def setPropertyValueRunning(self, property_name, property_value):
    #     if property_name == 'StreamBufferHandlingMode': #Needed as this property is under tl_steam, not regular nodemap.
    #          self.tl_stream_nodemap["StreamBufferHandlingMode"].value = property_value

    #     elif property_name == 'ADCBitDepth': #Checking to see if ADCBitDepth needs to be changed, as setting it takes a whole second. If it doesn't need to be changed, just pass.
    #         adcValueOld = self.getPropertyValue(property_name)
    #         if adcValueOld == property_value:
    #             pass
    #         else:
    #              self.propNodes[property_name].value = property_value
                  

    #     elif property_name == 'AcquisitionFrameRate' and self.propNodes[property_name].is_writable: #Needed as 'AcquisitionFrameRate' commonly fails to set as the acceptable values change depending on other property values.
    #          maxAcqFrameRate = self.propNodes[property_name].max
    #          if maxAcqFrameRate >= property_value:
    #               pass
    #          else:
    #               property_value = int(maxAcqFrameRate)
    #          self.propNodes[property_name].value = property_value
            
    #     elif self.propNodes[property_name].is_writable:
    #             self.propNodes[property_name].value = property_value  

    #     elif self.propNodes[property_name].is_readable:
    #             self.__logger.debug(f"Property {property_name} is not writable! Setting parameter from cam.")
    #             property_value = self.getPropertyValue(property_name)

    #     else:
    #         self.__logger.debug(f"Property {property_name} is not readable nor writable! Property not set!")

    #         property_value = None

    #     self.__logger.debug(f"Set {property_name} {property_value} on {self.model}")
    #     return property_value

    def setROIValue(self, property_name, property_value):
        if self.roiNodes[property_name].is_writable:
                self.roiNodes[property_name].value = property_value     
        elif self.roiNodes[property_name].is_readable:
                self.__logger.debug(f"Property {property_name} is not writable! Setting parameter from cam.")
                property_value = self.getROIValue(property_name)
        else:
            self.__logger.debug(f"Property {property_name} is not readable nor writable! Property not set!")

            property_value = None

        print(property_name,property_value)
        return property_value

###Get values from the camera and store as variable
    def getPropertyValue(self, property_name):
        # Check if the property exists in the import properties.
        # Available properties are set in __init__
        # Generalized the import of parametersto just take into account exceptions that should not 
        # be modified ever
        # names_dict = self.parameter_names_dict
        # if property_name in names_dict:
        
        if property_name == 'StreamBufferHandlingMode': #Needed as this property is under tl_steam, not regular nodemap.
             property_value = self.tl_stream_nodemap[property_name].value
      
        elif  self.propNodes[property_name].is_readable:
            property_value = self.propNodes[property_name].value

        else:
                self.__logger.debug(f"Property {property_name} is not readable!")
                property_value = None

        return property_value
    
    def getROIValue(self, property_name):
        # Check if the property exists in the import properties.
        # Available properties are set in __init__
        # Generalized the import of parametersto just take into account exceptions that should not 
        # be modified ever
        # names_dict = self.parameter_names_dict
        # if property_name in names_dict:
        if  self.roiNodes[property_name].is_readable:
                property_value = self.roiNodes[property_name].value
        else:
                self.__logger.debug(f"Property {property_name} is not readable!")
                property_value = None

        return property_value


    def openPropertiesGUI(self):
        pass
        # self.cam.show_property_dialog()

    def setCamForLiveView(self, trigBool):
    # Doing this to be on the safe side - SIMControler changes stuf
    # Maybe keep this here and to nothing on the SIMControler side (setCamsAfterExperiment)?
    # FIXME: Delete if obsolete
        trigger_source = 'Line2'
        trigger_mode = trigBool
        exposure_auto = 'Off'
        # It overrides what is in the widget each time you run live-view button
        # exposure_time = 2000.0 
        exposure_time = float(self.getPropertyValue('ExposureTime'))
        pixel_format = 'Mono8'
        bit_depth = 'Bits8'
        frame_rate_enable = True
        # Could not implement it by query. Max frame rate does not query.
        frame_rate = 45.0 # <45 Hz at full frame size
        buffer_mode = "NewestOnly"

        dic_parameters = {'TriggerSource':trigger_source, 'TriggerMode':trigger_mode, 'ExposureAuto':exposure_auto, 'ExposureTime':exposure_time, 'PixelFormat':pixel_format, 'AcquisitionFrameRateEnable':frame_rate_enable, 'AcquisitionFrameRate':frame_rate, 'StreamBufferHandlingMode':buffer_mode,'ADCBitDepth':bit_depth}

        for parameter_name in dic_parameters:
            # print(self.getPropertyValue(parameter_name))
            self.setPropertyValue(parameter_name, dic_parameters[parameter_name])
            # print(self.getPropertyValue(parameter_name))
            
    def setCamForAcquisition(self, buffer_size):
        # FIXME: Include that once onlien
        # Set triggers - tell it to wait for trigger.
        # print('Triggers not set yet.')
        # Stop stream just in case it was left open by mock or some
        # other process
        # self.device.stop_stream()
        # Set buffers
        self.device.start_stream(buffer_size)

    def setCamStopAcquisition(self):
        # FIXME: Include that once onlien
        # Set triggers - tell it to wait for trigger.
        # print('Triggers not set yet.')
        
        # Set buffers
        self.device.stop_stream() 

    def clearBuffers(self):
        waitingBuffers = self.device.tl_stream_nodemap['StreamOutputBufferCount'].value
        if waitingBuffers > 0:
            buffer_set = self.device.get_buffer(waitingBuffers)
            self.device.requeue_buffer(buffer_set)

    
    def grabFrameSet(self, buffer_size):
        # buffer_size = image number pulled from a cam
        
        buffer_type = "Mono16" #FIXME: do this with getproperty
        # waitingBuffers = self.device.tl_stream_nodemap['StreamOutputBufferCount']

        buffer_set = self.device.get_buffer(buffer_size) 
        # buffer = self.device.get_buffer()
        # print(self.device)
        """
        Copy buffer and requeue to avoid running out of buffers
        """
        items = []
        
        for buffer in buffer_set:        
            items.append(BufferFactory.copy(buffer))
        self.device.requeue_buffer(buffer_set)
        # item = BufferFactory.copy(buffer)
        # self.device.requeue_buffer(buffer)

        if buffer_type == "Mono16":
            # Development only done for Mono16 at this point
            """
            Mono12/Mono16 buffer data as cpointers can be cast to (uint16, c_ushort)
            """
            nparrays = []
            nparray = []
            for item in items:
                nparray = ctypes.cast(item.pdata, ctypes.POINTER(ctypes.c_ushort))
                nparrays.append(np.ctypeslib.as_array(nparray, (item.height, item.width)))
            # array = ctypes.cast(item.pdata, ctypes.POINTER(ctypes.c_ushort))
            # array = np.ctypeslib.as_array(array, (item.height, item.width))
            sim_set = nparrays

            """
                Destroy the copied item to prevent memory leaks
            """
            # FIXME: Include this in the final version?
            # BufferFactory.destroy(item)
        elif buffer_type == "Mono8":
            # FIXME: Do this in proper format - not finished yet
            # buffer_bytes_per_pixel = int(len(item.data)/(item.width * item.height))
           
            
            buffer_bytes_per_pixel_set = []
            for item in items:
                buffer_bytes_per_pixel_set.append(int(len(item.data)/(item.width * item.height)))
            if max(buffer_bytes_per_pixel_set) > 1:
                # If buffer_bytes exceed 8bit value, return empty set
                self.__logger.warning("Data not Mono8! Something went wrong.")
                sim_set = None
                return sim_set
            #  Taken from py_image_buffer_save_mono12_to_png_with_PIL.py
            """
            Buffer data as cpointers can be accessed using buffer.pbytes
           
            """
            num_channels = 1
            prev_frame_time = 0

            # array = (ctypes.c_ubyte * num_channels * item.width * item.height).from_address(ctypes.addressof(item.pbytes))

            arrays = []
            for item in items:
                arrays.append((ctypes.c_ubyte * num_channels * item.width * item.height).from_address(ctypes.addressof(item.pbytes)))
            
            """
            Create a reshaped NumPy array to display using OpenCV
            """
            # FIXME: check how I need to re-shape the data grabbed to bi output correctly
            # sim_set = np.ndarray(buffer=array, dtype=np.uint8, shape=(item.height, item.width, buffer_bytes_per_pixel))
            sim_set = []
            for k, array in enumerate(arrays):
                sim_set.append(np.ndarray(buffer=array, dtype=np.uint16, shape=(items[k].height, items[k].width, buffer_bytes_per_pixel_set[k])))
            
            # TODO: Remove this, kept just in case it would come in handy.
            # frame = np.transpose(frame)
            # frame = np.moveaxis(frame, 1 , 2)
            """
                Destroy the copied item to prevent memory leaks
            """
            # FIXME: Include this in the final version?
            # BufferFactory.destroy(item)
        else:
            self.__logger.warning("Unsupported data type! Mono16 and Mono8 currently supported")
            sim_set = None
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
