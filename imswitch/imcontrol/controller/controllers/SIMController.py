import os
import numpy as np
import time
import threading
from datetime import datetime
import tifffile as tif
import time
import numpy as np
from decimal import Decimal
from .SIMProcessor import SIMProcessor, SIMParameters
from concurrent.futures import ThreadPoolExecutor
from imswitch.imcommon.model import initLogger, ostools
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController
from imswitch.imcommon.framework import Signal
import statistics

class SIMController(ImConWidgetController):
    """Linked to SIMWidget."""

    sigRawStackReceived = Signal(np.ndarray, str)
    sigRawImgReceived = Signal(np.ndarray, str)
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
        self.SimProcessorLaser4 = SIMProcessor(self, self.sim_parameters, wavelength=488)
        self.SimProcessorLaser1.exWavelength = 488 #This handle is used to keep naming consistent when wavelengths may change.
        self.SimProcessorLaser2.exWavelength = 561
        self.SimProcessorLaser3.exWavelength = 640
        self.SimProcessorLaser4.exWavelength = 488
        self.SimProcessorLaser1.handle = str(self.SimProcessorLaser1.exWavelength) + 'F'
        self.SimProcessorLaser2.handle = str(self.SimProcessorLaser2.exWavelength) + 'F'
        self.SimProcessorLaser3.handle = str(self.SimProcessorLaser3.exWavelength) + 'F'
        self.SimProcessorLaser4.handle = str(self.SimProcessorLaser4.exWavelength) + 'S'
        self.SimProcessorLaser1.source = 'fluor'
        self.SimProcessorLaser2.source = 'fluor'
        self.SimProcessorLaser3.source = 'fluor'
        self.SimProcessorLaser4.source = 'scatter'
        self.SimProcessorLaser1.roOrder = 1
        self.SimProcessorLaser2.roOrder = 2
        self.SimProcessorLaser3.roOrder = 3
        self.SimProcessorLaser4.roOrder = 1
        self.processors = [self.SimProcessorLaser1,self.SimProcessorLaser2,self.SimProcessorLaser3,self.SimProcessorLaser4] #processor object list
        self.detectors = []
        for detector in self._master.detectorsManager: #detector object list
            if detector[1]._DetectorManager__forAcquisition:
                fullName = detector[0]
                shortName = fullName[:5].replace(" ", "")
                detector[1].handle = shortName
                self.detectors.append(detector[1])

        # Signals originating from SIMController.py        
        self.sigRawStackReceived.connect(self.displayRawImage)
        self.sigRawImgReceived.connect(self.displayRawImage)

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
        # self._commChannel.sigStop25D.connect(self.stop25D) #CTNOTE, was stopping everything twice. Unknown is causing problems.
        self._commChannel.sigStart25D.connect(self.start25D)
        self._commChannel.sigRecordPSFStack.connect(self.recordPSFStackSetFlag)

        self._commChannel.sigSIMAcqToggled.connect(self._widget.toggleBoxes)

        self._commChannel.sigAutoZernikeFinished.connect(self.AZFinished)

        self.AFCam = self._master.detectorsManager._subManagers['AF Cam']


        #Get RO names from SLM4DDManager and send values to widget function to populate RO list, selects currently active RO. (default or last used if not powered down)
        try:
            self.populateAndSelectROList()
        except TypeError:
            self._logger.error('Running order could not be set on SIM SLM.')
        #Get save directory root from config file and populate text box in SIM widget.
        self._widget.setUserDirInfo(setupInfoDict['saveDir'])
        
        # self.setSharedAttr(attrCategory, parameterName, value):
        self.sharedAttrs = self._commChannel.sharedAttrs._data
        self.AFManager = self._master.autofocusManager

        self.recordPSFStackFlag = False

    def recordPSFStackSetFlag(self):
        self.recordPSFStackFlag = True

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
        #CTNOTE: Change to dynamic
        projCamPixelSize = 2.74 / (200 / 9) # 2.74 is cam pixel size. 200 is the true obj tube lens length, 9 is effective focal length of 20x Olympus UPlanApoX objective.
        #Check is scatter cam should be active
        if self._commChannel.scatterCamActive == 2:
            self.scatterCam = True
        else: 
            self.scatterCam = False
        #   
        self.sim_parameters = sim_parameters #Make starting parameters available to all of SIMController.py
        # Create list of powered (active) lasers.
        poweredLasers = []
        for laser in self.lasers:
            if laser.percentPower > 0:
                poweredLasers.append(str(laser.wavelength)+'F')
        if '488F' in poweredLasers and self.scatterCam:
            poweredLasers.append(str('488S'))
        #
        self.getTilingSettings()   #Get the parameters that go into the createXYGridPositionArray function
        ####Set flags for using in logic later.
        if int(self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]) == 2:
            self.isTiling = True
        else:
            self.isTiling = False

        roiOriginList = []
        if int(self.sharedAttrs[('ROI List', 'Checkbox')]) == 2:
            self.isScanROI = True
            try:
                roiOriginList = self.getOrigins()
            except KeyError:
                self._logger.warning('ROI list is empty.')
        else:
            self.isScanROI = False

        if self._commChannel.sharedAttrs._data[('Z-Stack Settings', 'Z-Stack Checkbox')] == '0':
            self.zScanActive = False
            zList = [self._commChannel.sharedAttrs._data[('Positioner', 'Z', 'Z', 'Position')]]
        elif self._commChannel.sharedAttrs._data[('Z-Stack Settings', 'Z-Stack Checkbox')] == '2':
            self.zScanActive = True
            zList = self.zList
        # Set running order on SLM
        roID = self._widget.getSelectedRO()
        self._master.SLM4DDManager.setRunningOrder(roID)
        # Get max exposure time from the selected RO on SLM. This is done with naming structure. Name must start with numerical digits, then 'ms'. *1000 to make us.
        self.expTimeMax, self.numSLMChannels, chansSLM = self.parseROParamsFromSLM(roID)
        expectedLoopTime = ((self.expTimeMax*18*self.numSLMChannels)+(20*3))/1000000*1.15
        self.setActiveSLMChannels(self.numSLMChannels, chansSLM)

        #### Set attributes to processors and select only active processors (processors with powered lasers).
        self.activeProcessors = []
        for processor in self.processors:
            for detector in self.detectors:
                if processor.handle == detector.handle:
                    processor.detObj = detector
                    processor.shape = detector._shape

            if (processor.slmActive == True) and (processor.handle in poweredLasers): #Is "(processor.slmActive == True)" needed?
                self.activeProcessors.append(processor)
        
        if len(self.activeProcessors) == 0:
            self._logger.error("No active laser/detector combinations. Check SLM running order and laser power.")
            self.stopSIM()
            return
        
        shapeList = []
        for k, processor in enumerate(self.activeProcessors):
            processor.processorIndex = k
            shapeList.append(processor.shape)
        if ('488S' in poweredLasers):
            self.SimProcessorLaser4.processorIndex = 0 #Assumed 488 is index 0
        ####

        #### Confirm the used area of all active cam sensors are the same. Stop the process if not.
        
        setShapeList = set(shapeList) # Send to set which removes duplicate values. The length should be one is values are the same.
        if len(setShapeList) != 1:
            self._logger.error("Detector image shapes must be the same.")
            self.stopSIM()
            return
        shapeList = list(setShapeList)[0] #Put back into list form to be used to calculate tiling positions.
        ####


        ####
        self.tileOrigins = []
        positions = self._master.tilingManager.createSnakeArrays(self.num_grid_x, self.num_grid_y, self.overlap, self.startxpos, self.startypos, projCamPixelSize, roiOriginList, shapeList)
        for i in range(len(positions)):
            self.tileOrigins.append(positions[i][0])
        self.tileOrigin = positions[0][0]
        if not self.isTiling:
            positions = self.tileOrigins
        ####


        # Set all SIM parameters from GUI to each processor. All will be the same, except Recon WL
        self.updateProcessorParameters()

        #### Flags for state control, constant varables, this that need one time initialization.
        self.zLength = len(zList)
        self.numAllFrames = 0 # Number of frames, including dropped frames
        self.completeFrameSets = 0 # Number of frames, exncluding dropped frames
        self.framesPerDetector = 9
        self.frameCounter = 0
        dateTimeStartClick = datetime.now().strftime("%y%m%d_%H%M%S")
        time_global_start = time.time()
        self.tilingRep = 0
        isTimed = bool(int(self._commChannel.sharedAttrs._data[('Timing Settings', 'Period Checkbox')]))
        if isTimed: timingPeriodInSec = self.getPeriodInSec()
        timingPeriodInSec = self.getPeriodInSec()
        durationInSec = self.getDurationInSec()
        totalEndTime = 0
        self.startSettingsSaved = False
        completeZ = 0
        self.firstLoop = True

        startLoopTime = time.time()
        
        self._master.arduinoManager.activateSLMWriteOnly() #This command activates the arduino to be ready to receive triggers.
        # FIXME: Automate buffer size calculation based on image size, it did not work before
        # total_buffer_size_MB = 350 # in MBs
        for processor in self.activeProcessors:
            detector = processor.detObj
            # image_size = detector.shape
            # image_size_MB = (2*image_size[0]*image_size[1]/(1024**2))
            # buffer_size = int(total_buffer_size_MB // image_size_MB)
            buffer_size = 20 # Slightly more than double expected. If only set at 9, may miss information when it doesn't work well.
            self.setCamForExperimentSIM(detector, buffer_size, self.expTimeMax)
        self.exptFolderPath = self.makeExptFolderStr(dateTimeStartClick)
        self.setSharedAttr('User Dir Info', 'Current Path', self.exptFolderPath)
        self._commChannel.updateActiveDirectory(self.exptFolderPath)

        while self.SIMActive:

            self.roiIter = 0

            #### For timing period. Check every 1/10s if period time is exceeded yet.
            if self.completeFrameSets != 0:
                repTimer = time.time() - repTimerStart
                while repTimer < expectedLoopTime:
                    time.sleep(expectedLoopTime / 1000)
                    repTimer = time.time() - repTimerStart

            if self.completeFrameSets != 0 and isTimed: #Does not exceute on first loop
                repTimer = time.time() - repTimerStart

                if timingPeriodInSec < 100:
                    waitTime = timingPeriodInSec / 100
                else:
                    waitTime = 1

                if timingPeriodInSec > 30: 
                    self._logger.info(f'Timing based acquisition. Timing period is {timingPeriodInSec} seconds.')
                while (repTimer < timingPeriodInSec):
                    time.sleep(waitTime / 100)
                    repTimer = time.time() - repTimerStart

                    if self._widget.stop_button.isChecked(): #allows exit of the loop
                        self._widget.stop_button.setChecked(False)
                        self.stopSIM()
                        return
            repTimerStart = time.time()
            ####

            while self.roiIter < len(positions):

                #### Set variables for current and next positions. These will be used to move stage XY.
                currentROI = positions[self.roiIter] # Store position list of one ROI. (All tiles in one ROI)
                try:
                    nextROI = positions[self.roiIter + 1] # Store position list of the next ROI. Useful in looping from one ROI to another.
                except IndexError:
                    nextROI = positions[0] # This will loop around at end of ROI list. nextROI will be the first when currentROI is the last.
                if (not self.isTiling): # If only one position, put into list so len(currentROI) = 1.
                    currentROI = [currentROI]
                    nextROI = [nextROI]
                ####


                j = 0 # Position iterator

                while j < len(currentROI):
                    self.j = j
                    ####
                    if self.numAllFrames == 0:
                        exptTimeElapsed = 0.0
                    else:
                        exptTimeElapsed = time.time() - time_global_start
                    self.exptTimeElapsedStr = self.getElapsedTimeString(exptTimeElapsed)
                    self._commChannel.storeCurrentTimeString(self.exptTimeElapsedStr)
                    ####

                    self.currentPos = currentROI[self.j]
                    try:
                        self.nextPos = currentROI[self.j+1] # Next position to move to.
                    except IndexError:
                        self.nextPos = nextROI[0] # If at end of list, loops back around to beginning.

                    if self.firstLoop:
                        self.positionerXY.setPositionXY(self.tileOrigin[0], self.tileOrigin[1]) # Set XY to main origin.

                    if (self.isTiling or self.isScanROI):
                        self.positionerXY.checkBusyLoop()
                        if j == 0 and self.completeFrameSets != 0:
                            time.sleep(.5) #TODO: Change to calibrate by distance needed to move
                        else:
                            time.sleep(.05) #can probablz reduct slightly

                    ####Autofocus

                    ####

                    z = 0
                    while z < len(zList):



                        #### Moves piezo for Z stack.
                        if self.zScanActive: 
                            success = self.positioner.setPosition(zList[z], 'Z')
                            if (z == 0): #CTNOTE: Not smart. Small delay for large Z move. Should get speed of piezo and calculate this number.
                                time.sleep(0.05)
                            if success: self._commChannel.sigUpdateZPositionConfirmed.emit('Z','Z',zList[z]) #If reply is successful, just update position without a new query to stage.
                            else: self._commChannel.sigUpdateZPosition.emit('Z','Z') #If unsuccessful, query stage and apply its value to the widget.
                        ####
                        
                        self._master.arduinoManager.trigOneSequenceWriteOnly()
                        # time.sleep(0.5)
                        procTimeStart = time.time()
     
                        #### Locks for variables to be thread safe
                        errorLock = threading.Lock() #Lock for passing whether channel received all 9 images
                        saveSettingsLock = threading.Lock()
                        saveStackLock = threading.Lock()
                        snapshotLock = threading.Lock()
                        self.snapshotSettingsSaved = False
                        ####

                        self.errorQ = [] #List to be populated with error results from within processor threads
                        self.waitToMoveEvent = threading.Event() #When the last camera receives its images, this signal will fire to the positioner, moving the stage.

                        with ThreadPoolExecutor(max_workers=5) as executor: #
                            if (self.isTiling or self.isScanROI):
                                executor.submit(self.tilingMoveThread)
                            for processor in self.activeProcessors:
                                    executor.submit(self.mainSIMLoop, processor, errorLock, z, saveSettingsLock, saveStackLock, snapshotLock) 

                        if self._widget.stop_button.isChecked(): #allows exit of SIM loops once per cycle
                            # self.stopSIM()
                            self._widget.stop_button.setChecked(False)
                            return

                        self.numAllFrames += 1
                        if True not in self.errorQ:
                            self.completeFrameSets += 1 # increment only if no errors reported from processor threads
                            z += 1 # this controls positions. Increment only if successful. Repeat same location if any one camera fails.
                        self.firstLoop = False

                        procTimeDur = round(time.time()-procTimeStart,3)

                        endLoopTime = time.time()-startLoopTime
                        startLoopTime = time.time()

                        self._logger.debug(f'Dropped frames: {self.numAllFrames-self.completeFrameSets} of {self.numAllFrames}')
                        # self._logger.debug('Total frames: {}'.format(self.numAllFrames))
                        self._logger.debug(f'Acquisition time (s): {procTimeDur:.3f}')
                        self._logger.debug(f'Loop time (s): {endLoopTime:.3f}')
                        
                        
                    # self.completeFrameSets += 1 # increment only if no errors reported from processor threads
                    j += 1 # this controls positions. Increment only if successful. Repeat same location if any one camera fails.
                    completeZ += 1

                    
                    if self.sharedAttrs[('Timing Settings','Rep Checkbox')]=='2' and not (completeZ < len(positions)*len(currentROI)*int(self.sharedAttrs[('Timing Settings','Repetitions')])): 
                        self.stopSIM() # Stops tiling reps after all tiles*repetitions is done.

                    totalEndTime = time.time()-time_global_start

                    remainder = self.completeFrameSets % len(currentROI)


                self.frameCounter += 1
                self.tilingRep += 1
                self.roiIter += 1
                
                self._logger.debug(f'Elapsed time (s): {totalEndTime:.1f}\n')

            if self.sharedAttrs[('Timing Settings','Duration Checkbox')]=='2' and durationInSec != 0 and durationInSec < totalEndTime:
                if self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]=='0':
                    self.stopSIM()
                if self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]=='2' and remainder == 0:
                    self.stopSIM()
            



    def mainSIMLoop(self, processor, errorLock, z, saveSettingsLock, saveStackLock, snapshotLock):

        k = processor.processorIndex
        roOrder = processor.roOrder
        if self.scatterCam:
            numFluorProcessors = len(self.activeProcessors) - 1
        else:
            numFluorProcessors = len(self.activeProcessors)

        if k+1 == numFluorProcessors:
            lastChan = True
        else: 
            lastChan = False
        if processor.handle == '488S': lastChan = False

        broken = False # Initialize flag
        detector = processor.detObj # Set current detector object associated with proecssor.

        if self.numSLMChannels == 3: #seems like I am missing something here. How does 2 channels behanve?
            time.sleep(self.expTimeMax/1000000*(roOrder)*18) #approximately how long it will start for detector to start receiving images in buffer.
        else:
            time.sleep(self.expTimeMax/1000000*18)

        waitingBuffers = detector._camera.getBufferValue("SIM")
        # time.sleep(0.1) #CTNOTE: Temp sleep
        waitingBuffersEnd = 0
        bufferStartTime = time.time()

        while waitingBuffers != 9:
            # time.sleep(self.expTimeMax/1000000)
            waitingBuffers = detector._camera.getBufferValue("SIM") #FIXME This logic does not include a way to remove saved images for first 2 cams if for example the thrid cam fails
            if waitingBuffers != waitingBuffersEnd:
                bufferStartTime = time.time()
                bufferEndTime = time.time()
            else: 
                bufferEndTime = time.time()
            bufferTotalTime = bufferEndTime-bufferStartTime
            waitingBuffersEnd = waitingBuffers
            if waitingBuffers != 9 and bufferTotalTime > self.expTimeMax/20000: #self.expTimeMax/250000 = 4x exp time in correct units
                self._logger.error(f'Frameset thrown in trash. Buffer available is {waitingBuffers} on detector {detector.name}')
                broken = True
                with errorLock:
                    self.errorQ.append(True)
                for detector in self.detectors: # probably move this outside of thread structure, seems like it could be unsafe.
                    detector._camera.clearBuffers()
                # if lastChan:
                #     self.lastZ = (z == self.zLength - 1)
                #     if self.lastZ:
                #         self.waitToMoveEvent.set()
                #     else: 
                #         self.waitToMoveEvent.set()
                break #stop thread execution and waits at end for other threads to finish

        if not broken:
            with errorLock:
                self.errorQ.append(False)
            if lastChan:
                self.lastZ = (z == self.zLength - 1)
                # print('All images, all channels loaded into buffer')
                if self.lastZ and (self.isTiling or self.isScanROI):
            # if lastChan:
                    self.waitToMoveEvent.set()
                else: 
                    self.waitToMoveEvent.set()

                
            rawStack = detector._camera.grabFrameSet(self.framesPerDetector) # receive raw image stack
            self.sigRawStackReceived.emit(rawStack,f"{processor.handle} Raw") # display raw image stack
            
            # Set sim stack for reconstruction
            processor.setSIMStack(rawStack)
            # processor.stack = rawStack
            # Average raw stacks to make WF
            imageWF = processor.computeWFlbf(rawStack) # Why is this function in SIMProcessor? This function also sends to display.
            imageWF = imageWF.astype(np.uint16)

            
            if (self.isReconstruction):
                # Pass shared attributes to SIMprocessor
                processor.setCurrentSharedAttrs(self._commChannel.sharedAttrs)
                processor.reconstructSIMStackBackgroundLBF()

            if self.tilePreview and self.isTiling:
                # if self.j == 0 and k == 0: #PROBLEM: Tiling contrast changes all channels as channels are stacked in one layer per position.
                #     self.updateWFContLimits()
                self._commChannel.sigTileImage.emit(imageWF, self.currentPos, f"{processor.handle}WF-{self.j}",len(self.activeProcessors),k, self.completeFrameSets)

            with saveSettingsLock: # This lock restrict only one channel to savings the settings file once when also saving raw images.
                if ((self.isRecordRaw) or (self.isRecordWF) or (self.isRecordRecon)) and not (self.startSettingsSaved):
                    self._commChannel.sigSaveSettingsFirst.emit()
                    self.startSettingsSaved = True

            with saveStackLock:
                if processor.source == 'fluor':
                    if self.isRecordRaw:
                        self.recordRawFunc(self.j, processor, self.isTiling,self.tilingRep, z, self.roiIter, 'SIM')

                if self.isRecordWF:
                    self.recordWFFunc(self.j, imageWF, processor, self.isTiling,self.tilingRep, z, self.roiIter)
                if self.isRecordRecon and self.isReconstruction and processor.source == 'fluor':
                    self.recordSIMFunc(self.j, processor, self.isTiling,self.tilingRep, z, self.roiIter)

            
            if processor.saveOneTime: #Can possibly save channels at different frame numbers. Executes as soon as possible. Not an issue for Snapshot.
                self.recordOneSetWF(self.j, imageWF, processor)
                if processor.source == 'fluor':
                    self.recordOneSetRaw(self.j, processor)
                    if self.isReconstruction:
                        self.recordOneSetSIM(self.j, processor.SIMReconstruction, processor)
                processor.saveOneTime = False
                with snapshotLock: # Needed to only save one settings file per snapshot.
                    if self.snapshotSettingsSaved == False:
                        self._commChannel.sigSaveSettingsFirst.emit()
                        self.snapshotSettingsSaved = True

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
                self.positionerXY.setPositionXY(self.nextPos[0], self.nextPos[1])
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


    def recordRawFunc(self,j, processor, isTiling, tilingRep, z, roiIterator, source):
        if source == 'SIM':
            rawFolderName = 'RawStacks'
        else: rawFolderName = 'RawImgs'
        if isTiling:
            rawSavePath = os.path.join(self.exptFolderPath, "Tiling", rawFolderName)
        else:
            rawSavePath = os.path.join(self.exptFolderPath, "Timelapse", rawFolderName)
        if not os.path.exists(rawSavePath):
            os.makedirs(rawSavePath)
        if isTiling:
            rawFilenames = f"f{tilingRep:04}_roi{roiIterator:03}_pos{j:04}_z{z:03}_{processor.handle}_{self.exptTimeElapsedStr}.tif"
        else:
            rawFilenames = f"f{self.frameCounter:04}_roi{roiIterator:03}_pos{j:04}_z{z:03}_{processor.handle}_{self.exptTimeElapsedStr}.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(self.rawStack,rawSavePath, rawFilenames,), daemon=True).start()
        self.saveImageInBackground(processor.stack,rawSavePath, rawFilenames)

    def recordWFFunc(self,j,im, processor, isTiling, tilingRep, z, roiIterator):
        if isTiling:
            wfSavePath = os.path.join(self.exptFolderPath,"Tiling", "WF")
        else:
            wfSavePath = os.path.join(self.exptFolderPath,"Timelapse", "WF")
        if not os.path.exists(wfSavePath):
            os.makedirs(wfSavePath)
        if isTiling:
            wfFilenames = f"f{tilingRep:04}_roi{roiIterator:03}_pos{j:04}_z{z:03}_{processor.handle}_{self.exptTimeElapsedStr}.tif"
        else:
            wfFilenames = f"f{self.frameCounter:04}_roi{roiIterator:03}_pos{j:04}_z{z:03}_{processor.handle}_{self.exptTimeElapsedStr}.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames, ), daemon=True).start()
        self.saveImageInBackground(im,wfSavePath, wfFilenames)

    def recordSIMFunc(self,pos_num, processor, isTiling, tilingRep, z, roiIterator):
        if isTiling:
            reconSavePath = os.path.join(self.exptFolderPath,"Tiling", "Recon")
        else:
            reconSavePath = os.path.join(self.exptFolderPath,"Timelapse", "Recon")
        if not os.path.exists(reconSavePath):
            os.makedirs(reconSavePath)
        if isTiling:
            reconFilenames = f"f{tilingRep:04}_roi{roiIterator:03}_pos{pos_num:04}_z{z:03}_{processor.handle}_{self.exptTimeElapsedStr}.tif"
        else:
            reconFilenames = f"f{self.frameCounter:04}_roi{roiIterator:03}_pos{pos_num:04}_z{z:03}_{processor.handle}_{self.exptTimeElapsedStr}.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(self.SIMReconstruction, reconSavePath,reconFilenames ,)).start()
        self.saveImageInBackground(processor.SIMReconstruction, reconSavePath,reconFilenames)

    def recordOneSetRaw(self,j,processor):
        rawSavePath = os.path.join(self.exptFolderPath,'Snapshot')
        if not os.path.exists(rawSavePath):
            os.makedirs(rawSavePath)
        rawFilenames = f"f{self.frameCounter:04}_pos{j:04}_{processor.handle}_{self.exptTimeElapsedStr}_raw.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(self.rawStack,rawSavePath, rawFilenames,), daemon=True).start()
        self.saveImageInBackground(processor.stack,rawSavePath, rawFilenames)

    def recordOneSetWF(self,j,im, processor):
        wfSavePath = os.path.join(self.exptFolderPath,'Snapshot')
        if not os.path.exists(wfSavePath):
            os.makedirs(wfSavePath)
        wfFilenames = f"f{self.frameCounter:04}_pos{j:04}_{processor.handle}_{self.exptTimeElapsedStr}_WF.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames,), daemon=True).start()
        self.saveImageInBackground(im,wfSavePath, wfFilenames)


    def recordOneSetSIM(self,j,im, processor):
        simSavePath = os.path.join(self.exptFolderPath,'Snapshot')
        if not os.path.exists(simSavePath):
            os.makedirs(simSavePath)
        simFilenames = f"f{self.frameCounter:04}_pos{j:04}_{processor.handle}_{self.exptTimeElapsedStr}_SIM.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames,), daemon=True).start()
        self.saveImageInBackground(im,simSavePath, simFilenames)


    def zScanList(self, zScanList, zOrigin):
        self.zList = zScanList
        self.zOrigin = zOrigin


    def getElapsedTimeString(self, seconds):
        ss, ms = divmod(seconds,1)

        mm, ss = divmod(ss,60)
        hh, mm = divmod(mm,60)
        _, hh = divmod(hh,24)
        ss = f'{int(ss):02}'
        mm = f'{int(mm):02}'
        hh = f'{int(hh):03}'
        ms = f'{int(ms*1000):03}'

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
        timingSecs = 0.0
        try:
            timingPeriodBox = float(self._commChannel.sharedAttrs[('Timing Settings', 'Timing Period')])
        except ValueError:
            timingSecs = 0.0
            timingPeriodBox = 0.0
        except KeyError:
            timingSecs = 0.0
            timingPeriodBox = 0.0
        if timingPeriodBox > 0.0:
            timingUnit = self._commChannel.sharedAttrs[('Timing Settings', 'Timing Unit')]
            if timingUnit == 's':
                timingSecs = timingPeriodBox
            elif timingUnit == 'm':
                timingSecs = timingPeriodBox * 60
            elif timingUnit == 'h':

                timingSecs = timingPeriodBox * 3600
        return timingSecs

    
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


    def __del__(self):
        pass
        #self.imageComputationThread.quit()
        #self.imageComputationThread.wait()

    def displaySIMImage(self, im, name):
        """ Displays the image in the view. """
        self._widget.setSIMImage(im, name=name)

    def displayRawImage(self, im, name):
        """ Displays the image in the view. """
        self._widget.setRawImage(im, name)

    # def saveLastRawImage(self, im , name):
        

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
        self.SIMActive = False
        self._commChannel.updateSIMActive(self.SIMActive)
        try:
            self.simThread.join()
        except:
            pass
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

    def stop25D(self):
        self._commChannel.sigSIMAcqToggled.emit(False)
        self._widget.stop_button.setEnabled(False)
        self._widget.startSIM_button.setEnabled(True)
        self._widget.checkbox_reconstruction.setEnabled(True)
        self._widget.checkbox_record_reconstruction.setEnabled(True)
        self._widget.checkbox_record_WF.setEnabled(True)
        self.active25D = False
        self._commChannel.updateSIMActive(self.active25D)
        try:
            self.thread25D.join()
        except:
            pass
        for laser in self.lasers:
            laser.setEnabled(False)
        self._master.arduinoManager.deactivateSLMWriteOnly()
        for detector in self.detectors:
            if detector.forAcquisition: 
                detector.stopAcquisitionSIM()
                detector._camera.setPropertyValue('AcquisitionFrameRate', float(5), toPrint=False)
        if self.isTiling:
            self.positionerXY.setPositionXY(self.tileOrigin[0], self.tileOrigin[1])
            self.isTiling = False
        if self.zScanActive:
            self.positioner.setPosition(self.zOrigin, 'Z')
            self._commChannel.sigUpdateZPosition.emit('Z','Z')
            self.zScanActive = False
        if self._commChannel.autofocusActive == True:
            self._commChannel.autofocusActive = False


    def startSIM(self):

        # start the background thread
        # for detector in self.detectors:
        #     detector.stopAcquisition()
        self._commChannel.sigSIMAcqToggled.emit(True)
        self._widget.stop_button.setEnabled(True)
        self._widget.startSIM_button.setEnabled(False)
        self.SIMActive = True
        self._commChannel.updateSIMActive(self.SIMActive)

        simParametersFromGUI = self.getSIMParametersFromGUI()
        #sim_parameters["reconstructionMethod"] = self.getReconstructionMethod()
        #sim_parameters["useGPU"] = self.getIsUseGPU()
        


        self.simThread = threading.Thread(target=self.performSIMExperimentThread, args=(simParametersFromGUI,), daemon=True)
        self.simThread.start()

    def start25D(self):

        self._commChannel.stop25DNow = False
        self._commChannel.sigSIMAcqToggled.emit(True)
        self._widget.stop_button.setEnabled(False)
        self._widget.startSIM_button.setEnabled(False)
        self._widget.checkbox_record_reconstruction.setEnabled(False)
        self._widget.checkbox_reconstruction.setEnabled(False)
        self._widget.checkbox_record_WF.setEnabled(False)
        self._widget.checkbox_record_reconstruction.setCheckState(False)
        self._widget.checkbox_record_WF.setCheckState(False)
        self.active25D = True
        self._commChannel.updateSIMActive(self.active25D)
        



        self.thread25D = threading.Thread(target=self.perform25DExperimentThread, args=(), daemon=True)
        self.thread25D.start()


    def getTilingSettings(self):
        self.startxpos, self.startypos = self.positionerXY.get_abs()
        self.num_grid_x = int(self.sharedAttrs[('Tiling Settings','Steps - X')])
        self.num_grid_y = int(self.sharedAttrs[('Tiling Settings','Steps - Y')])
        self.overlap = float(self.sharedAttrs[('Tiling Settings','Overlap')])


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

        detector._camera.setPropertyValue('AcquisitionFrameRateEnable', True, False)
        detector._camera.setPropertyValue('AcquisitionFrameRate', 5.0, False)
        # detector._camera.setBufferTimeout(2000)

        trigger_source = 'Line0'
        trigger_mode = 'On'
        exposure_auto = 'Off'
        gamma = 1.0

        # Pull the exposure time from settings widget
        exposure_time = self.getParameterValue(detector, 'ExposureTime')

        # exposure_time = self.exposure # anything < 19 ms)
        pixel_format = 'Mono16'
        bit_depth = 'Bits12'

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
        dic_parameters = {'TriggerSource':trigger_source, 'TriggerMode':trigger_mode, 'ExposureAuto':exposure_auto, 'ExposureTime':exposure_time, 'Gamma':gamma, 'PixelFormat':pixel_format,'AcquisitionFrameRate':frame_rate,'StreamBufferHandlingMode':buffer_mode,'ADCBitDepth':bit_depth}

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

        detector._camera.setPropertyValue('AcquisitionFrameRateEnable', True, False)        
        detector._camera.setPropertyValue('AcquisitionFrameRate', 49.0)
        trigger_mode = 'On'
        exposure_auto = 'Off'
        gamma = 1.0
        trigger_source = 'Line0'
        detector._camera.setBufferTimeout(500)

        # # Pull the exposure time from settings widget
        exposure_time = self.getParameterValue(detector, 'ExposureTime')

        # # exposure_time = self.exposure # anything < 19 ms
        pixel_format = 'Mono16'
        bit_depth = 'Bits12'
        frame_rate_enable = True
        buffer_mode = "NewestOnly"
        triggerSelector = 'FrameStart'

        # Set cam parameters
        dic_parameters = { 'TriggerSelector': triggerSelector,'TriggerSource':trigger_source,'TriggerMode':trigger_mode,'AcquisitionFrameRateEnable':frame_rate_enable, 'ExposureAuto':exposure_auto, 'ExposureTime': exposure_time, 'Gamma':gamma, 'PixelFormat':pixel_format, 'StreamBufferHandlingMode':buffer_mode,'ADCBitDepth':bit_depth}

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


        #CTNOTE: Change to dynamic
        projCamPixelSize = 2.74 / (200 / 9) # 2.74 is cam pixel size. 200 is obj tube lens length, 9 is effective focal length of 20x Olympus UPlanApoX objective.
        #Check is scatter cam should be active
        if self._commChannel.scatterCamActive == 2:
            self.scatterCam = True
        else: 
            self.scatterCam = False
        # Create list of powered (active) lasers.
        poweredLasers = []
        for laser in self.lasers:
            if laser.percentPower > 0:
                poweredLasers.append(str(laser.wavelength)+'F')
        if '488F' in poweredLasers and self.scatterCam:
            poweredLasers.append(str('488S'))
        #
        self.getTilingSettings() #Get the parameters that go into the 'createSnakeArrays' method. Variables stores selfed as needed elsewhere too.
        ####Set flags for using in logic later.
        if int(self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]) == 2:
            self.isTiling = True
        else:
            self.isTiling = False

        roiOriginList = []
        if int(self.sharedAttrs[('ROI List', 'Checkbox')]) == 2:
            self.isScanROI = True
            try:
                roiOriginList = self.getOrigins()
            except KeyError:
                self._logger.warning('ROI list is empty.')
        else:
            self.isScanROI = False

        if self._commChannel.sharedAttrs._data[('Z-Stack Settings', 'Z-Stack Checkbox')] == '0':
            self.zScanActive = False
            zList = [self._commChannel.sharedAttrs._data[('Positioner', 'Z', 'Z', 'Position')]]
        elif self._commChannel.sharedAttrs._data[('Z-Stack Settings', 'Z-Stack Checkbox')] == '2':
            self.zScanActive = True
            zList = self.zList
        #

        #### Set attributes to processors and select only active processors (processors with powered lasers).
        self.activeProcessors = []
        for processor in self.processors:
            for detector in self.detectors: # Associate detector object with processor object.
                if processor.handle == detector.handle:
                    processor.detObj = detector
                    processor.shape = detector._shape
            if processor.handle in poweredLasers:
                self.activeProcessors.append(processor)

        if len(self.activeProcessors) == 0:
            self._logger.error("No active laser/detector combinations. Check if lasers are > 0% power.")
            self.stop25D()
            return
        
        shapeList = []
        for k, processor in enumerate(self.activeProcessors): #Give indices to active processors
            processor.processorIndex = k
            shapeList.append(processor.shape)
        if ('488S' in poweredLasers):
            self.SimProcessorLaser4.processorIndex = 0 #Assumed 488 is index 0
        ####
            
        #### Confirm the used area of all active cam sensors are the same. Stop the process if not.
        
        setShapeList = set(shapeList) # Send to set which removes duplicate values. The length should be one is values are the same.
        if len(setShapeList) != 1:
            self._logger.error("Detector image shapes must be the same.")
            self.stop25D()
            return
        shapeList = list(setShapeList)[0] #Put back into list form to be used to calculate tiling positions.
        ####

        #### Create XY position array given ROI and tiling settings.
        self.tileOrigins = []
        positions= self._master.tilingManager.createSnakeArrays(self.num_grid_x, self.num_grid_y, self.overlap, self.startxpos, self.startypos, projCamPixelSize, roiOriginList, shapeList)
        for i in range(len(positions)):
            self.tileOrigins.append(positions[i][0])
        self.tileOrigin = positions[0][0]
        if not self.isTiling:
            positions = self.tileOrigins
        ####
        

        #### Flags for state control, constant varables, this that need one time initialization.
        self.zLength = len(zList)
        self.numAllFrames = 0 # Number of frames, including dropped frames
        self.completeFrameSets = 0 # Number of frames, exncluding dropped frames
        self.frameCounter = 0
        self.tilingRep = 0
        isTimed = bool(int(self._commChannel.sharedAttrs._data[('Timing Settings', 'Period Checkbox')]))
        if isTimed: timingPeriodInSec = self.getPeriodInSec()
        durationInSec = self.getDurationInSec()
        totalEndTime = 0
        self.startSettingsSaved = False
        completeZ = 0
        self.firstLoop = True
        self.tilePreview = bool(int(self._commChannel.sharedAttrs._data[('Tiling Settings', 'Tiling Preview')]))
        dateTimeStartClick = datetime.now().strftime("%y%m%d_%H%M%S") # Datetime string registered when start button is pressed only.
        time_global_start = time.time()
        self.AFCounter = 0
        startLoopTime = time.time()
        ####


        

        # Set autoZern flag to True, if AZ checkbox is checked, create param list ========================================
        # if self.sharedAttrs[('Zernike SLM Parameters','Both', 'AZEnabled')]=='2':
        #     autoZern = True
        #     autoZernRep = 0
        #     self._commChannel.sigStartAutoZern.emit()
        #     time.sleep(1.) #CTNOTE: Test floor
        #     self.listLengthAZTestParams()
        # else:
        #     autoZern = False
        #     autoZernRep = -1



        self._master.arduinoManager.activate25DWriteOnly() #This command activates the arduino to be ready to receive triggers. 0.01s time delay.
        for processor in self.activeProcessors: # Set only active cams
            self.setCamForExperiment25D(processor.detObj)
        self.exptFolderPath = self.makeExptFolderStr(dateTimeStartClick) # Path of current experiment folder
        self.setSharedAttr('User Dir Info', 'Current Path', self.exptFolderPath) # Register this path with CommChannel in save settings file.
        self._commChannel.updateActiveDirectory(self.exptFolderPath) # Register this path as a CommChannel variable to be easily accessed by other controllers.

        ####Autofocus
        if (self._commChannel.initRegScore != None) :
            self.autofocusThread()
            self.AFMaskLeft = self._commChannel.AFMaskLeft
            self.AFMaskRight = self._commChannel.AFMaskRight
            self._logger.info('Autofocus active')    
        ####


        ## Start of acquisition loop. Order goes ROI->tile->Z. All Z's go, increment tile. All tiles go, increment ROI.
        while self.active25D:
            self.roiIter = 0
            #### For timing period. Check every 1/10s if period time is exceeded yet.
            if self.completeFrameSets != 0 and isTimed: #Does not exceute on first loop
                repTimer = time.time() - repTimerStart
                if timingPeriodInSec > 30:
                    self._logger.info(f'Timing based acquisition. Timing period is {timingPeriodInSec} seconds.')
                while repTimer < timingPeriodInSec:
                    time.sleep(timingPeriodInSec / 100)
                    repTimer = time.time() - repTimerStart
                    if self._commChannel.stop25DNow: #allows exit of the loop
                        self.stop25D()
                        return
                    
            if not isTimed: # these lines are a hacky way to slow down 2.5D
                time.sleep(0.04)

            repTimerStart = time.time()
            ####

            while self.roiIter < len(positions):


               

                #### Set variables for current and next positions. These will be used to move stage XY.
                currentROI = positions[self.roiIter] # Store position list of one ROI. (All tiles in one ROI)
                try:
                    nextROI = positions[self.roiIter + 1] # Store position list of the next ROI. Useful in looping from one ROI to another.
                except IndexError:
                    nextROI = positions[0] # This will loop around at end of ROI list. nextROI will be the first when currentROI is the last.
                if (not self.isTiling): # If only one position, put into list so len(currentROI) = 1.
                    currentROI = [currentROI]
                    nextROI = [nextROI]
                ####

                j = 0 # Position (tile) iterator

                while j < len(currentROI):



                    self.j = j # Self it for use elsewhere. Kind of sloppy.

                    #### Create time string for each 'tiling set' for saving filenames. All Z's are considered at the same time.
                    if self.numAllFrames == 0:
                        exptTimeElapsed = 0.0
                    else:
                        exptTimeElapsed = time.time() - time_global_start
                    self.exptTimeElapsedStr = self.getElapsedTimeString(exptTimeElapsed)
                    self._commChannel.storeCurrentTimeString(self.exptTimeElapsedStr)
                    ####
                    self.currentPos = currentROI[self.j]
                    try:
                        self.nextPos = currentROI[self.j+1] # Next position to move to.
                    except IndexError:
                        self.nextPos = nextROI[0] # If at end of list, loops back around to beginning.

                    if self.firstLoop and (self.isTiling or self.isScanROI):
                        self.positionerXY.setPositionXY(self.tileOrigin[0], self.tileOrigin[1]) # Set XY to main origin.

                    #### Stage wait times for jiggle.
                    if (self.isTiling or self.isScanROI):
                        self.positionerXY.checkBusyLoop() # ♣Stop program if XY stage is moving. CTNOTE: Makes image hang when moving by hand too.
                        if j == 0 and self.completeFrameSets != 0: #TODO NOT GOOD LOGIC. CAN BE FASTER IF SMARTER
                            time.sleep(.5) #Wait time for jiggle if the stage is moving from end to origin to start another tile.
                        else:
                            time.sleep(.05) #Wait time for jiggle if only moving to adjacent ROI.
                    ####

                    # ####Autofocus
                    # if (self._commChannel.sharedAttrs._data[('Autofocus Settings', 'Autofocus Checkbox')] == '2') and (self.completeFrameSets == 0):
                    #     localOrigin = float(self._commChannel.sharedAttrs._data[('Positioner', 'Z', 'Z', 'Position')])
                    #     AFList = self._master.autofocusManager.calcAFArray(localOrigin)
                    #     self.autofocusLoop(AFList)
                    #     scoreArray, bestIndex = self._master.autofocusManager.computeLaplacianArray(self._commChannel.AFArray)
                    #     bestZ = AFList[bestIndex]
                    #     offsetAF = bestZ - localOrigin
                    #     print(offsetAF)
                    #     self.channelAF = int(self.sharedAttrs[("Autofocus Settings","Autofocus Channel")])
                    #     if bestZ != localOrigin:
                    #         self.positioner.setPosition(bestZ, 'Z')
                    #         self._commChannel.sigUpdateZPosition.emit('Z','Z')
                    # ####

                    z = 0
                    while z < len(zList):

                        # Auto Zernike loop ==================================================================
                        if self._commChannel.autoZernChecked:
                            self._commChannel.sigBeginAutoZern.emit()
                            time.sleep(1)
                            while self._commChannel.autoZernChecked:
                                time.sleep(0.1)
                                rawImg = self._commChannel.lastImgDict['640F']
                                self.sigRawImgReceived.emit(rawImg,f"{processor.handle} Raw")
                                if self._commChannel.stop25DNow: #allows exit of the loop
                                    self.stop25D()

                            print('autozern ended')
                        # ====================================================================================





                        # Sets current value to Zernike coefficient ========================
                        # if autoZern and autoZernRep < self.AutoZernCalibValuesListLength:                    
                        #     self._commChannel.sigSetAutoZern.emit(autoZernRep)
                        #     time.sleep(0.1) # !!!can prob be deleted

                        #### Moves piezo for Z stack.
                        if self.zScanActive: 
                            success = self.positioner.setPosition(zList[z], 'Z')
                            time.sleep(0.05) #Demo day sleep, was dropping frames when z-stacking on 2.5D without this
                            if (z == 0): #CTNOTE: Not smart. Small delay for large Z move. Should get speed of piezo and calculate this number.
                                time.sleep(0.05)
                            if success: self._commChannel.sigUpdateZPositionConfirmed.emit('Z','Z',zList[z]) #If reply is successful, just update position without a new query to stage.
                            else: self._commChannel.sigUpdateZPosition.emit('Z','Z') #If unsuccessful, query stage and apply its value to the widget.
                        ####


                        self._master.arduinoManager.trigger25DWriteOnly() # Send actual trigger to cams.

                             
                        procTimeStart = time.time() # For tracking processing time of images. 

                        #### Locks for variables to be thread safe
                        errorLock = threading.Lock() #Lock for passing whether channel received all 9 images
                        saveSettingsLock = threading.Lock()
                        saveStackLock = threading.Lock()
                        snapshotLock = threading.Lock()
                        self.snapshotSettingsSaved = False
                        lastImgLock = threading.Lock()
                        
                        ####

                        self.errorQ = [] #List to be populated with error results from within processor threads
                        self.waitToMoveEvent = threading.Event() #When the last camera receives its images, this signal will fire to the positioner, moving the stage.

                        self.lastImgDict = dict()


                        with ThreadPoolExecutor(max_workers=5) as executor:
                            if (self.isTiling or self.isScanROI):
                                executor.submit(self.tilingMoveThread)
                            for processor in self.activeProcessors:
                                executor.submit(self.main25DLoop, processor, errorLock, z, saveSettingsLock, saveStackLock, snapshotLock, lastImgLock)

                        # last images are available

                        # score in the manager, put score in a list.
                        # if autoZern:
                        #     self._master.slm25DManager.calcAutoZern(self.lastImgDict) 
                        

                        if self._commChannel.stop25DNow: #allows exit of SIM loops once per cycle
                            self._widget.stop_button.setChecked(False)
                            self.stop25D()
                            return

                        self.numAllFrames += 1
                        if True not in self.errorQ:
                            self.completeFrameSets += 1 # increment only if no errors reported from processor threads
                            z += 1 # this controls positions. Increment only if successful. Repeat same location if any one camera fails.
                        self.firstLoop = False # #CTNOTE: Maybe put in if statement above. Set to false. Will start false until system is stopped and started again.

                        procTimeDur = time.time()-procTimeStart # Actual elapsed time for processing images.
                        endLoopTime = time.time()-startLoopTime
                        startLoopTime = time.time()

                        #### Print timing and frame information.
                        # self._logger.debug('Dropped frames: {}'.format(self.numAllFrames-self.completeFrameSets))
                        self._logger.debug(f'Dropped frames: {self.numAllFrames-self.completeFrameSets} of {self.numAllFrames}')
                        # self._logger.debug('Total frames: {}'.format(self.numAllFrames))
                        self._logger.debug(f'Acquisition time (s): {procTimeDur:.3f}')
                        self._logger.debug(f'Loop time (s): {endLoopTime:.3f}')
                        ####

                    # if self.recordPSFStackFlag:
                    #     recordedPSFStack = self._commChannel.getPSFStack()[0]
                    #     self._commChannel.sigSendZstackToRecordWindow.emit(recordedPSFStack)
                    #     self.recordPSFStackFlag = True
                        
                    
                    j += 1 # Controls XY position. Should only increment is images were successful. Re-doing of failed position handled on the Z level.
                    completeZ += 1 # Count from 0 to infinity complete Z stack only. Similar to j, but is never reset.

                    if self.sharedAttrs[('Timing Settings','Rep Checkbox')]=='2' and not (completeZ < len(positions)*len(currentROI)*int(self.sharedAttrs[('Timing Settings','Repetitions')])): 
                        self.stop25D() # Stops tiling reps after all ROIs*tiles*repetitions is done.

                    totalEndTime = time.time()-time_global_start

                #### Increment counters.
                self.frameCounter += 1 # Used in filenames of saved files. Keep an eye to see if there are problems/timing issues here.
                self.tilingRep += 1 # Used in filenames of saved files.
                self.roiIter += 1 # Increment roi index
                ####
                self._logger.debug(f'Elapsed time (s): {totalEndTime:.1f}\n')


                

            if self.sharedAttrs[('Timing Settings','Duration Checkbox')]=='2' and durationInSec != 0 and durationInSec < totalEndTime: #Will this stop in middle of tiling if duration hits?
                self.stop25D() # Stops system is duration based imaging is selected.


            # if autoZern:
            #     if ((autoZernRep + 1) % self.numCalibValues == 0): #!!! put 7 instead of 21 again - later have it un-hadrcoded ####and (autoZernRep != -1)
            #         # look at the list, fit parabola, get best value, set value, continue
            #         optimalCoefficientMax = self._master.slm25DManager.optimalCoeffValueMax(list(self._commChannel.autoZernCalibValuesDict.values())[((autoZernRep + 1) // self.numCalibValues) - 1])
            #         # self._commChannel.sigSetOptimalZern.emit(autoZernRep, optimalCoefficient)
            #         self._commChannel.sigSetOptimalZern.emit(autoZernRep, optimalCoefficientMax)
            #         #self._commChannel.sigSetOptimalZern.emit(autoZernRep, optimalCoefficientFit)
            #         #self._commChannel.sigSetOptimalZern.emit(autoZernRep, 0)

                    
            #         self._master.slm25DManager.resetList()


            #     if autoZernRep >= (self.AutoZernCalibValuesListLength - 1):  
            #         autoZernRep = -1
            #         self._commChannel.sigToggleAutoZern.emit(False)
            #         autoZern = False
            #         self._widget.stop_button.setChecked(False)
            #         self.stop25D()
            #     else:
            #         autoZernRep += 1
            #         time.sleep(.1) # !!! IMPORTANT, without that the loop skips frames, no idea why



    def main25DLoop(self, processor, errorLock, z, saveSettingsLock, saveStackLock, snapshotLock, lastImgLock):
        
        k = processor.processorIndex
        if self.scatterCam:
            numFluorProcessors = len(self.activeProcessors) - 1
        else:
            numFluorProcessors = len(self.activeProcessors)
        if k+1 == numFluorProcessors: # Set flag per processor on whether it is the last channel/processor. Usaed to determine when to move stage.
            lastChan = True 
        else: 
            lastChan = False
        if processor.handle == '488S': lastChan = False

        broken = False # Initialize flag
        detector = processor.detObj # Set current detector object associated with proecssor.
        
        #### Everything needed to confirm correct amount of images in buffer. If not correct, clear cam buffers and restart Z position.
        waitingBuffers = detector._camera.getBufferValue('25D') # Arguement is unused by method.
        startBufferTime = time.time()
        totalBufferTime = 0
        while waitingBuffers != 1:
            endBufferTime = time.time()
            totalBufferTime = endBufferTime - startBufferTime
            waitingBuffers = detector._camera.getBufferValue('25D')
            time.sleep(0.002)

            if (waitingBuffers != 1 and totalBufferTime > 0.1): # Will wait for 0.2 seconds for a buffer to come before resetting.

                self._logger.error(f'Frameset thrown in trash. Buffer available is {waitingBuffers} on detector {detector.name}')
                broken = True
                with errorLock:
                    self.errorQ.append(True)
                for detector in self.detectors: # probably move this outside of thread structure, seems like it could be unsafe.
                    detector._camera.clearBuffers()
                break
        ####
        #### If buffers are correct, and thread is for last channel, last Z, move stage.
        if not broken: 
            with errorLock:
                self.errorQ.append(False)
            if lastChan:
                self.lastZ = (z == self.zLength - 1)
                if self.lastZ and (self.isTiling or self.isScanROI):
                    self.waitToMoveEvent.set()
                else:
                    self.waitToMoveEvent.set()
        ####


        rawImg = detector._camera.grabFrame25D(1) # Get the image from the buffer.

        with lastImgLock:
            self.lastImgDict[processor.handle] = rawImg

        self.sigRawImgReceived.emit(rawImg,f"{processor.handle} Raw") # Send image to be displayed in Imswitch window.
        # self.displayRawImage(rawImg, f"{processor.handle} Raw")
        processor.stack = rawImg

        self._commChannel.sigGetLastRawImgs.emit(rawImg, processor.handle)

        #### Sends latest Z stack to CommChannel to be used by PSF analysis or anything else.

        if self.zScanActive: 
            if z == 0:
                resetStack = True
            else:
                resetStack = False
            self._commChannel.storeRecPSFStack(rawImg, resetStack, processor.handle)
        ####
                
        # processor.setSIMStack(rawImg) #CTNOTE: Why am I sending it to processor? Probably only needed for SIM, not 2.5D
        
        #### Emits every 2.5D image to tiling preview window.
        if self.tilePreview and self.isTiling:
            # if self.j == 0 and k == 0: #PROBLEM: Tiling contrast changes all channels as channels are stacked in one layer per position.
            #     self.updateWFContLimits()
            self._commChannel.sigTileImage.emit(rawImg, self.currentPos, f"{processor.handle}WF-{self.j}",len(self.activeProcessors),k, self.completeFrameSets)
        ####

        with saveSettingsLock: # This lock restrict only one channel to savings the settings file once when also saving raw images.
            if ((self.isRecordRaw)) and not (self.startSettingsSaved):
                self._commChannel.sigSaveSettingsFirst.emit()
                self.startSettingsSaved = True

        if (self.isRecordRaw): # and (self.frameCounter % 60 == 0): # Saves raw images.
            with saveStackLock: # Lock needed to avoid hiccups at start of saving process. Would miss some images from first channel sometimes without.
                self.recordRawFunc(self.j, processor, self.isTiling, self.tilingRep, z, self.roiIter, '25D')

        if processor.saveOneTime: #Can possibly save channels at different frame numbers. Executes as soon as possible. Not an issue for Snapshot.
            self.recordOneSetRaw(self.j, processor) #Save one image from each active channel.
            processor.saveOneTime = False
            with snapshotLock: #Needed to only save one settings file per snapshot.
                if self.snapshotSettingsSaved == False:
                    self._commChannel.sigSaveSettingsFirst.emit() # Sometimes causes small hang
                    self.snapshotSettingsSaved = True
                

        # processor.clearStack() #I dont think this needed as processor.stack is overwritten next loop

    def autofocusThread(self):
        self._commChannel.autofocusActive = True
        self.AFThread = threading.Thread(target=self.autofocusStart, args=(), daemon=True)
        self.AFThread.start()
        
    def autofocusStart(self):
        while (self._commChannel.initRegScore != None) and (self.active25D):
            self.autofocusLoop()

    def autofocusLoop(self):
        # periodInSec = self.getPeriodInSec()
        if self.firstLoop:
            self.AFScores = []
            self.cumZDiff = 0
        initRegScore = self._commChannel.initRegScore
        img = self.AFCam.grabFrameOnly()
        currentRegScore = self.AFManager.scoreOneLive(img, self.AFMaskLeft, self.AFMaskRight)

        self.AFScores.append(currentRegScore)

        time.sleep(3)

        if not (self.firstLoop) and (self.AFCounter % 20 == 0):
            avgScore = sum(self.AFScores)/len(self.AFScores)
            # medScore = statistics.median(self.AFScores)
            # print('10 AF Frames')

            scoreDiff = avgScore - initRegScore
            zDiff = self.AFManager.x_slp * scoreDiff
            # print(f'Z Difference: {zDiff}')
            print('AF execute')

            if abs(zDiff) >= 0.01:
                self.cumZDiff = self.cumZDiff + zDiff
                currentZ = self.positioner._position['Z']
                wantedZ = currentZ - zDiff
                self.positioner.setPosition(wantedZ, 'Z')
                self._commChannel.sigUpdateZPosition.emit('Z','Z')
                # self._commChannel.offsetFromInitZ = self.cumZDiff
                self._commChannel.sigSendZDrift.emit(self.cumZDiff)
                self._logger.warning(f'Total Z drift: {self.cumZDiff}')
                
                
            self.AFScores = []
            
        with open("AFOutput.txt", "a") as text_file:
            line = f'{currentRegScore:.2f},{self.cumZDiff:.2f}'
            text_file.write(f'{line}\n')

        self.AFCounter += 1
  
   
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

    def listLengthAZTestParams(self):
        self.AutoZernCalibValuesListLength = self._commChannel.numAZAlltestPoints
        self.numCalibValues = self._commChannel.numAZTestValuesPerZernCoeff

            
    def AZFinished(self):
        print('AZ finished') 
        # signal activates this function. Use it to break AZ loop if neccessary

    # def setParameter(self, parameterName, value):
    #     # FIXME: Just a place holder
    #     self._logger.error(f"{parameterName} with {value} not set! Setting of SIM parameters using attrChanged in widget is not set up yet.")