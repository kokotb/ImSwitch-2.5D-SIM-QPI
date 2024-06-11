from ctypes import WinDLL, create_string_buffer
import os
import sys
from imswitch.imcommon.model import initLogger

from .PositionerManager import PositionerManager

# Load SDK library - this is hardcoded - need to generalize that
path = "D:\\Documents\\4 - software\\python-scripting\\2p5D-SIM\\PriorSDK\\x64\\PriorScientificSDK.dll"
if os.path.exists(path):
    SDKPrior = WinDLL(path)
else:
    raise RuntimeError("DLL could not be loaded.")

class PriorStageManager(PositionerManager):
    """ Direct communication with Prior Stage using Prior SDK. """

    def __init__(self, positionerInfo, name, *args, **lowLevelManagers):
        if len(positionerInfo.axes) != 1:
            raise RuntimeError(f'{self.__class__.__name__} only supports one axis,'
                               f' {len(positionerInfo.axes)} provided.')

        super().__init__(positionerInfo, name, initialPosition={
            axis: 0 for axis in positionerInfo.axes
        })
        self.__logger = initLogger(self)

        self.positionerInfo = positionerInfo
        self.rx = create_string_buffer(1000)
        self.stage = self.initialize_stage()
        self.sessionID = self.connect_to_stage()
        self.check_connection()
        print(positionerInfo)
        
    # Functions to initialize stage
    def initialize_stage(self):
        stage = SDKPrior.PriorScientificSDK_Initialise()
        if stage:
            self.__logger.warning(f'Failed to initialize {stage}, loading mocker')
            sys.exit()
        else:
            print(f"Ok initialising {stage}")
            return stage
    
    def connect_to_stage(self):
        sessionID = SDKPrior.PriorScientificSDK_OpenNewSession()
        if sessionID < 0:
            print(f"Error getting sessionID {self.stage}")
        else:
            print(f"SessionID = {sessionID}")
            return sessionID
        
    def check_connection(self):
        ret = SDKPrior.PriorScientificSDK_cmd(
        self.sessionID, create_string_buffer(b"dll.apitest 33 goodresponse"), self.rx)
        print(f"api response {ret}, rx = {self.rx.value.decode()}")
        ret = SDKPrior.PriorScientificSDK_cmd(
        self.sessionID, create_string_buffer(b"dll.apitest -300 stillgoodresponse"), self.rx)
        print(f"api response {ret}, rx = {self.rx.value.decode()}")
    
    # Send messages to stage
    def query(self, msg):
        print(msg)
        ret = SDKPrior.PriorScientificSDK_cmd(
            self.sessionID, create_string_buffer(msg.encode()), self.rx
        )
        if ret:
            print(f"Api error {ret}")
        else:
            print(f"OK {self.rx.value.decode()}")

        # input("Press ENTER to continue...")
        return ret, self.rx.value.decode()
    
    # Re-do for Prior SDK that is connected to ImSwitch in PriorStageManager
    def move(self, value, _):
        
        if value == 0:
            return
        elif float(value) > 0:
            cmd = 'U {}'.format(value)
            # print(value)
        elif float(value) < 0:
            absvalue = abs(float(value))
            cmd = 'D {}'.format(absvalue)
            # print(value)
        self.query(cmd)

        self._position[self.axes[0]] = self._position[self.axes[0]] + value

    # def move(self, value, _):
    #     if value == 0:
    #         return
    #     elif float(value) > 0:
    #         cmd = 'MOVRX +' + str(round(float(value), 3))[0:6] + 'u'
    #     elif float(value) < 0:
    #         cmd = 'MOVRX -' + str(round(float(value), 3))[1:7] + 'u'
    #     self._rs232Manager.query(cmd)

    #     self._position[self.axes[0]] = self._position[self.axes[0]] + value

    def move_to_position(self, value):
        cmd = 'V {}'.format(value)
        self.query(cmd)
        self._position[self.axes[0]] = value
        print(value)

    
    def setPosition(self, value, _):
        cmd = 'V {}'.format(value)
        self.query(cmd)

        self._position[self.axes[0]] = value
        

    @property
    def position(self):
        _ = self.get_abs()
        return self._position

    def get_abs(self):
        cmd = 'PZ'
        reply = self.query(cmd)
        if reply is None:
            reply = self._position[self.axes[0]]
        else:
            # reply = float(reply.split(' ')[0])
            reply = reply
        self._position[self.axes[0]] = reply
        # print(reply)
        return reply


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
