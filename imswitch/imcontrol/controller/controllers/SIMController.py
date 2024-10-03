import requests
import json
import os
import glob

import numpy as np
import time
import threading
from datetime import datetime
import tifffile as tif
import os
import time
import numpy as np

from decimal import Decimal
import math
import logging
import sys


from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController
from imswitch.imcommon.framework import Signal, Thread, Worker, Mutex, Timer
# from imswitch.imcontrol.model import SLM4DDManager as SIMclient

import imswitch
import pandas as pd



try:
    import mcsim
    ismcSIM=True
except:
    ismcSIM=False

if ismcSIM:
    try:
        import cupy as cp
        from mcsim.analysis import sim_reconstruction as sim
        isGPU = True
    except:
        print("GPU not available")
        import numpy as cp 
        from mcsim.analysis import sim_reconstruction as sim
        isGPU = False
else:
    isGPU = False
    
try:
    import NanoImagingPack as nip
    isNIP = True
except:
    isNIP = False

try:
    from napari_sim_processor.processors.convSimProcessor import ConvSimProcessor
    from napari_sim_processor.processors.hexSimProcessor import HexSimProcessor
    isSIM = True
    
except:
    isSIM = False

try:
    # FIXME: This does not pass pytests!
    import torch
    isPytorch = True
except:
    isPytorch = False

