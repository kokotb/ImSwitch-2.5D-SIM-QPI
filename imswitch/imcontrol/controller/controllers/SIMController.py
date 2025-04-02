import os
import numpy as np
import time
import threading
from datetime import datetime
import tifffile as tif
import time
import numpy as np
from decimal import Decimal
from .SIMProcessor import SIMProcessor
from .SIMProcessor import SIMParameters
from concurrent.futures import ThreadPoolExecutor
from queue import Queue


from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController
from imswitch.imcommon.framework import Signal, Thread, Worker, Mutex, Timer
# from imswitch.imcontrol.model import SLM4DDManager as SIMclient

import imswitch
import pandas as pd


class SIMController(ImConWidgetController):
    """Linked to SIMWidget."""

    sigRawStackReceived = Signal(np.ndarray, str)
    sigSIMProcessorImageComputed = Signal(np.ndarray, str)
    sigWFImageComputed = Signal(np.ndarray, str)
    sigValueChanged = Signal()

    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)

        #Setup state variables
        self.isReconstruction = self._widget.getReconCheckState()
        self.isRecordRaw = False
        self.isRecordWF = False
        self.isRecordRecon = False
        self.tilePreview = False

     
        # Only napari implemented as of 12/9/24
        self.reconstructionMethod = "napari" # or "mcSIM"

        #This signal connect needs to run earlier than self.makeSetupInfoDict, so when SIM parameters are filled, it sends it to shared attributes.
        self._widget.sigSIMParamChanged.connect(self.valueChanged)
        self._widget.sigUserDirInfoChanged.connect(self.valueChanged)
        self._widget.sigROInfoChanged.connect(self.valueChanged)

        setupInfoDict = self.makeSetupInfoDict() # Pull SIM setup info into dict and also set on SIM widget.

        #Create list of available laser objects from config file.
        self.lasers = list(self._master.lasersManager._subManagers.values()) #List of just the laser object handles
            
        # Create positioner objects -- Positioner must have axis 'Z' or axis 'XY' listed in config file to be added correctly.
        for key in self._master.positionersManager._subManagers:
            if self._master.positionersManager._subManagers[key].axes == ['Z']:
                self.positioner = self._master.positionersManager._subManagers[key]
            elif self._master.positionersManager._subManagers[key].axes[0] == ['X'] or ['Y']:
                self.positionerXY = self._master.positionersManager._subManagers[key]
            else:
                self._logger.error(f"Positioner {self._master.positionersManager._subManagers[key].name} in config file does not have axes defined correctly")

        # Initializes a class object that we append the correct values to. The values of the actually class stay empty. Can change to be namespace and get rid of SIMParameters() objcet all together.
        self.sim_parameters = SIMParameters()
        for key in setupInfoDict:
            setattr(self.sim_parameters,key,setupInfoDict[key])

        # Create class objects for each processor channel.
        self.SimProcessorLaser1 = SIMProcessor(self, self.sim_parameters, wavelength=self.sim_parameters.ReconWL1)
        self.SimProcessorLaser2 = SIMProcessor(self, self.sim_parameters, wavelength=self.sim_parameters.ReconWL2)
        self.SimProcessorLaser3 = SIMProcessor(self, self.sim_parameters, wavelength=self.sim_parameters.ReconWL3)
        self.SimProcessorLaser1.handle = 488 #This handle is used to keep naming consistent when wavelengths may change.
        self.SimProcessorLaser2.handle = 561
        self.SimProcessorLaser3.handle = 640
        self.processors = [self.SimProcessorLaser1,self.SimProcessorLaser2,self.SimProcessorLaser3] #processor object list
        self.detectors = []
        for detector in self._master.detectorsManager: #detector object list
            self.detectors.append(detector[1])

        # Signals originating from SIMController.py        
        self.sigRawStackReceived.connect(self.displayRawImage)
        self.sigSIMProcessorImageComputed.connect(self.displaySIMImage)
        self.sigWFImageComputed.connect(self.displayWFImage)

        # Signals connecting SIMWidget actions with functions in SIMController
        self._widget.startSIM_button.clicked.connect(self.startSIM)
        self._widget.stop_button.clicked.connect(self.stopSIM)
        self._widget.checkbox_record_raw.stateChanged.connect(self.toggleRecording)
        self._widget.checkbox_record_WF.stateChanged.connect(self.toggleRecordWF)
        self._widget.checkbox_record_reconstruction.stateChanged.connect(self.toggleRecordReconstruction)
        self._widget.checkbox_reconstruction.stateChanged.connect(self.toggleReconstruction)
        self._widget.openFolderButton.clicked.connect(self.openFolder)
        self._widget.calibrateButton.clicked.connect(self.calibrateToggled)
        self._widget.saveOneSetButton.clicked.connect(self.saveOneSet)
        self._widget.sigStartSIM.connect(self.startSIM)
        self._widget.sigStopSIM.connect(self.stopSIM)

        # Communication channels signls (signals sent elsewhere in the program)
        # self._commChannel.sigAdjustFrame.connect(self.updateROIsize)
        self._commChannel.sigStopSim.connect(self.stopSIM)
        self._commChannel.sigZScanList.connect(self.zScanList)
        self._commChannel.sigTilePreview.connect(self.toggleTilePreview)
        self._commChannel.sigModuleSettings.connect(self.loadSIMSettings)
        self._commChannel.sigModuleSettings.connect(self.loadUserSettings)
        self._commChannel.sig25DAcqToggled.connect(self.start25D)
        
        #Get RO names from SLM4DDManager and send values to widget function to populate RO list, selects currently active RO. (default or last used if not powered down)
        self.populateAndSelectROList()
        #Get save directory root from config file and populate text box in SIM widget.
        self._widget.setUserDirInfo(setupInfoDict['saveDir'])
        #Create log file attributes that get filled during experiment
        self.log_times_loop = []
        
        # self.setSharedAttr(attrCategory, parameterName, value):
        self.sharedAttrs = self._commChannel.sharedAttrs._data

    def loadSIMSettings(self, moduleDict):
        try:
            loadBool = moduleDict['SIM Parameters']
        except KeyError:
            loadBool = 0
        if loadBool:
            params = self._commChannel.loadedSettings['SIM Parameters']

            for i in range(len(self._widget.elementListSIM)):
                if self._widget.elementListSIM[i]._type == 'str':
                    self._widget.elementListSIM[i].setText(params[self._widget.elementListSIM[i]._name])
                elif self._widget.elementListSIM[i]._type == 'combostr':
                    if self._widget.elementListSIM[i]._name == 'SLM Running Order':
                        try:
                            self._widget.elementListSIM[i].setCurrentText(params[self._widget.elementListSIM[i]._name])
                        except:
                            self._logger.warning('SLM running order could not be set.')
                            pass #should have a notice that the running order is not available at the moment.

    def loadUserSettings(self, moduleDict):
        try:
            loadBool = moduleDict['userDir']
        except KeyError:
            loadBool = 0
        if loadBool:
            params = self._commChannel.loadedSettings['User Dir Info']

            for i in range(len(self._widget.elementListUser)):
                self._widget.elementListUser[i].setText(params[self._widget.elementListUser[i]._name])

    def getOrigins(self):
        roiList = self._commChannel.sharedAttrs[('ROI List','List')]
        originList = []
        for i in range(len(roiList)):
            Xstring, Ystring, Zstring = roiList[i][1].split(' | ')
            X = Xstring.split(':')[1]
            Y = Ystring.split(':')[1]
            posTuple = (X, Y)
            originList.append(posTuple)
        return originList

        
    def performSIMExperimentThread(self, sim_parameters):
        """
        Select a sequence on the SLM that will choose laser combination.
        Run the sequence by sending the trigger to the SLM.
        Run continuous on a single frame. 
        Run snake scan for larger FOVs.
        """
        
        # self.isReconstructing = False # Is this line needed, all other references to this variable are in SIMProcessor

        self.sim_parameters = sim_parameters #Make starting parameters available to all of SIMController.py

        # Check if lasers are set and have power in them select only lasers with powers
        poweredLasers = []
        for laser in self.lasers:
            if laser.percentPower > 0:
                poweredLasers.append(laser.wavelength)

        projCamPixelSize = (sim_parameters.Pixelsize)/(sim_parameters.Magnification) # This may be very slightly miscalced (sig figs). Conversion to pixel space gives 512.05, not 512.

        #Get the parameters that go into the createXYGridPositionArray function
        self.getTilingSettings()
        # self._commChannel.sigCalcPositionArray.emit()
        roiOriginList = []

        if int(self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]) == 2:
            self.isTiling = True
        else:
            self.isTiling = False

        if int(self.sharedAttrs[('ROI List', 'Checkbox')]) == 2:
            self.isScanROI = True
        else:
            self.isScanROI = False

        if self.isScanROI:
            try:
                roiOriginList = self.getOrigins()
            except KeyError:
                self._logger.warning('ROI list is empty.')

        self.tileOrigins = []
        positions = self._master.tilingManager.createXYGridPositionArrayWithROI(self.num_grid_x, self.num_grid_y, self.overlap, self.startxpos, self.startypos, projCamPixelSize, roiOriginList)
        for i in range(len(positions)):
            self.tileOrigins.append(positions[i][-1])
        
        self.tileOrigin = positions[0][-1]




        if not self.isTiling:
            positions = self.tileOrigins
        
        #Get Z-Stack list
        if self._commChannel.sharedAttrs._data[('Z-Stack Settings', 'Z-Stack Checkbox')] == '0':
            self.zScanActive = False
            zList = [self._commChannel.sharedAttrs._data[('Positioner', 'Z', 'Z', 'Position')]]
            self.zLength = len(zList)
        elif self._commChannel.sharedAttrs._data[('Z-Stack Settings', 'Z-Stack Checkbox')] == '2':
            self.zScanActive = True
            zList = self.zList
            self.zLength = len(zList)
            #zOrigin stored as self.zOrigin already


        ''' # For nameing tiling squares A1, A2, .....C5 etc.
        # gridNamesX = [str(x+1) for x in range(self.num_grid_x)]
        # gridNamesY = list(string.ascii_uppercase)[:self.num_grid_y]
        # test = []
        # for item in gridNamesY:
        #     for value in gridNamesX:
        #         test.append(item+value)
        '''
        
        # Datetime string registered when start button is pressed only.
        dateTimeStartClick = datetime.now().strftime("%y%m%d_%H%M%S")
        

        # Set all SIM parameters from GUI to each processor. All will be the same, except Recon WL
        self.updateProcessorParameters()

        
        self.numAllFrames = 0 # Number of frames, including dropped frames
        self.completeFrameSets = 0 # Number of frames, exncluding dropped frames
        self.framesPerDetector = 9
        self.frameCounter = 0
        #Set tiling flag, determines whether program will enter the tiling code.


        self.numActiveChannels = len(poweredLasers)
        

        # Set running order on SLM
        roID = self._widget.getSelectedRO()
        self._master.SLM4DDManager.setRunningOrder(roID)
        # Get max exposure time from the selected RO on SLM. This is done with naming structure. Name must start with numerical digits, then 'ms'. *1000 to make us.
        self.expTimeMax, numSLMChannels, chansSLM = self.parseROParamsFromSLM(roID)
        self.setActiveSLMChannels(numSLMChannels, chansSLM)
        self.activeProcessors = []
        for processor in self.processors:
            if processor.slmActive == True:
                self.activeProcessors.append(processor)
            for detector in self.detectors:
                if processor.handle == detector._wavelength:
                    processor.detObj = detector
        for k, processor in enumerate(self.activeProcessors):
            processor.processorIndex = k



        # -------------------Set-up cams-------------------

        # FIXME: Automate buffer size calculation based on image size, it did not work before
        total_buffer_size_MB = 350 # in MBs
        for detector in self.detectors:
            image_size = detector.shape
            image_size_MB = (2*image_size[0]*image_size[1]/(1024**2))
            buffer_size = int(total_buffer_size_MB // image_size_MB)
            # buffer_size = 9
            self.setCamForExperimentSIM(detector, buffer_size,self.expTimeMax)
        

        time_global_start = time.time()
        # time_whole_start = time_global_start
        # self.processors2 = self.processors[0]
        # self.processors2 = [self.processors2]

        self._master.arduinoManager.activateSLMWriteOnly() #This command activates the arduino to be ready to receive triggers.
       # 0.01s time delay built into activate SLM function. trigOneSequence() cannot be called too fast. Only adds to very first loop time. 1 ms was not enough. If query is waited for, value is 0.02
        self.tilingRep = 0
        timingPeriodInSec = self.getPeriodInSec()
        durationInSec = self.getDurationInSec()
        totalEndTime = 0
        self.startSettingsSaved = False
        while self.active and poweredLasers != []:
            

            self.exptFolderPath = self.makeExptFolderStr(dateTimeStartClick)
            self.setSharedAttr('User Dir Info', 'Current Path', self.exptFolderPath)
            self._commChannel.updateActiveDirectory(self.exptFolderPath)

            # Scan over all positions generated for grid
            

            if self.completeFrameSets != 0 and timingPeriodInSec is not None:
                repTimer = time.time() - repTimerStart
                while repTimer < timingPeriodInSec:
                    time.sleep(.1)
                    repTimer = time.time() - repTimerStart
                    if self._widget.stop_button.isChecked(): #allows exit of SIM loops once per cycle
                        self._widget.stop_button.setChecked(False)
                        return
            repTimerStart = time.time()

            self.roiIterator = 0

            while self.roiIterator < len(positions):
                j = 0 # Position iterator
                oneROI = positions[self.roiIterator]

                if (not self.isTiling) and (not self.isScanROI):
                    oneROI = [oneROI]


                while j < len(oneROI):
                    self.j = j
                    if self.numAllFrames == 0:
                        exptTimeElapsed = 0.0
                    else:
                        exptTimeElapsed = time.time() - time_global_start
                    self.exptTimeElapsedStr = self.getElapsedTimeString(exptTimeElapsed)
                    self._commChannel.storeCurrentTimeString(self.exptTimeElapsedStr)
                    self.nextPos = oneROI[self.j]
                    self.currentPos = oneROI[self.j-1]
                    self.positionerXY.checkBusyLoop()


                    if j == 0 and self.completeFrameSets != 0 and self.isTiling:
                        time.sleep(.5) #TODO: Change to calibrate by distance needed to move
                    # elif (j==0) and (self.completeFrameSets == 0):
                    #     pass
                    else:
                        time.sleep(.05) #can probablz reduct slightly
                    z = 0
                    while z < len(zList):
                    # for z in range(len(zList)):
                        if self.zScanActive:
                            self.positioner.setPosition(zList[z], 'Z')
                            self._commChannel.sigUpdateZPosition.emit('Z','Z')

                        timestart = time.time()
                                        
                        # Trigger SIM set acquisition. Will trigger as many channels are as on SLM.
                        
                        self._master.arduinoManager.trigOneSequenceWriteOnly()
                        # self._master.arduinoManager.trigOneSequence()
     



                        errorLock = threading.Lock() #Lock for passing whether channel received all 9 images
                        saveLock = threading.Lock()
                        self.errorQ = [] #List to be populated with error results from within processor threads
                        self.waitToMoveEvent = threading.Event() #When the last camera receives its images, this signal will fire to the positioner, moving the stage.

                        with ThreadPoolExecutor(max_workers=4) as executor: #
                            if self.isTiling:
                                executor.submit(self.tilingMoveThread)
                            for processor in self.activeProcessors:
                                    executor.submit(self.mainSIMLoop, processor, errorLock, z, saveLock) 

                        if self._widget.stop_button.isChecked(): #allows exit of SIM loops once per cycle
                            # self.stopSIM()
                            self._widget.stop_button.setChecked(False)
                            return

                        self.numAllFrames += 1
                        if True not in self.errorQ:
                            self.completeFrameSets += 1 # increment only if no errors reported from processor threads
                            z += 1 # this controls positions. Increment only if successful. Repeat same location if any one camera fails.
                        loopEndTime = time.time()-timestart
                        print(loopEndTime)
                        self._logger.debug('Dropped frames: {}'.format(self.numAllFrames-self.completeFrameSets))
                        self._logger.debug('Total frames: {}'.format(self.numAllFrames))
                        
                    # self.completeFrameSets += 1 # increment only if no errors reported from processor threads
                    j += 1 # this controls positions. Increment only if successful. Repeat same location if any one camera fails.


                    
                    if self.sharedAttrs[('Timing Settings','Rep Checkbox')]==2 and not (self.completeFrameSets + 1 < len(oneROI)*int(self.sharedAttrs[('Timing Settings','Repetitions')])): 
                        self._commChannel.sigStopSim.emit() # Stops tiling reps after all tiles*repetitions is done.

                    totalEndTime = time.time()-time_global_start
                    remainder = self.completeFrameSets % len(oneROI)

                    if self.sharedAttrs[('Timing Settings','Duration Checkbox')]==2 and durationInSec != 0 and durationInSec < totalEndTime:
                        if self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]=='0':
                            self._commChannel.sigStopSim.emit()
                        if self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]=='2' and remainder == 0:
                            self._commChannel.sigStopSim.emit()



                self.frameCounter += 1


                self.tilingRep += 1

                self.roiIterator += 1
                
                print(f'total time: {totalEndTime}')
            


        

    def mainSIMLoop(self, processor, errorLock, z, saveLock):
        # saveOneTime = self.saveOneTime
        # print(saveOneTime)

        k = processor.processorIndex
        if k+1 == len(self.activeProcessors):
            lastChan = True
        else: 
            lastChan = False

        broken = False
        
        # Set current detector being used
        detector = processor.detObj
