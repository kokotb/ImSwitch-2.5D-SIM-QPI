from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import APIExport
import numpy as np
from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcommon.framework import Signal
import threading
import ctypes
import math

class ZStackController(ImConWidgetController):



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self.sharedAttrs = self._commChannel.sharedAttrs._data
        self._widget.sigZStackInfoChanged.connect(self.valueChanged)
        self._widget.initZStackInfo()
        self._widget.sigZStackInfoChanged.connect(self.calcZStepArray)
        self._widget.runZStackToggle.connect(self.runZStackToggle)
        self._commChannel.sigSIMAcqToggled.connect(self._widget.toggleRunZStackEnabled)

    def runZStackToggle(self, state):
        if state == 0:
            self._widget.zStepDistance_textedit.setEnabled(False)
            self._widget.totalZ_textedit.setEnabled(False)
            self._widget.checkbox_zStackCenter.setEnabled(False)
            self._widget.zStackScanDir.setEnabled(False)

        if state == 2:
            self._widget.zStepDistance_textedit.setEnabled(True)
            self._widget.totalZ_textedit.setEnabled(True)
            self._widget.checkbox_zStackCenter.setEnabled(True)
            self._widget.zStackScanDir.setEnabled(True)





    def calcZStepArray(self):

        stepDist = float(self._widget.zStepDistance_textedit.text())
        totalDist = float(self._widget.totalZ_textedit.text())
        zScanDir = self._widget.zStackScanDir.currentText()
        currentZ = self.sharedAttrs['Positioner','Z','Z','Position'] #stored as float in sharedattrs
        centerCheckbox = self._widget.checkbox_zStackCenter.checkState()

        if zScanDir == 'Up':
            zScanSign = -1
        elif zScanDir == 'Down':
            zScanSign = 1

        floorSteps = math.floor(totalDist / stepDist)
        zScanList = []

        if centerCheckbox == 2:

            startZ = currentZ - zScanSign * float(self._widget.zOffset_textedit.text())
            zScanList.append(round(startZ,1))

            for i in range(floorSteps):
                zScanList.append(round(startZ+zScanSign*((i+1)*stepDist),1))

        else:
            zScanList.append(round(currentZ,1))

            for i in range(floorSteps):
                zScanList.append(round(currentZ+zScanSign*((i+1)*stepDist),1))




        self._commChannel.sigZScanList.emit(zScanList, currentZ)

        return zScanList








    def valueChanged(self, attrCategory, parameterName, value):
        self.setSharedAttr(attrCategory, parameterName, value)

    def setSharedAttr(self, attrCategory, parameterName, value):
        """Sending attribute to shared attributes

        Args:
            parameterName (str): name of a parameter passed from wdiget
            attr (_type_): type of a attribute (value, enabled, ...)    
            value (_type_): value of the parameter read from wdiget
        """
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