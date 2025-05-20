from .PositionerManager import PositionerManager
import sys
from pathlib import Path
from imswitch.imcommon.model import initLogger
from dlls.Queensgate import dll_adapter

class QueensgatePiezoManager(PositionerManager):
    def __init__(self, positionerInfo, name, *args, **lowLevelManagers):
        if len(positionerInfo.axes) > 1:
            raise RuntimeError(f'{self.__class__.__name__} only supports two axes,'
                               f' {len(positionerInfo.axes)} provided.')

        super().__init__(positionerInfo, name, initialPosition={
            axis: 0 for axis in positionerInfo.axes
        })
        self.__logger = initLogger(self)
        self.dll = dll_adapter.DllAdapter()
        self.positionerInfo = positionerInfo
        self.moveLimitsRegHolder = self.positionerInfo.limits
        self.port = positionerInfo.managerProperties['port'].strip("ASRL")

        self.loadDLL()

        status = self.initialize_all()

        self.check_axes()

        if status == False:
            queensgateMock = True
            from . import MockQueensgateDLL
            self.dll = MockQueensgateDLL.DllAdapter()  
            
        else:
            queensgateMock = False


        
        # Set intial values to match the widget
        self.zeroOnStartup = positionerInfo.managerProperties['zeroOnStartup']
        if self.zeroOnStartup:
            self.setPosition(0)
        else:
            # for j, axis in enumerate(self.axes):
            startPos = self.get_abs()
            self.setPosition(startPos)
        
    

    def loadDLL(self):
        imswitch_parent = str(Path.cwd())
        dllPath = imswitch_parent+"\\dlls\\Queensgate\\controller_interface64.dll"
        isOk = self.dll.Init(dllPath)
        if not isOk:
            print ("ERROR: Could not load DLL " + dllPath + " from current directory")
            sys.exit(-1)

    def initialize_all(self):
        """Initialize the stage and go to mock if not present."""
        status = self.dll.OpenSession(self.port)
        self.dll.DoCommand('controller.security.user.set 233573869')
        return status
    
    def check_axes(self):
        """Check axes if set-up correctly."""
        for axis in self.axes:
            if axis == 'Z':
                pass
            else:
                print(f'{axis} is not a Z axis!')


    def query(self, msg):
        """Sends commands to stage using PriorSDK."""
        # print(msg)
        ret, val = self.dll.DoCommand(msg)[0]

        return ret, val
    
    def microToPico(self, microVal):
        return microVal * 1e6
    
    def picoToMicro(self, picoVal):
        return picoVal / 1e6
        
    def move(self, dist, axis):
        self.moveRelative(dist, axis) 
    
    def moveRelative(self, dist, axis):
        """Moves the piezo relative to current position. """

        old_pos = self.get_abs()

        if old_pos + dist < self.moveLimitsRegHolder[0] or old_pos + dist > self.moveLimitsRegHolder[1]:
            self.__logger.error(f'Out of bounds request on {axis} axis. Range is between {self.moveLimitsRegHolder}.')
            self._position[axis] = float(old_pos)
            return
        
        newPos = old_pos+dist
        self.setPosition(newPos)

        current_position = self.get_abs()
        self._position[axis] = float(current_position)
        # print(self._position) #queries from get_abs



    # def busyWaitLoop(self): #CTNOTE This function hangs the GUI for long operations
    #     """Loops until stage becomes available."""
    #     busy = self.query("controller.z.busy.get")[1]
    #     while busy != '0':
    #         # Query until stop moving
    #         time.sleep(0.005)
    #         busy = self.query("controller.z.busy.get")[1]
    #         print('Piezo no longer busy.')


    # def checkIfMoving(self): #CTNOTE This function hangs the GUI for long operations
    #     busyQuery = self.query("controller.z.busy.get")[1]
    #     if busyQuery != '0':
    #         busy = True
    #     else:
    #         busy = False
    #     return busy


    def setPosition(self, position, axis = 'Z'):
        position = float(position)
        if position < self.moveLimitsRegHolder[0] or position > self.moveLimitsRegHolder[1]:

            self.__logger.error(f'Out of bounds request for Z piezo. Range is between {self.moveLimitsRegHolder}')
            old_pos = self.get_abs()
            self._position[axis] = float(old_pos)
            return
        new_position = str(self.microToPico(position))
        msg_set_position = "stage.position.command.set 0"+" "+new_position
        ret, val = self.query(msg_set_position)
        if ret == 'value': success = True
        else: success = False
        self._position[axis] = round(position,1)
        self.__logger.info(self._position)

        return success




    # def getSpeedLow(self):
    #     msg_get_speed = "controller.stage.speed.get"
    #     response = self.query(msg_get_speed)
    #     speed = response[1]
    #     return speed

    # def setSpeedLow(self, speed):
    #     if speed <= 0:
    #         print(f"Invalid speed setting at {speed} um/s!")
    #         speed = 6000 # Default on the device at the moment 28550
    #         print(f"Setting speed to default {speed} um/s!")
    #     elif speed > 15000:
    #         print(f"Max speed limit exceed at {speed} um/s! Max is 15000 um/s.")
    #         speed = 6000 # Default on the device at the moment
    #         print(f"Setting speed to default {speed} um/s!")
    #     msg_set_speed = "controller.stage.speed.set "+str(speed)
    #     self.query(msg_set_speed)
    #     speed_set = self.getSpeedLow()
    #     print(f"{speed_set} um/s") #calculated, not queries from get_abs     

    @property
    def position(self):
        # self.busyWaitLoop()
        _ = self.get_abs
        return self._position

    def get_abs(self):
        _, val = self.query("stage.position.command.get 0")
        position = self.picoToMicro(float(val))
        return position


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
