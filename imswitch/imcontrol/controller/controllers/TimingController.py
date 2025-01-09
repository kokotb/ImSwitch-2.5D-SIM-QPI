from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import APIExport
import numpy as np
from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcommon.framework import Signal
import threading
import ctypes

class TimingController(ImConWidgetController):


    # sigTilingPositions = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self._widget.sigTimingInfoChanged.connect(self.valueChanged)
        self._widget.sigTimingCheckChanged.connect(self.valueChanged)
        self.sharedAttrs = self._commChannel.sharedAttrs._data
        self._widget.populateUnitsList()
        self._widget.timingPeriod_textedit.setText("0")
        self._widget.timingDuration_textedit.setText("0")
        self._widget.tilingReps_textedit.setText("1")
        self._widget.sigTimingCheckChanged.emit('Timing Settings','Rep Checkbox', 0)
        self._widget.sigTimingCheckChanged.emit('Timing Settings','Duration Checkbox', 0)


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
