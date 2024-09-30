from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import APIExport
import numpy as np
from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcommon.framework import Signal


class TilingController(ImConWidgetController):
    """ Linked to WatcherWidget. """

    # sigTilingPositions = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        # self._widget.sigSaveFocus.connect(self.saveFocus)
        self._widget.sigTilingInfoChanged.connect(self.valueChanged)
        # self._image = []
        # self._skipOrNot = None
        self._widget.initTilingInfo()

        # self.num_grid_x = self._widget.numGridX_textedit.text()

        # self.num_grid_y = self._widget.numGridY_textedit.text()
        
        # self.overlap = self._widget.overlap_textedit.text()

        for key in self._master.positionersManager._subManagers:
            if self._master.positionersManager._subManagers[key].axes[0] == ['X'] or ['Y']:
                self.positionerXY = self._master.positionersManager._subManagers[key]





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

    def getTilingParams(self):
        self.num_grid_x = self._widget.numGridX_textedit.text()
        self.num_grid_y = self._widget.numGridY_textedit.text()
        self.overlap = self._widget.overlap_textedit.text()



    # def saveFocus(self, bool):
    #     self._skipOrNot = bool
    #     # self._commChannel.sigSaveFocus.emit()

    # @APIExport()
    # def setTileLabel(self, label) -> None:
    #     self._widget.setLabel(label)

    # @APIExport()
    # def getSkipOrNot(self) -> bool:
    #     return self._skipOrNot

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
