from ctypes import WinDLL, create_string_buffer
import os
import sys
from pathlib import Path
from imswitch.imcommon.model import initLogger

from .PositionerManager import PositionerManager

class PriorStageManager(PositionerManager):

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
        
        self.SDKPrior, self.SDKPriorMock, self.api, self.sessionID = self.initialize_all()
        
        self.check_axes()
        # Set intial values to match the widget
        self.zeroOnStartup = positionerInfo.managerProperties['zeroOnStartup']
        if self.zeroOnStartup:
            for axis in self.axes: 
                self.setPosition(self._position[axis], axis)


    def initialize_all(self):
        """Initialize the stage and go to mock if not present."""
        # Load SDK library
        imswitch_parent = str(Path.cwd())
        path = imswitch_parent+"\\dlls\\PriorSDK\\x64\\PriorScientificSDK.dll"
        if os.path.exists(path):
            SDKPrior = WinDLL(path)
        else:
            raise RuntimeError("DLL could not be loaded.")
        
        # Initialize API
        stage = SDKPrior.PriorScientificSDK_Initialise()
        if stage:
            self.__logger.warning(f'Failed to initialize {stage}, loading mocker')
            # sys.exit()
        else:
            print(f"Ok initialising {stage}")
        
        #Initialize communication sessionID
        sessionID = SDKPrior.PriorScientificSDK_OpenNewSession()
        if sessionID < 0:
            print(f"Error getting sessionID {stage}")
            # sys.exit()
        else:
            print(f"SessionID = {sessionID}")
        
        # Check if connection works
        ret = SDKPrior.PriorScientificSDK_cmd(
        sessionID, create_string_buffer(b"dll.apitest 33 goodresponse"), self.rx)
        print(f"api response {ret}, rx = {self.rx.value.decode()}")
        ret = SDKPrior.PriorScientificSDK_cmd(
        sessionID, create_string_buffer(b"dll.apitest -300 stillgoodresponse"), self.rx)
        print(f"api response {ret}, rx = {self.rx.value.decode()}")
        
        # Try to initialize stage
        
        # Extracts the port number used for device initialization
        port = ''.join(filter(lambda i: i.isdigit(), self.port))
        msg = "controller.connect " + port
        if self.query_initial(msg, SDKPrior, sessionID)[0]==0:
            SDKPriorMock = False
            print("Stage initialized")
        else:
            # Could not connect, load mock PriorSDK DLL
            from . import MockSDKPriorDLL
            SDKPrior = MockSDKPriorDLL.MockSDKPriorDLL
            SDKPriorMock = True       
        
        return SDKPrior, SDKPriorMock, stage, sessionID
    
    
    def query_initial(self, msg, SDKPrior, sessionID,):
        """Queries on intialization when SDKPrior is not yet present."""
        # print(msg)
        ret = SDKPrior.PriorScientificSDK_cmd(
            sessionID, create_string_buffer(msg.encode()), self.rx
        )
        if ret:
            print(f"Api error {ret}")
        # else:
        #     print(f"OK {self.rx.value.decode()}")

        return ret, self.rx.value.decode()   


    def check_axes(self):
        """Check axes if set-up correctly."""
        for axis in self.axes:
            if axis == 'X':
                pass
            elif axis == 'Y':
                pass
            else:
                print(f'{axis} is not an XY axis!')


    def query(self, msg):
        """Sends commands to stage using PriorSDK."""
        # print(msg)
        if self.SDKPriorMock:
            ret, value_out = self.SDKPrior.PriorScientificSDK_cmd(self, 
                self.sessionID, create_string_buffer(msg.encode()), self.rx
            )
        else:    
            ret = self.SDKPrior.PriorScientificSDK_cmd(
                self.sessionID, create_string_buffer(msg.encode()), self.rx
            )
            if ret:
                print(f"Api error {ret}")
            # else:
            #     print(f"OK {self.rx.value.decode()}")
            value_out = self.rx.value.decode()

        return ret, value_out
        

    def move(self, dist, axis):
        # self.setPosition(self._position[axis] + dist, axis)
        self.moveRelative(dist, axis) 
    

    def setPositionXY(self, position_x, position_y):
        new_position = [str(position_x), str(position_y)]
        msg_set_position = "controller.stage.goto-position "+new_position[0]+" "+new_position[1]
        self.query(msg_set_position)
        self._position['X'] = position_x
        self._position['Y'] = position_y
        print(self._position) #calculated, not queries from get_abs

    def moveRelative(self, dist, axis):
        """Moves the stage for a relative given step. """
        if axis == 'X':
            axis_order = 0
        elif axis =='Y':
            axis_order = 1
        else:
            axis_order = 'None'
            print(f"{axis} is invalid input for Prior XY stage!")
        
        distance = ['0','0']
        distance[axis_order] = str(dist)
        
        msg_move_relative = "controller.stage.move-relative "+distance[0]+" "+distance[1]
        self.query(msg_move_relative)
        self.checkBusy()
        current_position = self.get_abs()
        self._position[axis] = float(current_position[axis_order])
        print(self._position) #queries from get_abs


    def checkBusy(self):
        """Loops until stage becomes available."""
        busy = self.query("controller.stage.busy.get")[1]
        while busy != '0':
            # Query until stop moving
            busy = self.query("controller.stage.busy.get")[1]
        # print('Not busy.')


    def setPosition(self, position, axis):
        if axis == 'X':
            axis_order = 0
        elif axis =='Y':
            axis_order = 1
        else:
            axis_order = 'None'
            print(f"{axis} is invalid input for Prior XY stage!")

        current_position = self.get_abs()
        # Each xy position setting 
        new_position = current_position
        new_position[axis_order] = str(position)
        msg_set_position = "controller.stage.goto-position "+new_position[0]+" "+new_position[1]
        self.query(msg_set_position)
        self._position[axis] = position
        print(self._position) #calcuated, not queries from get_abs


    def getSpeedLow(self):
        msg_get_speed = "controller.stage.speed.get"
        response = self.query(msg_get_speed)
        speed = response[1]
        return speed

    def setSpeedLow(self, speed):
        if speed <= 0:
            print(f"Invalid speed setting at {speed} um/s!")
            speed = 6000 # Default on the device at the moment 28550
            print(f"Setting speed to default {speed} um/s!")
        elif speed > 15000:
            print(f"Max speed limit exceed at {speed} um/s! Max is 15000 um/s.")
            speed = 6000 # Default on the device at the moment
            print(f"Setting speed to default {speed} um/s!")
        msg_set_speed = "controller.stage.speed.set "+str(speed)
        self.query(msg_set_speed)
        speed_set = self.getSpeedLow()
        print(f"{speed_set} um/s") #calculated, not queries from get_abs     

    @property
    def position(self):
        self.checkBusy()
        _ = self.get_abs()
        return self._position

    def get_abs(self):
        response = self.query("controller.stage.position.get")
        position = response[1].split(",", 1)
        return position
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
