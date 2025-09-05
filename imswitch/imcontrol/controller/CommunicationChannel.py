from typing import Mapping

import numpy as np
from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import pythontools, APIExport, SharedAttributes
from imswitch.imcommon.model import initLogger


class CommunicationChannel(SignalInterface):
    """
    Communication Channel is a class that handles the communication between Master Controller
    and Widgets, or between Widgets.
    """

    sigUpdateImage = Signal(
        str, np.ndarray, bool, list, bool
    )  # (detectorName, image, init, scale, isCurrentDetector)
    
    sigAcquisitionStarted = Signal()
    
    sigAcquisitionStopped = Signal()

    sigSIMAcqToggled = Signal(bool)

    sig25DAcqToggled = Signal(bool)

    sigStopSim = Signal()

    sigStop25D = Signal()

    sigStart25D = Signal()

    sigRecordPSFStack = Signal()

    sigSendZstackToRecordWindow = Signal(list)

    sigTileImage = Signal(np.ndarray, tuple, str, int, int, int)

    sigTilePreview = Signal()

    sigRunAutofocus = Signal()

    sigScriptExecutionFinished = Signal()

    sigAdjustFrame = Signal(object)  # (shape)

    sigDetectorSwitched = Signal(str, str)  # (newDetectorName, oldDetectorName)

    sigGridToggled = Signal(bool)  # (enabled)

    sigCrosshairToggled = Signal(bool)  # (enabled)

    sigWriteParamsFromCam = Signal(object, float)

    sigAddItemToVb = Signal(object)  # (item)

    sigRemoveItemFromVb = Signal(object)  # (item)

    sigRecordingStarted = Signal()

    sigRecordingEnded = Signal()

    sigUpdateRecFrameNum = Signal(int)  # (frameNumber)

    sigUpdateRecTime = Signal(int)  # (recTime)

    sigMemorySnapAvailable = Signal(
        str, np.ndarray, object, bool
    )  # (name, image, filePath, savedToDisk)

    sigRunScan = Signal(bool, bool)  # (recalculateSignals, isNonFinalPartOfSequence)

    sigAbortScan = Signal()

    sigScanStarting = Signal()

    sigScanBuilt = Signal(object)  # (deviceList)

    sigScanStarted = Signal()

    sigScanDone = Signal()

    sigScanEnded = Signal()

    sigSLMMaskUpdated = Signal(object)  # (mask)

    sigToggleBlockScanWidget = Signal(bool)

    sigSnapImg = Signal()

    # sigSnapImgPrev = Signal(str, np.ndarray, str)  # (detector, image, nameSuffix)

    sigRequestScanParameters = Signal()

    sigSendScanParameters = Signal(dict, dict, object)  # (analogParams, digitalParams, scannerList)

    # sigSetAxisCenters = Signal(object, object)  # (axisDeviceList, axisCenterList)

    # sigStartRecordingExternal = Signal()

    # sigRequestScanFreq = Signal()
    
    # sigSendScanFreq = Signal(float)  # (scanPeriod)

    #sigRequestScannersInScan = Signal()

    sigStartAutoZern = Signal()

    sigStartAutoZernFinerLoop = Signal()

    sigSendAutoZernListLen = Signal(int, int)

    sigSetAutoZern = Signal(int)

    sigSetOptimalZern = Signal(int, float)

    sigAutoZernCalc = Signal(int)

    sigSaveFocus = Signal()

    sigToggleAutoZern = Signal(bool)

    sigLiveviewToggled = Signal(bool)

    # sigScanFrameFinished = Signal()  # TODO: emit this signal when a scanning frame finished, maybe in scanController if possible? Otherwise in APDManager for now, even if that is not general if you want to do camera-based experiments. Could also create a signal specifically for this from the scan curve generator perhaps, specifically for the rotation experiments, would that be smarter?
    
    # sigUpdateRotatorPosition = Signal(str)  # (rotatorName)

    sigSetSyncInMovementSettings = Signal(str, float)  # (rotatorName, position)

    sigNewFrame = Signal()

    sigZScanList = Signal(list, float)

    sigLoadSettings = Signal(dict)

    sigModuleSettings = Signal(dict)

    sigSaveSettingsFirst = Signal()
 
    # sigRecPSFStack = Signal(np.ndarray, bool, int)

    sigRecAFStack = Signal(np.ndarray, bool, int)

    sigGetLastRawImgs = Signal(np.ndarray, int)

    sigSendZDrift = Signal(float)

    # sigGetROIOrigins = Signal()

    # sigCalcZStack = Signal()

    # sigSaving = Signal()

    # useq-schema related signals
    # sigSetXYPosition = Signal(float, float)
    sigUpdateXYPosition = Signal(str,str)
    sigUpdateZPosition = Signal(str,str)
    sigUpdateZPositionConfirmed = Signal(str,str, float)
    sigSetExposure = Signal(float)
    sigSetSpeed = Signal(float)
    sigSIMStopped = Signal()
    sigToggleAutofocus = Signal(bool)
    sigGetAndScoreAF = Signal()
    sigSetForPSF = Signal(bool)
    

    @property
    def sharedAttrs(self):
        return self.__sharedAttrs

    def __init__(self, main, setupInfo):
        super().__init__()
        self.__main = main
        self.__sharedAttrs = SharedAttributes()
        self.__logger = initLogger(self)
        self._scriptExecution = False
        self.__main._moduleCommChannel.sigExecutionFinished.connect(self.executionFinished)
        self.sigLoadSettings.connect(self.storeLoadedSettings)
        # self.sigRecPSFStack.connect(self.storeRecPSFStack)
        self.sigRecAFStack.connect(self.storeRecAFStack)
        self.sigStop25D.connect(self.updateStop25DCommand)
        self.sigGetLastRawImgs.connect(self.saveLastRawImgs)
        self.roiList = []
        self.simActive = False
        self.activeDir = None
        self.stop25DNow = False
        self.lastImgDict = {'488F': None, '561F': None,'640F': None, '488S': None}

        #Autofocus variables
        self.calCurveFit = False
        self.initRegScore = None
        # self.offsetFromInitZ = 0.0
        self.currentRegScore = None
        self.currentPredZ = None
        self.initZ = None
        self.autofocusEnabled = False
        self.autofocusActive = False
        self.AFMaskLeft = None
        self.AFMaskRight = None
        #Scatter Cam 
        self.scatterCamActive = 0 #False

    # def storeROIList(self, roiList):
    #     self.roiList = roiList
    # def test(self, value):
    #     print(value)
    def updateStop25DCommand(self):
        self.stop25DNow = True

    def saveLastRawImgs(self, rawImg, handle):
        self.lastImgDict[handle] = rawImg

    # def saveLastROIClickAF(self, AFParams):
    #     self.AFParams = AFParams

    def getPSFStack(self):
        self.zStackList488 = getattr(self, "zStackList488", [])
        self.zStackList561 = getattr(self, "zStackList561", [])
        self.zStackList640 = getattr(self, "zStackList640", [])
        allPSFStacks = [self.zStackList488, self.zStackList561, self.zStackList640]

        return allPSFStacks

    def storeRecPSFStack(self, stack, reset, handle):
        
        if handle == '488F':
            if reset == True:
                self.zStackList488 = []
            self.zStackList488.append(stack)

        elif handle == '561F':
            if reset == True:
                self.zStackList561 = []
            self.zStackList561.append(stack)

        elif handle == '640F':
            if reset == True:
                self.zStackList640 = []   
            self.zStackList640.append(stack)

    def storeRecAFStack(self, stack, reset, handle):
        if reset == True:
            self.AFArray = []   
        self.AFArray.append(stack)



    def updateSIMActive(self, active):
        self.simActive = active
        if self.simActive == False:
            self.sigSIMStopped.emit()

    def storeLoadedSettings(self, dict):
        self.loadedSettings = dict

    def updateActiveDirectory(self, dir):
        self.activeDir = dir

    def storeCurrentTimeString(self, timeString):
        self.currentTimeString = timeString

    def getCenterViewbox(self):
        """ Returns the center point of the viewbox, as an (x, y) tuple. """
        if 'Image' in self.__main.controllers:
            return self.__main.controllers['Image'].getCenterViewbox()
        else:
            raise RuntimeError('Required image widget not available')

    def getDimsScan(self):
        if 'Scan' in self.__main.controllers:
            return self.__main.controllers['Scan'].getDimsScan()
        else:
            raise RuntimeError('Required scan widget not available')

    def getNumScanPositions(self):
        if 'Scan' in self.__main.controllers:
            return self.__main.controllers['Scan'].getNumScanPositions()
        else:
            raise RuntimeError('Required scan widget not available')

    def get_image(self, detectorName=None):
        return self.__main.controllers['View'].get_image(detectorName)

    @APIExport(runOnUIThread=True)
    def acquireImage(self) -> None:
        image = self.get_image()
        self.output.append(image)

    def runScript(self, text):
        self.output = []
        self._scriptExecution = True
        self.__main._moduleCommChannel.sigRunScript.emit(text)

    def executionFinished(self):
        self.sigScriptExecutionFinished.emit()
        self._scriptExecution = False

    def isExecuting(self):
        return self._scriptExecution

    @APIExport()
    def signals(self) -> Mapping[str, Signal]:
        """ Returns signals that can be used with e.g. the getWaitForSignal
        action. Currently available signals are:

         - acquisitionStarted
         - acquisitionStopped
         - recordingStarted
         - recordingEnded
         - scanEnded

        They can be accessed like this: api.imcontrol.signals().scanEnded
        """

        return pythontools.dictToROClass({
            'acquisitionStarted': self.sigAcquisitionStarted,
            'acquisitionStopped': self.sigAcquisitionStopped,
            'recordingStarted': self.sigRecordingStarted,
            'recordingEnded': self.sigRecordingEnded,
            'scanEnded': self.sigScanEnded,
            'saveFocus': self.sigSaveFocus
        })


# Copyright (C) 2020-2022 ImSwitch developers
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
