from .LaserManager import LaserManager
import math
from imswitch.imcommon.model import initLogger


class AAAOTFLaserManager(LaserManager):
    """ LaserManager for controlling one channel of an AA Opto-Electronic
    acousto-optic modulator/tunable filter through RS232 communication.

    Manager properties:

    - ``rs232device`` -- name of the defined rs232 communication channel
      through which the communication should take place
    - ``channel`` -- index of the channel in the acousto-optic device that
      should be controlled (indexing starts at 1)
    """

    def __init__(self, laserInfo, name, **lowLevelManagers):
        self._logger = initLogger(self)
        self.laserDict = {'2':'488','3':'561','4':'640'}
        self._channel = int(laserInfo.managerProperties['channel'])
        self._rs232manager = lowLevelManagers['rs232sManager'][
            laserInfo.managerProperties['rs232device']
        ]
        # self.maxdBm = laserInfo.maxdBmValue
        self.percentPower = laserInfo.valueInit
        self.externalControl(1)
        super().__init__(laserInfo, name, isBinary=False, valueUnits='%', valueDecimals=0)


    def getStatus(self, ):
        cmd = 'L' + str(self._channel)
        ans = self._rs232manager.query(cmd)
        status = int(ans.split('S')[-1])
        return status


    def setEnabled(self, enabled):
        """Turn on (1) or off (0) laser emission"""
        if enabled:
            value = 1
            status = 'enabled'
        else:
            value = 0
            status = 'disabled'
        cmd = 'L' + str(self._channel) + 'O' + str(value)
        ans = self._rs232manager.query(cmd)
        channel = self.laserDict[str(self._channel)]
        self._logger.info(f'{channel} laser {status}')

    def setValue(self, percentPower):
        """Handles output power.
        Sends a RS232 command to the laser specifying the new intensity.
        """
        maxdBm = self._LaserManager__maxdBm
        self.setdBm = self.powerPercentTodBm(maxdBm, percentPower)
        self.percentPower = percentPower
        valueaotf = round(self.setdBm,1)
        cmd = 'L' + str(self._channel) + 'D' + str(valueaotf)
        ans = self._rs232manager.query(cmd)
        channel = self.laserDict[ans.split('F')[0].split('l')[1]]
        self._logger.info(f'{channel} laser {percentPower:.0f}% power')


    def externalControl(self, state):
        """Switch the channel to external control""" 
        cmd = 'I' + str(state) #1=external, 0=internal
        self._rs232manager.write(cmd)
        # channel = self.laserDict[ans.split('F')[0].split('l')[1]]
        # self._logger.info(f'{channel} laser external control enabled')

    def powerPercentTodBm(self,maxdBm,power):
        try:
            offset = 5*math.log(100)-maxdBm
            setdBm = 5*math.log(power) - offset
        except ValueError as ve:
            setdBm = -2.0

        return setdBm



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
