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
        self._commChannel.sigModuleSettings.connect(self.loadSettings)
        self._commChannel.sigSetForPSF.connect(self.editForPSF)
        # self._commChannel.sigCalcZStepArray.connect(self.calcZStepArray)

    def editForPSF(self, start):
        if start:
            self.initCenter = self._widget.checkbox_zStackCenter.isChecked()
            self.initEnabled = self._widget.checkbox_zStack.isChecked()
            self._widget.checkbox_zStackCenter.setChecked(True)
            self._widget.checkbox_zStack.setChecked(True)
        if not start:
            self._widget.checkbox_zStackCenter.blockSignals(True)
            self._widget.checkbox_zStackCenter.setChecked(self.initCenter)
            self._widget.checkbox_zStackCenter.blockSignals(False)
            self._widget.checkbox_zStack.blockSignals(True)
            self._widget.checkbox_zStack.setChecked(self.initEnabled)
            self._widget.checkbox_zStack.blockSignals(False)


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
        try: 
            stepDist = float(self._widget.zStepDistance_textedit.text())
        except ValueError:
            return
        try:
            totalDist = float(self._widget.totalZ_textedit.text())
        except ValueError:
            return
        
        zScanDir = self._widget.zStackScanDir.currentText()
        currentZ = float(self.sharedAttrs['Positioner','Z','Z','Position'])
        centerCheckbox = self._widget.checkbox_zStackCenter.checkState()

        if zScanDir == 'Up':
            zScanSign = -1
        elif zScanDir == 'Down':
            zScanSign = 1
        try:
            floorSteps = math.floor(totalDist / stepDist)
        except ZeroDivisionError:
            return
        zScanList = []

        if centerCheckbox == 2:

            startZ = currentZ - zScanSign * float(self._widget.zOffset_textedit.text())
            zScanList.append(round(startZ,1))

            for i in range(floorSteps):
                zScanList.append(round(startZ+zScanSign*((i+1)*stepDist),1))
            self._widget.numSteps_textedit.setText(str(len(zScanList)))

        else:
            zScanList.append(round(currentZ,1))

            for i in range(floorSteps):
                zScanList.append(round(currentZ+zScanSign*((i+1)*stepDist),1))
            self._widget.numSteps_textedit.setText(str(len(zScanList)))




        self._commChannel.sigZScanList.emit(zScanList, currentZ)

        

        return zScanList


    def loadSettings(self, moduleDict):
        try:
            loadBool = moduleDict['zstack']
        except KeyError:
            loadBool = 0
        if loadBool:
            params = self._commChannel.loadedSettings['Z-Stack Settings']

            for i in range(len(self._widget.elementList)):
                if self._widget.elementList[i]._type == 'str':
                    self._widget.elementList[i].setText(params[self._widget.elementList[i]._name])
                elif self._widget.elementList[i]._type == 'int':
                    self._widget.elementList[i].setChecked(int(params[self._widget.elementList[i]._name]))
                elif self._widget.elementList[i]._type == 'combostr':
                    self._widget.elementList[i].setCurrentText(params[self._widget.elementList[i]._name])

        self._widget.floorTotalZ() #Recalc 'Start Offset' after entering new values.





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