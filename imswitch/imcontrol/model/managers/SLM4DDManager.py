
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



class SLM4DDManager(SignalInterface):
    
# SLM returns code for ERROR in integer form. This is ERROR dictionary used to
# decode errors in following functions.
    def __init__(self, SIMSLMInfo):

        self.ERROR_Dictionary = {
            0 : "FDD_SUCCESS",
            1 : "FDD_MEM_INDEX_OUT_OF_BOUNDS",
            2 : "FDD_MEM_NULL_POINTER",
            3 : "FDD_MEM_ALLOC_FAILED",
            4 : "FDD_DEV_SET_TIMEOUT_FAILED",
            5 : "FDD_DEV_SET_BAUDRATE_FAILED",
            6 : "FDD_DEV_OPEN_FAILED",
            7 : "FDD_DEV_NOT_OPEN",
            8 : "FDD_DEV_ALREADY_OPEN",
            9 : "FDD_DEV_NOT_FOUND",
            10 : "FDD_DEV_ACCESS_DENIED",
            11 : "FDD_DEV_READ_FAILED ",
            12 : "FDD_DEV_WRITE_FAILED",
            13 : "FDD_DEV_TIMEOUT",
            14 : "FDD_DEV_RESYNC_FAILED",
            15 : "FDD_SLAVE_INVALID_PACKET",
            16 : "FDD_SLAVE_UNEXPECTED_PACKET ",
            17 : "FDD_SLAVE_ERROR ",
            18 : "FDD_SLAVE_EXCEPTION",
        }

        path = SIMSLMInfo.path
        port = SIMSLMInfo.port
        self.slmDLL = self.getSLMDLL(path)
        self.openSLM(port)
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

        ROgetselected = self.slmDLL.R4_RpcRoGetSelected
        ptr_getRO = ctypes.pointer(ctypes.c_int16())
        ret = ROgetselected(ptr_getRO)

        if ret == 0:
            retRO = ptr_getRO.contents.value
            retStr = 'Current RO: ' + str(retRO)
        else:
            retStr = "Failed to read RO: " + self.ERROR_Dictionary[ret]
            retRO = None

        return (retRO)


    def setRunningOrder(self,setROValue):
        getROCountVal = self.getROCount()[0]
        if setROValue >= 0 and setROValue < getROCountVal:
            ROsetselected = self.slmDLL.R4_RpcRoSetSelected
            # ptr_setRO = ctypes.pointer(ctypes.c_int16())
            ret = ROsetselected(setROValue)
            
            if ret == 0:
                newRO = self.getRunningOrder()
                if newRO == setROValue:
                    setROBool = True
                    retStr = ('Successfully set selected RO to ' + str(setROValue))
            else:
                setROBool = False
                retStr = "Failed to set RO to " + str(setROValue) + " : " + self.ERROR_Dictionary[ret]
        else:
            retStr = 'Desired RO out of bounds. Valid entries are 0:' + str(getROCountVal-1)
            setROBool = False
        print(retStr)    

        return (setROBool, retStr)


    def getROCount(self):
        getROCountFunc = self.slmDLL.R4_RpcRoGetCount
        ptr_getROCount = ctypes.pointer(ctypes.c_int16())
        ret = getROCountFunc(ptr_getROCount)
        if ret == 0:
            retROCount = ptr_getROCount.contents.value
            retStr = 'Number of ROs on device: ' + str(retROCount)
        else:
            retStr = "Failed to count ROs: " + self.ERROR_Dictionary[ret]
            retROCount = None

        return (retROCount, retStr)


    def slmActivate(self):
        slmActivate = self.slmDLL.R4_RpcRoActivate
        ret = slmActivate()
        if ret == 0:
            slmActivateBool = True
            retStr = 'SLM Activated'
        else:
            slmActivateBool = False
            retStr = 'SLM not activated: ' + self.ERROR_Dictionary[ret]
        return slmActivateBool, retStr


    def slmDeactivate(self):
        slmDeactivate = self.slmDLL.R4_RpcRoDeactivate
        ret = slmDeactivate()
        if ret == 0:
            slmDeactivateBool = True
            retStr = 'SLM Deactivated'
        else:
            slmDeactivateBool = False
            retStr = 'SLM not deactivated: ' + self.ERROR_Dictionary[ret]
        return slmDeactivateBool, retStr


    def slmRestart(self):
        slmRestart = self.slmDLL.R4_RpcSysReboot
        ret = slmRestart()
        if ret == 0:
            slmRestartBool = True
            retStr = 'SLM restarting. Process may take up to 10 seconds.'
        else:
            slmRestartBool = False
            retStr = 'SLM not restarting: ' + self.ERROR_Dictionary[ret]
        return slmRestartBool, retStr


    def setDefaultRO(self, defaultRO):

        setDefaultRO = self.slmDLL.R4_RpcRoSetDefault
        ret = setDefaultRO(defaultRO)

        if ret == 0:
            retBool = True
            retStr = 'Default RO set to: ' + str(defaultRO)
        else:
            retStr = "Failed to set default RO: " + self.ERROR_Dictionary[ret]
            retBool = False

        return (retBool, retStr)


    def getROName(self, ROIndex):
        getROName = self.slmDLL.R4_RpcRoGetName
        varArray = (ctypes.c_char*50)()
        ptr_getROName = ctypes.pointer(varArray)
        ret = getROName(ROIndex, ptr_getROName, 50)
        ROName = ptr_getROName.contents.value
        if ret == 0:
            retStr = "RO name identified successfully"
        else:
            retStr = "Failed ti identify RO name: "  + self.ERROR_Dictionary[ret]
        return (ROName, retStr)


    def getRepertoireUniqueId(self):
        getRepUnIdFunc = self.slmDLL.R4_RpcSysGetRepertoireUniqueId
        varArray = (ctypes.c_char*50)()
        ptr_getRepUnId = ctypes.pointer(varArray)
        ret = getRepUnIdFunc(ptr_getRepUnId, 50)
        repUnId = ptr_getRepUnId.contents.value
        repUnId = repUnId.decode("utf-8")
        if ret == 0:
            retStr = "Reprtoire unique Id identified succesfully: " + repUnId
        else:
            retStr = "Failed to identify repertoire unique Id: " + self.ERROR_Dictionary[ret]
        return (repUnId)


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
        getActivationStateFunc = self.slmDLL.R4_RpcRoGetActivationState
        ptr_ActState = ctypes.pointer(ctypes.c_uint8())
        #ptr_ActState = ctypes.pointer(ctypes.c_char_p())
        ret = getActivationStateFunc(ptr_ActState)
        actState = ptr_ActState.contents.value
        State_Dictionary = {
        80 : "Repertoire loading",
        81 : "Starting",
        82 : "Maintenance – Software deactivated",
        83 : "Maintenance – Hardware and Software deactivated",
        84 : "Maintenance – Hardware deactivated ",
        85 : "Activating",
        86 : "Active",
        87 : "No Repertoire available",
        }
        state = State_Dictionary[actState]
        if ret == 0:
            retStr = "Activation state identified successfully: " + state
        else:
            retStr = "Failed to identify activation state: " + self.ERROR_Dictionary[ret]
        return state, retStr


    def getAllRONames(self):
        totalROCount = self.getROCount()[0]
        RONameDict = {}
        if totalROCount == None:
            logging.error('RO count failed')
        else:
            for i in range (totalROCount):
                roName = self.getROName(i)[0]
                RONameDict[i] = roName.decode("utf-8")

        return RONameDict







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
    #     self._rs232manager.query(cmd)
    

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
