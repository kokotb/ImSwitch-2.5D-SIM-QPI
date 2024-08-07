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
        self.t1_stream_nodemap = device.tl_stream_nodemap
        # tl_stream_nodemap = device.tl_stream_nodemap
        self.t1_stream_nodemap['StreamAutoNegotiatePacketSize'].value = True
        self.t1_stream_nodemap["StreamBufferHandlingMode"].value = "NewestOnly"
##Populate dict with desired node values/properties from camera
        # Define node names
        self.node_names = ['OffsetX', 'OffsetY', 'Width', 'Height', 'PixelFormat', 
                                       'ExposureAuto','ExposureTime','DeviceStreamChannelPacketSize', 'Gamma',
                                       'Gain','AcquisitionFrameRateEnable','AcquisitionFrameRate','ADCBitDepth', 'WidthMax', 'HeightMax','DeviceStreamChannelPacketSize', 'TriggerSource','TriggerMode']
        # Link node names to imswitch names
        self.node_names_dict = {'OffsetX':'x0', 'OffsetY':'y0', 'Width':'image_width', 'Height':'image_height', 'PixelFormat':'pixel_format', 
                                       'ExposureAuto':'exposureauto','ExposureTime':'exposure','DeviceStreamChannelPacketSize':'streampacketsize', 'Gamma':'gamma',
                                       'Gain':'gain','AcquisitionFrameRateEnable':'acqframerateenable','AcquisitionFrameRate':'acqframerate','ADCBitDepth':'ADC_bit_depth',
                                       'WidthMax':'sensor_width', 
                                       'HeightMax':'sensor_height',
                                       'TriggerSource':'trigger_source',
                                       'TriggerMode':'trigger_mode'}
        # Generate imswitch names dict (inverse dictionary)
        self.parameter_names_dict = {}
        for node_name in self.node_names:
            # Only takes the nodes we use for pulling data our of config files
            if node_name in self.node_names_dict:
                self.parameter_names_dict[self.node_names_dict[node_name]] = node_name

        # Get actual nodes
        self.nodes = self.nodemap.get_node(self.node_names)
##Create string referencing model name of cam =='ATX245S-M' for all cams

        # FIXME: Initializations settings, AcquisitionFrameRateEnable, AcquisitionFrameRate
        # will be moved to config files, we should not be having hardcoded cam configs
        self.model = device_info['serial']