######TIMING BUFFER WAITING LOGIC BREAKS DOWN AT FAST SPEEDS. NEED DIFFERENT WAY.
        time.sleep(self.expTimeMax/1000000*(k)*20) #approximately how long it will start for detector to start receiving images in buffer.
        waitingBuffers = detector._camera.getBufferValue()

        waitingBuffersEnd = 0
        bufferStartTime = time.time()
        # broken = False
        # time.sleep(self.expTimeMax/1000000*16)
        # time.sleep(1)
        while waitingBuffers != 9:
            time.sleep(self.expTimeMax/1000000)
            waitingBuffers = detector._camera.getBufferValue() #FIXME This logic does not include a way to remove saved images for first 2 cams if for example the thrid cam fails
            if waitingBuffers != waitingBuffersEnd:
                bufferStartTime = time.time()
                bufferEndTime = time.time()
            else: 
                bufferEndTime = time.time()
            bufferTotalTime = bufferEndTime-bufferStartTime
            waitingBuffersEnd = waitingBuffers
            if waitingBuffers != 9 and bufferTotalTime > self.expTimeMax/250000: #self.expTimeMax/250000 = 4x exp time in correct units
                self._logger.error(f'Frameset thrown in trash. Buffer available is {waitingBuffers} on detector {detector.name}')
                broken = True
                with errorLock:
                    self.errorQ.append(True)
                for detector in self.detectors: # probably move this outside of thread structure, seems like it could be unsafe.
                    detector._camera.clearBuffers()
                # detector._camera.clearBuffers()
                if lastChan:
                    self.lastZ = (z == self.zLength - 1)
                    if self.lastZ:
                        self.waitToMoveEvent.set()
                    else: 
                        self.waitToMoveEvent.set()
                break #stop thread execution and waits at end for other threads to finish

        if not broken:
            with errorLock:
                self.errorQ.append(False)
            if lastChan:
                self.lastZ = (z == self.zLength - 1)
                # print('All images, all channels loaded into buffer')
                if self.lastZ:
            # if lastChan:
                    self.waitToMoveEvent.set()
                else: 
                    self.waitToMoveEvent.set()

                
            rawStack = detector._camera.grabFrameSet(self.framesPerDetector, 'SIM') # receive raw image stack
            self.sigRawStackReceived.emit(np.array(rawStack),f"{processor.handle} Raw") # display raw image stack
            
            # Set sim stack for reconstruction
            processor.setSIMStack(rawStack)
            
            # Average rawe stack to make WF
            imageWF = processor.computeWFlbf(rawStack) # Why is this function in SIMProcessor?
            imageWF = imageWF.astype(np.uint16)

            
            if self.isReconstruction:
                # Pass shared attributes to SIMprocessor
                processor.setCurrentSharedAttrs(self._commChannel.sharedAttrs)
                processor.reconstructSIMStackBackgroundLBF()

            if self.tilePreview and self.isTiling:
                # if self.j == 0 and k == 0: #PROBLEM: Tiling contrast changes all channels as channels are stacked in one layer per position.
                #     self.updateWFContLimits()
                self._commChannel.sigTileImage.emit(imageWF, self.currentPos, f"{processor.handle}WF-{self.j}",self.numActiveChannels,k, self.completeFrameSets)

            if ((self.isRecordRaw) or (self.isRecordWF) or (self.isRecordRecon)) and not (self.startSettingsSaved):
                with saveLock:
                    self._commChannel.sigSaveSettingsFirst.emit()
                    self.startSettingsSaved = True

            if self.isRecordRaw:
                self.recordRawFunc(self.j, processor, self.isTiling,self.tilingRep, z, self.roiIterator)

            if self.isRecordWF:
                self.recordWFFunc(self.j, imageWF, processor, self.isTiling,self.tilingRep, z, self.roiIterator)

            if self.isRecordRecon and self.isReconstruction:
                self.recordSIMFunc(self.j, processor, self.isTiling,self.tilingRep, z, self.roiIterator)

            
            if processor.saveOneTime: #Can possibly save channels at different frame numbers. Executes as soon as possible. Not an issue for Snapshot.
                self.recordOneSetRaw(self.j, processor)
                self.recordOneSetWF(self.j, imageWF, processor)
                if self.isReconstruction:
                    self.recordOneSetSIM(self.j, processor.SIMReconstruction, processor)
                processor.saveOneTime = False

            processor.clearStack() #I dont think this needed as processor.stack is overwritten next loop



    def updateWFContLimits(self):
        # contLimitsList = []
        for i in range(len(self._widget.viewer.layers)):
            if 'WF' in self._widget.viewer.layers[i].name:
                # contLimitsList.append([self._widget.viewer.layers[i].name, self._widget.viewer.layers[i]._contrast_limits])
                self.setSharedAttr('Channel Contrast Limits', self._widget.viewer.layers[i].name, self._widget.viewer.layers[i]._contrast_limits)

    def tilingMoveThread(self):

        self.waitToMoveEvent.wait()
        self.waitToMoveEvent.clear()
        if True not in self.errorQ:
            if self.lastZ:
        # print(f'Thread {threading.current_thread().getName()} started moving')
                self.positionerXY.setPositionXY(self.nextPos[0], self.nextPos [1])
            # self.positionerXY.checkBusyLoop()
        else:
            pass

    def parseROParamsFromSLM(self, roID):
        expTimeMax = int(self.roNameList[roID].split('_')[0].split('ms')[0])*1000
        numSLMChannels = int(self.roNameList[roID].split('_')[1].split('Ch')[0])
        chansSLM = self.roNameList[roID].split('_')[2]

        return expTimeMax, numSLMChannels, chansSLM

    def setActiveSLMChannels(self,numSLMChannels, chansSLM):
        if numSLMChannels == 3:
            for processor in self.processors:
                processor.slmActive = True
        elif numSLMChannels == 1:
            for processor in self.processors:
                if str(processor.handle) == chansSLM:
                    processor.slmActive = True
                else: processor.slmActive = False
            
    
    def valueChanged(self, attrCategory, parameterName, value):
        self.setSharedAttr(attrCategory, parameterName, value)


    def makeSetupInfoDict(self):

        if self._setupInfo.sim is None:
            self._widget.replaceWithError('SIM is not configured in your setup file.')
            return
        
        setupInfo = self._setupInfo.sim
        setupInfoKeyList = [a for a in dir(setupInfo) if not a.startswith('__') and not callable(getattr(setupInfo, a))] #Pulls all attribute names from class not dunder (__) and not functions.
        setupValueList = []
        for item in setupInfoKeyList:
            setupValueList.append(getattr(setupInfo,item)) #Pulls values of the attributes.
        setupInfoDict = dict(zip(setupInfoKeyList,setupValueList)) #Put names, values in a dict.
        self._widget.setSIMWidgetFromConfig(setupInfoDict) #Call function in SIMWidget that pulls in dict just created.

        return setupInfoDict
          
    def updateProcessorParameters(self):
        self.sim_parameters = self.getSIMParametersFromGUI()
        for processor in self.processors:

            processor.setParameters(self.sim_parameters)

        self.SimProcessorLaser1.wavelength = self.sim_parameters.ReconWL1
        self.SimProcessorLaser2.wavelength = self.sim_parameters.ReconWL2
        self.SimProcessorLaser3.wavelength = self.sim_parameters.ReconWL3

    def recordOneSetRaw(self,j,processor):
        rawSavePath = os.path.join(self.exptFolderPath,'Snapshot')
        if not os.path.exists(rawSavePath):
            os.makedirs(rawSavePath)
        rawFilenames = f"f{self.frameCounter:04}_pos{j:04}_{int(processor.handle):03}_{self.exptTimeElapsedStr}_raw.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(self.rawStack,rawSavePath, rawFilenames,), daemon=True).start()
        self.saveImageInBackground(processor.stack,rawSavePath, rawFilenames)

    def recordRawFunc(self,j, processor, isTiling, tilingRep, z, roiIterator):
        if isTiling:
            rawSavePath = os.path.join(self.exptFolderPath, "Tiling", "RawStacks")
        else:
            rawSavePath = os.path.join(self.exptFolderPath, "Timelapse", "RawStacks")
        if not os.path.exists(rawSavePath):
            os.makedirs(rawSavePath)
        if isTiling:
            rawFilenames = f"f{tilingRep:04}_roi{roiIterator:03}_pos{j:04}_z{z:03}_{int(processor.handle):03}_{self.exptTimeElapsedStr}.tif"
        else:
            rawFilenames = f"f{self.frameCounter:04}_roi{roiIterator:03}_pos{j:04}_z{z:03}_{int(processor.handle):03}_{self.exptTimeElapsedStr}.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(self.rawStack,rawSavePath, rawFilenames,), daemon=True).start()
        self.saveImageInBackground(processor.stack,rawSavePath, rawFilenames)

    def recordOneSetWF(self,j,im, processor):
        wfSavePath = os.path.join(self.exptFolderPath,'Snapshot')
        if not os.path.exists(wfSavePath):
            os.makedirs(wfSavePath)
        wfFilenames = f"f{self.frameCounter:04}_pos{j:04}_{int(processor.handle):03}_{self.exptTimeElapsedStr}_WF.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames,), daemon=True).start()
        self.saveImageInBackground(im,wfSavePath, wfFilenames)

    def recordWFFunc(self,j,im, processor, isTiling, tilingRep, z, roiIterator):
        if isTiling:
            wfSavePath = os.path.join(self.exptFolderPath,"Tiling", "WF")
        else:
            wfSavePath = os.path.join(self.exptFolderPath,"Timelapse", "WF")
        if not os.path.exists(wfSavePath):
            os.makedirs(wfSavePath)
        if isTiling:
            wfFilenames = f"f{tilingRep:04}_roi{roiIterator:03}_pos{j:04}_z{z:03}_{int(processor.handle):03}_{self.exptTimeElapsedStr}.tif"
        else:
            wfFilenames = f"f{self.frameCounter:04}_roi{roiIterator:03}_pos{j:04}_z{z:03}_{int(processor.handle):03}_{self.exptTimeElapsedStr}.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames, ), daemon=True).start()
        self.saveImageInBackground(im,wfSavePath, wfFilenames)

    def recordOneSetSIM(self,j,im, processor):
        simSavePath = os.path.join(self.exptFolderPath,'Snapshot')
        if not os.path.exists(simSavePath):
            os.makedirs(simSavePath)
        simFilenames = f"f{self.frameCounter:04}_pos{j:04}_{int(processor.handle):03}_{self.exptTimeElapsedStr}_SIM.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames,), daemon=True).start()
        self.saveImageInBackground(im,simSavePath, simFilenames)

    def recordSIMFunc(self,pos_num, processor, isTiling, tilingRep, z, roiIterator):
        if isTiling:
            reconSavePath = os.path.join(self.exptFolderPath,"Tiling", "Recon")
        else:
            reconSavePath = os.path.join(self.exptFolderPath,"Timelapse", "Recon")
        if not os.path.exists(reconSavePath):
            os.makedirs(reconSavePath)
        if isTiling:
            reconFilenames = f"f{tilingRep:04}_roi{roiIterator:03}_pos{pos_num:04}_z{z:03}_{int(processor.handle):03}_{self.exptTimeElapsedStr}.tif"
        else:
            reconFilenames = f"f{self.frameCounter:04}_roi{roiIterator:03}_pos{pos_num:04}_z{z:03}_{int(processor.handle):03}_{self.exptTimeElapsedStr}.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(self.SIMReconstruction, reconSavePath,reconFilenames ,)).start()
        self.saveImageInBackground(processor.SIMReconstruction, reconSavePath,reconFilenames)

    def zScanList(self, zScanList, zOrigin):
        self.zList = zScanList
        self.zOrigin = zOrigin


    def getElapsedTimeString(self, seconds):
        ss, ms = divmod(seconds,1)

        mm, ss = divmod(ss,60)
        hh, mm = divmod(mm,60)
        _, hh = divmod(hh,24)
        ss = "{:02d}".format(int(ss))
        mm = "{:02d}".format(int(mm))
        hh = "{:03d}".format(int(hh)) 
        # dd = "{:01d}".format(int(dd))
        ms = str(round(Decimal(ms),3))[2:5]

        elapsedStr = f"{hh}h{mm}m{ss}s{ms}ms"

        return elapsedStr


    def makeExptFolderStr(self, date_in):
        userName = self._widget.getUserName()
        exptName = self._widget.getExptName()
        if not userName:
            userName = 'username'
        if not exptName:
            exptName = 'exptname'
        exptFolderName = "_".join((date_in,userName,exptName))
        exptFolderPath = os.path.join(self._widget.getRecFolder(), exptFolderName)
        return exptFolderPath      




    def populateAndSelectROList(self):
        self.roNameList = self._master.SLM4DDManager.getAllRONames()
        for i in range(len(self.roNameList)):
            self._widget.addROName(i,self.roNameList[i])
        roSelectedOnSLM = self._master.SLM4DDManager.getRunningOrder()
        self._widget.setSelectedRO(roSelectedOnSLM)

    def calibrateToggled(self):
        self.updateProcessorParameters()
        for processor in self.processors:
            processor.isCalibrated = False

    def saveOneSet(self):
            for processor in self.processors:
                processor.saveOneTime = True

    def getPeriodInSec(self):
        try:
            timingPeriodBox = float(self._commChannel.sharedAttrs[('Timing Settings', 'Timing Period')])
        except ValueError:
            timingPeriodBox = 0
        except KeyError:
            timingPeriodBox = None
        if timingPeriodBox is not None:
            timingUnit = self._commChannel.sharedAttrs[('Timing Settings', 'Timing Unit')]
            if timingUnit == 's':
                timingSecs = timingPeriodBox
            elif timingUnit == 'm':
                timingSecs = timingPeriodBox * 60
            elif timingUnit == 'h':

                timingSecs = timingPeriodBox * 3600
            return timingSecs
        return None
    
    def getDurationInSec(self):
        try:
            timingDurationBox = float(self._commChannel.sharedAttrs[('Timing Settings', 'Duration')])
        except ValueError:
            timingDurationBox = 0
        except KeyError:
            timingDurationBox = None
        if timingDurationBox is not None:
            durationUnit = self._commChannel.sharedAttrs[('Timing Settings', 'Duration Unit')]
            if durationUnit == 's':
                durationsSecs = timingDurationBox
            elif durationUnit == 'm':
                durationsSecs = timingDurationBox * 60
            elif durationUnit == 'h':

                durationsSecs = timingDurationBox * 3600
            return durationsSecs
        return None



    def toggleReconstruction(self):
        self.isReconstruction = not self.isReconstruction
        if not self.isReconstruction:
            self.isActive = False #All of these function here have this same general self variable. Probably a conflict if it was actually used.

    def toggleTilePreview(self):
        self.tilePreview = not self.tilePreview
    
    def toggleRecording(self):
        self.isRecordRaw = not self.isRecordRaw
        # print(self.isRecordRaw)
        if not self.isRecordRaw:
            self.isActive = False

    def toggleRecordWF(self):
        self.isRecordWF = not self.isRecordWF
        if not self.isRecordWF:
            self.isActive = False



    def toggleRecordReconstruction(self):
        self.isRecordRecon = not self.isRecordRecon
        if not self.isRecordRecon:
            self.isActive = False

    def openFolder(self):
        """ Opens current folder in File Explorer. """
        folder = self._widget.getRecFolder()
        if not os.path.exists(folder):
            os.makedirs(folder)
        ostools.openFolderInOS(folder)


    # def initFastAPISIM(self, params):
    #     self.fastAPISIMParams = params
    #     self.IS_FASTAPISIM = True

    #     # Usage example
    #     host = self.fastAPISIMParams["host"]
    #     port = self.fastAPISIMParams["port"]
    #     tWaitSequence = self.fastAPISIMParams["tWaitSquence"]

    #     if tWaitSequence is None:
    #         tWaitSequence = 0.1
    #     if host is None:
    #         host = "169.254.165.4"
    #     if port is None:
    #         port = 8000

    #     # self.SIMClient = SIMClient(URL=host, PORT=port)
    #     # self.SIMClient.set_pause(tWaitSequence)




    def __del__(self):
        pass
        #self.imageComputationThread.quit()
        #self.imageComputationThread.wait()

    def toggleSIMDisplay(self, enabled=True):
        self._widget.setSIMDisplayVisible(enabled)

    def monitorChanged(self, monitor):
        self._widget.setSIMDisplayMonitor(monitor)

    # def patternIDChanged(self, patternID):
    #     wl = self.getpatternWavelength()
    #     if wl == 'Laser 488nm':
    #         laserTag = 0
    #     elif wl == 'Laser 561nm':
    #         laserTag = 1
    #     elif wl == 'Laser 640nm':
    #         laserTag = 2
    #     else:
    #         laserTag = 0
    #         self._logger.error("The laser wavelength is not implemented")
    #     self.simPatternByID(patternID,laserTag)

    def getpatternWavelength(self):
        return self._widget.laser_dropdown.currentText()

    def displayMask(self, image):
        self._widget.updateSIMDisplay(image)

    def setIlluPatternByID(self, iRot, iPhi):
        self.detector.setIlluPatternByID(iRot, iPhi)

    def displaySIMImage(self, im, name):
        """ Displays the image in the view. """
        self._widget.setSIMImage(im, name=name)

    def displayRawImage(self, im, name):
        """ Displays the image in the view. """
        self._widget.setRawImage(im, name)

    def displayWFImage(self, im, name):
        """ Displays the image in the view. """
        self._widget.setWFImage(im, name)
    
    # def updateROIsize(self): #CTFIX
    #     # FIXME: Make it so calibration of only the modified detector is 
    #     # toggled False
    #     # Each time size is changed on chip, calibration needs to be reset
    #     processors = self.allProcessors
    #     if processors != []:
    #         for processor in processors:
    #             processor.isCalibrated = False
    
    def saveParams(self):
        pass

    def loadParams(self):
        pass

    def stopSIM(self):
        self._commChannel.sigSIMAcqToggled.emit(False)
        self._widget.stop_button.setEnabled(False)
        self._widget.startSIM_button.setEnabled(True)
        self.active = False
        self._commChannel.updateSIMActive(self.active)
        self.simThread.join()
        for laser in self.lasers:
            laser.setEnabled(False)
        self._master.arduinoManager.deactivateSLMWriteOnly()
        for detector in self.detectors:
            detector.stopAcquisitionSIM()
            detector._camera.setPropertyValue('AcquisitionFrameRate', float(5), toPrint=False)
        if self.isTiling:
            self.positionerXY.setPositionXY(self.tileOrigin[0], self.tileOrigin[1])
            self.isTiling = False
        if self.zScanActive:
            self.positioner.setPosition(self.zOrigin, 'Z')
            self._commChannel.sigUpdateZPosition.emit('Z','Z')


    def startSIM(self):

        # start the background thread
        # for detector in self.detectors:
        #     detector.stopAcquisition()
        self._commChannel.sigSIMAcqToggled.emit(True)
        self._widget.stop_button.setEnabled(True)
        self._widget.startSIM_button.setEnabled(False)
        self.active = True
        self._commChannel.updateSIMActive(self.active)

        simParametersFromGUI = self.getSIMParametersFromGUI()
        #sim_parameters["reconstructionMethod"] = self.getReconstructionMethod()
        #sim_parameters["useGPU"] = self.getIsUseGPU()
        
        # Clear logger files before start of experiment
        self.log_times_loop = []

        
        # self._commChannel.sharedAttrs._data[('Detector','488 Cam','ROI')][2:]

        self.simThread = threading.Thread(target=self.performSIMExperimentThread, args=(simParametersFromGUI,), daemon=True)
        self.simThread.start()

    def start25D(self):


        self._commChannel.sigSIMAcqToggled.emit(True)
        self._widget.stop_button.setEnabled(True)
        self._widget.startSIM_button.setEnabled(False)
        self.active = True
        self._commChannel.updateSIMActive(self.active)
        
        # Clear logger files before start of experiment
        self.log_times_loop = []

        
        # self._commChannel.sharedAttrs._data[('Detector','488 Cam','ROI')][2:]

        self.simThread = threading.Thread(target=self.perform25DExperimentThread, args=(), daemon=True)
        self.simThread.start()



        
    def getTilingSettings(self):
        self.startxpos, self.startypos = self.positionerXY.get_abs()
        self.num_grid_x = int(self.sharedAttrs[('Tiling Settings','Steps - X')])
        self.num_grid_y = int(self.sharedAttrs[('Tiling Settings','Steps - Y')])
        self.overlap = float(self.sharedAttrs[('Tiling Settings','Overlap')])
        # self.reconFramesSkipped = int(self.sharedAttrs[('Timing Settings','Repetitions')])

    def getParameterValue(self, detector, parameter_name):
        detector_name = detector._DetectorManager__name
        shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
        if parameter_name == 'ExposureTime':
            value = float(shared_attributes[('Detector', detector_name, 'Param', parameter_name)])
        else:
            self._logger.warning("Debuging needed.")
            self._logger.debug(f"Parameter {parameter_name} not set up in getParameterValue!")
        return value
    
    def setCamForExperimentSIM(self, detector, num_buffers, expTimeMax):


        detector._camera.setPropertyValue('AcquisitionFrameRate', 5.0)
        trigger_source = 'Line2'
        trigger_mode = 'On'
        exposure_auto = 'Off'
        gamma = 1.0

        # Pull the exposure time from settings widget
        exposure_time = self.getParameterValue(detector, 'ExposureTime')

        # exposure_time = self.exposure # anything < 19 ms
        pixel_format = 'Mono16'
        bit_depth = 'Bits12'
        frame_rate_enable = True
        buffer_mode = "OldestFirst"

        # Check if exposure is low otherwise set to max value
        exposure_limit = expTimeMax # us
        if exposure_time > exposure_limit:
            exposure_time = float(exposure_limit)
            self.exposure = exposure_time
            self._logger.warning(f"Exposure time set > {exposure_limit/1000:.2f} ms (SLM running order limited). Setting exposure tme to {exposure_limit/1000:.2f} ms on {detector.name}")
        
        #Calc Acq Frame Rate
        frame_rate = 1000000/exposure_limit*.95


        # Set cam parameters
        dic_parameters = {'TriggerSource':trigger_source, 'TriggerMode':trigger_mode, 'ExposureAuto':exposure_auto, 'ExposureTime':exposure_time, 'Gamma':gamma, 'PixelFormat':pixel_format, 'AcquisitionFrameRateEnable':frame_rate_enable, 'AcquisitionFrameRate':frame_rate,'StreamBufferHandlingMode':buffer_mode,'ADCBitDepth':bit_depth}

        # for detector in detectors:
        for parameter_name in dic_parameters:
            # print(detector._camera.getPropertyValue(parameter_name))
            detector._camera.setPropertyValue(parameter_name, dic_parameters[parameter_name])
            if parameter_name == 'ExposureTime':
                self._commChannel.sigWriteParamsFromCam.emit(detector, dic_parameters[parameter_name])
            # print(detector._camera.getPropertyValue(parameter_name))
        # detector.tl_stream_nodemap['StreamBufferHandlingMode'].value = buffer_mode
        detector.startAcquisitionSIM(num_buffers)

    def setCamForExperiment25D(self, detector):


        detector._camera.setPropertyValue('AcquisitionFrameRate', 150.0)
        trigger_mode = 'On'
        exposure_auto = 'Off'
        gamma = 1.0
        trigger_source = 'Line2'

        # Pull the exposure time from settings widget
        # exposure_time = self.getParameterValue(detector, 'ExposureTime')

        # exposure_time = self.exposure # anything < 19 ms
        pixel_format = 'Mono16'
        bit_depth = 'Bits12'
        frame_rate_enable = True
        buffer_mode = "NewestOnly"
        triggerSelector = 'ExposureActive'

        # Set cam parameters
        dic_parameters = {'AcquisitionFrameRateEnable':frame_rate_enable,  'TriggerSelector': triggerSelector,'TriggerSource':trigger_source,'TriggerMode':trigger_mode,'Gamma':gamma, 'PixelFormat':pixel_format, 'StreamBufferHandlingMode':buffer_mode,'ADCBitDepth':bit_depth}

        # for detector in detectors:
        for parameter_name in dic_parameters:
            # print(detector._camera.getPropertyValue(parameter_name))
            detector._camera.setPropertyValue(parameter_name, dic_parameters[parameter_name])
            # if parameter_name == 'ExposureTime':
            #     self._commChannel.sigWriteParamsFromCam.emit(detector, dic_parameters[parameter_name])
            # print(detector._camera.getPropertyValue(parameter_name))
        # detector.tl_stream_nodemap['StreamBufferHandlingMode'].value = buffer_mode
        detector.startAcquisition25D()

    #@APIExport(runOnUIThread=True)
    def sim_getSnapAPI(self, mystack):
        mystack.append(self.detector.getLatestFrame())
        #print(np.shape(mystack))

    def metadataCollector(self):
        """Grabs all metadata from sharedAttributes and returns metadata
        dictionary and resolution vector
        Returns:
            tuple: pixelsize in the right format for imageJ to show it
            dict: dictionary od metadata in OEM format, readable by BioFormats
        """
        # --------------------------Set your export--------------------------
        
        units = "um"
        psz = 0.123 # in selected units
        single_channel_names = ["488"] # If multichannel image, all can names
        posX = 0.1 # in selected units
        posY = 0.3 # in selected units
        posZ = 0.5 # in selected units
        # Generate the date in right format
        now = datetime.now()
        # OEM docs say the date should be in this form, so I am keeping it
        now_string = "{}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)
        # now_string = "{}_{:02d}_{:02d}-{:02d}.{:02d}.{:02d}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)
        
        # --------------------------Set your export--------------------------
        
        # imageJ metadata format
        resolution=(1./psz, 1./psz)
        
        # mix of imageJ and OEM data format (axes and units are in imageJ format)
        # TODO: Will maybe need to change to one, I've read there can be conflicts
        metadata = {
                        # Not sure where this one is from - same syntax for both
                        # "axes": "YX",
                        # ImageJ format export
                        "Labels": single_channel_names, # ImageJ export
                        "unit": units, # ImageJ export
                        # OEM format exports
                        'Pixels': {
                            'PhysicalSizeX': psz,
                            'PhysicalSizeXUnit': units,
                            'PhysicalSizeY': psz,
                            'PhysicalSizeYUnit': units
                        },
                        "Channel": {"Name": single_channel_names},
                        'Plane': {
                            'PositionX': posX, 'PositionXUnit': units,
                            'PositionY': posY, 'PositionYUnit': units,
                            'PositionZ': posZ, 'PositionZUnit': units,
                            },
                        "AcquisitionDate": now_string
                        }
        return resolution, metadata

    def saveImageInBackground(self, image, path, filename):
        # print(threading.current_thread())
        # ijmetadata = {'data_shape':image.shape}
        try:
            # self.folder = self._widget.getRecFolder()
            filename = os.path.join(path,filename) 
            image = np.array(image)
            
            # Grab metadata
            resolution_grab, metadata_grab = self.metadataCollector()
            
            tif.imwrite(filename, image, resolution = resolution_grab,
                        metadata = metadata_grab, imagej=True)
            # tif.imwrite(filename, image, imagej=True)
            # tif.imwrite(filename, image, metadata=ijmetadata)
            self._logger.debug("Saving file: " + filename)
        except  Exception as e:
            self._logger.error(e)

    def getSIMParametersFromGUI(self):
        ''' retrieve parameters from the GUI '''
        sim_parameters = self.sim_parameters


        # Copies current widget values to the SIMParameters object
        sim_parameters.ReconWL1 = np.float32(self._widget.ReconWL1_textedit.text())/1000
        sim_parameters.ReconWL2 = np.float32(self._widget.ReconWL2_textedit.text())/1000
        sim_parameters.ReconWL3 = np.float32(self._widget.ReconWL3_textedit.text())/1000
        sim_parameters.Pixelsize = np.float32(self._widget.pixelsize_textedit.text())
        sim_parameters.NA = np.float32(self._widget.NA_textedit.text())
        sim_parameters.Alpha = np.float32(self._widget.alpha_textedit.text())
        sim_parameters.Beta = np.float32(self._widget.beta_textedit.text())
        sim_parameters.w = np.float32(self._widget.w_textedit.text())
        sim_parameters.eta = np.float32(self._widget.eta_textedit.text())
        sim_parameters.n = np.float32(self._widget.n_textedit.text())
        sim_parameters.Magnification = np.float32(self._widget.magnification_textedit.text())
        sim_parameters.saveDir = self._widget.path_edit.text()
        return sim_parameters
    
    def perform25DExperimentThread(self):
        """
        Select a sequence on the SLM that will choose laser combination.
        Run the sequence by sending the trigger to the SLM.
        Run continuous on a single frame. 
        Run snake scan for larger FOVs.
        """
        


        # Check if lasers are set and have power in them select only lasers with powers
        poweredLasers = []
        for laser in self.lasers:
            if laser.percentPower > 0:
                poweredLasers.append(laser.wavelength)

        projCamPixelSize = 0.12331 # This may be very slightly miscalced (sig figs). Conversion to pixel space gives 512.05, not 512.

        #Get the parameters that go into the createXYGridPositionArray function
        self.getTilingSettings()
        # self._commChannel.sigCalcPositionArray.emit()
        roiOriginList = []

        if int(self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]) == 2:
            self.isTiling = True
        else:
            self.isTiling = False

        if int(self.sharedAttrs[('ROI List', 'Checkbox')]) == 2:
            self.isScanROI = True
        else:
            self.isScanROI = False

        if self.isScanROI:
            try:
                roiOriginList = self.getOrigins()
            except KeyError:
                self._logger.warning('ROI list is empty.')

        self.tileOrigins = []
        positions = self._master.tilingManager.createXYGridPositionArrayWithROI(self.num_grid_x, self.num_grid_y, self.overlap, self.startxpos, self.startypos, projCamPixelSize, roiOriginList)
        for i in range(len(positions)):
            self.tileOrigins.append(positions[i][-1])
        
        self.tileOrigin = positions[0][-1]




        if not self.isTiling:
            positions = self.tileOrigins
        
        #Get Z-Stack list
        if self._commChannel.sharedAttrs._data[('Z-Stack Settings', 'Z-Stack Checkbox')] == '0':
            self.zScanActive = False
            zList = [self._commChannel.sharedAttrs._data[('Positioner', 'Z', 'Z', 'Position')]]
            self.zLength = len(zList)
        elif self._commChannel.sharedAttrs._data[('Z-Stack Settings', 'Z-Stack Checkbox')] == '2':
            self.zScanActive = True
            zList = self.zList
            self.zLength = len(zList)
            #zOrigin stored as self.zOrigin already


        ''' # For nameing tiling squares A1, A2, .....C5 etc.
        # gridNamesX = [str(x+1) for x in range(self.num_grid_x)]
        # gridNamesY = list(string.ascii_uppercase)[:self.num_grid_y]
        # test = []
        # for item in gridNamesY:
        #     for value in gridNamesX:
        #         test.append(item+value)
        '''
        
        # Datetime string registered when start button is pressed only.
        dateTimeStartClick = datetime.now().strftime("%y%m%d_%H%M%S")
    
        
        self.numAllFrames = 0 # Number of frames, including dropped frames
        self.completeFrameSets = 0 # Number of frames, exncluding dropped frames

        self.frameCounter = 0
        #Set tiling flag, determines whether program will enter the tiling code.


        self.numActiveChannels = len(poweredLasers)
        
        # Get max exposure time from the selected RO on SLM. This is done with naming structure. Name must start with numerical digits, then 'ms'. *1000 to make us.
        self.activeProcessors = []
        for processor in self.processors:
            # if processor.slmActive == True:
            self.activeProcessors.append(processor)
            for detector in self.detectors:
                if processor.handle == detector._wavelength:
                    processor.detObj = detector
        for k, processor in enumerate(self.activeProcessors):
            processor.processorIndex = k



        # -------------------Set-up cams-------------------

        # FIXME: Automate buffer size calculation based on image size, it did not work before
        # total_buffer_size_MB = 350 # in MBs
        for detector in self.detectors:
            # image_size = detector.shape
            # image_size_MB = (2*image_size[0]*image_size[1]/(1024**2))
            # buffer_size = int(total_buffer_size_MB // image_size_MB)
            # buffer_size = 9
            self.setCamForExperiment25D(detector)
        

        time_global_start = time.time()
        # time_whole_start = time_global_start
        # self.processors2 = self.processors[0]
        # self.processors2 = [self.processors2]

        self._master.arduinoManager.activate25DWriteOnly() #This command activates the arduino to be ready to receive triggers.
       # 0.01s time delay built into activate SLM function. trigOneSequence() cannot be called too fast. Only adds to very first loop time. 1 ms was not enough. If query is waited for, value is 0.02
        self.tilingRep = 0
        timingPeriodInSec = self.getPeriodInSec()
        durationInSec = self.getDurationInSec()
        totalEndTime = 0
        self.startSettingsSaved = False
        current25DTiming = '100'
        self._master.arduinoManager.update25DTimingWriteOnly(current25DTiming)
        # time.sleep(1)
        while self.active and poweredLasers != []:
            

            self.exptFolderPath = self.makeExptFolderStr(dateTimeStartClick)
            self.setSharedAttr('User Dir Info', 'Current Path', self.exptFolderPath)
            self._commChannel.updateActiveDirectory(self.exptFolderPath)

            # Scan over all positions generated for grid
            

            if self.completeFrameSets != 0 and timingPeriodInSec is not None:
                repTimer = time.time() - repTimerStart
                while repTimer < timingPeriodInSec:
                    time.sleep(.1)
                    repTimer = time.time() - repTimerStart
                    if self._widget.stop_button.isChecked(): #allows exit of SIM loops once per cycle
                        self._widget.stop_button.setChecked(False)
                        return
            repTimerStart = time.time()

            self.roiIterator = 0

            while self.roiIterator < len(positions):
                j = 0 # Position iterator
                oneROI = positions[self.roiIterator]

                if (not self.isTiling) and (not self.isScanROI):
                    oneROI = [oneROI]


                while j < len(oneROI):
                    self.j = j
                    if self.numAllFrames == 0:
                        exptTimeElapsed = 0.0
                    else:
                        exptTimeElapsed = time.time() - time_global_start
                    self.exptTimeElapsedStr = self.getElapsedTimeString(exptTimeElapsed)
                    self._commChannel.storeCurrentTimeString(self.exptTimeElapsedStr)
                    self.nextPos = oneROI[self.j]
                    self.currentPos = oneROI[self.j-1]
                    self.positionerXY.checkBusyLoop()


                    if j == 0 and self.completeFrameSets != 0 and self.isTiling:
                        time.sleep(.5) #TODO: Change to calibrate by distance needed to move
                    # elif (j==0) and (self.completeFrameSets == 0):
                    #     pass
                    else:
                        time.sleep(.05) #can probablz reduct slightly
                    z = 0
                    while z < len(zList):
                    # for z in range(len(zList)):
                        if self.zScanActive:
                            self.positioner.setPosition(zList[z], 'Z')
                            self._commChannel.sigUpdateZPosition.emit('Z','Z')

                        timestart = time.time()
                                        
                        # Trigger SIM set acquisition. Will trigger as many channels are as on SLM.
                        
                        
  
                        errorLock = threading.Lock() #Lock for passing whether channel received all 9 images
                        saveLock = threading.Lock()
                        self.errorQ = [] #List to be populated with error results from within processor threads
                        self.waitToMoveEvent = threading.Event() #When the last camera receives its images, this signal will fire to the positioner, moving the stage.

                        with ThreadPoolExecutor(max_workers=4) as executor: #
                            if self.isTiling:
                                executor.submit(self.tilingMoveThread)
                            for processor in self.activeProcessors:
                                    executor.submit(self.main25DLoop, processor, errorLock, z, saveLock)

                        if self._widget.stop_button.isChecked(): #allows exit of SIM loops once per cycle
                            # self.stopSIM()
                            self._widget.stop_button.setChecked(False)
                            return

                        self.numAllFrames += 1
                        if True not in self.errorQ:
                            self.completeFrameSets += 1 # increment only if no errors reported from processor threads
                            z += 1 # this controls positions. Increment only if successful. Repeat same location if any one camera fails.
                        loopEndTime = time.time()-timestart
                        print(loopEndTime)
                        self._logger.debug('Dropped frames: {}'.format(self.numAllFrames-self.completeFrameSets))
                        self._logger.debug('Total frames: {}'.format(self.numAllFrames))
                        
                    # self.completeFrameSets += 1 # increment only if no errors reported from processor threads
                    j += 1 # this controls positions. Increment only if successful. Repeat same location if any one camera fails.


                    
                    if self.sharedAttrs[('Timing Settings','Rep Checkbox')]==2 and not (self.completeFrameSets + 1 < len(oneROI)*int(self.sharedAttrs[('Timing Settings','Repetitions')])): 
                        self._commChannel.sigStopSim.emit() # Stops tiling reps after all tiles*repetitions is done.

                    totalEndTime = time.time()-time_global_start
                    remainder = self.completeFrameSets % len(oneROI)

                    if self.sharedAttrs[('Timing Settings','Duration Checkbox')]==2 and durationInSec != 0 and durationInSec < totalEndTime:
                        if self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]=='0':
                            self._commChannel.sigStopSim.emit()
                        if self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]=='2' and remainder == 0:
                            self._commChannel.sigStopSim.emit()



                self.frameCounter += 1


                self.tilingRep += 1

                self.roiIterator += 1
                
                print(f'total time: {totalEndTime}')
            


        

    def main25DLoop(self, processor, errorLock, z, saveLock):
        # saveOneTime = self.saveOneTime
        # print(saveOneTime)

        k = processor.processorIndex
        if k+1 == len(self.activeProcessors):
            lastChan = True
        else: 
            lastChan = False

        broken = False
        
        # Set current detector being used
        detector = processor.detObj
        # time.sleep(0.1)
