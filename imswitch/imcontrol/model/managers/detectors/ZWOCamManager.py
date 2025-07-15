from imswitch.imcommon.model import initLogger
from .DetectorManager import DetectorManager, DetectorAction, DetectorNumberParameter, DetectorListParameter
from ctypes import*
import ctypes
import numpy as np
import time

import cv2
import os

class ASI_CAMERA_INFO(ctypes.Structure):
    _fields_ = [
        ("Name", ctypes.c_char * 64),
        ("CameraID", ctypes.c_int),
        ("MaxHeight", ctypes.c_int),
        ("MaxWidth", ctypes.c_int),
        ("IsColorCam", ctypes.c_int),
        ("BayerPattern", ctypes.c_int),
        ("SupportedBins", ctypes.c_int * 16),
        ("SupportedVideoFormat", ctypes.c_int * 8),
        ("MechanicalShutter", ctypes.c_int),
        ("ST4Port", ctypes.c_int),
        ("IsCoolerCam", ctypes.c_int),
        ("IsUSB3Host", ctypes.c_int),
        ("IsUSB3Camera", ctypes.c_int),
        ("ElecPerADU", ctypes.c_float),
        ("BitDepth", ctypes.c_int),
        ("IsTriggerCam", ctypes.c_int),
        ("Unused", ctypes.c_char * 16)
    ]

