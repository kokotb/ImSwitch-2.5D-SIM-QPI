import enum
import glob
import cv2
import os
import re
import numpy as np
from PIL import Image
from scipy import signal as sg
from imswitch.imcontrol.view.guitools.ViewSetupInfo import ViewSetupInfo as SetupInfo
from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger
import requests


class SIMslmManager(SignalInterface):
    
    def __init__(self,  setupInfo, **lowLevelManagers):
        self._rs232manager = lowLevelManagers['rs232sManager'][
            setupInfo.managerProperties['rs232device']
        ]
        
    print("Here!")
    # # Structure copied over from SIMclient
    #     self.commands = {
    #         "start": "/start_viewer/",
    #         "single_run": "/start_viewer_single_loop/",
    #         "pattern_compeleted": "/wait_for_viewer_completion/",
    #         "pause_time": "/set_wait_time/",
    #         "stop_loop": "/stop_viewer/",
    #         "pattern_wl": "/change_wavelength/",
    #         "display_pattern": "/display_pattern/",
    #     }
    #     self.iseq = 60
    #     self.itime = 120
    #     self.laser_power = (400, 250)

    # def get_request(self, url, timeout=0.3):
    #     try:
    #         response = requests.get(url, timeout=timeout)
    #         return response.json()
    #     except Exception as e:
    #         print(e)
    #         return -1

    # def start_viewer(self):
    #     url = self.base_url + self.commands["start"]
    #     return self.get_request(url)

    # def start_viewer_single_loop(self, number_of_runs, timeout=2):
    #     url = f"{self.base_url}{self.commands['single_run']}{number_of_runs}"
    #     return self.get_request(url, timeout=timeout)

    # def wait_for_viewer_completion(self):
    #     url = self.base_url + self.commands["pattern_compeleted"]
    #     self.get_request(url)

    # def set_pause(self, period):
    #     url = f"{self.base_url}{self.commands['pause_time']}{period}"
    #     self.get_request(url)

    # def stop_loop(self):
    #     url = self.base_url + self.commands["stop_loop"]
    #     self.get_request(url)

    # def set_wavelength(self, wavelength):
    #     url = f"{self.base_url}{self.commands['pattern_wl']}{wavelength}"
    #     self.get_request(url)

    # def display_pattern(self, iPattern):
    #     url = f"{self.base_url}{self.commands['display_pattern']}{iPattern}"
    #     self.get_request(url)

    
    # sigSIMMaskUpdated = Signal(object)  # (maskCombined)

    # def __init__(self, simInfo, *args, **kwargs):
    #         sigSIMMaskUpdated = Signal(object)  # (maskCombined)

    # def __init__(self, simInfo, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.__logger = initLogger(self)

    #     if simInfo is None:
    #         return

    #     self.__simInfo = simInfo
    #     self.__wavelength = self.__simInfo.wavelength
    #     self.__pixelsize = self.__simInfo.pixelSize
    #     self.__angleMount = self.__simInfo.angleMount
    #     self.__simSize = (self.__simInfo.width, self.__simInfo.height)
    #     self.__patternsDir = self.__simInfo.patternsDir
    #     self.nRotations = self.__simInfo.nRotations
    #     self.nPhases = self.__simInfo.nPhases
    #     self.simMagnefication = self.__simInfo.nPhases
    #     self.isFastAPISIM = self.__simInfo.isFastAPISIM
    #     self.simPixelsize = self.__simInfo.simPixelsize
    #     self.simNA = self.__simInfo.simNA
    #     self.simN = self.__simInfo.simN # refr
    #     self.simETA = self.__simInfo.simETA

    #     # Load all patterns
    #     if type(self.__patternsDir) is not list:
    #         self.__patternsDir = [self.__patternsDir]

    #     # define paramerters for fastAPI (optional)
    #     fastAPISIM_host = self.__simInfo.fastAPISIM_host
    #     fastAPISIM_port = self.__simInfo.fastAPISIM_port
    #     fastAPISIM_tWaitSequence = self.__simInfo.tWaitSequence
    #     self.fastAPISIMParams = {"host":fastAPISIM_host,
    #                              "port":fastAPISIM_port,
    #                              "tWaitSquence":fastAPISIM_tWaitSequence}

    #     self.isFastAPISIM = self.__simInfo.isFastAPISIM


    # def update(self):
    #     pass

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