######TIMING BUFFER WAITING LOGIC BREAKS DOWN AT FAST SPEEDS. NEED DIFFERENT WAY.
        # time.sleep(self.expTimeMax/1000000*(k)*20) #approximately how long it will start for detector to start receiving images in buffer.
        # waitingBuffers = detector._camera.getBufferValue()

        # waitingBuffersEnd = 0
        # bufferStartTime = time.time()
        # broken = False
        # time.sleep(self.expTimeMax/1000000*16)
        # time.sleep(1)
        # while waitingBuffers != 9:
        #     time.sleep(self.expTimeMax/1000000)
        #     waitingBuffers = detector._camera.getBufferValue() #FIXME This logic does not include a way to remove saved images for first 2 cams if for example the thrid cam fails
        #     if waitingBuffers != waitingBuffersEnd:
        #         bufferStartTime = time.time()
        #         bufferEndTime = time.time()
        #     else: 
        #         bufferEndTime = time.time()
        #     bufferTotalTime = bufferEndTime-bufferStartTime
        #     waitingBuffersEnd = waitingBuffers
        #     if waitingBuffers != 9 and bufferTotalTime > self.expTimeMax/250000: #self.expTimeMax/250000 = 4x exp time in correct units
        #         self._logger.error(f'Frameset thrown in trash. Buffer available is {waitingBuffers} on detector {detector.name}')
        #         broken = True
        #         with errorLock:
        #             self.errorQ.append(True)
        #         for detector in self.detectors: # probably move this outside of thread structure, seems like it could be unsafe.
        #             detector._camera.clearBuffers()
        #         # detector._camera.clearBuffers()
        #         if lastChan:
        #             self.lastZ = (z == self.zLength - 1)
        #             if self.lastZ:
        #                 self.waitToMoveEvent.set()
        #             else: 
        #                 self.waitToMoveEvent.set()
        #         break #stop thread execution and waits at end for other threads to finish
        broken = False
        if not broken:
            with errorLock:
                self.errorQ.append(False)
            if lastChan:
                self.lastZ = (z == self.zLength - 1)
                # print('All images, all channels loaded into buffer')
                if self.lastZ:
            # if lastChan:
                    self.waitToMoveEvent.set()
                else: 
                    self.waitToMoveEvent.set()

            # print(detector)
            rawStack = detector._camera.grabFrameSet(1) # receive raw image stack
            # rawStack = np.random.rand(1024, 1024)*4095
            # print(rawStack)
            self.sigRawStackReceived.emit(np.array(rawStack),f"{processor.handle} Raw") # display raw image stack
            
            # Set sim stack for reconstruction
            # processor.setSIMStack(rawStack)
            
            # Average rawe stack to make WF
            # imageWF = processor.computeWFlbf(rawStack) # Why is this function in SIMProcessor?
            # imageWF = imageWF.astype(np.uint16)

            
            # if self.isReconstruction:
                # Pass shared attributes to SIMprocessor
                # processor.setCurrentSharedAttrs(self._commChannel.sharedAttrs)
                # processor.reconstructSIMStackBackgroundLBF()

            # if self.tilePreview and self.isTiling:
            #     # if self.j == 0 and k == 0: #PROBLEM: Tiling contrast changes all channels as channels are stacked in one layer per position.
            #     #     self.updateWFContLimits()
            #     self._commChannel.sigTileImage.emit(imageWF, self.currentPos, f"{processor.handle}WF-{self.j}",self.numActiveChannels,k, self.completeFrameSets)

            if ((self.isRecordRaw)) and not (self.startSettingsSaved):
                with saveLock:
                    self._commChannel.sigSaveSettingsFirst.emit()
                    self.startSettingsSaved = True

            if self.isRecordRaw:
                self.recordRawFunc(self.j, processor, self.isTiling,self.tilingRep, z, self.roiIterator)

            # if self.isRecordWF:
            #     self.recordWFFunc(self.j, imageWF, processor, self.isTiling,self.tilingRep, z, self.roiIterator)

            # if self.isRecordRecon and self.isReconstruction:
            #     self.recordSIMFunc(self.j, processor, self.isTiling,self.tilingRep, z, self.roiIterator)

            
            if processor.saveOneTime: #Can possibly save channels at different frame numbers. Executes as soon as possible. Not an issue for Snapshot.
                self.recordOneSetRaw(self.j, processor)
                # self.recordOneSetWF(self.j, imageWF, processor)
                # if self.isReconstruction:
                #     self.recordOneSetSIM(self.j, processor.SIMReconstruction, processor)
                processor.saveOneTime = False

            processor.clearStack() #I dont think this needed as processor.stack is overwritten next loop




    
    # def createLogFile(self):
    #     if self._widget.checkbox_logging.isChecked():
    #         dir_save = os.path.join(self.exptFolderPath,"logging")
    #         if not os.path.exists(dir_save):
    #             os.makedirs(dir_save)
    #         export_name = os.path.join(dir_save,"log_file.xlsx")
            
    #         # Loop time logging
    #         t_loop = np.transpose(self.log_times_loop)
    #         t_loop_column_names = ["frame","loop time [s]"]
    #         df = pd.DataFrame(data=t_loop, index=t_loop_column_names).T
    #         df.to_excel(export_name, sheet_name="Sheet1")
    
    # def getReconstructionMethod(self):
    #     return self._widget.SIMReconstructorList.currentText()

    # def getIsUseGPU(self):
    #     return self._widget.useGPUCheckbox.isChecked()
    
    # def valueChanged(self, parameterName, value):
    #     self.setSharedAttr(parameterName, _valueAttr, value)
    
    # def attrChanged(self, key, value):
    #     #BK EDIT - not sure we will use this in our case
    #     if self.settingAttr or len(key) != 3 or key[0] != _attrCategory:
    #         return

    #     parameterName = key[1]
    #     if key[2] == _valueAttr:
    #         # FIXME: not set up yet just a place holder
    #         self.setParameter(parameterName, value)
    
    def setSharedAttr(self, attrCategory, parameterName, value):
        """Sending attribute to shared attributes

        Args:
            parameterName (str): name of a parameter passed from wdiget
            attr (_type_): type of a attribute (value, enabled, ...)
            value (_type_): value of the parameter read from wdiget
        """
        self.settingAttr = True
        try:
            self._commChannel.sharedAttrs[(attrCategory, parameterName)] = value
        finally:
            self.settingAttr = False
            
    # def setParameter(self, parameterName, value):
    #     # FIXME: Just a place holder
    #     self._logger.error(f"{parameterName} with {value} not set! Setting of SIM parameters using attrChanged in widget is not set up yet.")