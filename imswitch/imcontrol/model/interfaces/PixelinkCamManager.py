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
from pixelinkWrapper import*
from ctypes import*
import numpy
import cv2
import os

class PixelCam:
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
                           'ADCBitDepth', 'WidthMax', 'HeightMax','TriggerSource','TriggerMode', 'TriggerSelector', 'PixelFormat','DeviceStreamChannelPacketSize']
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


    def streamActive(self):
        # print("start_live1")
        # print(self.device)
        # print("start_live2")
        num_buffers = 500
        self.device.start_stream(num_buffers)

    def streamInactive(self):
        self.__logger.info("stop_live")
        self.device.stop_stream()

    def suspend_live(self):
        self.__logger.info("Suspended")
        # print(self.device)
        self.device.stop_stream()
        
        # self.cam.suspend_live()  # suspend imaging into prepared state

    def prepare_live(self):
        self.__logger.info("prepare_live")
        self.device.start_stream()
        # self.cam.prepare_live()  # prepare prepared state for live imaging
    
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
    def setPropertyValue(self, property_name, property_value, toPrint=True):
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
                  property_value = float(maxAcqFrameRate)
             self.propNodes[property_name].value = property_value
            
        elif self.propNodes[property_name].is_writable:
                self.propNodes[property_name].value = property_value  

        elif self.propNodes[property_name].is_readable:
                self.__logger.debug(f"Property {property_name} is not writable! Setting parameter from cam.")
                property_value = self.getPropertyValue(property_name)

        else:
            self.__logger.debug(f"Property {property_name} is not readable nor writable! Property not set!")

            property_value = None
        if toPrint:
            self.__logger.debug(f"Set {property_name} {property_value} on {self.model}")
        return property_value
    


    def setROIValue(self, property_name, property_value):
        if self.roiNodes[property_name].is_writable:
                self.roiNodes[property_name].value = property_value     
        elif self.roiNodes[property_name].is_readable:
                self.__logger.debug(f"Property {property_name} is not writable! Setting parameter from cam.")
                property_value = self.getROIValue(property_name)
        else:
            self.__logger.debug(f"Property {property_name} is not readable nor writable! Property not set!")

            property_value = None

        # print(property_name,property_value)
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
        trigger_source = 'Line0'
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

    
    def getBufferValue(self, mode):
        value = self.tl_stream_nodemap['StreamOutputBufferCount'].value
        return value
    
    def draw_circle(event,x,y,flags,param):
        if event == cv.EVENT_LBUTTONDBLCLK:
            cv2.circle(img,(x,y),100,(255,0,0),-1)

    
    def grabFrameAF(self):
        # img = np.zeros((1280,1024), np.uint8)
        rawFrame = create_string_buffer(1024 * 1280 * 2)
        ret = PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.START)
        ret = PxLApi.getNextFrame(self.hCamera, rawFrame)
        frameDesc = ret[1]
        ret = PxLApi.formatImage(rawFrame, frameDesc, PxLApi.ImageFormat.RAW_MONO8)
        formatedImage = ret[1]
        npFormatedImage = numpy.full_like(formatedImage, formatedImage, order="C")
        npFormatedImage.dtype = numpy.uint8
        imageHeight = int(frameDesc.Roi.fHeight)
        imageWidth = int(frameDesc.Roi.fWidth)
        newShape = (imageHeight, imageWidth)
        npFormatedImage = numpy.reshape(npFormatedImage, newShape)
        cv2.namedWindow('AF Preview')
        cv2.setMouseCallback('AF Preview', self.printthething)
        cv2.imshow('AF Preview', npFormatedImage)

        return npFormatedImage
    
    def printthething(self):
         pass
    



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
