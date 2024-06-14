from .PositionerManager import PositionerManager

from ctypes import WinDLL, create_string_buffer

class MockSDKPriorDLL(PositionerManager):
    """ PositionerManager for mock positioner used for repeating measurements and/or timelapses.

    Manager properties:

    None
    """

    def __init__(self, positionerInfo, name, **lowLevelManagers):

        if len(positionerInfo.axes) != 2:
            raise RuntimeError(f'{self.__class__.__name__} only supports both XY axes,'
                               f' {len(positionerInfo.axes)} provided.')
                               
        super().__init__(positionerInfo, name, initialPosition={
            axis: 0 for axis in positionerInfo.axes
        })
        
        self.positionerInfo = positionerInfo

    def PriorScientificSDK_Initialise(self):
        return 0

    def PriorScientificSDK_OpenNewSession(self, position):
        return 0

    def PriorScientificSDK_cmd(self, sessionID, msg_encoded_in_buffer, rx):
        msg = msg_encoded_in_buffer.value.decode()
        if msg == "controller.stage.position.get":
            value_x = self._position['X']
            value_y = self._position['Y']
            value_out = str(value_x)+","+str(value_y)
            ret = 0
        if "controller.stage.goto-position" in msg:
            ret = 0
            value_out = "0,0"
        if "controller.stage.speed.get" in msg:
            ret = 0
            value_out = "1"
        if "controller.stage.speed.set" in msg:
            ret = 0
            value_out = int(float(msg.split(" ")[1]))
        return ret, value_out 
        


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
