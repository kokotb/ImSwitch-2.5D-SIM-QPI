
from imswitch.imcontrol.view.guitools.ViewSetupInfo import ViewSetupInfo as SetupInfo
from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger
import time


class ArduinoManager(SignalInterface):
    """ 
    Arduino trigger to start and stop SLM sequence.
    """
    def __init__(self,  setupInfo, **lowLevelManagers):
        
        # TODO: Remove after development. Handled in MasterController.
        # the same way StandManager is handled
        # That is how they handled this in SLMManager.py
        # if setupInfo is None:
        #     self._rs232manager = None
        #     return
        
        # FIXME: Check in config file that the baudrate is set right
        self._rs232manager = lowLevelManagers['rs232sManager'][
            setupInfo.managerProperties['rs232device']
        ]

        # super().__init__(setupInfo)
    
    def trigOneSequence(self):
        """Sends a trigger to SLM to start a sequence."""
        # running_order order as a string
        # FIXME: Needs to be synced with our commands on Arduino
        cmd = 'S'+str(0)
        response = self._rs232manager.query(cmd)
        print(response)

    def trigOneSequenceWriteOnly(self):
        """Sends a trigger to SLM to start a sequence."""
        # running_order order as a string
        # FIXME: Needs to be synced with our commands on Arduino
        cmd = 'S'+str(0)
        self._rs232manager.write(cmd)


    def activateSLMWriteOnly(self):
        """Sends a trigger to SLM to put SPO0 high, activating the SLM. Ready for a trigger."""

        # FIXME: Needs to be synced with our commands on Arduino
        cmd = 'A'
        self._rs232manager.write(cmd)
        time.sleep(0.01)


    def activateSLM(self):
        """Sends a trigger to SLM to put SPO0 high, activating the SLM. Ready for a trigger."""
        # running_order order as a string
        # FIXME: Needs to be synced with our commands on Arduino
        cmd = 'A'
        response = self._rs232manager.query(cmd)
        print(response)

    def deactivateSLMWriteOnly(self):
        """Sends a trigger to SLM to put SPO0 low, deactivating the SLM."""
        # running_order order as a string
        # FIXME: Needs to be synced with our commands on Arduino
        cmd = 'Q'
        self._rs232manager.write(cmd)


    def deactivateSLM(self):
        """Sends a trigger to SLM to put SPO0 low, deactivating the SLM."""
        # running_order order as a string
        # FIXME: Needs to be synced with our commands on Arduino
        cmd = 'Q'
        response = self._rs232manager.write(cmd)
        print(response)

    def startContSequence(self, running_order):
        """Sends a trigger to SLM to start a sequence."""
        # running_order order as a string
        # FIXME: Needs to be synced with our commands on Arduino
        cmd = 'C'+str(running_order)
        response = self._rs232manager.query(cmd)
        print(response)
        
    def stopSequence(self):
        """Sends loop termination signal."""
        cmd = 'Q'
        response = self._rs232manager.query(cmd)
        print(response)

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