class ZWOCamManager(DetectorManager):
    """ DetectorManager that deals with LUCID cameras and the   parameters for frame extraction from them.

    Manager properties:

    - ``cameraListIndex`` -- the camera's index in the TIS camera list (list
      indexing starts at 0); set this string to an invalid value, e.g. the
      string "mock" to load a mocker
    - ``tis`` -- dictionary of TIS camera properties
    """

    def __init__(self, detectorInfo, name, **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)
        # self.arduinoManager = ArduinoManager(self.__setupInfo.Arduino,**lowLevelManagers)
        # Load the DLL
        path = R"dlls\ZWOASICam\lib\x64\ASICamera2.dll"
        self._camera = ctypes.cdll.LoadLibrary(path)  # Adjust path

        # Define constants
        self.ASI_EXPOSURE = 0
        self.ASI_GAIN = 1
        self.ASI_BRIGHTNESS = 2
        self.ASI_START_CAPTURE_TIMEOUT = 2000
        self.ASI_FALSE = 0
        self.ASI_TRUE = 1
        self.ASI_IMG_RAW8 = 0  # Grayscale 8-bit

        # Step 1: Get number of connected cameras
        num_cameras = self._camera.ASIGetNumOfConnectedCameras()
        if num_cameras < 1:
            raise RuntimeError("No ASI cameras found")
        
        # Step 2: Get camera info
        self.cam_info = ASI_CAMERA_INFO()
        self._camera.ASIGetCameraProperty(ctypes.byref(self.cam_info), 0)

        # Step 3: Open and initialize camera
        self.cam_id = self.cam_info.CameraID
        self._camera.ASIOpenCamera(self.cam_id)
        self._camera.ASIInitCamera(self.cam_id)


        # Step 4: Set controls
        # self._camera.ASISetControlValue(self.cam_id, self.ASI_EXPOSURE, 300, self.ASI_FALSE)  # 1 sec exposure
        # self._camera.ASISetControlValue(self.cam_id, self.ASI_GAIN, 0, self.ASI_FALSE)
        # self._camera.ASISetControlValue(self.cam_id, self.ASI_BRIGHTNESS, 1, self.ASI_FALSE)

        # Step 5: Set ROI format (full size, binning 1, RAW8)
        self._camera.ASISetROIFormat(self.cam_id, self.cam_info.MaxWidth, self.cam_info.MaxHeight, 1, self.ASI_IMG_RAW8)
        
        self._running = False
        self._adjustingParameters = False
        self._camSet = False #CTNOTE What exactly does camSet do?

        #Names and values from config file
        self.setupInfo = detectorInfo.managerProperties['camProperties']
        self.roiInfo = detectorInfo.managerProperties['ROI']
        
        #Properties that will not EVER change, but are also not defult

        #Read all camProperties in config file and set on cams. This operation is only for properties, not ROIs
        # for propertyName, propertyValue in self.setupInfo.items():
        #     self._camera.setPropertyValue(propertyName, propertyValue)

        
        # fullShape = (self.setupInfo['sensor_width'] ,self.setupInfo['sensor_height'])
        fullShape = (self.roiInfo['Width'] ,self.roiInfo['Height'])
        fullShapeSensor = (1936 , 1096)
        frameStartGlobal = (detectorInfo.managerProperties['x0_global'], detectorInfo.managerProperties['y0_global'])
        frameStart = (self.roiInfo['OffsetX'], self.roiInfo['OffsetY'])
        # offsetRelative = (self.setupInfo['x0_global'], self.setupInfo['y0_global'])
        offsetRelative = (0,0)
        
        # These parameters are from config file, used to populate the detector settings panel.
        # Initialization parameters
        #CTNOTE: Possible conflicts if not able to be successfully set on cam (cam and config file would be different at that point).
        exposure_init = self.setupInfo['ExposureTime']
        gain_init = self.setupInfo['Gain']
        gamma_init = self.setupInfo['Gamma']
        # exposureauto_init = self.setupInfo['ExposureAuto']
        trigmode_init = self.setupInfo['TriggerMode']
        #trigsource_init not needed yet. All triggers on Line0. QPI may change this.

        parameters = {
            'ExposureTime': DetectorNumberParameter(group='Acq. Control', value=exposure_init, valueUnits='us',
                                                editable=True),
            'Gain': DetectorNumberParameter(group='Analog Control', value=gain_init, valueUnits='arb.u.',
                                            editable=True),
            'Gamma': DetectorNumberParameter(group='Analog Control', value=gamma_init, valueUnits='arb.u.',
                                                  editable=True),
            # 'ExposureAuto': DetectorListParameter(group='Acq. Control', value=exposureauto_init, options=['Off','Once','Continuous'],
            #                                     editable=False),
            'TriggerMode': DetectorListParameter(group='Acq. Control', value=trigmode_init, options=['Off','On'],
                                                editable=True)
                                                         
        }

        ## No actions connected yet. If you want to enable, need to add actions=actions to super().__init__ below.
        # actions = {
        #     'More properties': DetectorAction(group='Misc',
        #                                       func=self._camera.openPropertiesGUI)
        # }

        super().__init__(detectorInfo, name, fullShape=fullShape, supportedBinnings=[1],
                         model=21, parameters=parameters, 
                         croppable=True, frameStart=frameStart, offsetRelative=offsetRelative, 
                         frameStartGlobal=frameStartGlobal, fullShapeSensor=fullShapeSensor)
 
    @property
    def scale(self):
        return [1,1]

    def getLatestFrame(self, returnFrameNumber = False):
        pass
        

        
    # def getExposure(self):
    #     ret = PxLApi.getFeature(self.hCamera, PxLApi.FeatureId.EXPOSURE)
    #     if not(PxLApi.apiSuccess(ret[0])):
    #         print("!! Attempt to get exposure returned %i!" % ret[0])
    #         return
    #     params = ret[2]
    #     exposureInSec = params[0]
    #     return exposureInSec
    
    # def setExposure(self, exposureInSec):
    #     ret = PxLApi.setFeature(self.hCamera, PxLApi.FeatureId.EXPOSURE, PxLApi.FeatureFlags.MANUAL, [exposureInSec])
    #     if (not PxLApi.apiSuccess(ret[0])) and (not self.api_range_error(ret[0])):
    #         print("!! Attempt to set exposure returned %i!" % ret[0])
    #         return
    #     newExposure = self.getExposure()
    #     newExposureInMS = newExposure * 1000
    #     self.__logger.info(f"Exposure set to {newExposureInMS} ms on AF cam")

    #     return exposureInSec
    
    # def getROI(self):
    #     ret = PxLApi.getFeature (self.hCamera, PxLApi.FeatureId.ROI)
    #     if PxLApi.apiSuccess(ret[0]):
    #         flags = ret[1]
    #         updatedParams = ret[2]
    #         width = updatedParams[PxLApi.RoiParams.WIDTH]
    #         height = updatedParams[PxLApi.RoiParams.HEIGHT]
    #         left = updatedParams[PxLApi.RoiParams.LEFT]
    #         top = updatedParams[PxLApi.RoiParams.TOP]
    #     return [left, top, width, height]

    def setROI(self, params): #Params should be lsit of [left, top, width, height]
        
        self.left = params[0]
        self.top = params[1]
        self.width = params[2]
        self.height = params[3]

        print(f'ROI:{self.left}, {self.top}, {self.width}, {self.height}')
    

    # def setParameter(self, name, value):
    #     """Sets a parameter value and returns the value.
    #     If the parameter doesn't exist, i.e. the parameters field doesn't
    #     contain a key with the specified parameter name, an error will be
    #     raised."""        
    #     def trigToggle():
    #         self._camera.setPropertyValue(name, value, False)
    #     super().setParameter(name, value)

    #     if name not in self._DetectorManager__parameters:
    #         raise AttributeError(f'Non-existent parameter "{name}" specified')
    #     if name == 'TriggerMode':
    #         self._performSafeCameraAction(trigToggle)
    #         value = self._camera.getPropertyValue(name)
    #     else:
    #         value = self._camera.setPropertyValue(name, value)
    #     return value

    # def getParameter(self, name):
    #     """Gets a parameter value and returns the value.
    #     If the parameter doesn't exist, i.e. the parameters field doesn't
    #     contain a key with the specified parameter name, an error will be
    #     raised."""

    #     if name not in self._parameters:
    #         raise AttributeError(f'Non-existent parameter "{name}" specified')

    #     value = self._camera.getPropertyValue(name)
    #     return value

    # def setBinning(self, binning):
    #     super().setBinning(binning)

    def getChunk(self):
        return self._camera.grabFrame()[np.newaxis, :, :]

    def flushBuffers(self):
        pass

    def startAcquisition(self):
        if not self._running:
            self._camera.setCamForLiveView()
            self._camSet = False #why is camset false?
            self._camera.start_live()
            # print(self._camera)
            self._running = True

    def stopAcquisition(self):
        if self._running:
            self._running = False
            self._camSet = False
            self._camera.suspend_live()

    def stopAcquisitionSIM(self):
        if self._running:
            self._running = False
            self._camSet = False
            self._camera.suspend_live()

    # def stopAcquisitionForROIChange(self):
    #     self._running = False
    #     self._camera.suspend_live()

    @property
    def pixelSizeUm(self):
        return [1, 1, 1]

    def crop(self, hpos, vpos, hsize, vsize):
        def cropAction():
            self._camera.setROI(hpos, vpos, hsize, vsize)
            

        self._performSafeCameraAction(cropAction)

        # This should be the only place where self.frameStart is changed
        self._frameStart = (self._camera.getROIValue("OffsetX"), self._camera.getROIValue("OffsetY"))
        # Only place self.shapes is changed
        self._shape = (self._camera.getROIValue("Width"),self._camera.getROIValue("Height"))


    def _performSafeCameraAction(self, function):
        """ This method is used to change those camera properties that need
        the camera to be idle to be able to be adjusted.
        """
        self._adjustingParameters = True
        wasrunning = self._running
        if wasrunning:
            self.stopAcquisitionForROIChange()
        function()
        if wasrunning:
            self.resumeAcquisition()
        self._adjustingParameters = False


    # # def grabFrameAF(self):
    # #     def drawRect(event, x,y,flag,params):
    # #         top = y - 50
    # #         left = x - 50
    # #         right = x + 50
    # #         bottom = y + 50
    # #         self.xsize = 100
    # #         self.ysize = 100
    # #         self.top = top
    # #         self.left = left
            

    # #         if (event == cv2.EVENT_LBUTTONDOWN) and self.oneRect == False:
    # #             cv2.rectangle(npFormatedImage, (left, top), (right, bottom), (255, 0, 0), 2)
    # #             self.oneRect = True
        
    # #     self.oneRect = False
    # #     rawFrame = create_string_buffer(1024 * 1280 * 2)
    # #     ret = PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.START)
    # #     ret = PxLApi.getNextFrame(self.hCamera, rawFrame)
    # #     frameDesc = ret[1]
    # #     ret = PxLApi.formatImage(rawFrame, frameDesc, PxLApi.ImageFormat.RAW_MONO8)
    # #     formatedImage = ret[1]
    # #     npFormatedImage = numpy.full_like(formatedImage, formatedImage, order="C")
    # #     npFormatedImage.dtype = numpy.uint8
    # #     imageHeight = int(frameDesc.Roi.fHeight)
    # #     imageWidth = int(frameDesc.Roi.fWidth)
    # #     newShape = (imageHeight, imageWidth)
    # #     npFormatedImage = numpy.reshape(npFormatedImage, newShape)
    # #     cv2.namedWindow('AF Preview')
    # #     cv2.setMouseCallback('AF Preview', drawRect)
    # #     while True:
    # #         cv2.imshow('AF Preview', npFormatedImage)
    # #         if cv2.waitKey(1) & 0xFF == ord("q"):
    # #             break
    # #     cv2.destroyAllWindows()
    # #     print(self.left,self.top,self.xsize,self.ysize)
    # #     return self.left,self.top,self.xsize,self.ysize
    
    def grabFrameOnly(self):
        # def drawRect(event, x,y,flag,params):
        #     top = y - 50
        #     left = x - 50
        #     right = x + 50
        #     bottom = y + 50
        #     self.xsize = 100
        #     self.ysize = 100
        #     self.top = top
        #     self.left = left
            

        #     if (event == cv2.EVENT_LBUTTONDOWN) and self.oneRect == False:
        #         cv2.rectangle(npFormatedImage, (left, top), (right, bottom), (255, 0, 0), 2)
        #         self.oneRect = True
        
        # self.oneRect = False

        self._camera.ASIStartExposure(self.cam_id, self.ASI_FALSE)
        status = ctypes.c_int()
        while True:
            self._camera.ASIGetExpStatus(self.cam_id, ctypes.byref(status))
            if status.value == 2:  # ASI_EXP_SUCCESS
                break
            # time.sleep(0.001)
        buffer_size = self.cam_info.MaxWidth * self.cam_info.MaxHeight
        img_buffer = (ctypes.c_ubyte * buffer_size)()
        self._camera.ASIGetDataAfterExp(self.cam_id, ctypes.byref(img_buffer), buffer_size)
        image = np.frombuffer(img_buffer, dtype=np.uint8)
        image = image.reshape((self.cam_info.MaxHeight, self.cam_info.MaxWidth))

        # rawFrame = create_string_buffer(1024 * 1280 * 2)
        # ret = PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.START)
        # ret = PxLApi.getNextFrame(self.hCamera, rawFrame)
        # frameDesc = ret[1]
        # ret = PxLApi.formatImage(rawFrame, frameDesc, PxLApi.ImageFormat.RAW_MONO8)
        # formatedImage = ret[1]
        # npFormatedImage = numpy.full_like(formatedImage, formatedImage, order="C")
        # npFormatedImage.dtype = numpy.uint8
        # imageHeight = int(frameDesc.Roi.fHeight)
        # imageWidth = int(frameDesc.Roi.fWidth)
        # newShape = (imageHeight, imageWidth)
        # npFormatedImage = numpy.reshape(npFormatedImage, newShape)
        # ret = PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.STOP)
        # assert PxLApi.apiSuccess(ret[0])
        return image


    # def openPropertiesDialog(self):
    #     self._camera.openPropertiesGUI()

    
    # def close(self):
    #     # ret = PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.STOP)
    #     # assert PxLApi.apiSuccess(ret[0])
    #     ret = PxLApi.uninitialize(self.hCamera)
    #     assert PxLApi.apiSuccess(ret[0])
    #     self.__logger.info(f'Shutting down camera, model: {self._camera.model}')

    def setOffsetRelative(self, value):
        self._offsetRelative = value


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
