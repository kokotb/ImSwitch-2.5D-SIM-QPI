import numpy as np

from imswitch.imcommon.model import initLogger
from .DetectorManager import DetectorManager, DetectorAction, DetectorNumberParameter, DetectorListParameter


class LUCIDManager(DetectorManager):
    """ DetectorManager that deals with LUCID cameras and the
    parameters for frame extraction from them.

    Manager properties:

    - ``cameraListIndex`` -- the camera's index in the TIS camera list (list
      indexing starts at 0); set this string to an invalid value, e.g. the
      string "mock" to load a mocker
    - ``tis`` -- dictionary of TIS camera properties
    """

    def __init__(self, detectorInfo, name, **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)

        self._camera = self._getTISObj(detectorInfo.managerProperties['cameraListIndex'])
        
        self._running = False
        self._adjustingParameters = False

        self.setupInfo = detectorInfo.managerProperties['lucid']
        
        # Get old properties to compare with new for setting of FOV
        properties_old = {}
        
        for propertyName, propertyValue in self.setupInfo.items():
            properties_old[propertyName] = self._camera.getPropertyValue(propertyName)
            # properties_new[propertyName] = propertyValue

        # Set cam parameters in righ order for image height and centerdeness
        hsize_set = self.setupInfo["image_height"]
        hsize_old = properties_old["image_height"]
        hpos_new = self.setupInfo["y0"]
        vsize_set = self.setupInfo["image_width"]
        vsize_old = properties_old["image_width"]
        vpos_new = self.setupInfo["x0"]
        if hsize_set < hsize_old:
            # Shrink first then move, if moving sets us of the cam at current image size, cam will
            # not accept that
            self._camera.setPropertyValue("image_height", hsize_set)
            self._camera.setPropertyValue("y0", hpos_new)
        else:
            # Move first then enlarge, if larger size is of the cam size at current location cam
            # will not accept that
            self._camera.setPropertyValue("y0", hpos_new)
            self._camera.setPropertyValue("image_height", hsize_set)
        # Do the same for the other axis
        if vsize_set < vsize_old:
            self._camera.setPropertyValue("image_width", vsize_set)
            self._camera.setPropertyValue("x0", vpos_new)
        else:
            self._camera.setPropertyValue("x0", vpos_new)
            self._camera.setPropertyValue("image_width", vsize_set)

        for propertyName, propertyValue in self.setupInfo.items():
            # TODO: Remove after develpement is finished
            # print(self._camera.getPropertyValue(propertyName))
            # print(f"{propertyName},{propertyValue}")
            self._camera.setPropertyValue(propertyName, propertyValue)

        
        # fullShape = (self.setupInfo['sensor_width'] ,self.setupInfo['sensor_height'])
        fullShape = (self.setupInfo['image_width'] ,self.setupInfo['image_height'])
        fullShapeSensor = (self.setupInfo['sensor_width'] ,self.setupInfo['sensor_height'])
        frameStartGlobal = (self.setupInfo['x0'], self.setupInfo['y0'])
        frameStart = (self.setupInfo['x0'], self.setupInfo['y0'])
        # offsetRelative = (self.setupInfo['x0_global'], self.setupInfo['y0_global'])
        offsetRelative = (0,0)
        self.globalOffset = (detectorInfo.managerProperties['x0_global'], detectorInfo.managerProperties['y0_global'])
        # FIXME: When doing actual full chip...Tink if we can implement this smartly
        # fullShape = (self._camera.getPropertyValue('sensor_width'),self._camera.getPropertyValue('sensor_height'))
        # offsets = (self.setupInfo['x0'], self.setupInfo['y0'])
        # self.crop(hpos=offsetRelative[1]+frameStart[1], vpos=offsetRelative[0]+frameStart[0], hsize=fullShape[1], vsize=fullShape[0])
        # FIXME: Remove this? It makes debug window very confusing.
        # Just crop, no moving of image on the sensor, do not know yet why this is needed
        # self.__logger.debug("Currently commented! Setting crop - it is not the same as final setting in the widget!")
        # self.crop(hpos=0, vpos=0, hsize=fullShape[1], vsize=fullShape[0])
        

## These parameters are used to populate the detector settings panel.
        parameters = {
            'exposure': DetectorNumberParameter(group='Acq. Control', value=2000, valueUnits='us',
                                                editable=True),
            'gain': DetectorNumberParameter(group='Analog Control', value=0, valueUnits='arb.u.',
                                            editable=True),
            'gamma': DetectorNumberParameter(group='Analog Control', value=1, valueUnits='arb.u.',
                                                  editable=True),
            'exposureauto': DetectorListParameter(group='Acq. Control', value='Off', options=['Off','Once','Continuous'],
                                                editable=True)                    
        }

        # Prepare actions
        actions = {
            'More properties': DetectorAction(group='Misc',
                                              func=self._camera.openPropertiesGUI)
        }

        super().__init__(detectorInfo, name, fullShape=fullShape, supportedBinnings=[1],
                         model=self._camera.model, parameters=parameters, actions=actions, croppable=True, frameStart=frameStart, offsetRelative=offsetRelative, frameStartGlobal=frameStartGlobal, fullShapeSensor=fullShapeSensor)
 
    @property
    def scale(self):
        return [1,1]

    def getLatestFrame(self, returnFrameNumber = False):
        # print(self._camera)
        if not self._adjustingParameters:
            self.__image = self._camera.grabFrame()
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

        super().setParameter(name, value)

        if name not in self._DetectorManager__parameters:
            raise AttributeError(f'Non-existent parameter "{name}" specified')

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
            
            self._camera.start_live()
            # print(self._camera)
            self._running = True

    def stopAcquisition(self):
        if self._running:
            self._running = False
            self._camera.suspend_live()

    def stopAcquisitionForROIChange(self):
        self._running = False
        self._camera.stop_live()
        
    def acquireSetNow(self):
        print("acquireSetNow")

    @property
    def pixelSizeUm(self):
        return [1, 1, 1]

    def crop(self, hpos, vpos, hsize, vsize):
        def cropAction():
            self._camera.setROI(hpos, vpos, hsize, vsize)

        self._performSafeCameraAction(cropAction)
        # TODO: unsure if frameStart is needed? Try without.
        # This should be the only place where self.frameStart is changed
        self._frameStart = (hpos, vpos)
        # Only place self.shapes is changed
        self._shape = (vsize,hsize)

    def _performSafeCameraAction(self, function):
        """ This method is used to change those camera properties that need
        the camera to be idle to be able to be adjusted.
        """
        self._adjustingParameters = True
        wasrunning = self._running
        self.stopAcquisitionForROIChange()
        function()
        if wasrunning:
            self.startAcquisition()
        self._adjustingParameters = False

    def openPropertiesDialog(self):
        self._camera.openPropertiesGUI()

    def _getTISObj(self, cameraId):
        try:
            from imswitch.imcontrol.model.interfaces.lucidcamera import CameraTIS

            camera = CameraTIS(cameraId)
            # print(camera)
        except Exception:
            self.__logger.warning(f'Failed to initialize TIS camera {cameraId}, loading mocker')
            from imswitch.imcontrol.model.interfaces.tiscamera_mock import MockCameraTIS
            camera = MockCameraTIS()
            print(camera)

        self.__logger.info(f'Initialized camera, serial ending: {camera.model[-2:]}')  #Prints "Initialized camera. serial ending...."
        return camera
    
    def close(self):
        self.__logger.info(f'Shutting down camera, model: {self._camera.model}')
        pass

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