##Sets ExposureAuto to Off on the camera. There is propably a better place to do this.
        self.nodes['ExposureAuto'].value = 'Off'
        self.nodes['AcquisitionFrameRateEnable'].value = True
        self.nodes['AcquisitionFrameRate'].value = 25.0

        # Get all current cam parameters
        self.parameters = {}
        for node_name in self.node_names:
            if node_name in self.node_names_dict:
                # print(self.getPropertyValue(self.node_names_dict[node_name]))
                self.parameters[self.node_names_dict[node_name]] = self.getPropertyValue(self.node_names_dict[node_name])
        
        # self.exposure = 100.1negotbuffer
        # self.gain = 0.0
        # self.gamma = 1
        self.SensorHeight = self.parameters['sensor_height']
        self.SensorWidth = self.parameters['sensor_width']
        # Setting image shape to full sensor
        self.shape = (self.SensorHeight,self.SensorWidth)
        
        # FIXME: Delete after development is done
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

    def grabFrame(self):
        buffer_type = "Mono8"

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

        if buffer_type == "Mono16":
            # FIXME: Include this in live view also? Now is hardcoded...
            # Development only done for Mono8 at this point for live view
            """
            Mono12/Mono16 buffer data as cpointers can be cast to (uint16, c_ushort)
            """
            array = ctypes.cast(item.pdata, ctypes.POINTER(ctypes.c_ushort))
            array = np.ctypeslib.as_array(array, (item.height, item.width))
            frame = array

            """
                Destroy the copied item to prevent memory leaks
            """
            # BufferFactory.destroy(item)
        elif buffer_type == "Mono8":
            
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
        else:
            self.__logger.warning("Unsupported data type! Mono16 and Mono8 currently supported")
            frame = None
        return frame

    def setROI(self, hpos, vpos, hsize, vsize):
        # v-vertical, h-horizontal
        # print('setROI1')
        hsize_max = self.SensorWidth
        vsize_max = self.SensorHeight
        

        self.__logger.debug(
            f'{self.model}: setROI started with {hsize}x{vsize} at {hpos},{vpos}.'
        )

        # ---------------New implementation2-------------------
        # Already imeplemented in SettingsController - moved there, kept for safety if function is 
        # called not from SettingsController 
        # # Cam only accepts multiples of 8 for positions, set position to the nearest multiple of 8
        mod = 8
        integer, decimal = divmod(hpos/mod,1)
        if decimal < 0.5:
            hpos_new = int(mod*integer)
        else:
            hpos_new = int(mod*(integer+1))
        integer, decimal = divmod(vpos/mod,1)
        if decimal < 0.5:
            vpos_new = int(mod*integer)
        else:
            vpos_new = int(mod*(integer+1))

        integer, decimal = divmod(hsize/mod,1)
        if decimal < 0.5:
            hsize_new = int(mod*integer)
        else:
            hsize_new = int(mod*(integer+1))
        integer, decimal = divmod(vsize/mod,1)
        if decimal < 0.5:
            vsize_new = int(mod*integer)
        else:
            vsize_new = int(mod*(integer+1))
        
        hsize_new = max(hsize_new, 32)  # minimum ROI size (32 for Lucid cam)
        vsize_new = max(vsize_new, 32)  # minimum ROI size (32 for Lucid cam)
         
         
        hpos_new = hpos
        vpos_new = vpos
        
        # Get current image size
        hsize_old = self.getPropertyValue("image_width")
        vsize_old = self.getPropertyValue("image_height")
        
        # hpos_old = self.getPropertyValue("x0")
        # vpos_old = self.getPropertyValue("y0")
        # Need to limit values - cam does not except values if we go of the cam area with 
        # either position or size of the image

        # Crop image size if target size at target offset sets us over the cam border
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

        # Check wheter we are shrinking or enrlarging an image, this sets wether to move the image
        # first and then set the size or shrink the image first and then move the image
        # h == horizontal
        # v == vertical
        if hsize_set < hsize_old:
            # Shrink first then move, if moving sets us of the cam at current image size, cam will
            # not accept that
            self.setPropertyValue("image_width", hsize_set)
            self.setPropertyValue("x0", hpos_new)
        else:
            # Move first then enlarge, if larger size is of the cam size at current location cam
            # will not accept that
            self.setPropertyValue("x0", hpos_new)
            self.setPropertyValue("image_width", hsize_set)
        # Do the same for the other axis
        if vsize_set < vsize_old:
            self.setPropertyValue("image_height", vsize_set)
            self.setPropertyValue("y0", vpos_new)
        else:
            self.setPropertyValue("y0", vpos_new)
            self.setPropertyValue("image_height", vsize_set)
        # ---------------New implementation2-------------------

        # FIXME: Delete after development is done
        # # ---------------old implementation-------------------
        
        # if self.nodes['Width'].is_readable and self.nodes['Width'].is_writable:
        #     self.setPropertyValue("image_width", hsize)
        # if self.nodes['Height'].is_readable and self.nodes['Height'].is_writable:
        #     self.setPropertyValue("image_height", vsize)
        # # TODO: Limit offset movement so we don't go of axis
        # if self.nodes['OffsetX'].is_readable and self.nodes['OffsetX'].is_writable:
        #     # Cam only accepts multiples of 8 for offset position
        #     integer, decimal = divmod(hpos/mod,1)
        #     if decimal < 0.5:
        #         hpos_set = int(mod*integer)
        #     else:
        #         hpos_set = int(mod*(integer+1))    
        #     self.setPropertyValue("x0", hpos_set)
        # if self.nodes['OffsetY'].is_readable and self.nodes['OffsetY'].is_writable:
        #     # Cam only accepts multiples of mod for offset position
        #     integer, decimal = divmod(vpos/mod,1)
        #     if decimal < 0.5:
        #         vpos_set = int(mod*integer)
        #     else:
        #         vpos_set = int(mod*(integer+1))      
        #     self.setPropertyValue("y0", vpos_set)
        # # ---------------old implementation-------------------

        # ---------------new implementation-------------------
        #Replaces what si below
        # if self.nodes['Width'].is_readable and self.nodes['Width'].is_writable:
        #     if hsizemax == hsize:
                
        #         # self.nodes['OffsetX'].value = hpos
        #         # self.nodes['Width'].value = hsize
        #         self.setPropertyValue("x0", hpos)
        #         self.setPropertyValue("image_width", hsize)
        #     else:
        #         # self.nodes['Width'].value = hsize
        #         self.setPropertyValue("image_width", hsize)
        # if self.nodes['Height'].is_readable and self.nodes['Height'].is_writable:
        #     if vsizemax == vsize:
        #         self.setPropertyValue("y0", vpos)
        #         self.setPropertyValue("image_height", vsize)
        #         # self.nodes['OffsetY'].value = vpos
        #         # self.nodes['Height'].value = vsize
        #     else:
        #         # self.nodes['Height'].value = vsize
        #         self.setPropertyValue("image_height", vsize)
        # # TODO: Limit offset movement so we don't go of axis
        # if self.nodes['OffsetX'].is_readable and self.nodes['OffsetX'].is_writable:
        #     # Cam only accepts multiples of mod for offset position
        #     integer, decimal = divmod(hpos/mod,1)
        #     if decimal < 0.5:
        #         hpos_set = int(mod*integer)
        #     else:
        #         hpos_set = int(mod*(integer+1))    
        #     # self.nodes['OffsetX'].value = hpos_set
        #     self.setPropertyValue("x0", hpos_set)
        # if self.nodes['OffsetY'].is_readable and self.nodes['OffsetY'].is_writable:
        #     # Cam only accepts multiples of mod for offset position
        #     integer, decimal = divmod(vpos/mod,1)
        #     if decimal < 0.5:
        #         vpos_set = int(mod*integer)
        #     else:
        #         vpos_set = int(mod*(integer+1))      
        #     # self.nodes['OffsetY'].value = vpos_set
        #     self.setPropertyValue("y0", vpos_set)
        # ---------------new implementation-------------------
        
        #self.cam.frame_filter_set_parameter(self.roi_filter, 'Top'.encode('utf-8'), vpos)        # self.cam.frame_filter_set_parameter(self.roi_filter, 'Top', vpos)
        # self.cam.frame_filter_set_parameter(self.roi_filter, 'Left', hpos)
        # self.cam.frame_filter_set_parameter(self.roi_filter, 'Height', vsize)
        # self.cam.frame_filter_set_parameter(self.roi_filter, 'Width', hsize)
        top = self.nodes['OffsetY'].value
        left = self.nodes['OffsetX'].value
        hei = self.nodes['Height'].value
        wid = self.nodes['Width'].value
