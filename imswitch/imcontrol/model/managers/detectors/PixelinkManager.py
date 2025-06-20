import numpy as np
import time
from imswitch.imcommon.model import initLogger
from .DetectorManager import DetectorManager, DetectorAction, DetectorNumberParameter, DetectorListParameter
from ..ArduinoManager import ArduinoManager
from pixelinkWrapper import*
from imswitch.imcontrol.model.interfaces.PixelinkCamManager import PixelCam
from ctypes import*
import numpy
import cv2
import os

class PixelinkManager(DetectorManager):
    """ DetectorManager that deals with LUCID cameras and the   parameters for frame extraction from them.

    Manager properties:

    - ``cameraListIndex`` -- the camera's index in the TIS camera list (list
      indexing starts at 0); set this string to an invalid value, e.g. the
      string "mock" to load a mocker
    - ``tis`` -- dictionary of TIS camera properties
    """

    def __init__(self, detectorInfo, name, **_lowLevelManagers):
        PT_MONO = 1
        EXIT_SUCCESS = 0
        EXIT_FAILURE = 1
        self.__logger = initLogger(self, instanceName=name)
        # self.arduinoManager = ArduinoManager(self.__setupInfo.Arduino,**lowLevelManagers)
        self._camera = PixelCam
        ret = PxLApi.initialize(0) #serial number if not '0' for any valid cam
        if not PxLApi.apiSuccess(ret[0]):
            print("Error: Unable to initialize a camera")
            return EXIT_FAILURE
        self.hCamera = ret[1]
        
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
        fullShapeSensor = (1280 , 1024)
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
                         model=85, parameters=parameters, 
                         croppable=True, frameStart=frameStart, offsetRelative=offsetRelative, 
                         frameStartGlobal=frameStartGlobal, fullShapeSensor=fullShapeSensor)
 
    @property
    def scale(self):
        return [1,1]

    def getLatestFrame(self, returnFrameNumber = False):
        # print(self._camera)
        if not self._adjustingParameters:
            self.__image = self._camera.grabFrameAF()
            # print(self.__image)
        
        if returnFrameNumber:
            frameNumber = 4 # Arbitrary number set for testing.
            return self.__image, frameNumber
        else:    
            return self.__image

    def setParameter(self, name, value):
        """Sets a parameter value and returns the value.
        If the parameter doesn't exist, i.e. the parameters field doesn't
        contain a key with the specified parameter name, an error will be
        raised."""        
        def trigToggle():
            self._camera.setPropertyValue(name, value, False)
        super().setParameter(name, value)

        if name not in self._DetectorManager__parameters:
            raise AttributeError(f'Non-existent parameter "{name}" specified')
        if name == 'TriggerMode':
            self._performSafeCameraAction(trigToggle)
            value = self._camera.getPropertyValue(name)
        else:
            value = self._camera.setPropertyValue(name, value)
        return value

    def getParameter(self, name):
        """Gets a parameter value and returns the value.
        If the parameter doesn't exist, i.e. the parameters field doesn't
        contain a key with the specified parameter name, an error will be
        raised."""

        if name not in self._parameters:
            raise AttributeError(f'Non-existent parameter "{name}" specified')

        value = self._camera.getPropertyValue(name)
        return value

    def setBinning(self, binning):
        super().setBinning(binning)

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

    def stopAcquisitionForROIChange(self):
        self._running = False
        self._camera.suspend_live()

    @property
    def pixelSizeUm(self):
        return [1, 1, 1]

    def crop(self, hpos, vpos, hsize, vsize):
        # def cropAction():
        #     self._camera.setROI(hpos, vpos, hsize, vsize)
            

        # self._performSafeCameraAction(cropAction)

        # # This should be the only place where self.frameStart is changed
        # self._frameStart = (self._camera.getROIValue("OffsetX"), self._camera.getROIValue("OffsetY"))
        # # Only place self.shapes is changed
        # self._shape = (self._camera.getROIValue("Width"),self._camera.getROIValue("Height"))

        pass

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


    def grabFrameAF(self):
        def drawRect(event, x,y,flag,params):
            top = y - 50
            left = x - 50
            right = x + 50
            bottom = y + 50
            self.xsize = 100
            self.ysize = 100
            self.top = top
            self.left = left
            

            if (event == cv2.EVENT_LBUTTONDOWN) and self.oneRect == False:
                cv2.rectangle(npFormatedImage, (left, top), (right, bottom), (255, 0, 0), 2)
                self.oneRect = True
        
        self.oneRect = False
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
        cv2.setMouseCallback('AF Preview', drawRect)
        while True:
            cv2.imshow('AF Preview', npFormatedImage)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        cv2.destroyAllWindows()
        print(self.left,self.top,self.xsize,self.ysize)
        return self.left,self.top,self.xsize,self.ysize
    
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
        ret = PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.STOP)
        assert PxLApi.apiSuccess(ret[0])
        return npFormatedImage


    def openPropertiesDialog(self):
        self._camera.openPropertiesGUI()

    
    def close(self):
        # ret = PxLApi.setStreamState(self.hCamera, PxLApi.StreamState.STOP)
        # assert PxLApi.apiSuccess(ret[0])
        ret = PxLApi.uninitialize(self.hCamera)
        assert PxLApi.apiSuccess(ret[0])
        self.__logger.info(f'Shutting down camera, model: {self._camera.model}')

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