isDEBUG = False

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
        # self._widget.sigTilingInfoChanged.connect(self.valueChanged)
        self._widget.sigROInfoChanged.connect(self.valueChanged)
        # self._widget.initTilingInfo()


        setupInfoDict = self.makeSetupInfoDict() # Pull SIM setup info into dict and also set on SIM widget.

        #Create list of available laser objects from config file.
        # allLasersDict = self._master.lasersManager.getAllDeviceNames() #Dict of laser name keys and object values.
        self.lasers = list(self._master.lasersManager._subManagers.values()) #List of just the laser object handles
        if len(self.lasers) == 0:
            self._logger.error("No laser found")

        # Create list of detectors objects
        self.detectors = list(self._master.detectorsManager._subManagers.values())
            
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

        # Create class objects for each channel.
        self.SimProcessorLaser1 = SIMProcessor(self, self.sim_parameters, wavelength=self.sim_parameters.ReconWL1)
        self.SimProcessorLaser2 = SIMProcessor(self, self.sim_parameters, wavelength=self.sim_parameters.ReconWL2)
        self.SimProcessorLaser3 = SIMProcessor(self, self.sim_parameters, wavelength=self.sim_parameters.ReconWL3)
        self.SimProcessorLaser1.handle = 488 #This handle is used to keep naming consistent when wavelengths may change.
        self.SimProcessorLaser2.handle = 561
        self.SimProcessorLaser3.handle = 640
        self.processors = [self.SimProcessorLaser1,self.SimProcessorLaser2,self.SimProcessorLaser3]


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
        # self._widget.checkbox_tilepreview.stateChanged.connect(self.toggleTilePreview)
        self._widget.openFolderButton.clicked.connect(self.openFolder)
        self._widget.calibrateButton.clicked.connect(self.calibrateToggled)
        self._widget.saveOneSetButton.clicked.connect(self.saveOneSet)
        # Communication channels signls (signals sent elsewhere in the program)
        self._commChannel.sigAdjustFrame.connect(self.updateROIsize)
        self._commChannel.sigStopSim.connect(self.stopSIM)
        self._commChannel.sigTilePreview.connect(self.toggleTilePreview)
        # self._commChannel.checkbox_tilepreview.stateChanged.connect(self.toggleTilePreview)

        
        #Get RO names from SLM4DDManager and send values to widget function to populate RO list.
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
        
        dic_det_names = {488:'488 Cam', 561:'561 Cam', 640:'640 Cam'} 
        detector_names_connected = self._master.detectorsManager.getAllDeviceNames()
        
        dic_laser_present = {488:True, 561:True, 640:True}
        processors_dic = {488:self.SimProcessorLaser1,561:self.SimProcessorLaser2,640:self.SimProcessorLaser3}
        
        # Check if lasers are set and have power in them select only lasers with powers
        poweredLasers = []
        for laser in self.lasers:
            if laser.percentPower > 0:
                poweredLasers.append(laser.wavelength)

        ##CTNOTE TEMPORARY        
        lasersInUse = [488,561,640] #Overwriting poweredLasers to keep all on at the moment.
        ##CTNOTE TEMPORARY      
        
        # Check if detector is present comparing hardcoded names to connected 
        # names, detector names are used only for pulling imageSize from the 
        # detector
        # FIXME: Check again if this laser checkup makes sense
        det_names = []
        if lasersInUse != []:
            for dic in lasersInUse:
                det_name = dic_det_names[dic]
                if det_name in detector_names_connected:
                    det_names.append(det_name)
                else:
                    self._logger.debug(f"Specified detector {det_name} for {dic} nm laser not present in \n{detector_names_connected} - correct hardcoded names. Defaulting to detector No. 0.")
                    if len(lasersInUse) > len(detector_names_connected):
                        self._logger.debug(f"Not enough detectors configured in config file: {detector_names_connected} for all laser wavelengths selected {lasersInUse}")
                    # FIXME: If used for anything else but pixel number 
                    # readout it should be changed to not continue the code if 
                    # detector not present
                    # break
                    # Defaulting to detector 0 to be still able to run the 
                    # code with only one detector connected. Probably redundant
                    # since detectors default to mocker if the right number of 
                    # detectors is configured in the config file
                    det_name = detector_names_connected[0]
                    det_names.append()
        
        
        
        #Assembling detector list based on active AOTF channels. Pulls current detector shape.
        self.detectors = []        

        
        if det_names != []:
            for det_name in det_names:
                detector = self._master.detectorsManager[det_name]
                self.detectors.append(detector)

        else:
            self._logger.debug(f"Lasers not enabled. Setting image_size_px to default 512x512.")





        
        # Set processors for selected lasers
        processors = []
        isLaser = []

        for wl in lasersInUse:
            if lasersInUse != []:
                processors.append(processors_dic[wl])
                isLaser.append(dic_laser_present[wl])
                processors_dic[wl].isCalibrated = False # force calibration each time 'Start' is pressed.


        # Make processors object attribute so calibration can be changed when 
        # detector size is changed.
        self.processors = processors
        magnification = sim_parameters.Magnification
        camPixelSize = sim_parameters.Pixelsize
        projCamPixelSize = camPixelSize/magnification

 
        self.getTilingSettings() #Get the parameters that go into the createXYGridPositionArray function
        positions = self._master.tilingManager.createXYGridPositionArray(self.num_grid_x, self.num_grid_y, self.overlap, self.startxpos, self.startypos, projCamPixelSize)
        self.tileOrigin = positions[0]

        # Set stacks to be saved into separate folder

        dateTimeStartClick = datetime.now().strftime("%y%m%d%H%M%S")

        # Set file-path read from GUI for each processor
        self.updateProcessorParameters()

            
        # Set count for frames to 0
        self.frameSetCount = 0
        completeFrameSets = 0 # Initialized this counter now that we are not "skipping" broken frames during tiling.
        self.saveOneTime = False
        self.saveOneSetRaw = False
        self.saveOneSetWF = False
        

        # Set running order on SLM
        roID = self._widget.getSelectedRO()
        self._master.SLM4DDManager.setRunningOrder(roID)
        # Get max exposure time from the selected RO on SLM
        expTimeMax = int(self.roNameList[roID].split('ms')[0])*1000

        # -------------------Set-up cams-------------------

        # FIXME: Automate buffer size calculation based on image size, it did not work before
        total_buffer_size_MB = 350 # in MBs
        for detector in self.detectors:
            image_size = detector.shape
            image_size_MB = (2*image_size[0]*image_size[1]/(1024**2))
            buffer_size, decimal = divmod(total_buffer_size_MB/image_size_MB,1)
            # buffer_size = 9
            self.setCamForExperiment(detector, int(buffer_size),expTimeMax)
        


        droppedFrameSets = 0
        time_global_start = time.time()
        time_whole_start = time_global_start
        self._master.arduinoManager.activateSLMWriteOnly() #This command activates the arduino to be ready to receiv e triggers.
        time.sleep(.01) # Need small time delay between sending activateSLM() and trigOneSequence() functions. Only adds to very first loop time. 1 ms was not enough.

        # fullCycles = 0
        
        while self.active and lasersInUse != []:

            stackSIM = [] 
            for k in range(len(processors)):
                # wfImages.append([])
                stackSIM.append([]) 
            # TODO: SLM drives laser powers, do lasers really need to be 
            # enabled?

                
            # Set frame number - prepared for time-lapse
         
            
            # Generate time_step
            if self.frameSetCount == 0:
                exptTimeElapsed = 0.0
            else:
                exptTimeElapsed = time.time() - time_global_start

            self.exptTimeElapsedStr = self.getElapsedTimeString(exptTimeElapsed)

            # Scan over all positions generated for grid
            j = 0 # Position iterator
            while j < len(positions):
 
                pos = positions[j]
                
                # FIXME: Remove after development is completed
                times_color = []
                time_color_start = time.time()

                # Move stage only if grid positions is greater than 1
                if len(positions) != 1 and j != 0:
                    self.positionerXY.setPositionXY(pos[0], pos[1])
                    self.isTiling = True
                    time.sleep(.3)

                time_color_end = time.time()
                time_color_total = time_color_end-time_color_start
                times_color.append(["{:0.3f} ms".format(time_color_total*1000),"move stage"])
                                
                # Trigger SIM set acquisition for all present lasers
                time_color_start = time.time()

                self._master.arduinoManager.trigOneSequenceWriteOnly()
               

                time_color_end = time.time()
                time_color_total = time_color_end-time_color_start
                times_color.append(["{:0.3f} ms".format(time_color_total*1000),"startOneSequence"])

                numActiveChannels = len(poweredLasers)
                self.exptFolderPath = self.makeExptFolderStr(dateTimeStartClick)
                # Loop over channels
                for k, processor in enumerate(processors):
                    # Setting a reconstruction processor for current laser
                    self.powered = self.detectors[k]._detectorInfo.managerProperties['wavelength'] in poweredLasers
                    self.LaserWL = self.detectors[k]._detectorInfo.managerProperties['wavelength']
                    
                    # Set current detector being used
                    detector = self.detectors[k]
                    
                    # FIXME: Remove after development is completed


                    time_color_start = time.time()
                    
                    # 3 angles 3 phases
                    framesPerDetector = 9


                    waitingBuffers = detector._camera.getBufferValue()

                    waitingBuffersEnd = 0
                    bufferStartTime = time.time()
                    broken = False
                    if k == 0:
                        time.sleep(expTimeMax/1000000*16)
                    while waitingBuffers != 9:
                        
                        time.sleep(expTimeMax/1000000)
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
                        broken = False
                        # print(waitingBuffers,bufferTotalTime)
                        if waitingBuffers != 9 and bufferTotalTime > expTimeMax/250000: #expTimeMax/250000 = 4x exp time in correct units
                        # if waitingBuffers != 9 and bufferTotalTime > .1: #expTimeMax/250000 = 4x exp time in correct units
                            self._logger.error(f'Frameset thrown in trash. Buffer available is {waitingBuffers} on detector {detector.name}')
                            for detector in self.detectors:
                                detector._camera.clearBuffers()
                            
                            broken = True
                            break
                        
                        
                    if broken == True:
                        droppedFrameSets += 1
                        
                        break

                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"buffer filling"])

                    time_color_start = time.time()
                    self.rawStack = detector._camera.grabFrameSet(framesPerDetector)
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"grab_stack"])

                    time_color_start = time.time()


                    if self.powered:
                        self.sigRawStackReceived.emit(np.array(self.rawStack),f"{processor.handle} Raw")
                        
                        # Set sim stack for processing all functions work on 
                        processor.setSIMStack(self.rawStack)
                        
                        # Push all wide fields into one array.
                        imageWF = processor.getWFlbf(self.rawStack)
                        imageWF = imageWF.astype(np.uint16)
                        if self.tilePreview and not len(positions)==1:
                            self._commChannel.sigTileImage.emit(imageWF, pos, f"{processor.handle}WF-{j}",numActiveChannels,k, completeFrameSets)

                    
                    # Activate recording and reconstruction in processor
                    processor.setRecordingMode(self.isRecordRecon)
                    processor.setReconstructionMode(self.isReconstruction)
                    processor.setWavelength(self.LaserWL, sim_parameters)
                    
                    # FIXME: Remove after development is completed
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"acquire data"])

                    time_color_start = time.time()

                    if k == 0 and self.saveOneTime:
                        self.saveOneSetRaw = True
                    if self.saveOneSetRaw and self.powered:
                        self.recordOneSetRaw(j)
                    if self.isRecordRaw and self.powered:
                        self.recordRawFunc(j)

                    if k == 0 and self.saveOneTime:
                        self.saveOneSetWF = True
                    if self.saveOneSetWF and self.powered:
                        self.recordOneSetWF(j, imageWF)
                    if self.isRecordWF and self.powered:
                        self.recordWFFunc(j, imageWF)


                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"save data"])

                    time_color_start = time.time()
                    
                    # if self.isReconstruction and div_1 == 0:
                    if self.isReconstruction and self.powered:
                        threading.Thread(target=processor.reconstructSIMStackLBF(self.exptFolderPath,self.frameSetCount, j, self.exptTimeElapsedStr,self.saveOneSetRaw), args=(self.frameSetCount, j, self.exptTimeElapsedStr,self.saveOneSetRaw, ), daemon=True).start()


                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"reconstruct data"])

                    processor.clearStack()                    

               
                    if k==(len(processors)-1) and self.saveOneSetRaw and self.saveOneTime:
                        self.saveOneSetRaw = False
                        self.saveOneTime = False
                        self.saveOneSetWF = False
                
                # self._widget.viewer.grid.enabled = True
                self._logger.debug(f"{times_color}")

                self.frameSetCount += 1
                
                
                # Timing of the process for testing purposes
                time_whole_end = time.time()
                time_whole_total = time_whole_end-time_whole_start                
                time_whole_start = time.time()
                time_global_total = time_whole_end-time_global_start
                self._logger.debug('Loop time: {:.2f} s'.format(time_whole_total))
                self._logger.debug('Expt time: {:.2f} s'.format(time_global_total))
                self._logger.debug('Dropped frames: {}'.format(droppedFrameSets))
                self._logger.debug('Total frames: {}'.format(self.frameSetCount))
                
                self.log_times_loop.append([self.frameSetCount - 1, time_whole_total])


                if self._widget.stop_button.isChecked():
                    self._widget.stop_button.setChecked(False)
                    return
                



                if broken:
                    pass
                else:
                    j += 1
                    completeFrameSets += 1

                if len(positions) != 1 and not (completeFrameSets +1 < len(positions)*int(self.sharedAttrs[('Tiling Settings','Tiling Repetitions')])): 
                    self._commChannel.sigStopSim.emit() # Actually calced wrong. Correct calc allows one more cycle than wanted. If we call stopSIM one cycle early, appears to work. Very stupid.
                


                

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
        threading.Thread(target=self.saveImageInBackground, args=(self.rawStack,rawSavePath, rawFilenames,), daemon=True).start()

    def recordRawFunc(self,j):
        rawSavePath = os.path.join(self.exptFolderPath, "RawStacks")
        if not os.path.exists(rawSavePath):
            os.makedirs(rawSavePath)
        rawFilenames = f"f{self.frameSetCount:04}_pos{j:04}_{int(self.LaserWL):03}_{self.exptTimeElapsedStr}.tif"
        threading.Thread(target=self.saveImageInBackground, args=(self.rawStack,rawSavePath, rawFilenames,), daemon=True).start()

    def recordOneSetWF(self,j,im):
        wfSavePath = os.path.join(self.exptFolderPath,'Snapshot')
        if not os.path.exists(wfSavePath):
            os.makedirs(wfSavePath)
        wfFilenames = f"f{self.frameSetCount:04}_pos{j:04}_{int(self.LaserWL):03}_{self.exptTimeElapsedStr}_WF.tif"
        threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames,), daemon=True).start()

    def recordWFFunc(self,j,im):
        wfSavePath = os.path.join(self.exptFolderPath, "WF")
        if not os.path.exists(wfSavePath):
            os.makedirs(wfSavePath)
        wfFilenames = f"f{self.frameSetCount:04}_pos{j:04}_{int(self.LaserWL):03}_{self.exptTimeElapsedStr}.tif"
        threading.Thread(target=self.saveImageInBackground, args=(im,wfSavePath, wfFilenames,), daemon=True).start()





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
        try:
            # self.folder = self._widget.getRecFolder()
            filename = os.path.join(path,filename) #FIXME: Remove hardcoded path
            image = np.array(image)
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

    def getIsUseGPU(self):
        return self._widget.useGPUCheckbox.isChecked()
    
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


