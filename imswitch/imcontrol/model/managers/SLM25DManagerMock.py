import numpy as np
from PIL import Image
from scipy import signal as sg
from imswitch.imcontrol.view.guitools.ViewSetupInfo import ViewSetupInfo as SetupInfo
from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger



from ctypes import *
import ctypes
from pathlib import Path
import logging



class SLM25DManagerMock(SignalInterface):
    
# SLM returns code for ERROR in integer form. This is ERROR dictionary used to
# decode errors in following functions.
    def __init__(self, SLM25DInfo):

        pass


        #super().__init__(SIMSLMInfo, 'SIMslm')

    # Opens SLMDLL library ===========================================================
    def getSLMDLL(self, path):
        slmDLL = WinDLL(path)
        return slmDLL

    # ==============================================================================



    # ================================================================================
    #  All following functions return an answer in tuple form (answer, return string),
    #  where return string informs user about success of the operation and identifies
    #  type of error if neccessary.
    # ================================================================================

    def openSLM(self, port):
        #Port input in form of COMX
        openComPort = self.slmDLL.FDD_DevOpenComPort
        portb = port.encode('utf-8')
        ret = openComPort(portb,250,115200,True)

        if ret == 0:
            retBool = True
            retStr = 'SLM connected? ' + str(retBool)
            
        else:
            retBool = False
            retStr = 'SLM connected? ' + str(retBool) + " : " + self.ERROR_Dictionary[ret]
        print(retStr)
        return retBool, retStr


    def closeSLM(self):
        closeComPort = self.slmDLL.FDD_DevClose
        ret = closeComPort()
        if ret == 0:
            retBool = True
            retStr = 'SLM closed? ' + str(retBool)
        else:
            retBool = False
            retStr = 'SLM closed? ' + str(retBool) + " : " + self.ERROR_Dictionary[ret]

        return retBool, retStr


    def getRunningOrder(self):
        return (2)


    def setRunningOrder(self, setROValue):
        return (True, "Set RO Mock")


    def getROCount(self):
        return (9, "RO count = 9")


    def slmActivate(self):
        return True, 'SLM Activated'


    def slmDeactivate(self):
        return True, 'SLM Deactivated'


    def slmRestart(self):
        return True, 'SLM Restarted'


    def setDefaultRO(self, defaultRO):
        return True, 'RO default set'


    def getROName(self, ROIndex):
        retStr = "RO name identified successfully (Mocker)"
        return ("ROName", retStr)


    def getRepertoireUniqueId(self):
        retStr = "RepUnId name identified successfully (Mocker)"
        return ("repUnId", retStr)


    # def getProgress(slmDLL):
    #     getProgressPercentageFunc = slmDLL.R4_DevGetProgress
    #     ptr_getProgress = ctypes.pointer(ctypes.c_uint8())
    #     ret = getProgressPercentageFunc(ptr_getProgress)
    #     progressPct = ptr_getProgress.contents.value
    #     #print(self.ERROR_Dictionary[getProgressPct])
    #     if ret == 0:
    #         retStr = "Progress percentage identified succesfully. Progress = " + str(progressPct) + "%"
    #     else:
    #         retStr = "Failed to identify progress percentage: " + self.ERROR_Dictionary[ret]
    #     return (progressPct, retStr)


    def getActState(self):
        retStr = "RepUnId name identified successfully (Mocker)"
        return ("state", retStr)


    def getAllRONames(self):
        RONameDict = {}
        for i in range (9):
            RONameDict[i] = "RO name" + str(i)
        return RONameDict

    def maskCombined(self):
        return True, 'SLM Deactivated'

    # openSLMBool, openSLMStr = openSLM(slmDLL,'COM4')
    # print(openSLMStr)
    # getROVal,getROStr = getRunningOrder(slmDLL)
    # setROBool, setROStr = setRunningOrder(slmDLL, 5)

    # activationState = getActState(slmDLL)
    # print(activationState)

    # closeBool, closeSLMStr = closeSLM(slmDLL)


    # print(getROStr)
    # print(setROBool)
    # print(setROStr)

    # print(closeSLMStr)



    # def set_running_order(self, orderID):
    #     """Sets running order on the SLM. """
    #     cmd = "RO "+str(orderID)
    #     # self._rs232manager.query(cmd)
    

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