##Large string of ROI info that print during camera initialization
        self.__logger.info(
            f'ROI set: w{wid} x h{hei} at l{left},t{top}'
        )
##


###Write values from JSON config to the camera
    def setPropertyValue(self, property_name, property_value):
        # Check if the property exists in the import properties.
        # Available properties are set in __init__
        # gain: min=0, max=48
        # gamma: min=0.2, max=2.0
        # exposure: min and max can change depending on other settings
        # Generalized the import of parametersto just take into account exceptions that should not 
        # be modified ever

        names_dict = self.parameter_names_dict
        if property_name in names_dict:
            if property_name == "image_width":
                # Check if we can read and write to a variable on the cam
                # Throw an error if we cannot
                if self.nodes[names_dict[property_name]].is_readable and self.nodes[names_dict[property_name]].is_writable:
                    # All is good, do the writing
                    self.nodes[names_dict[property_name]].value = property_value
                    self.shape = (self.shape[0], property_value)
                else:
                    if self.nodes[names_dict[property_name]].is_readable:
                        # We can just read the parameter - setting cam parameter as parameter
                        self.__logger.debug(f"Property {property_name} is not writable! Setting parameter from cam.")
                        property_value = self.getPropertyValue(property_name)
                    else:
                        self.__logger.debug(f"Property {property_name} is not readable nor writable! Property not set!")
                        # FIXME: Maybe leave parameter in if needed for computation?
                        property_value = None
            elif property_name == "image_height":
                if self.nodes[names_dict[property_name]].is_readable and self.nodes[names_dict[property_name]].is_writable:
                    self.nodes[names_dict[property_name]].value = property_value
                    self.shape = (property_value, self.shape[1])    
                else:
                    if self.nodes[names_dict[property_name]].is_readable:
                        self.__logger.debug(f"Property {property_name} is not writable! Setting parameter from cam.")
                        property_value = self.getPropertyValue(property_name)
                    else:
                        self.__logger.debug(f"Property {property_name} is not readable nor writable! Property not set!")
                        property_value = None
            elif property_name == "sensor_width" or property_name == "sensor_height":
                pass
            else:
                if self.nodes[names_dict[property_name]].is_readable and self.nodes[names_dict[property_name]].is_writable:
                    self.nodes[names_dict[property_name]].value = property_value     
                else:
                    if self.nodes[names_dict[property_name]].is_readable:
                        self.__logger.debug(f"Property {property_name} is not writable! Setting parameter from cam.")
                        property_value = self.getPropertyValue(property_name)
                    else:
                       self.__logger.debug(f"Property {property_name} is not readable nor writable! Property not set!")
                       # FIXME: Maybe leave parameter in if needed for computation?
                       property_value = None
                # Different nodeamp
        elif property_name == "buffer_mode":
            if self.t1_stream_nodemap["StreamBufferHandlingMode"].is_readable and self.t1_stream_nodemap["StreamBufferHandlingMode"].is_writable:
                self.t1_stream_nodemap["StreamBufferHandlingMode"].value = property_value     
            else:
                if self.t1_stream_nodemap["StreamBufferHandlingMode"].is_readable:
                    self.__logger.debug(f"Property {property_name} is not writable!")
                    property_value = self.getPropertyValue(property_name)
                else:
                    self.__logger.debug(f"Property {property_name} is not readable nor writable! Property not set!")
                    # FIXME: Maybe leave parameter in if needed for computation?
                    property_value = None
        else:
            self.__logger.warning(f'Property {property_name} does not exist')
            return False
        return property_value

        # FIXME: Delete if not needed
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
        # Check if the property exists in the import properties.
        # Available properties are set in __init__
        # Generalized the import of parametersto just take into account exceptions that should not 
        # be modified ever
        names_dict = self.parameter_names_dict
        if property_name in names_dict:
            if property_name == "image_width":
                # Need to check wether we can even read property from a cam
                if self.nodes[names_dict[property_name]].is_readable:
                    property_value = self.nodes[names_dict[property_name]].value
                else:
                    self.__logger.debug(f"Property {property_name} is not readable!")
                    property_value = None
                # self.shape[1] = property_value
            elif property_name == "image_height":
                if self.nodes[names_dict[property_name]].is_readable:
                    property_value = self.nodes[names_dict[property_name]].value
                else:
                    self.__logger.debug(f"Property {property_name} is not readable!")
                    property_value = None
                # self.shape[0] = property_value
            else:
                if self.nodes[names_dict[property_name]].is_readable:
                    property_value = self.nodes[names_dict[property_name]].value
                else:
                    self.__logger.debug(f"Property {property_name} is not readable!")
                    property_value = None
        # Different nodeamp
        elif property_name == "buffer_mode":
            if self.t1_stream_nodemap["StreamBufferHandlingMode"].is_readable:
                    property_value = self.t1_stream_nodemap["StreamBufferHandlingMode"].value
            else:
                self.__logger.debug(f"Property {property_name} is not readable!")
                property_value = None  
        else:
            self.__logger.warning(f'Property {property_name} does not exist')
            return False
        return property_value

        
        # FIXME: Old hard-coded code. Delete after testing new code.
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

    def setCamForLiveView(self):
    # Doing this to be on the safe side - SIMControler changes stuf
    # Maybe keep this here and to nothing on the SIMControler side (setCamsAfterExperiment)?
    # FIXME: Delete if obsolete
        packet_size = 9000
        trigger_source = 'Line0'
        trigger_mode = 'Off'
        exposure_auto = 'Off'
        # It overrides what is in the widget each time you run live-view button
        # exposure_time = 2000.0 
        exposure_time = float(self.getPropertyValue('exposure'))
        pixel_format = 'Mono8'
        frame_rate_enable = True
        # Could not implement it by query. Max frame rate does not query.
        frame_rate = 45.0 # <45 Hz at full frame size
        buffer_mode = "NewestOnly"

        parameter_names = {'streampacketsize', 'trigger_source', 'trigger_mode', 'exposureauto', 'exposure', 'pixel_format', 'acqframerateenable', 'acqframerate','buffer_mode'}

        dic_parameters = {'streampacketsize':packet_size, 'trigger_source':trigger_source, 'trigger_mode':trigger_mode, 'exposureauto':exposure_auto, 'exposure':exposure_time, 'pixel_format':pixel_format, 'acqframerateenable':frame_rate_enable, 'acqframerate':frame_rate, 'buffer_mode':buffer_mode}

        for parameter_name in parameter_names:
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

    
    def grabFrameSet(self, buffer_size):
        # buffer_size = image number pulled from a cam
        
        buffer_type = "Mono16"
        # print(f"---Buffer gra --- on {self.device}")
        buffer_set = self.device.get_buffer(buffer_size) 
        # buffer = self.device.get_buffer()
        # print(self.device)
        """
        Copy buffer and requeue to avoid running out of buffers
        """
        items = []
        
        for buffer in buffer_set:        
            items.append(BufferFactory.copy(buffer))
            self.device.requeue_buffer(buffer)
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