class SIMParameters(object):
    def __init__(self):
        pass

class SIMProcessor(object):

    def __init__(self, parent, simParameters, wavelength):
        '''
        setup parameters
        '''
        #current parameters is setting for 60x objective 488nm illumination
        self.parent = parent
        # self.mFile = "/Users/bene/Dropbox/Dokumente/Promotion/PROJECTS/MicronController/PYTHON/NAPARI-SIM-PROCESSOR/DATA/SIMdata_2019-11-05_15-21-42.tiff"

        self.NA = simParameters.NA
        self.n = simParameters.n
        self.wavelength = wavelength/1000
        self.pixelsize = simParameters.Pixelsize
        self.magnification = simParameters.Magnification
        self.alpha = simParameters.Alpha
        self.beta = simParameters.Beta
        self.w = simParameters.w
        self.eta = simParameters.eta

        self.phases_number = 3
        self.angles_number = 3
        self.dz= 0.55
        self.group = 30
        self.use_phases = True
        self.find_carrier = True
        self.isCalibrated = False
        self.use_gpu = isPytorch ##Pytorch boolen refernce
        self.stack = []
        self._nsteps = self.angles_number * self.phases_number
        self._nbands = self.angles_number

        # processing parameters
        self.isRecording = False
        self.allPatterns = []
        self.isReconstructing = False

        # initialize logger
        self._logger = initLogger(self, tryInheritParent=False)

        # switch for the different reconstruction algorithms
        self.reconstructionMethod = "napari"

        # set model
        #h = HexSimProcessor(); #
        if isSIM:
            self.h = ConvSimProcessor()
            self.k_shape = (3,1)
        else:
            self._logger.error("Please install napari sim! pip install napari-sim-processor")

        # setup
        self.h.debug = False
        self.setReconstructorInit()
        self.kx_input = np.zeros(self.k_shape, dtype=np.single)
        self.ky_input = np.zeros(self.k_shape, dtype=np.single)
        self.p_input = np.zeros(self.k_shape, dtype=np.single)
        self.ampl_input = np.zeros(self.k_shape, dtype=np.single)

        # set up the GPU for mcSIM
        if isGPU:
            # GPU memory usage
            mempool = cp.get_default_memory_pool()
            pinned_mempool = cp.get_default_pinned_memory_pool()
            memory_start = mempool.used_bytes()

    def loadPattern(self, path=None, filetype="bmp"):
        # sort filenames numerically
        import glob
        import cv2

        if path is None:
            path = sim_parameters["patternPath"]
        allPatternPaths = sorted(glob.glob(os.path.join(path, "*."+filetype)))
        self.allPatterns = []
        for iPatternPath in allPatternPaths:
            mImage = cv2.imread(iPatternPath)
            mImage = cv2.cvtColor(mImage, cv2.COLOR_BGR2GRAY)
            self.allPatterns.append(mImage)
        return self.allPatterns

    def getPattern(self, iPattern):
        # return ith sim pattern
        return self.allPatterns[iPattern]

    def setParameters(self, sim_parameters):
        # uses parameters from GUI
        self.pixelsize= sim_parameters.Pixelsize
        self.NA= sim_parameters.NA
        self.n= sim_parameters.n
        self.reconstructionMethod = "napari" # sim_parameters["reconstructionMethod"]
        #self.use_gpu = False #sim_parameters["useGPU"]
        self.eta =  sim_parameters.eta
        self.magnification = sim_parameters.Magnification
        self.path = sim_parameters.saveDir
        self.alpha = sim_parameters.Alpha
        self.beta = sim_parameters.Beta
        self.w = sim_parameters.w

    def setReconstructionMethod(self, method):
        self.reconstructionMethod = method

    def setReconstructor(self):
        '''
        Sets the attributes of the Processor
        Executed frequently, upon update of several settings
        '''

        self.h.usePhases = self.use_phases
        self.h.magnification = self.magnification
        self.h.NA = self.NA
        self.h.n = self.n
        self.h.wavelength = self.wavelength
        self.h.pixelsize = self.pixelsize
        self.h.alpha = self.alpha
        self.h.beta = self.beta
        self.h.w = self.w
        self.h.eta = self.eta
        self.h._nsteps = self._nsteps
        self.h._nbands = self._nbands

        if not self.find_carrier:
            self.h.kx = self.kx_input
            self.h.ky = self.ky_input

    def setReconstructorInit(self):
        '''
        Sets the attributes of the Processor
        Executed frequently, upon update of several settings
        '''

        self.h.usePhases = self.use_phases
        self.h.magnification = self.magnification
        self.h.NA = self.NA
        self.h.n = self.n
        self.h.wavelength = self.wavelength
        #self.h.wavelength = 0.52
        self.h.pixelsize = self.pixelsize
        self.h.alpha = self.alpha
        self.h.beta = self.beta
        self.h.w = self.w
        self.h.eta = self.eta
        self.h._nsteps = self._nsteps
        self.h._nbands = self._nbands

        if not self.find_carrier:
            self.h.kx = self.kx_input
            self.h.ky = self.ky_input
        
    def getWFlbf(self, mStack):
        # display the BF image
        # bfFrame = np.sum(np.array(mStack[-3:]), 0)
        bfFrame = np.round(np.mean(np.array(mStack), 0)) #CTNOTE See if need all 9 or 3





        self.parent.sigWFImageComputed.emit(bfFrame, f"{self.handle} WF")
        return bfFrame
        
    def setSIMStack(self, stack):
        self.stack = stack

    def getSIMStack(self):
        return np.array(self.stack)

    def clearStack(self):
        self.stack=[]

    def get_current_stack_for_calibration(self,data):
        self._logger.error("get_current_stack_for_calibration not implemented yet")
        '''
        Returns the 4D raw image (angles,phases,y,x) stack at the z value selected in the viewer

        if(0):
            data = np.expand_dims(np.expand_dims(data, 0), 0)
            dshape = data.shape # TODO: Hardcoded ...data.shape
            zidx = 0
            delta = group // 2
            remainer = group % 2
            zmin = max(zidx-delta,0)
            zmax = min(zidx+delta+remainer,dshape[2])
            new_delta = zmax-zmin
            data = data[...,zmin:zmax,:,:]
            phases_angles = phases_number*angles_number
            rdata = data.reshape(phases_angles, new_delta, dshape[-2],dshape[-1])
            cal_stack = np.swapaxes(rdata, 0, 1).reshape((phases_angles * new_delta, dshape[-2],dshape[-1]))
        '''
        return data


    def calibrate(self, imRaw):
        '''
        calibration
        '''
        #self._logger.debug("Starting to calibrate the stack")
        if self.reconstructionMethod == "napari":
            #imRaw = get_current_stack_for_calibration(mImages)
            if type(imRaw) is list:
                imRaw = np.array(imRaw)
            if self.use_gpu:
                self.h.calibrate_pytorch(imRaw, self.find_carrier)
            else:
                #self.h.calibrate(imRaw, self.find_carrier)
                self.h.calibrate(imRaw)
            self.isCalibrated = True
            if self.find_carrier: # store the value found
                self.kx_input = self.h.kx
                self.ky_input = self.h.ky
                self.p_input = self.h.p
                self.ampl_input = self.h.ampl
            self._logger.debug("Done calibrating the stack")


        elif self.reconstructionMethod == "mcsim":
            """
            test running SIM reconstruction at full speed on GPU
            """

            # ############################
            # for the first image, estimate the SIM parameters
            # this step is slow, can take ~1-2 minutes
            # ############################
            self._logger.debug("running initial reconstruction with full parameter estimation")

            # first we need to reshape the stack to become 3x3xNxxNy
            imRawMCSIM = np.stack((imRaw[0:3,],imRaw[3:6,],imRaw[6:,]),0)
            imgset = sim.SimImageSet({"pixel_size": self.pixelsize,
                                    "na": self.NA,
                                    "wavelength": self.wavelength*1e-3},
                                    imRawMCSIM,
                                    otf=None,
                                    wiener_parameter=0.3,
                                    frq_estimation_mode="band-correlation",
                                    # frq_guess=frqs_gt, # todo: can add frequency guesses for more reliable fitting
                                    phase_estimation_mode="wicker-iterative",
                                    phases_guess=np.array([[0, 2*np.pi / 3, 4 * np.pi / 3],
                                                            [0, 2*np.pi / 3, 4 * np.pi / 3],
                                                            [0, 2*np.pi / 3, 4 * np.pi / 3]]),
                                    combine_bands_mode="fairSIM",
                                    fmax_exclude_band0=0.4,
                                    normalize_histograms=False,
                                    background=100,
                                    gain=2,
                                    use_gpu=self.use_gpu)

            # this included parameter estimation
            imgset.reconstruct()
            # extract estimated parameters
            self.mcSIMfrqs = imgset.frqs
            self.mcSIMphases = imgset.phases - np.expand_dims(imgset.phase_corrections, axis=1)
            self.mcSIMmod_depths = imgset.mod_depths
            self.mcSIMotf = imgset.otf

            # clear GPU memory
            imgset.delete()

    def getIsCalibrated(self):
        return self.isCalibrated


    
    def reconstructSIMStackLBF(self,exptPath, frameSetCount, pos_num, exptTimeElapsedStr, saveOne):
        '''
        reconstruct the image stack asychronously
        '''
        # TODO: Perhaps we should work with quees?
        # reconstruct and save the stack in background to not block the main thread
        if not self.isReconstructing:  # not
            self.isReconstructing=True
            mStackCopy = np.array(self.stack.copy())
            # self.mReconstructionThread = threading.Thread(target=self.reconstructSIMStackBackgroundLBF(mStackCopy, date, frame_num, pos_num, dt_frame), args=(mStackCopy, ), daemon=True)
            # self.mReconstructionThread.start()
            self.reconstructSIMStackBackgroundLBF(mStackCopy, exptPath, frameSetCount, pos_num, exptTimeElapsedStr,saveOne)

    def setRecordingMode(self, isRecording):
        self.isRecording = isRecording

    def setReconstructionMode(self, isReconstruction):
        self.isReconstruction = isReconstruction

    # def setDate(self, date):
    #     self.date = date
        
    # def setPath(self, path):
    #     self.path = path
        
    def setFrameNum(self, frame_num):
        self.frame_num = frame_num
        
    def setPositionNum(self, pos_num):
        self.pos_num = pos_num

    def setWavelength(self, wavelength, sim_parameters):
        self.LaserWL = wavelength
        if self.LaserWL == 488:
            self.h.wavelength = sim_parameters.ReconWL1
        elif self.LaserWL == 561:
            self.h.wavelength = sim_parameters.ReconWL2
        elif self.LaserWL == 640:
            self.h.wavelength = sim_parameters.ReconWL1
        
    def reconstructSIMStackBackgroundLBF(self, mStack, exptPath, frameSetCount, pos_num, exptTimeElapsedStr,saveOne):
        '''
        reconstruct the image stack asychronously
        the stack is a list of 9 images (3 angles, 3 phases)
        '''
        # compute image
        # initialize the model
        self._logger.debug("Processing frames")
        if not self.getIsCalibrated():
            
            self.setReconstructor()
            self.calibrate(mStack)
        self.SIMReconstruction = self.reconstruct(mStack)

        # save images eventually
        if self.isRecording:
            self.recordSIMFunc(exptPath, frameSetCount,pos_num, exptTimeElapsedStr)
        if saveOne:
            exptPathOne = os.path.join(exptPath, "Snapshot")
            self.recordOneSetSIM(exptPathOne, frameSetCount,pos_num, exptTimeElapsedStr)

        self.parent.sigSIMProcessorImageComputed.emit(np.array(self.SIMReconstruction), f"{self.handle} Recon") #Reconstruction emit
        
        self.isReconstructing = False

    def recordSIMFunc(self, exptPath, frameSetCount,pos_num,exptTimeElapsedStr):
        reconSavePath = os.path.join(exptPath, "Recon")
        reconFilenames = f"f{frameSetCount:04}_pos{pos_num:04}_{int(self.LaserWL):03}_{exptTimeElapsedStr}.tif"
        threading.Thread(target=self.saveImageInBackground, args=(self.SIMReconstruction, reconSavePath,reconFilenames ,)).start()

    def recordOneSetSIM(self, exptPath, frameSetCount,pos_num,exptTimeElapsedStr):
        reconSavePath = exptPath
        reconFilenames = f"f{frameSetCount:04}_pos{pos_num:04}_{int(self.LaserWL):03}_{exptTimeElapsedStr}_recon.tif"
        threading.Thread(target=self.saveImageInBackground, args=(self.SIMReconstruction, reconSavePath,reconFilenames ,)).start()

    def saveImageInBackground(self, image, savePath, saveName ):
        try:
            if not os.path.exists(savePath):
                os.makedirs(savePath)
            
            # self.folder = self.path
            filePath = os.path.join(savePath,saveName) #FIXME: Remove hardcoded path
            tif.imwrite(filePath, image)
            self._logger.debug("Saving file: "+filePath)
        except  Exception as e:
            self._logger.error(e)

    def reconstruct(self, currentImage):
        '''
        reconstruction
        '''
        if self.reconstructionMethod == "napari":
            # we use the napari reconstruction method
            self._logger.debug("reconstructing the stack with napari")
            assert self.isCalibrated, 'SIM processor not calibrated, unable to perform SIM reconstruction'

            dshape= np.shape(currentImage)
            phases_angles = self.phases_number*self.angles_number
            rdata = currentImage[:phases_angles, :, :].reshape(phases_angles, dshape[-2],dshape[-1])
            if self.use_gpu:
                imageSIM = self.h.reconstruct_pytorch(rdata.astype(np.float32)) #TODO:this is left after conversion from torch
            else:
                imageSIM = self.h.reconstruct_rfftw(rdata)

            return imageSIM #CTNOTE This is returned with negative values

        elif self.reconstructionMethod == "mcSIM":
            """
            test running SIM reconstruction at full speed on GPU
            """

            '''
            # load images
            root_dir = os.path.join(Path(__file__).resolve().parent, 'data')
            fname_data = os.path.join(root_dir, "synthetic_microtubules_512.tif")
            imgs = tifffile.imread(fname_data)
            '''
            self._logger.debug("reconstructing the stack with mcsim")

            imgset_next = sim.SimImageSet({"pixel_size": self.dxy,
                                        "na": self.na,
                                        "wavelength": self.wavelength},
                                        currentImage,
                                        otf=self.mcSIMotf,
                                        wiener_parameter=0.3,
                                        frq_estimation_mode="fixed",
                                        frq_guess=self.mcSIMfrqs,
                                        phase_estimation_mode="fixed",
                                        phases_guess=self.mcSIMphases,
                                        combine_bands_mode="fairSIM",
                                        mod_depths_guess=self.mcSIMmod_depths,
                                        use_fixed_mod_depths=True,
                                        fmax_exclude_band0=0.4,
                                        normalize_histograms=False,
                                        background=100,
                                        gain=2,
                                        use_gpu=True,
                                        print_to_terminal=False)

            imgset_next.reconstruct()
            imageSIM = imgset_next.sim_sr.compute()
            return imageSIM

    # def simSimulator(self, Nx=512, Ny=512, Nrot=3, Nphi=3):
    #     Isample = np.zeros((Nx,Ny))
    #     Isample[np.random.random(Isample.shape)>0.999]=1

    #     allImages = []
    #     for iRot in range(Nrot):
    #         for iPhi in range(Nphi):
    #             IGrating = 1+np.sin(((iRot/Nrot)*nip.xx((Nx,Ny))+(Nrot-iRot)/Nrot*nip.yy((Nx,Ny)))*np.pi/2+np.pi*iPhi/Nphi)
    #             allImages.append(nip.gaussf(IGrating*Isample,3))

    #     allImages=np.array(allImages)
    #     allImages-=np.min(allImages)
    #     allImages/=np.max(allImages)
    #     return allImages
