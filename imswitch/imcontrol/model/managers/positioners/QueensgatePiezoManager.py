from .PositionerManager import PositionerManager


class QueensgatePiezoManager(PositionerManager):
    """ PositionerManager for control of a Piezoconcept Z-piezo through RS232
    communication.

    Manager properties:

    - ``rs232device`` -- name of the defined rs232 communication channel
      through which the communication should take place
    """

    def __init__(self, positionerInfo, name, *args, **lowLevelManagers):
        if len(positionerInfo.axes) != 1:
            raise RuntimeError(f'{self.__class__.__name__} only supports one axis,'
                               f' {len(positionerInfo.axes)} provided.')

        super().__init__(positionerInfo, name, initialPosition={
            axis: 0 for axis in positionerInfo.axes
        })
        self._rs232Manager = lowLevelManagers['rs232sManager'][
            positionerInfo.managerProperties['rs232device']
        ]

        self.positionerInfo = positionerInfo
    
    def move(self, value, _, acceleration = False, speed = False):
        
        if value == 0:
            return
        elif float(value) > 0:
            cmd = 'U {}'.format(value)
            # print(value)
        elif float(value) < 0:
            absvalue = abs(float(value))
            cmd = 'D {}'.format(absvalue)
            # print(value)
        self._rs232Manager.query(cmd)

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

    # def move_to_position(self, value, axis):
    #     cmd = 'V {}'.format(value)
    #     self._rs232Manager.query(cmd)
    #     self._position[axis] = value
    #     print(value)

    
    def setPosition(self, value, _):
        cmd = 'V {}'.format(value)
        self._rs232Manager.query(cmd)
        self._position[_] = value
        print(value)


    def getSpeedLow(self):
        print("getSpeed not implemented yet!")
        pass


    def setSpeedLow(self, speed):
        print(f"setSpeed not implemented yet for {self.positionerInfo.managerName}")
        pass
        

    @property
    def position(self):
        _ = self.get_abs()
        return self._position

    def get_abs(self):
        cmd = 'PZ'
        reply = self._rs232Manager.query(cmd)
        if reply is None:
            reply = self._position[self.axes[0]]
        else:
            # reply = float(reply.split(' ')[0])
            reply = float(reply)
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
