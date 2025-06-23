from ..basecontrollers import ImConWidgetController
import numpy as np
from imswitch.imcommon.model import initLogger
import os
import cv2
import tifffile as tif
import threading

import time

class AutofocusController(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self.sharedAttrs = self._commChannel.sharedAttrs._data
        # self._widget.sigAutofocusInfoChanged.connect(self.valueChanged)
        # self._widget.checkbox_Autofocus.stateChanged.connect(self.testFunc)
        self._widget.initValues()
        # self._commChannel.sigToggleAutofocus.connect(self.toggleAutofocusCheckbox)
        self._widget.openPreview.clicked.connect(self.openSetAFWindowThread)
        self._widget.AFWindow.roiReset.clicked.connect(self.resetROIOnCam)
        self._widget.AFWindow.roiSet.clicked.connect(self.setROIOnCam)
        self._widget.AFWindow.calCurve.clicked.connect(self.runCalCurve)
        self._widget.AFWindow.acqImgButton.clicked.connect(self.getOneFrameToSet)

        self.zPositioner = self._master.positionersManager._subManagers['Z']
        self.AFCam = self._master.detectorsManager._subManagers['AF Cam']


    def resetROIOnCam(self):
        self.AFCam.setROI([0,0,1280,1024])
        self.getOneFrameToSet()

    def setROIOnCam(self):
        try:
            wantedROI = self._widget.AFWindow.embeddedImage.lastClick
            self.AFCam.setROI(wantedROI)
            self.getOneFrameToSet()
        except AttributeError:
            self._logger.warning("ROI has not yet been selected. Please click the center of desired ROI.")

    def openSetAFWindowThread(self):
        threading.Thread(target=self._widget.openSetAFWindow(), args=(), daemon=True).start()

    def getOneFrameToSet(self):
        img = self.AFCam.grabFrameOnly()
        pixmapImg = self._widget.AFWindow.convert_ndarray_to_qpixmap(img)
        self._widget.AFWindow.embeddedImage.setPixmap(pixmapImg)

    def getOneFrame(self): 
        img = self.AFCam.grabFrameOnly()
        return img
    
    def runCalCurve(self):
        path = R'D:\SIM_Data\_Settings\AFImages'
        zList, currentZ = self.calcZRange()
        # zList = zList.reverse()
        for count, z in enumerate(zList):
            filename = f"{count:03}.tif"
            self.zPositioner.setPosition(zList[count], 'Z')
            time.sleep(0.001)
            img = self.getOneFrame()
            self.saveImageInBackground(img, path, filename)
        self.zPositioner.setPosition(currentZ, 'Z')
        print('AF stack saved.')




        

    def calcZRange(self):
        currentZ = self.zPositioner._position['Z']
        bottom = currentZ - 20
        top = currentZ + 20
        steps = 51
        zList = np.linspace(top, bottom, steps)
        return zList, currentZ


    
    def saveImageInBackground(self, image, path, filename):
        try:
            # self.folder = self._widget.getRecFolder()
            filename = os.path.join(path,filename) 
            image = np.array(image)
            tif.imwrite(filename, image, imagej=True)
            self._logger.debug("Saving AF image: " + filename)

        except  Exception as e:
            self._logger.error(e)
    

















    def valueChanged(self, attrCategory, parameterName, value):
        self.setSharedAttr(attrCategory, parameterName, value)

    def setSharedAttr(self, attrCategory, parameterName, value):
        """Sending attribute to shared attributes

        Args:
            parameterName (str): name of a parameter passed from wdiget
            attr (_type_): type of a attribute (value, enabled, ...)
            value (_type_): value of the parameter read from wdiget
        """
        # print(value)
        self.settingAttr = True
        try:
            self._commChannel.sharedAttrs[(attrCategory, parameterName)] = value
        finally:
            self.settingAttr = False

    


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
