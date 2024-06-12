from ctypes import WinDLL, create_string_buffer
import os
import sys
from imswitch.imcommon.model import initLogger

from .PositionerManager import PositionerManager

# Load SDK library - this is hardcoded - need to generalize that
imswitch_parent = "C:\\VSCode"
path = imswitch_parent+"\\ImSwitch-2.5D-SIM-QPI\\dlls\\PriorSDK\\x64\\PriorScientificSDK.dll"
if os.path.exists(path):
    SDKPrior = WinDLL(path)
else:
    raise RuntimeError("DLL could not be loaded.")


class PriorStageManager(PositionerManager):
    """ PositionerManager for control of a Piezoconcept Z-piezo through RS232
    communication.

    Manager properties:

    - ``rs232device`` -- name of the defined rs232 communication channel
      through which the communication should take place
    """

    def __init__(self, positionerInfo, name, *args, **lowLevelManagers):
        if len(positionerInfo.axes) > 2:
            raise RuntimeError(f'{self.__class__.__name__} only supports two axes,'
                               f' {len(positionerInfo.axes)} provided.')

        super().__init__(positionerInfo, name, initialPosition={
            axis: 0 for axis in positionerInfo.axes
        })
        self.__logger = initLogger(self)

        self.positionerInfo = positionerInfo
        self.port = positionerInfo.managerProperties['port']
        self.rx = create_string_buffer(1000)
        self.api = self.initialize_API()
        self.sessionID = self.open_session()
        self.check_connection_to_api()
        self.intialize_stage()
        self.check_axes()
        # Set intial values to match the widget
        # for axis in self.axes: 
        #     self.setPosition(self._position[axis], axis)
        print("PriorStageManager intialized.")



    # Functions to initialize stage
    def initialize_API(self):
        stage = SDKPrior.PriorScientificSDK_Initialise()
        if stage:
            self.__logger.warning(f'Failed to initialize {stage}, loading mocker')
            sys.exit()
        else:
            print(f"Ok initialising {stage}")
            return stage


    def open_session(self):
        sessionID = SDKPrior.PriorScientificSDK_OpenNewSession()
        if sessionID < 0:
            print(f"Error getting sessionID {self.api}")
        else:
            print(f"SessionID = {sessionID}")
            return sessionID


    def check_connection_to_api(self):
        ret = SDKPrior.PriorScientificSDK_cmd(
        self.sessionID, create_string_buffer(b"dll.apitest 33 goodresponse"), self.rx)
        print(f"api response {ret}, rx = {self.rx.value.decode()}")
        ret = SDKPrior.PriorScientificSDK_cmd(
        self.sessionID, create_string_buffer(b"dll.apitest -300 stillgoodresponse"), self.rx)
        print(f"api response {ret}, rx = {self.rx.value.decode()}")

    def check_axes(self):
        for axis in self.axes:
            if axis == 'X':
                pass
            elif axis == 'Y':
                pass
            else:
                print(f'{axis} is not an XY axis!')

    def intialize_stage(self):
        # Extracts the port number used for device initialization
        port = ''.join(filter(lambda i: i.isdigit(), self.port))
        msg = "controller.connect " + port
        self.query(msg)


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
    
    def get_position(self):
        response = self.query("controller.stage.position.get")
        position = response[1].split(",", 1)
        return position
    
    def move(self, dist, axis):
        self.setPosition(self._position[axis] + dist, axis)

    def setPosition(self, position, axis):
        if axis == 'X':
            axis_order = 0
        elif axis =='Y':
            axis_order = 1
        else:
            axis_order = 'None'
            print(f"{axis} is invalid input for Priro XY stage!")

        current_position = self.get_position()
        new_position = current_position
        new_position[axis_order] = str(position)
        msg_set_position = "controller.stage.position.set "+new_position[0]+" "+new_position[1]
        self.query(msg_set_position)
        self._position[axis] = position

    def move_to_position(self, position, axis):
        if axis == 'X':
            axis_order = 0
        elif axis =='Y':
            axis_order = 1
        else:
            axis_order = 'None'
            print(f"{axis} is invalid input for Prior XY stage!")
        # print("Move to set position.")
        current_position = self.get_position()
        new_position = current_position
        new_position[axis_order] = str(position)
        msg_set_position = "controller.stage.goto-position "+new_position[0]+" "+new_position[1]
        self.query(msg_set_position)
        self._position[axis] = position

    
    # def move(self, value, _):
        
    #     if value == 0:
    #         return
    #     elif float(value) > 0:
    #         cmd = 'U {}'.format(value)
    #         # print(value)
    #     elif float(value) < 0:
    #         absvalue = abs(float(value))
    #         cmd = 'D {}'.format(absvalue)
    #         # print(value)
    #     self._rs232Manager.query(cmd)

    #     self._position[self.axes[0]] = self._position[self.axes[0]] + value

    # # def move(self, value, _):
    # #     if value == 0:
    # #         return
    # #     elif float(value) > 0:
    # #         cmd = 'MOVRX +' + str(round(float(value), 3))[0:6] + 'u'
    # #     elif float(value) < 0:
    # #         cmd = 'MOVRX -' + str(round(float(value), 3))[1:7] + 'u'
    # #     self._rs232Manager.query(cmd)

    # #     self._position[self.axes[0]] = self._position[self.axes[0]] + value

    # def move_to_position(self, value):
    #     cmd = 'V {}'.format(value)
    #     self._rs232Manager.query(cmd)
    #     self._position[self.axes[0]] = value
    #     print(value)

    
    # def setPosition(self, value, _):
    #     cmd = 'V {}'.format(value)
    #     self._rs232Manager.query(cmd)

    #     self._position[self.axes[0]] = value
        

    # @property
    # def position(self):
    #     _ = self.get_abs()
    #     return self._position

    # def get_abs(self):
    #     cmd = 'PZ'
    #     reply = self._rs232Manager.query(cmd)
    #     if reply is None:
    #         reply = self._position[self.axes[0]]
    #     else:
    #         # reply = float(reply.split(' ')[0])
    #         reply = float(reply)
    #     self._position[self.axes[0]] = reply
    #     # print(reply)
    #     return reply


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
