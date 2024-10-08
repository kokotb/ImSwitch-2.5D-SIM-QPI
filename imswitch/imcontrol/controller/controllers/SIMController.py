import os
import numpy as np
import time
import threading
from datetime import datetime
import tifffile as tif
import os
import time
import numpy as np
from decimal import Decimal
import string
from .SIMProcessor import SIMProcessor
from .SIMProcessor import SIMParameters
from concurrent.futures import ThreadPoolExecutor



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
        self.isRecordRaw = False
        self.isReconstruction = self._widget.getReconCheckState()
        self.isRecordRecon = False
        self.tilePreview = False
        self.isRecordWF = False
     
        # Only napari implemented as of 12/9/24
        self.reconstructionMethod = "napari" # or "mcSIM"

        #This signal connect needs to run earlier than self.makeSetupInfoDict, so when SIM parameters are filled, it sends it to shared attributes.
        self._widget.sigSIMParamChanged.connect(self.valueChanged)
        self._widget.sigUserDirInfoChanged.connect(self.valueChanged)
        self._widget.sigROInfoChanged.connect(self.valueChanged)

        setupInfoDict = self.makeSetupInfoDict() # Pull SIM setup info into dict and also set on SIM widget.

        #Create list of available laser objects from config file.
        self.lasers = list(self._master.lasersManager._subManagers.values()) #List of just the laser object handles
        # if len(self.lasers) == 0:  #Not likely to be used given how the mockers work.
            # self._logger.error("No laser found")
            
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

        # Signals originating from SIMController.py
        self.sigRawStackReceived.connect(self.displayRawImage)
        self.sigSIMProcessorImageComputed.connect(self.displaySIMImage)
        self.sigWFImageComputed.connect(self.displayWFImage)
        # Signals connecting SIMWidget actions with functions in SIMController
        self._widget.start_button.clicked.connect(self.startSIM)
        self._widget.stop_button.clicked.connect(self.stopSIM)
        self._widget.checkbox_record_raw.stateChanged.connect(self.toggleRecording)
        self._widget.checkbox_record_WF.stateChanged.connect(self.toggleRecordWF)
        self._widget.checkbox_record_reconstruction.stateChanged.connect(self.toggleRecordReconstruction)
        self._widget.checkbox_reconstruction.stateChanged.connect(self.toggleReconstruction)
        self._widget.openFolderButton.clicked.connect(self.openFolder)
        self._widget.calibrateButton.clicked.connect(self.calibrateToggled)
        self._widget.saveOneSetButton.clicked.connect(self.saveOneSet)
        # Communication channels signls (signals sent elsewhere in the program)
        self._commChannel.sigAdjustFrame.connect(self.updateROIsize)
        self._commChannel.sigStopSim.connect(self.stopSIM)
        self._commChannel.sigTilePreview.connect(self.toggleTilePreview)
        
        #Get RO names from SLM4DDManager and send values to widget function to populate RO list, selects currently active RO. (default or last used if not powered down)
        self.populateAndSelectROList()
        #Get save directory root from config file and populate text box in SIM widget.
        self._widget.setUserDirInfo(setupInfoDict['saveDir'])
        #Create log file attributes that get filled during experiment
        self.log_times_loop = []
        # self.setSharedAttr(attrCategory, parameterName, value):
        self.sharedAttrs = self._commChannel.sharedAttrs._data
        
    def performSIMExperimentThread(self, sim_parameters):
        """
        Select a sequence on the SLM that will choose laser combination.
        Run the sequence by sending the trigger to the SLM.
        Run continuous on a single frame. 
        Run snake scan for larger FOVs.
        """
        
        self.isReconstructing = False # Is this line needed, all other references to this variable are in SIMProcessor
        

        # Newly added, prep for SLM integration
        self.sim_parameters = sim_parameters
        
        processors_dic = {488:self.SimProcessorLaser1,561:self.SimProcessorLaser2,640:self.SimProcessorLaser3}
        

        # Check if lasers are set and have power in them select only lasers with powers
        poweredLasers = []
        for laser in self.lasers:
            if laser.percentPower > 0:
                poweredLasers.append(laser.wavelength)
        self.detectors = [] 
        self.processors = []
        if poweredLasers != []:
            for k, dic in enumerate(poweredLasers):
                detector = self._master.detectorsManager[str(dic) + ' Cam'] #CTNOTE depends on 'XXX Cam' detector name structure. Can change to wavelength attribute.
                self.detectors.append(detector)
                self.processors.append(processors_dic[dic])
                processors_dic[dic].detObj = detector
                processors_dic[dic].processorIndex = k #Give processor an index up front instead of during the (k, processor) for loop.
                processors_dic[dic].isCalibrated = False # force calibration each time 'Start' is pressed. May need to be overwritten from previous session.
        else:
            self._logger.error("No powered lasers.")

        # magnification = sim_parameters.Magnification
        # camPixelSize = sim_parameters.Pixelsize
        projCamPixelSize = (sim_parameters.Pixelsize)/(sim_parameters.Magnification) # This may be very slightly miscalced (sig figs). Conversion to pixel space gives 512.05, not 512.

        #Get the parameters that go into the createXYGridPositionArray function
        self.getTilingSettings() 
        positions = self._master.tilingManager.createXYGridPositionArray(self.num_grid_x, self.num_grid_y, self.overlap, self.startxpos, self.startypos, projCamPixelSize)
        self.tileOrigin = positions[-1] 
        ''' # For nameing tiling squares A1, A2, .....C5 etc.
        # gridNamesX = [str(x+1) for x in range(self.num_grid_x)]
        # gridNamesY = list(string.ascii_uppercase)[:self.num_grid_y]
        # test = []
        # for item in gridNamesY:
        #     for value in gridNamesX:
        #         test.append(item+value)
        '''
        
        # Datetime string registered when start button is pressed only.
        dateTimeStartClick = datetime.now().strftime("%y%m%d%H%M%S")

        # Set all SIM parameters from GUI to each processor. All will be the same, except Recon WL
        self.updateProcessorParameters()

        # Set count for frames to 0
        self.frameSetCount = 0
        self.completeFrameSets = 0 # Initialized this counter now that we are not "skipping" broken frames during tiling.
        self.saveOneTime = False
        self.saveOneSetRaw = False
        self.saveOneSetWF = False
        #Set tiling flag, determines whether program will enter the tiling code.
        if int(self.sharedAttrs[('Tiling Settings','Tiling Checkbox')]) == 2:
            self.isTiling = True
        else:
            self.isTiling = False

        self.numActiveChannels = len(poweredLasers)
        

        # Set running order on SLM
        roID = self._widget.getSelectedRO()
        self._master.SLM4DDManager.setRunningOrder(roID)
        # Get max exposure time from the selected RO on SLM. This is done with naming structure. Name must start with numerical digits, then 'ms'
        self.expTimeMax = int(self.roNameList[roID].split('ms')[0])*1000

        # -------------------Set-up cams-------------------

        # FIXME: Automate buffer size calculation based on image size, it did not work before
        total_buffer_size_MB = 350 # in MBs
        for detector in self.detectors:
            image_size = detector.shape
            image_size_MB = (2*image_size[0]*image_size[1]/(1024**2))
            buffer_size = int(total_buffer_size_MB // image_size_MB)
            # buffer_size = 9
            self.setCamForExperiment(detector, buffer_size,self.expTimeMax)
        


        droppedFrameSets = 0
        time_global_start = time.time()
        # time_whole_start = time_global_start


        # Maybe change to query with variable assignment. Will probably ensure line is executed completed with delay less than 10 ms.
        self._master.arduinoManager.activateSLMWriteOnly() #This command activates the arduino to be ready to receive triggers.
       # 0.01s time delay built into activate SLM function. trigOneSequence() cannot be called too fast. Only adds to very first loop time. 1 ms was not enough. If query is waited for, value is 0.02
        


        while self.active and poweredLasers != []:
      
        
            # Generate time_step
            if self.frameSetCount == 0:
                exptTimeElapsed = 0.0
            else:
                exptTimeElapsed = time.time() - time_global_start
            self.exptTimeElapsedStr = self.getElapsedTimeString(exptTimeElapsed)

            # Scan over all positions generated for grid
            j = 0 # Position iterator
            while j < len(positions):
                self.j = j
                self.pos = positions[self.j]
                timestart = time.time()
                
                                
                # Trigger SIM set acquisition for all present lasers


                self._master.arduinoManager.trigOneSequenceWriteOnly()
                # time.sleep(1) #sleep to make different amounts of processors not throw  an error
               

                self.exptFolderPath = self.makeExptFolderStr(dateTimeStartClick)
                # Loop over channels
                self.waitToMoveEvent = threading.Event()
                with ThreadPoolExecutor(max_workers=4) as executor:
                    if self.isTiling:
                        executor.submit(self.tilingMoveThread)
                    executor.map(self.mainSIMLoop, self.processors)

                    # Setting a reconstruction processor for current laser
                    # self.powered = self.detectors[k]._detectorInfo.managerProperties['wavelength'] in poweredLasers

                # self._widget.viewer.grid.enabled = True


                self.frameSetCount += 1
                
                

                self._logger.debug('Dropped frames: {}'.format(droppedFrameSets))
                self._logger.debug('Total frames: {}'.format(self.frameSetCount))
                



                if self._widget.stop_button.isChecked():
                    self._widget.stop_button.setChecked(False)
                    return
                



                # if broken:
                #     pass
                # else:
                j += 1
                self.completeFrameSets += 1

                if self.isTiling and not (self.completeFrameSets + 1 < len(positions)*int(self.sharedAttrs[('Tiling Settings','Tiling Repetitions')])): 
                    self._commChannel.sigStopSim.emit() # Actually calced wrong. The +1 after self.completeFrameSets shouldn't be there. If we call stopSIM one cycle early, appears to work. Very stupid.
                print(time.time()-timestart)

    def mainSIMLoop(self, processor):
        k = processor.processorIndex
        if k+1 == self.numActiveChannels:
            lastChan = True
        else:
            lastChan = False
        self.LaserWL = processor.handle
        
        # Set current detector being used
        detector = processor.detObj
        
        # FIXME: Remove after development is completed


        # 3 angles 3 phases
        framesPerDetector = 9

        time.sleep(self.expTimeMax/1000000*(k)*18)
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
            # print(bufferTotalTime)

            # print(bufferTotalTime)
            # print(waitingBuffers)
            waitingBuffersEnd = waitingBuffers
            # broken = False
            # print(waitingBuffers,bufferTotalTime)
            if waitingBuffers != 9 and bufferTotalTime > self.expTimeMax/250000: #self.expTimeMax/250000 = 4x exp time in correct units
            # if waitingBuffers != 9 and bufferTotalTime > .1: #self.expTimeMax/250000 = 4x exp time in correct units
                self._logger.error(f'Frameset thrown in trash. Buffer available is {waitingBuffers} on detector {detector.name}')
                for detector in self.detectors:
                    detector._camera.clearBuffers()
                # broken = True
                # break
            
        print(f'Thread {threading.current_thread().getName()} buffers done on processor {k}, lastChan = {lastChan}')


        if lastChan:
            self.waitToMoveEvent.set()

            
        # if broken == True:
        #     droppedFrameSets += 1
            
            # break

        self.rawStack = detector._camera.grabFrameSet(framesPerDetector)




        self.sigRawStackReceived.emit(np.array(self.rawStack),f"{processor.handle} Raw")
        
        # Set sim stack for processing all functions work on 
        processor.setSIMStack(self.rawStack)
        
        # Push all wide fields into one array.
        imageWF = processor.getWFlbf(self.rawStack)
        imageWF = imageWF.astype(np.uint16)
        if self.tilePreview and self.isTiling:
            self._commChannel.sigTileImage.emit(imageWF, self.pos, f"{processor.handle}WF-{self.j}",self.numActiveChannels,k, self.completeFrameSets)

        
        # Activate recording and reconstruction in processor
        processor.setRecordingMode(self.isRecordRecon)
        processor.setReconstructionMode(self.isReconstruction)
        processor.setWavelength(self.LaserWL, self.sim_parameters)
        
        if k == 0 and self.saveOneTime:
            self.saveOneSetRaw = True
        if self.saveOneSetRaw:
            self.recordOneSetRaw(self.j)
        if self.isRecordRaw:
            self.recordRawFunc(self.j)

        if k == 0 and self.saveOneTime:
            self.saveOneSetWF = True
        if self.saveOneSetWF:
            self.recordOneSetWF(self.j, imageWF)
        if self.isRecordWF:
            self.recordWFFunc(self.j, imageWF)


        
        # if self.isReconstruction and div_1 == 0:
        if self.isReconstruction:
            processor.reconstructSIMStackLBF(self.exptFolderPath,self.frameSetCount, self.j, self.exptTimeElapsedStr,self.saveOneSetRaw)


        processor.clearStack()                    

    
        if k==(len(self.processors)-1) and self.saveOneSetRaw and self.saveOneTime:
            self.saveOneSetRaw = False
            self.saveOneTime = False
            self.saveOneSetWF = False
                

    def tilingMoveThread(self):

        self.waitToMoveEvent.wait()
        self.waitToMoveEvent.clear()
        print(f'Thread {threading.current_thread().getName()} started moving')
        self.positionerXY.setPositionXY(self.pos[0], self.pos[1])
            # self.positionerXY.checkBusy()

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

    def recordOneSetRaw(self,j):
        rawSavePath = os.path.join(self.exptFolderPath,'Snapshot')
        if not os.path.exists(rawSavePath):
            os.makedirs(rawSavePath)
        rawFilenames = f"f{self.frameSetCount:04}_pos{j:04}_{int(self.LaserWL):03}_{self.exptTimeElapsedStr}_raw.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(self.rawStack,rawSavePath, rawFilenames,), daemon=True).start()
        self.saveImageInBackground(self.rawStack,rawSavePath, rawFilenames)

    def recordRawFunc(self,j):
        rawSavePath = os.path.join(self.exptFolderPath, "RawStacks")
        if not os.path.exists(rawSavePath):
            os.makedirs(rawSavePath)
        rawFilenames = f"f{self.frameSetCount:04}_pos{j:04}_{int(self.LaserWL):03}_{self.exptTimeElapsedStr}.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(self.rawStack,rawSavePath, rawFilenames,), daemon=True).start()
        self.saveImageInBackground(self.rawStack,rawSavePath, rawFilenames)

    def recordOneSetWF(self,j,im):
        wfSavePath = os.path.join(self.exptFolderPath,'Snapshot')
        if not os.path.exists(wfSavePath):
            os.makedirs(wfSavePath)
        wfFilenames = f"f{self.frameSetCount:04}_pos{j:04}_{int(self.LaserWL):03}_{self.exptTimeElapsedStr}_WF.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames,), daemon=True).start()
        self.saveImageInBackground(im,wfSavePath, wfFilenames)

    def recordWFFunc(self,j,im):
        wfSavePath = os.path.join(self.exptFolderPath, "WF")
        if not os.path.exists(wfSavePath):
            os.makedirs(wfSavePath)
        wfFilenames = f"f{self.frameSetCount:04}_pos{j:04}_{int(self.LaserWL):03}_{self.exptTimeElapsedStr}.tif"
        # threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames, ), daemon=True).start()
        self.saveImageInBackground(im,wfSavePath, wfFilenames)





    def getElapsedTimeString(self, seconds):
        ss, ms = divmod(seconds,1)

        mm, ss = divmod(ss,60)
        hh, mm = divmod(mm,60)
        dd, hh = divmod(hh,24)
        ss = "{:02d}".format(int(ss))
        mm = "{:02d}".format(int(mm))
        hh = "{:02d}".format(int(hh))
        dd = "{:01d}".format(int(dd))
        ms = str(round(Decimal(ms),3))[2:5]

        elapsedStr = f"{dd}d{hh}h{mm}m{ss}s{ms}ms"
        return elapsedStr


    def makeExptFolderStr(self, date_in):
        userName = self._widget.getUserName()
        exptName = self._widget.getExptName()
        if not userName:
            userName = 'username'
        if not exptName:
            exptName = 'exptname'
        exptFolderName = "_".join((date_in,userName,exptName))
        self.exptFolderPath = os.path.join(self._widget.getRecFolder(), exptFolderName)
        return self.exptFolderPath      




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
        self.saveOneTime = True


    # def timeMe(self, timedList, function):
    #         time_color_start = time.time()
    #         function         
    #         time_color_total = time.time()-time_color_start
    #         timedList.append(["{:0.3f} ms".format(time_color_total*1000),"startOneSequence"])
    #         return timedList


    def toggleReconstruction(self):
        self.isReconstruction = not self.isReconstruction
        if not self.isReconstruction:
            self.isActive = False #All of these function here have this same general self variable. Probably a conflict if it was actually used.

    def toggleTilePreview(self):
        self.tilePreview = not self.tilePreview
    
    def toggleRecording(self):
        self.isRecordRaw = not self.isRecordRaw
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
    
    def updateROIsize(self):
        # FIXME: Make it so calibration of only the modified detector is 
        # toggled False
        # Each time size is changed on chip, calibration needs to be reset
        processors = self.processors
        if processors != []:
            for processor in processors:
                processor.isCalibrated = False
    
    def saveParams(self):
        pass

    def loadParams(self):
        pass

    def stopSIM(self):
        self._commChannel.sigSIMAcqToggled.emit(False)
        self.active = False
        self.simThread.join()
        for laser in self.lasers:
            laser.setEnabled(False)
        self._master.arduinoManager.deactivateSLMWriteOnly()
        for detector in self.detectors:
            detector.stopAcquisitionSIM()
        if self.isTiling:
            self.positionerXY.setPositionXY(self.tileOrigin[0], self.tileOrigin[1])
            self.isTiling = False
        # Save log file
        self.createLogFile()







    def startSIM(self):

        # start the background thread
        # for detector in self.detectors:
        #     detector.stopAcquisition()
        self._commChannel.sigSIMAcqToggled.emit(True)
        self.active = True
        simParametersFromGUI = self.getSIMParametersFromGUI()
        #sim_parameters["reconstructionMethod"] = self.getReconstructionMethod()
        #sim_parameters["useGPU"] = self.getIsUseGPU()
        
        # Clear logger files before start of experiment
        self.log_times_loop = []

        self.simThread = threading.Thread(target=self.performSIMExperimentThread, args=(simParametersFromGUI,), daemon=True)
        self.simThread.start()



    # TODO: for timelapse and zstack, check running is still needed also stop

    def updateDisplayImage(self, image):
        image = np.fliplr(image.transpose())
        self._widget.img.setImage(image, autoLevels=True, autoDownsample=False)
        self._widget.updateSIMDisplay(image)
        # self._logger.debug("Updated displayed image")
        
    def getTilingSettings(self):
        self.startxpos, self.startypos = self.positionerXY.get_abs()
        self.num_grid_x = int(self.sharedAttrs[('Tiling Settings','Steps - X')])
        self.num_grid_y = int(self.sharedAttrs[('Tiling Settings','Steps - Y')])
        self.overlap = float(self.sharedAttrs[('Tiling Settings','Overlap')])
        self.reconFramesSkipped = int(self.sharedAttrs[('Tiling Settings','Tiling Repetitions')])

    def getParameterValue(self, detector, parameter_name):
        detector_name = detector._DetectorManager__name
        shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
        if parameter_name == 'ExposureTime':
            value = float(shared_attributes[('Detector', detector_name, 'Param', parameter_name)])
        else:
            self._logger.warning("Debuging needed.")
            self._logger.debug(f"Parameter {parameter_name} not set up in getParameterValue!")
        return value
    
    def setCamForExperiment(self, detector, num_buffers, expTimeMax):


        detector._camera.setPropertyValue('AcquisitionFrameRate', 5.0)
        trigger_source = 'Line2'
        trigger_mode = 'On'
        exposure_auto = 'Off'

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
        dic_parameters = {'TriggerSource':trigger_source, 'TriggerMode':trigger_mode, 'ExposureAuto':exposure_auto, 'ExposureTime':exposure_time, 'PixelFormat':pixel_format, 'AcquisitionFrameRateEnable':frame_rate_enable, 'AcquisitionFrameRate':frame_rate,'StreamBufferHandlingMode':buffer_mode,'ADCBitDepth':bit_depth}

        # for detector in detectors:
        for parameter_name in dic_parameters:
            # print(detector._camera.getPropertyValue(parameter_name))
            detector._camera.setPropertyValue(parameter_name, dic_parameters[parameter_name])
            # print(detector._camera.getPropertyValue(parameter_name))
        # detector.tl_stream_nodemap['StreamBufferHandlingMode'].value = buffer_mode
        detector.startAcquisitionSIM(num_buffers)

    #@APIExport(runOnUIThread=True)
    def sim_getSnapAPI(self, mystack):
        mystack.append(self.detector.getLatestFrame())
        #print(np.shape(mystack))


    def saveImageInBackground(self, image, path, filename):
        print(threading.current_thread())
        try:
            # self.folder = self._widget.getRecFolder()
            filename = os.path.join(path,filename) #FIXME: Remove hardcoded path
            image = np.array(image)
            # tif.imwrite(filename, image, imagej=True, metadata = {'pixelsize':2,'units':'um'})
            tif.imwrite(filename, image, imagej=True)
            self._logger.debug("Saving file: "+filename)
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
    
    def createLogFile(self):
        if self._widget.checkbox_logging.isChecked():
            dir_save = os.path.join(self.exptFolderPath,"logging")
            if not os.path.exists(dir_save):
                os.makedirs(dir_save)
            export_name = os.path.join(dir_save,"log_file.xlsx")
            
            # Loop time logging
            t_loop = np.transpose(self.log_times_loop)
            t_loop_column_names = ["frame","loop time [s]"]
            df = pd.DataFrame(data=t_loop, index=t_loop_column_names).T
            df.to_excel(export_name, sheet_name="Sheet1")
    
    def getReconstructionMethod(self):
        return self._widget.SIMReconstructorList.currentText()

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