from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import APIExport
import numpy as np
from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcommon.framework import Signal
import threading
import ctypes
from napari.experimental import link_layers

class ROIController(ImConWidgetController):


    # sigTilingPositions = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self._widget.sigROIInfoChanged.connect(self.valueChanged)
        self.sharedAttrs = self._commChannel.sharedAttrs._data
        self._widget.sigAddROI.connect(self.addPositionToROIList)
        self._widget.sigReplaceROI.connect(self.replaceROI)
        self._widget.gotoButton.clicked.connect(self.gotoSelectedROI)
        # self._widget.initSharedAttributes()

        for key in self._master.positionersManager._subManagers:
            if self._master.positionersManager._subManagers[key].axes == ['Z']:
                self.positioner = self._master.positionersManager._subManagers[key]
            elif self._master.positionersManager._subManagers[key].axes[0] == ['X'] or ['Y']:
                self.positionerXY = self._master.positionersManager._subManagers[key]


        
    def replaceROI(self):
        currentIndex = self._widget.ROIList.currentRow()
        if currentIndex > -1:
            self._widget.ROIList.takeItem(currentIndex)
            currentX = self.sharedAttrs['Positioner','XY','X','Position']
            currentY = self.sharedAttrs['Positioner','XY','Y','Position']
            currentZ = self.sharedAttrs['Positioner','Z','Z','Position']
            currentString = self.formatCurrentROIData(currentX, currentY, currentZ)
            self._widget.ROIList.insertItem(currentIndex, currentString)

    def gotoSelectedROI(self):
        currentName = self._widget.getCurrentName()
        if currentName != None:
            currentX, currentY, currentZ = self.parseCurrentSelection(currentName)
            self.positionerXY.setPositionXY(currentX, currentY)
            self.positioner.setPosition(currentZ, 'Z')
            self._commChannel.sigUpdateZPosition.emit('Z','Z')
            self._commChannel.sigUpdateXYPosition.emit('XY','X')
            self._commChannel.sigUpdateXYPosition.emit('XY','Y')


    def addPositionToROIList(self):
        currentX = self.sharedAttrs['Positioner','XY','X','Position']
        currentY = self.sharedAttrs['Positioner','XY','Y','Position']
        currentZ = self.sharedAttrs['Positioner','Z','Z','Position']
        currentString = self.formatCurrentROIData(currentX, currentY, currentZ)
        self._widget.addROI(currentString)

    def formatCurrentROIData(self, currentX, currentY, currentZ):
        currentString = f'X:{currentX} | Y:{currentY} | Z:{currentZ}'
        return currentString
    
    def parseCurrentSelection(self, currentName):
        x ,y, z = currentName.split(' | ')
        currentX = float(x.split(':')[1])
        currentY = float(y.split(':')[1])
        currentZ = float(z.split(':')[1])
        return currentX, currentY, currentZ


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
