from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import APIExport
import numpy as np
from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcommon.framework import Signal
import threading
import ctypes

class TilingController(ImConWidgetController):


    # sigTilingPositions = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        # self._widget.sigSaveFocus.connect(self.saveFocus)
        self._widget.sigTilingInfoChanged.connect(self.valueChanged)
        # self._image = []
        # self._skipOrNot = None
        self._widget.initTilingInfo()

        for key in self._master.positionersManager._subManagers:
            if self._master.positionersManager._subManagers[key].axes[0] == ['X'] or ['Y']:
                self.positionerXY = self._master.positionersManager._subManagers[key]

        self._commChannel.sigTileImage.connect(self.mainWFTileImageThread)
        self.numTiledImages = 0


    
    
    def mainWFTileImage(self, im, coords, name):
        
        im = im[np.newaxis,:,:]
        if not self.windowExists():
            self.layerSet = set()
            self._widget.createTilingWindow()
            xSteps = int(self._widget.numGridX_textedit.text())
            ySteps = int(self._widget.numGridY_textedit.text())
            totalSteps = xSteps * ySteps

            if len(self._widget.tilingView.layers) != 0:
                for layer in self._widget.tilingView.layers:
                    self._widget.tilingView.layers.remove(layer)
            self.originRealCoords = coords
            self.addTileImageToCanvas(im, [0,0,0], name=name)
            self.layerSet.add(name)
        else:

            
            if name not in self.layerSet:
                currentRealCoords = coords
                currentPixCoords = self.convertRealToPix(currentRealCoords)
                self.addTileImageToCanvas(im, currentPixCoords, name)
                self.layerSet.add(name)
            else:
                self._widget.tilingView.layers[name].data = np.concatenate((im.data,self._widget.tilingView.layers[name].data),axis=0)













    def mainWFTileImageThread(self, im , coords, name):
        threading.Thread(target=self.mainWFTileImage(im, coords, name), args=(im, coords,name, ), daemon=True).start()



    def addTileImageToCanvas(self, im, currentPixCoords, name):
        self._widget.tilingView.add_image(im, translate = currentPixCoords, name=name)


    def convertRealToPix(self, currentRealCoords):
        xoffset = 0 - self.originRealCoords[0]
        yoffset = 0 - self.originRealCoords[1]
        scale = 1/0.1233 #pixels per micron

        
        currentXPixCoords = (currentRealCoords[0] + xoffset) * -scale
        currentYPixCoords = (currentRealCoords[1] + yoffset) * scale
        currentPixCoords = [currentYPixCoords,currentXPixCoords] #imswitch seems to use [Y,X] coordinates
        return currentPixCoords
 

    def windowExists(self):

        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        
        titles = []
        def foreach_window(hwnd, lParam):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                titles.append(buff.value)
            return True
        EnumWindows(EnumWindowsProc(foreach_window), 0)
        
        return ('Tiling Preview' in titles)


    
        





















    # def saveFocus(self, bool):
    #     self._skipOrNot = bool
    #     # self._commChannel.sigSaveFocus.emit()

    # @APIExport()
    # def setTileLabel(self, label) -> None:
    #     self._widget.setLabel(label)

    # @APIExport()
    # def getSkipOrNot(self) -> bool:
    #     return self._skipOrNot


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
