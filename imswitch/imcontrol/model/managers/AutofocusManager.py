import numpy as np
from PIL import Image
from scipy import signal as sg
# from imswitch.imcontrol.view.guitools.ViewSetupInfo import ViewSetupInfo as SetupInfo
from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger
import time
import os
import cv2


class AutofocusManager(SignalInterface):

    def __init__(self):
        super().__init__()
        self._logger = initLogger(self)

    def getXfromY(self, y):
        x = (y-self.y_int)/self.x_slp

        return x

    def getYfromX(self, x):
        y = (self.x_slp*x) + self.y_int

        return y

            

# Copyright (C) 2020-2024 ImSwitch developers
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
