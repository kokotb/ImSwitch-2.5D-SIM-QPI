import requests
import json
import os

import numpy as np
import time
import threading
from datetime import datetime
import tifffile as tif
import os
import time
import numpy as np
from datetime import datetime

import math
import logging
import sys


from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController
from imswitch.imcommon.framework import Signal, Thread, Worker, Mutex, Timer
# from imswitch.imcontrol.model import SIMslmManager as SIMclient

import imswitch



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

    sigImageReceived = Signal(np.ndarray, str)
    sigSIMProcessorImageComputed = Signal(np.ndarray, str)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self.IS_FASTAPISIM=False
        self.IS_HAMAMATSU=False
        # switch to detect if a recording is in progress
        self.isRecording = False
        self.isReconstruction = False

        # Laser flag
        self.LaserWL = 0

        self.simFrameVal = 0
        self.nsimFrameSyncVal = 3

        # Choose which laser will be recorded
        self.is488 = True
        self.is561 = True
        self.is640 = True
        
        
        

        # we can switch between mcSIM and napari
        self.reconstructionMethod = "napari" # or "mcSIM"

        # save directory of the reconstructed frames
        self.simDir = os.path.join(dirtools.UserFileDirs.Root, 'imcontrol_sim')
        if not os.path.exists(self.simDir):
            os.makedirs(self.simDir)

        # load config file
        if self._setupInfo.sim is None:
            self._widget.replaceWithError('SIM is not configured in your setup file.')
            return
        
        self.setupInfo = self._setupInfo.sim
        
        # Set if mock is present or not
        self.mock = self.setupInfo.isMock

        # connect live update  https://github.com/napari/napari/issues/1110
        self.sigImageReceived.connect(self.displayImage)

        # select lasers
        allLaserNames = self._master.lasersManager.getAllDeviceNames()
        self.lasers = []
        for iDevice in allLaserNames:
            if iDevice.lower().find("laser")>=0 or iDevice.lower().find("led"):
                self.lasers.append(self._master.lasersManager[iDevice])
        if len(self.lasers) == 0:
            self._logger.error("No laser found")
            # add a dummy laser
            class dummyLaser():
                def __init__(self, name, power):
                    self.power = 0.0
                    self.setEnabled = lambda x: x
                    self.name = name
                    self.power = power
                def setPower(self,power):
                    self.power = power
                def setEnabled(self,enabled):
                    self.enabled = enabled
            for i in range(2):
                self.lasers.append(dummyLaser("Laser"+str(i), 100))
        # select detectors
        allDetectorNames = self._master.detectorsManager.getAllDeviceNames()
        self.detector = self._master.detectorsManager[allDetectorNames[0]]
        if self.detector.model == "CameraPCO":
            # here we can use the buffer mode
            self.isPCO = True
        else:
            # here we need to capture frames consecutively
            self.isPCO = False

        # select positioner
        # FIXME: Hardcoded position of positioner, dependent on .xml configuration of positioners, maybe go to by-positioner-name positioner selection and throwing an error if it does not match
        self.positionerName = self._master.positionersManager.getAllDeviceNames()[0]
        self.positioner = self._master.positionersManager[self.positionerName]
        self.positionerNameXY = self._master.positionersManager.getAllDeviceNames()[1]
        self.positionerXY = self._master.positionersManager[self.positionerNameXY]

        # setup the SIM processors
        sim_parameters = SIMParameters()
        self.SimProcessorLaser1 = SIMProcessor(self, sim_parameters, wavelength=sim_parameters.wavelength_1)
        self.SimProcessorLaser2 = SIMProcessor(self, sim_parameters, wavelength=sim_parameters.wavelength_2)
        self.SimProcessorLaser3 = SIMProcessor(self, sim_parameters, wavelength=sim_parameters.wavelength_3)

        # Connect CommunicationChannel signals
        self.sigSIMProcessorImageComputed.connect(self.displayImage)

        self.initFastAPISIM(self._master.simManager.fastAPISIMParams)

        # FIXME: imswitch as is currently set up does not contain 
        # IS_HEADLESS attirbute  
        # if imswitch.IS_HEADLESS:
        #     return
        # return
        self._widget.start_button.clicked.connect(self.startSIM)
        self._widget.stop_button.clicked.connect(self.stopSIM)

        #self._widget.is488LaserButton.clicked.connect(self.toggle488Laser)
        #self._widget.is561LaserButton.clicked.connect(self.toggle561Laser)
        #self._widget.is640LaserButton.clicked.connect(self.toggle640Laser)
        self._widget.checkbox_record_raw.stateChanged.connect(self.toggleRecording)
        self._widget.checkbox_record_reconstruction.stateChanged.connect(self.toggleRecordReconstruction)
        self._widget.checkbox_mock.stateChanged.connect(self.toggleMockUse)
        #self._widget.sigPatternID.connect(self.patternIDChanged)
        self._widget.number_dropdown.currentIndexChanged.connect(self.patternIDChanged)
        #self._widget.checkbox_reconstruction.stateChanged.connect(self.toggleRecording)
        # read parameters from the widget
        self._widget.start_timelapse_button.clicked.connect(self.startTimelapse)
        self._widget.start_zstack_button.clicked.connect(self.startZstack)
        self._widget.openFolderButton.clicked.connect(self.openFolder)
        self.folder = self._widget.getRecFolder()

    def toggleRecording(self):
        self.isRecording = not self.isRecording
        if not self.isRecording:
            self.isActive = False

    def toggleRecordReconstruction(self):
        self.isReconstruction = not self.isReconstruction
        if not self.isReconstruction:
            self.isActive = False
            
    def toggleMockUse(self):
        self.mock = self._widget.checkbox_mock.isChecked()

    def openFolder(self):
        """ Opens current folder in File Explorer. """
        folder = self._widget.getRecFolder()
        if not os.path.exists(folder):
            os.makedirs(folder)
        ostools.openFolderInOS(folder)


    def initFastAPISIM(self, params):
        self.fastAPISIMParams = params
        self.IS_FASTAPISIM = True

        # Usage example
        host = self.fastAPISIMParams["host"]
        port = self.fastAPISIMParams["port"]
        tWaitSequence = self.fastAPISIMParams["tWaitSquence"]

        if tWaitSequence is None:
            tWaitSequence = 0.1
        if host is None:
            host = "169.254.165.4"
        if port is None:
            port = 8000

        self.SIMClient = SIMClient(URL=host, PORT=port)
        self.SIMClient.set_pause(tWaitSequence)


    def initHamamatsuSLM(self):
        self.hamamatsuslm = nip.HAMAMATSU_SLM() # FIXME: Add parameters
        #def __init__(self, dll_path = None, OVERDRIVE = None, use_corr_pattern = None, wavelength = None, corr_pattern_path = None):
        allPatterns = self._master.simManager.allPatterns[self.patternID]
        for im_number, im in enumerate(allPatterns):
            self.hamamatsuslm.send_dat(im, im_number)

    def __del__(self):
        pass
        #self.imageComputationThread.quit()
        #self.imageComputationThread.wait()

    def toggleSIMDisplay(self, enabled=True):
        self._widget.setSIMDisplayVisible(enabled)

    def monitorChanged(self, monitor):
        self._widget.setSIMDisplayMonitor(monitor)

    def patternIDChanged(self, patternID):
        wl = self.getpatternWavelength()
        if wl == 'Laser 488nm':
            laserTag = 0
        elif wl == 'Laser 561nm':
            laserTag = 1
        elif wl == 'Laser 640nm':
            laserTag = 2
        else:
            laserTag = 0
            self._logger.error("The laser wavelength is not implemented")
        self.simPatternByID(patternID,laserTag)

    def getpatternWavelength(self):
        return self._widget.laser_dropdown.currentText()

    def displayMask(self, image):
        self._widget.updateSIMDisplay(image)

    def setIlluPatternByID(self, iRot, iPhi):
        self.detector.setIlluPatternByID(iRot, iPhi)

    def displayImage(self, im, name="SIM Reconstruction"):
        """ Displays the image in the view. """
        self._widget.setImage(im, name=name)

    def saveParams(self):
        pass

    def loadParams(self):
        pass

    def stopSIM(self):
        self.active = False
        self.simThread.join()
        self.lasers[0].setEnabled(False)
        self.lasers[1].setEnabled(False)
        if self.isPCO:
            self.detector.setParameter("trigger_source","Internal trigger")
            self.detector.setParameter("buffer_size",-1)
            self.detector.flushBuffers()

    # TODO: old definition - to delete after dev
    # def startSIM(self):
    #     #  need to be in trigger mode
    #     # therefore, we need to stop the camera first and then set the trigger mode

    #     if self.isPCO:
    #         # prepare camera for buffer mode
    #         self._commChannel.sigStopLiveAcquisition.emit(True)
    #         self.detector.setParameter("trigger_source","External start")
    #         self.detector.setParameter("buffer_size",9)
    #         self.detector.flushBuffers()
    #     #self._commChannel.sigStartLiveAcquistion.emit(True)

    #     # start the background thread
    #     self.active = True
    #     sim_parameters = self.getSIMParametersFromGUI()
    #     #sim_parameters["reconstructionMethod"] = self.getReconstructionMethod()
    #     #sim_parameters["useGPU"] = self.getIsUseGPU()
    #     self.simThread = threading.Thread(target=self.performSIMExperimentThread, args=(sim_parameters,), daemon=True)
    #     self.simThread.start()


    def startSIM(self):
        #  need to be in trigger mode
        # therefore, we need to stop the camera first and then set the trigger mode

        # TODO: Will need to use that with our cam, check with Cody the format
        if self.isPCO:
            # prepare camera for buffer mode
            self._commChannel.sigStopLiveAcquisition.emit(True)
            self.detector.setParameter("trigger_source","External start")
            self.detector.setParameter("buffer_size",9)
            self.detector.flushBuffers()
        #self._commChannel.sigStartLiveAcquistion.emit(True)

        # start the background thread
        self.active = True
        sim_parameters = self.getSIMParametersFromGUI()
        #sim_parameters["reconstructionMethod"] = self.getReconstructionMethod()
        #sim_parameters["useGPU"] = self.getIsUseGPU()
        self.simThread = threading.Thread(target=self.performSIMExperimentThread, args=(sim_parameters,), daemon=True)
        self.simThread.start()

    # for timelapse and zstack, check running is still needed also stop

    def startTimelapse(self):
        if self.isPCO:    
            self._commChannel.sigStopLiveAcquisition.emit(True)
            self.detector.setParameter("trigger_source","External start")
            self.detector.setParameter("buffer_size",9)
            self.detector.flushBuffers()

        self.active = True
        sim_parameters = self.getSIMParametersFromGUI()

        timePeriod = int(self._widget.period_textedit.text())
        Nframes = int(self._widget.frames_textedit.text())
        self.oldTime = time.time()-timePeriod # to start the timelapse immediately
        iiter = 0
        # if it is nessary to put timelapse in background
        while iiter < Nframes:
            if time.time() - self.oldTime > timePeriod:
                self.oldTime = time.time()
                self.simThread = threading.Thread(target=self.performSIMTimelapseThread, args=(sim_parameters,), daemon=True)
                self.simThread.start()
                iiter += 1
        self._logger.debug("Timelapse finished")
        self.active = False
        self.lasers[0].setEnabled(False)
        self.lasers[1].setEnabled(False)
        if self.isPCO:    
            self.detector.setParameter("trigger_source","Internal trigger")
            self.detector.setParameter("buffer_size",-1)
        self.detector.flushBuffers()

    def startZstack(self):
        
        if self.isPCO:
            self._commChannel.sigStopLiveAcquisition.emit(True)
            self.detector.setParameter("trigger_source","External start")
            self.detector.setParameter("buffer_size",9)
            self.detector.flushBuffers()

        self.active = True
        sim_parameters = self.getSIMParametersFromGUI()
        zMin = float(self._widget.zmin_textedit.text())
        zMax = float(self._widget.zmax_textedit.text())
        zStep = int(self._widget.nsteps_textedit.text())
        zDis = int((zMax - zMin) / zStep)
        self._master.detectorsManager
        #do Zstack in background
        self.simThread = threading.Thread(target=self.performSIMZstackThread, args=(sim_parameters,zDis,zStep), daemon=True)
        self.simThread.start()


    def toggle488Laser(self):
        self.is488 = not self.is488
        if self.is488:
            self._widget.is488LaserButton.setText("488 on")
        else:
            self._widget.is488LaserButton.setText("488 off")

    def toggle561Laser(self):
        self.is561 = not self.is561
        if self.is561:
            self._widget.is561LaserButton.setText("561 on")
        else:
            self._widget.is561LaserButton.setText("561 off")
            
    def toggle640Laser(self):
        self.is640 = not self.is640
        if self.is640:
            self._widget.is640LaserButton.setText("640 on")
        else:
            self._widget.is640LaserButton.setText("640 off")

    def updateDisplayImage(self, image):
        image = np.fliplr(image.transpose())
        self._widget.img.setImage(image, autoLevels=True, autoDownsample=False)
        self._widget.updateSIMDisplay(image)
        # self._logger.debug("Updated displayed image")
        
    def getExperimentSettings(self):
        parameter_dict = self._widget.getRecParameters()
        
        # Load parameters to object
        self.num_grid_x = int(parameter_dict['num_grid_x'])
        self.num_grid_y = int(parameter_dict['num_grid_y'])
        self.overlap = float(parameter_dict['overlap'])

    #@APIExport(runOnUIThread=True)
    def simPatternByID(self, patternID: int, wavelengthID: int):
        try:
            patternID = int(patternID)
            wavelengthID = int(wavelengthID)
            self.SIMClient.set_wavelength(wavelengthID)
            self.SIMClient.display_pattern(patternID)
            return wavelengthID
        except Exception as e:
            self._logger.error(e)

    #@APIExport(runOnUIThread=True)
    # TODO: Old one ti delete
    # def performSIMExperimentThread(self, sim_parameters):
    #     """
    #     Iterate over all SIM patterns, display them and acquire images
    #     """
    #     self.patternID = 0
    #     self.isReconstructing = False
    #     nColour = 2 #[488, 640]
    #     dic_wl = [488, 640]

    #     # retreive Z-stack parameters
    #     zStackParameters = self._widget.getZStackParameters()
    #     zMin, zMax, zStep = zStackParameters[0], zStackParameters[1], zStackParameters[2] # if zStep < 0, it will not move in z
    #     tDebounce = 0.1 # debounce time between z-steps

    #     # retreive timelapse parameters
    #     timelapsedParameters = self._widget.getTimelapseParameters()
    #     timePeriod, Nframes = timelapsedParameters[0], timelapsedParameters[1] # if NFrames < 0, it will run indefinitely

    #     # get current z-position
    #     zPosInitially = self.positioner.get_abs()

    #     # run the experiment indefinitely
    #     while self.active:

    #         # iterate over all z-positions
    #         if zStep > 0:
    #             allZPositions = np.arange(zMin, zMax, zStep)
    #         else:
    #             allZPositions = [0]

    #         for iColour in range(nColour):
    #             # toggle laser
    #             if not self.active:
    #                 if len(allZPositions)!=1:
    #                     self.positioner.move(value=zPosInitially, axis="Z", is_absolute=True, is_blocking=True)
    #                     time.sleep(tDebounce)
    #                 break

    #             if iColour == 0 and self.is488 and self.lasers[iColour].power>0.0:
    #                 # enable laser 1
    #                 self.lasers[0].setEnabled(True)
    #                 self.lasers[1].setEnabled(False)
    #                 self._logger.debug("Switching to pattern"+self.lasers[0].name)
    #                 processor = self.SimProcessorLaser1
    #                 processor.setParameters(sim_parameters)
    #                 self.LaserWL = processor.wavelength
    #                 # set the pattern-path for laser wl 1
    #             elif iColour == 1 and self.is640 and self.lasers[iColour].power>0.0:
    #                 # enable laser 2
    #                 self.lasers[0].setEnabled(False)
    #                 self.lasers[1].setEnabled(True)
    #                 self._logger.debug("Switching to pattern"+self.lasers[1].name)
    #                 processor = self.SimProcessorLaser2
    #                 processor.setParameters(sim_parameters)
    #                 self.LaserWL = processor.wavelength
    #                 # set the pattern-path for laser wl 1
    #             else:
    #                 time.sleep(.1) # reduce CPU load
    #                 continue

    #             # select the pattern for the current colour
    #             self.SIMClient.set_wavelength(dic_wl[iColour])

    #             for zPos in allZPositions:
    #                 # move to the next z-position
    #                 if len(allZPositions)!=1:
    #                     self.positioner.move(value=zPos+zPosInitially, axis="Z", is_absolute=True, is_blocking=True)
    #                     time.sleep(tDebounce)

    #                 if self.isPCO:
    #                     # display one round of SIM patterns for the right colour
    #                     self.SIMClient.start_viewer_single_loop(1)

    #                     # ensure lasers are off to avoid photo damage
    #                     self.lasers[0].setEnabled(False)
    #                     self.lasers[1].setEnabled(False)

    #                     # download images from the camera
    #                     self.SIMStack = self.detector.getChunk(); self.detector.flushBuffers()
    #                     if self.SIMStack is None:
    #                         self._logger.error("No image received")
    #                         continue
    #                 else:
    #                     # we need to capture images and display patterns one-by-one
    #                     self.SIMStack = []
    #                     try:
    #                         mExposureTime = self.detector.getParameter("exposure")/1e6 # s^-1
    #                     except:
    #                         mExposureTime = 0.1
    #                     for iPattern in range(9):
    #                         self.SIMClient.display_pattern(iPattern)
    #                         time.sleep(mExposureTime) # make sure we take the next newest frame to avoid motion blur from the pattern change

    #                         # Todo: Need to ensure thatwe have the right pattern displayed and the buffer is free - this heavily depends on the exposure time..
    #                         mFrame = None
    #                         lastFrameNumber = -1
    #                         timeoutFrameRequest = 3 # seconds
    #                         cTime = time.time()
    #                         frameRequestNumber = 0
    #                         while(1):
    #                             # something went wrong while capturing the frame
    #                             if time.time()-cTime> timeoutFrameRequest:
    #                                 break
    #                             mFrame, currentFrameNumber = self.detector.getLatestFrame(returnFrameNumber=True)
    #                             if currentFrameNumber <= lastFrameNumber:
    #                                 time.sleep(0.05)
    #                                 continue  
    #                             frameRequestNumber += 1
    #                             if frameRequestNumber > self.nsimFrameSyncVal:
    #                                 print(f"Frame number used for stack: {currentFrameNumber}") 
    #                                 break
    #                             lastFrameNumber = currentFrameNumber
                                
    #                             #mFrame = self.detector.getLatestFrame() # get the next frame after the pattern has been updated
    #                         self.SIMStack.append(mFrame)
    #                     if self.SIMStack is None:
    #                         self._logger.error("No image received")
    #                         continue
                    
    #                 # Simulate the stack
    #                 self.SIMstack = processor.simSimulator()
    #                 self.sigImageReceived.emit(np.array(self.SIMStack),"SIMStack"+str(processor.wavelength))
                    
    #                 processor.setSIMStack(self.SIMStack)
    #                 processor.getWF(self.SIMStack)

    #                 # activate recording in processor
    #                 processor.setRecordingMode(self.isRecording)
    #                 processor.setReconstructionMode(self.isReconstruction)
    #                 processor.setWavelength(self.LaserWL,sim_parameters)


    #                 # store the raw SIM stack
    #                 if self.isRecording and self.lasers[iColour].power>0.0:
    #                     date = datetime.now().strftime("%Y_%m_%d-%I-%M-%S_%p")
    #                     processor.setDate(date)
    #                     mFilenameStack = f"{date}_SIM_Stack_{self.LaserWL}nm_{zPos+zPosInitially}mum.tif"
    #                     threading.Thread(target=self.saveImageInBackground, args=(self.SIMStack, mFilenameStack,), daemon=True).start()
    #                 # self.detector.stopAcquisition()
    #                 # We will collect N*M images and process them with the SIM processor

    #                 # process the frames and display
    #                 processor.reconstructSIMStack()

    #                 # reset the per-colour stack to add new frames in the next imaging series
    #                 processor.clearStack()

    #             # move back to initial position
    #             if len(allZPositions)!=1:
    #                 self.positioner.move(value=zPosInitially, axis="Z", is_absolute=True, is_blocking=True)
    #                 time.sleep(tDebounce)


    #         # wait for the next round
    #         time.sleep(timePeriod)

    def performSIMExperimentThread(self, sim_parameters):
        """
        Select a sequence on the SLM that will choose laser combination.
        Run the sequence by sending the trigger to the SLM.
        Run continuous on a single frame. 
        Run snake scan for larger FOVs.
        """
        time_whole_start = time.time()
        # Newly added, prep for SLM integration
        mock = self.mock
        laser_wl = 488
        exposure_ms = 1
        dic_wl_dev = {488:0, 561:1, 640:2}
        dic_exposure_dev = {0.5:'0' , 1:'1'} # 0.5 ms, 1 ms
        dic_patternID = {'00':0,'01':1, '02':2, '10':3, '11':4, '12':5}
        # self.patternID = 0
        self.patternID = dic_patternID[str(dic_wl_dev[laser_wl])+dic_exposure_dev[exposure_ms]]
        self.isReconstructing = False
        nColour = 1 #[488, 640]
        dic_wl_in = [488, 561, 640]
        dic_laser_present = {488:self.is488, 561:self.is561, 640:self.is640}
        processors_dic = {488:self.SimProcessorLaser1,561:self.SimProcessorLaser2,640:self.SimProcessorLaser3}
        
        # TODO: Remove if not in use.
        # self.file_path = self._widget.getRecFolder()
        
        # Check if lasers are set and have power in them select only lasers with powers
        dic_wl = []
        # num_lasers = 0            
        for k, dic in enumerate(dic_wl_in):
            if dic_laser_present[dic] and self.lasers[dic_wl_dev[dic]].power > 0.0:
                dic_wl.append(dic)
                # num_lasers += 1
        
        # Set processors for selected lasers
        processors = []
        isLaser = []
        for wl in dic_wl:
            if dic_wl != []:
                processors.append(processors_dic[wl])
                isLaser.append(dic_laser_present[wl])
                # Set calibration before each run if selected in GUI
                if processors_dic[wl].isCalibrated:
                    # If calibrated it will check in widget if calibrate
                    # Widget True, calibration needs to be False
                    processors_dic[wl].isCalibrated = not self._widget.checkbox_calibrate.isChecked()
        
        # retreive Z-stack parameters
        zStackParameters = self._widget.getZStackParameters()
        zMin, zMax, zStep = zStackParameters[0], zStackParameters[1], zStackParameters[2] # if zStep < 0, it will not move in z
        tDebounce = 0.1 # debounce time between z-steps

        # retreive timelapse parameters
        timelapsedParameters = self._widget.getTimelapseParameters()
        timePeriod, Nframes = timelapsedParameters[0], timelapsedParameters[1] # if NFrames < 0, it will run indefinitely

        # get current z-position
        zPosInitially = self.positioner.get_abs()

        # TODO: Old, to check and delete
        # run the experiment indefinitely
        count = 0
        while self.active and not mock and dic_wl != []:
        # run only once
        # while count == 0:
            count += 1

            # TODO: We don't need that remove?
            # iterate over all z-positions
            if zStep > 0:
                # TODO: Disabling this option although accessible through GUI
                # allZPositions = np.arange(zMin, zMax, zStep)
                allZPositions = [0]
            else:
                allZPositions = [0]

            # TODO: Our triggering schema is different, number of colors is 
            # determined by the SLM program - SLM directly controls the lasers
            # I suggest removal of this for loop
            
            # Change from openUC2 concept - all colors are taken at once
            # Might be a bad idea, but we need to try our options - one trigger
            # will trigger the 3 color sequence, we don't have a trigger 
            # for each sequence
            
            # SLM enables lasers - we do not need activation of the lasers
            # self.lasers[0].setEnabled(True)
            # self.lasers[1].setEnabled(True)
            # self.lasers[2].setEnabled(True)
            
            
            
            for iColour in range(nColour):
                # Move piezo to initial position
                if not self.active:
                    if len(allZPositions)!=1:
                        self.positioner.move(value=zPosInitially, axis="Z", is_absolute=True, is_blocking=True)
                        time.sleep(tDebounce)
                    break
                # toggle laser
                if iColour == 0 and self.is488 and self.lasers[iColour].power>0.0:
                    # enable laser 1
                    self.lasers[0].setEnabled(True)
                    self.lasers[1].setEnabled(False)
                    self.lasers[2].setEnabled(False)
                    self._logger.debug("Switching to pattern"+self.lasers[0].name)
                    processor = self.SimProcessorLaser1
                    processor.setParameters(sim_parameters)
                    self.LaserWL = processor.wavelength
                    # set the pattern-path for laser wl 1
                elif iColour == 1 and self.is561 and self.lasers[iColour].power>0.0:
                    # enable laser 2
                    self.lasers[0].setEnabled(False)
                    self.lasers[1].setEnabled(True)
                    self.lasers[2].setEnabled(False)
                    self._logger.debug("Switching to pattern"+self.lasers[1].name)
                    processor = self.SimProcessorLaser2
                    processor.setParameters(sim_parameters)
                    self.LaserWL = processor.wavelength
                    # set the pattern-path for laser wl 2
                elif iColour == 2 and self.is640 and self.lasers[iColour].power>0.0:
                    # enable laser 2
                    self.lasers[0].setEnabled(False)
                    self.lasers[1].setEnabled(False)
                    self.lasers[2].setEnabled(True)
                    self._logger.debug("Switching to pattern"+self.lasers[2].name)
                    processor = self.SimProcessorLaser2
                    processor.setParameters(sim_parameters)
                    self.LaserWL = processor.wavelength
                    # set the pattern-path for laser wl 3
                else:
                    time.sleep(.1) # reduce CPU load
                    continue

                # select the pattern for the current colour
                self.SIMClient.set_wavelength(dic_wl[iColour])

                for zPos in allZPositions:
                    # move to the next z-position
                    if len(allZPositions)!=1:
                        self.positioner.move(value=zPos+zPosInitially, axis="Z", is_absolute=True, is_blocking=True)
                        time.sleep(tDebounce)

                    if self.isPCO:
                        # display one round of SIM patterns for the right colour
                        self.SIMClient.start_viewer_single_loop(1)

                        # ensure lasers are off to avoid photo damage
                        self.lasers[0].setEnabled(False)
                        self.lasers[1].setEnabled(False)
                        self.lasers[2].setEnabled(False)

                        # download images from the camera
                        self.SIMStack = self.detector.getChunk(); self.detector.flushBuffers()
                        if self.SIMStack is None:
                            self._logger.error("No image received")
                            continue
                    else:
                        # we need to capture images and display patterns one-by-one
                        self.SIMStack = []
                        try:
                            mExposureTime = self.detector.getParameter("exposure")/1e6 # s^-1
                        except:
                            mExposureTime = 0.1
                        for iPattern in range(9):
                            self.SIMClient.display_pattern(iPattern)
                            time.sleep(mExposureTime) # make sure we take the next newest frame to avoid motion blur from the pattern change

                            # Todo: Need to ensure thatwe have the right pattern displayed and the buffer is free - this heavily depends on the exposure time..
                            mFrame = None
                            lastFrameNumber = -1
                            timeoutFrameRequest = 3 # seconds
                            cTime = time.time()
                            frameRequestNumber = 0
                            while(1):
                                # something went wrong while capturing the frame
                                if time.time()-cTime> timeoutFrameRequest:
                                    break
                                mFrame, currentFrameNumber = self.detector.getLatestFrame(returnFrameNumber=True)
                                if currentFrameNumber <= lastFrameNumber:
                                    time.sleep(0.05)
                                    continue  
                                frameRequestNumber += 1
                                if frameRequestNumber > self.nsimFrameSyncVal:
                                    print(f"Frame number used for stack: {currentFrameNumber}") 
                                    break
                                lastFrameNumber = currentFrameNumber
                                
                                #mFrame = self.detector.getLatestFrame() # get the next frame after the pattern has been updated
                            np.append(self.SIMStack, mFrame)
                            # self.SIMStack.append(mFrame)
                        if self.SIMStack is None:
                            self._logger.error("No image received")
                            continue
                    
                    
                    # Simulate the stack
                    self.SIMstack = processor.simSimulator()
                    self.sigImageReceived.emit(np.array(self.SIMStack),"SIMStack"+str(processor.wavelength))
                    
                    processor.setSIMStack(self.SIMStack)
                    processor.getWF(self.SIMStack)

                    # activate recording in processor
                    processor.setRecordingMode(self.isRecording)
                    processor.setReconstructionMode(self.isReconstruction)
                    processor.setWavelength(self.LaserWL,sim_parameters)


                    # store the raw SIM stack
                    if self.isRecording and self.lasers[iColour].power>0.0:
                        date = datetime.now().strftime("%Y_%m_%d-%I-%M-%S_%p")
                        processor.setDate(date)
                        mFilenameStack = f"{date}_SIM_Stack_{self.LaserWL}nm_{zPos+zPosInitially}mum.tif"
                        threading.Thread(target=self.saveImageInBackground, args=(self.SIMStack, mFilenameStack,), daemon=True).start()
                    # self.detector.stopAcquisition()
                    # We will collect N*M images and process them with the SIM processor

                    # process the frames and display
                    processor.reconstructSIMStack()

                    # reset the per-colour stack to add new frames in the next imaging series
                    processor.clearStack()

                # move back to initial position
                if len(allZPositions)!=1:
                    self.positioner.move(value=zPosInitially, axis="Z", is_absolute=True, is_blocking=True)
                    time.sleep(tDebounce)

            # TODO: Delete this our keep. At least check.
            # Deactivate indefinite running of the experiment
            self.active = False
            print(count)
            # wait for the next round
            time.sleep(timePeriod)

        # Creating a mocker
        if mock:
            print("Activating mocker for our SIM implementation.")
        
        # TODO: Check if it affects speed, remove if it does
        # Set folder to separate folder
        folder = os.path.join(sim_parameters.path, "stack")
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.folder = folder
        
        # Creating a unique identifier for experiment name generated 
        # before a grid scan is acquired
        date_in = datetime.now().strftime("%Y_%m_%d-%I-%M-%S_%p")
        # Set file-path read from GUI for each processor
        for processor in processors:
            processor.setPath(sim_parameters.path)
        # TODO: Remove, laser selection is done at the beginning of the 
        # function. This below is old implementation.
        # # If no laser present do nothing
        # num_lasers = 0            
        # for k, dic in enumerate(dic_wl):
        #     if isLaser[k] and self.lasers[dic_wl_dev[dic]].power > 0.0:
        #         num_lasers += 1
        # # Will not run if no laser is present
        # while self.active and mock and num_lasers != 0:
        
        # # If no laser present do nothing
        while self.active and mock and dic_wl != []:
        # run only once
        # while count == 0:
            count += 1 
            
            # Generate empty array to populate with wide-field images for 
            # each color
            wfImages = []
            stackSIM = []
            positions = []
            
            # Load experiment parameters to object
            self.getExperimentSettings()
            
            # ----------scanning over more FOVs------------
            # TODO: Copy to top of the function - this is common to all 
            # mock and actual scan
            ##################################################
            # ----------------Grid scan info---------------- #
            # ----Copy over to top once fully implemented--- #
            ##################################################
            # Generate positions - can be done anywhere in this function
            # Copied over from grid_xy script
            
            # Set positioner info axis_y is set to 'X' for testing purposes
            # Positioner info for ImSwitch to recognize the stage
            positioner_xy = 'XY' # Must match positioner name in config file
            axis_x = 'X'
            axis_y = 'Y'  # Change to 'Y' when testing for real
            dic_axis = {'X':0, 'Y':1}
            
            # Image size - I need to grab that from GUI but is hardcoded 
            # at the moment
            image_pix_x = 512 # TODO: read from widget 
            image_pix_y = 512 # TODO: read from widge
            pix_size = 0.123 # um # TODO: read from widge
            
            # Set experiment info
            grid_x_num = self.num_grid_x
            grid_y_num = self.num_grid_y
            overlap_xy = self.overlap
            xy_scan_type = 'square' # or 'quad', not sure what that does yet...
            count_limit = 9999
            
            ##################################################
            # ----------------Grid scan info---------------- #
            # ----Copy over to top once fully implemented--- #
            ##################################################
            
            # Grab starting position that we can return to
            positions_start = self.positionerXY.get_abs()
            start_position_x = float(positions_start[dic_axis[axis_x]])
            start_position_y = float(positions_start[dic_axis[axis_y]])
            xy_start = [start_position_x, start_position_y]
            
            # Determine stage travel range, stage accepts values in microns
            frame_size_x = image_pix_x*pix_size
            frame_size_y = image_pix_y*pix_size
            
            # Step-size based on overlap info
            x_step = (1 - overlap_xy) * frame_size_x
            y_step = (1 - overlap_xy) * frame_size_y
            xy_step = [x_step, y_step]
            
            # Confirm parameters are set correctly
            assert x_step != 0 and y_step != 0, 'xy_step == 0 - check that xy_overlap is < 1, and that frame_size is > 0'
            
            if grid_x_num > 0 and grid_y_num > 0:
                x_range = grid_x_num * x_step
                y_range = grid_y_num * y_step
                xy_range = [x_range, y_range]
            else:
                print("Grid parameters are not set correct!")
            
            # Generate list of coordinates
            positions = []
            y_start = xy_start[1]
            y_list = list(np.arange(0, grid_y_num, 1)*y_step+y_start)
            
            # ------------Grid scan------------
            # Generate positions for each row
            for y in y_list:
                # Where to start this row
                x_start = xy_start[0]
                if xy_scan_type == 'square':
                    x_stop = x_start - x_range
                    # Generate x coordinates
                    x_list = list(np.arange(0, -grid_x_num, -1)*x_step+x_start)
                elif xy_scan_type == 'quad':
                    x_stop = x_start - math.sqrt(x_range**2 - (y-y_start)**2)
                    # Generate x coordinates
                    x_list = list(np.arange(x_start, x_stop, -x_step))
                    
                # Run every other row backwards to minimize stage movement
                if y_list.index(y) % 2 == 1:
                    x_list.reverse()
                
                # Populate the final list
                for x in x_list:
                    # print(np.round(x, 2))
                    # positions.append([np.round(x, 2),np.round(y, 2)])
                    positions.append([x,y])
                    
                # Truncate the list if the length/the number of created
                # positions exceeds the specified limit
                if len(positions) > count_limit:
                    positions = positions[:count_limit]
                    self.logger.warning(f"Number fo positions was reduced to {count_limit}!")
            # ------------Grid scan------------
            
            # -----------SIM acquire-----------
            # Generate empty vectors to save data
            # Will also be maybe used for processing
            for k in range(0, len(processors)):
                wfImages.append([])
                stackSIM.append([])
            
            # Generate one image for each color to make testing code faster
            # Simulation takes 0.33 s for 512x512 image - the default of 
            # simSimulator (hardcoded in the simulator)
            color_stacks_simulated = []
            for processor in processors:
                stack_simulated = processor.simSimulator()
                color_stacks_simulated.append(stack_simulated)
            # -----------SIM acquire-----------
            
            # Set frame number - prepared for time-lapse
            # Final implementation will maybe have a little 
            # different form - we will need to empty a buffer of
            # the cam as fast as possible
            frame_num = 0
            
            # Scan over all positions generated for grid
            for j, pos in enumerate(positions):
                
                # Move stage
                x_set = pos[0]
                y_set = pos[1]
                # tDebounceXY = 0 # prepared in case we need it
                self.positionerXY.setPositionXY(x_set, y_set)
                # time.sleep(tDebounceXY) # prepared in case we need it
                # For development purposes
                # print(f"Move to x = {x_set}, y = {y_set}")
                
                # Acquire SIM set for all present lasers
                # ----sub loop start----
                for k, processor in enumerate(processors):
                    # -----loop start-----
                    # If power of laser set to  0 or laser set not be used in
                    # measurement skip laser
                    if not isLaser[k] or self.lasers[dic_wl_dev[dic_wl[k]]].power <= 0.0:
                        time.sleep(.1) # reduce CPU load
                        continue
                    time_color_start = time.time()
                    
                    # TODO: see if lasers need to be enabled to take an image
                    # using our SLM. The reasons the comment below is kept here
                    # Toggle laser
                    # Enable lasers
                    # self.lasers[0].setEnabled(True)
                    # self.lasers[1].setEnabled(True)
                    # self.lasers[2].setEnabled(True)
                    # self._logger.debug(f"Enabling all lasers {self.lasers[0].name}, {self.lasers[1].name}, {self.lasers[2].name}"+)
                    
                    # Setting a reconstruction processor for current laser
                    processor.setParameters(sim_parameters)
                    self.LaserWL = processor.wavelength
                    
                    # Simulate the stack
                    # Simulation takes 0.38 sec, so I decided to pre-generate
                    # three images and go with that.
                    # time_simu_start = time.time()
                    # self.SIMStack = processor.simSimulator()
                    # time_simu_end = time.time()
                    # time_simu_total  = time_simu_end - time_simu_start
                    # self._logger.debug('--Simulation took: {:.2f} sec\n--'.format(time_simu_total))
                    
                    # Choose pre-simulated image - testing code is 4x faster
                    self.SIMStack = color_stacks_simulated[k]
                    
                    # TODO: remove after development is done, kept for testing
                    # Push all colors into one array - export disabled below
                    # Enable below if you need this
                    # stackSIM[k].append(self.SIMStack)
                    
                    self.sigImageReceived.emit(np.array(self.SIMStack),f"SIMStack{int(processor.wavelength*1000):03}")
                    
                    # Set sim stack for processing all functions work on 
                    # self.stack in SIMProcessor class
                    processor.setSIMStack(self.SIMStack)
                    
                    # Push all wide fields into one array
                    wfImages[k].append(processor.getWFlbf(self.SIMStack))
                    
                    # Activate recording and reconstruction in processor
                    processor.setRecordingMode(self.isRecording)
                    processor.setReconstructionMode(self.isReconstruction)
                    processor.setWavelength(self.LaserWL, sim_parameters)
                    
                    # Save the raw SIM stack
                    # TODO: Remove if obsolete, or move to before the loop?
                    # Maybe include in accompanying log file (exact times) 
                    # after recording is finished?
                    # date = datetime.now().strftime("%Y_%m_%d-%I-%M-%S_%p")
                    # TODO: Remove? Our implementation feeds frame number and 
                    # position direct into the processor function (the only 
                    # way we could make it work reliably)
                    # Sets the date in processor for saving file
                    # processor.setDate(date) 
                    if self.isRecording and self.lasers[dic_wl_dev[dic_wl[k]]].power>0.0:
                        date = f"{date_in}_frame_{frame_num:004}" # prepped for timelapse
                        processor.setDate(date)
                        mFilenameStack = f"{date}_pos_{j:03}_SIM_Stack_{int(self.LaserWL*1000):03}nm.tif"
                        threading.Thread(target=self.saveImageInBackground, args=(self.SIMStack, mFilenameStack,), daemon=True).start()
                        if k == len(processors)-1:
                            # Save WF three color
                            mFilenameStack1 = f"{date}_pos_{j:03}_SIM_Stack_{'_'.join(map(str,dic_wl))}_wf.tif"
                            threading.Thread(target=self.saveImageInBackground, args=(wfImages, mFilenameStack1,), daemon=True).start()
                            
                            # TODO: Delete this, just for development purposes
                            # Export a stack for all three lasers in one file
                            # Did not seem very useful for further data
                            # processing
                            # mFilenameStack2 = f"{date}_SIM_Stack_pos_{j:03}_{'_'.join(map(str,dic_wl))}.tif"
                            # threading.Thread(target=self.saveImageInBackground, args=(stackSIM, mFilenameStack2,), daemon=True).start()
                    # -----loop end-----
                    # TODO: Remove this? Kept commented from original code.
                    # self.detector.stopAcquisition()
                    
                    # Process the frames and display reconstructions
                    processor.reconstructSIMStackLBF(date_in, frame_num, j)

                    # reset the per-colour stack to add new frames in the next
                    # imaging series
                    processor.clearStack()
                    # ----sub loop end----
                    
                    # Timing of the process for testing purposes
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    
                    self._logger.debug('--Frame took: {:.2f} sec\n--'.format(time_color_total))
            
            # TODO: Delete this our keep. At least check.
            # Deactivate indefinite running of the experiment
            self.active = False
            print(count)
            # TODO: Remove this (left from openUC2 implementation)
            # Maybe good idea for longer time-lapse movies to do a "snapshot"
            # every couple of images and program this section to grab only one 
            # set of images on trigger - time-lapse to in two ways, snap-shot 
            # with wait times and continuous trigger mode (as fast as possible)
            # wait for the next round
            # time.sleep(timePeriod)
            
            # Timing of the process for testing purposes
            time_whole_end = time.time()
            time_whole_total = time_whole_end-time_whole_start
            
            self._logger.debug('--\nDone!\nIt took: {:.2f} sec\n--'.format(time_whole_total))
            

    def performSIMTimelapseThread(self, sim_parameters):
        """
        Do timelapse SIM
        Q: should it have a separate thread?
        """
        self.isReconstructing = False
        nColour = 2 #[488, 640]
        dic_wl = [488, 640]
        for iColour in range(nColour):
            # toggle laser
            if not self.active:
                break

            if iColour == 0 and self.is488 and self.lasers[iColour].power>0.0:
                # enable laser 1
                self.lasers[0].setEnabled(True)
                self.lasers[1].setEnabled(False)
                self._logger.debug("Switching to pattern"+self.lasers[0].name)
                processor = self.SimProcessorLaser1
                processor.setParameters(sim_parameters)
                self.LaserWL = processor.wavelength
                # set the pattern-path for laser wl 1
            elif iColour == 1 and self.is640 and self.lasers[iColour].power>0.0:
                # enable laser 2
                self.lasers[0].setEnabled(False)
                self.lasers[1].setEnabled(True)
                self._logger.debug("Switching to pattern"+self.lasers[1].name)
                processor = self.SimProcessorLaser2
                processor.setParameters(sim_parameters)
                self.LaserWL = processor.wavelength
                # set the pattern-path for laser wl 1
            else:
                continue


            # select the pattern for the current colour
            self.SIMClient.set_wavelength(dic_wl[iColour])

            # display one round of SIM patterns for the right colour
            self.SIMClient.start_viewer_single_loop(1)

            # ensure lasers are off to avoid photo damage
            self.lasers[0].setEnabled(False)
            self.lasers[1].setEnabled(False)

            # download images from the camera
            self.SIMStack = self.detector.getChunk(); self.detector.flushBuffers()
            if self.SIMStack is None:
                self._logger.error("No image received")
                continue
            self.sigImageReceived.emit(np.array(self.SIMStack),"SIMStack"+str(processor.wavelength))
            processor.setSIMStack(self.SIMStack)


            # activate recording in processor
            processor.setRecordingMode(self.isRecording)
            processor.setReconstructionMode(self.isReconstruction)
            processor.setWavelength(self.LaserWL,sim_parameters)

            # store the raw SIM stack
            if self.isRecording and self.lasers[iColour].power>0.0:
                uniqueID = np.random.randint(0,1000)
                date = datetime.now().strftime("%Y_%m_%d-%I-%M-%S_%p")
                processor.setDate(date)
                mFilenameStack = f"{date}_SIM_Stack_{self.LaserWL}nm_{uniqueID}.tif"
                threading.Thread(target=self.saveImageInBackground, args=(self.SIMStack, mFilenameStack,), daemon=True).start()
            # self.detector.stopAcquisition()
            # We will collect N*M images and process them with the SIM processor

            # process the frames and display
            #processor.reconstructSIMStack()

            # reset the per-colour stack to add new frames in the next imaging series
            processor.clearStack()

    def performSIMZstackThread(self,sim_parameters,zDis,zStep):
        mStep = 0
        acc = 0    #hardcoded acceleration
        mspeed = 1000   #hardcoded speed
        while mStep < zStep:
            self.positioner.move(zDis,self.positioner.axes[0], acceleration = acc, speed=mspeed)
            mStep += 1
            self.performSIMTimelapseThread(sim_parameters)
            time.sleep(0.1)
        self.active = False
        self.lasers[0].setEnabled(False)
        self.lasers[1].setEnabled(False)
        if self.isPCO:
            self.detector.setParameter("trigger_source","Internal trigger")
            self.detector.setParameter("buffer_size",-1)
        self.detector.flushBuffers()
        self._logger.debug("Zstack finished")


    #@APIExport(runOnUIThread=True)
    def sim_getSnapAPI(self, mystack):
        mystack.append(self.detector.getLatestFrame())
        #print(np.shape(mystack))


    def saveImageInBackground(self, image, filename = None):
        if filename is None:
            date = datetime.now().strftime("%Y_%m_%d-%I-%M-%S_%p")
            filename = f"{date}_SIM_Stack.tif"
        try:
            # self.folder = self._widget.getRecFolder()
            self.filename = os.path.join(self.folder,filename) #FIXME: Remove hardcoded path
            tif.imwrite(self.filename, image)
            self._logger.debug("Saving file: "+self.filename)
        except  Exception as e:
            self._logger.error(e)

    def getSIMParametersFromGUI(self):
        ''' retrieve parameters from the GUI '''
        sim_parameters = SIMParameters()


        # parse textedit fields
        sim_parameters.pixelsize = np.float32(self._widget.pixelsize_textedit.text())
        sim_parameters.NA = np.float32(self._widget.NA_textedit.text())
        sim_parameters.n = np.float32(self._widget.n_textedit.text())
        sim_parameters.alpha = np.float32(self._widget.alpha_textedit.text())
        sim_parameters.beta = np.float32(self._widget.beta_textedit.text())
        sim_parameters.eta = np.float32(self._widget.eta_textedit.text())
        sim_parameters.wavelength_1 = np.float32(self._widget.wavelength1_textedit.text())
        sim_parameters.wavelength_2 = np.float32(self._widget.wavelength2_textedit.text())
        sim_parameters.wavelength_3 = np.float32(self._widget.wavelength3_textedit.text())
        sim_parameters.magnification = np.float32(self._widget.magnification_textedit.text())
        sim_parameters.path = self._widget.path_edit.text()
        return sim_parameters


    def getReconstructionMethod(self):
        return self._widget.SIMReconstructorList.currentText()

    def getIsUseGPU(self):
        return self._widget.useGPUCheckbox.isChecked()


class SIMParameters(object):
    # wavelength_1 = 0.57
    # wavelength_2 = 0.66
    # wavelength_3 = 0.75
    # NA = 0.8
    # n = 1.0
    # magnification = 22.5
    # pixelsize = 2.73
    # eta = 0.6
    # alpha = 0.5
    # beta = 0.98#
    # path = 'D:\\Documents\\4 - software\python-scripting\\2p5D-SIM\\test_export\\'
    wavelength_1 = 0.488
    wavelength_2 = 0.561
    wavelength_3 = 0.640
    NA = 1.4
    n = 1.33
    magnification = 60
    pixelsize = 6.5
    eta = 0.6
    alpha = 0.5
    beta = 0.98#
    path = 'D:\\Documents\\4 - software\python-scripting\\2p5D-SIM\\test_export\\'

'''#####################################
# SIM PROCESSOR
#####################################'''

class SIMProcessor(object):

    def __init__(self, parent, simParameters, wavelength=488):
        '''
        setup parameters
        '''
        #current parameters is setting for 60x objective 488nm illumination
        self.parent = parent
        self.mFile = "/Users/bene/Dropbox/Dokumente/Promotion/PROJECTS/MicronController/PYTHON/NAPARI-SIM-PROCESSOR/DATA/SIMdata_2019-11-05_15-21-42.tiff"
        self.phases_number = 3
        self.angles_number = 3
        self.NA = simParameters.NA
        self.n = simParameters.n
        self.wavelength = wavelength
        self.pixelsize = simParameters.pixelsize
        self.magnification = simParameters.magnification
        self.dz= 0.55
        self.alpha = 0.5
        self.beta = 0.98
        self.w = 0.2
        self.eta = simParameters.eta
        self.group = 30
        self.use_phases = True
        self.find_carrier = True
        self.isCalibrated = False
        self.use_gpu = isPytorch
        self.stack = []

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
        self.setReconstructor()
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
        self.pixelsize= sim_parameters.pixelsize
        self.NA= sim_parameters.NA
        self.n= sim_parameters.n
        self.reconstructionMethod = "napari" # sim_parameters["reconstructionMethod"]
        #self.use_gpu = False #sim_parameters["useGPU"]
        self.eta =  sim_parameters.eta
        self.magnification = sim_parameters.magnification

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
        #self.h.wavelength = self.wavelength
        #self.h.wavelength = 0.52
        self.h.pixelsize = self.pixelsize
        self.h.alpha = self.alpha
        self.h.beta = self.beta
        self.h.w = self.w
        self.h.eta = self.eta
        if not self.find_carrier:
            self.h.kx = self.kx_input
            self.h.ky = self.ky_input

    def getWF(self, mStack):
        # display the BF image
        bfFrame = np.sum(np.array(mStack[-3:]), 0)
        self.parent.sigSIMProcessorImageComputed.emit(bfFrame, f"Widefield SUM{int(self.wavelength*1000):03}")
        
    def getWFlbf(self, mStack):
        # display the BF image
        bfFrame = np.sum(np.array(mStack[-3:]), 0)
        self.parent.sigSIMProcessorImageComputed.emit(bfFrame, f"Widefield SUM{int(self.wavelength*1000):03}")
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
            imgset = sim.SimImageSet({"pixel_size": self.pixelsize ,
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


    def reconstructSIMStack(self):
        '''
        reconstruct the image stack asychronously
        '''
        # TODO: Perhaps we should work with quees?
        # reconstruct and save the stack in background to not block the main thread
        if not self.isReconstructing:  # not
            self.isReconstructing=True
            mStackCopy = np.array(self.stack.copy())
            self.mReconstructionThread = threading.Thread(target=self.reconstructSIMStackBackground, args=(mStackCopy,), daemon=True)
            self.mReconstructionThread.start()
    
    def reconstructSIMStackLBF(self, date, frame_num, pos_num):
        '''
        reconstruct the image stack asychronously
        '''
        # TODO: Perhaps we should work with quees?
        # reconstruct and save the stack in background to not block the main thread
        if not self.isReconstructing:  # not
            self.isReconstructing=True
            mStackCopy = np.array(self.stack.copy())
            self.mReconstructionThread = threading.Thread(target=self.reconstructSIMStackBackgroundLBF(mStackCopy, date, frame_num, pos_num), args=(mStackCopy, ), daemon=True)
            self.mReconstructionThread.start()

    def setRecordingMode(self, isRecording):
        self.isRecording = isRecording

    def setReconstructionMode(self, isReconstruction):
        self.isReconstruction = isReconstruction

    def setDate(self, date):
        self.date = date
        
    def setPath(self, path):
        self.path = path
        
    def setFrameNum(self, frame_num):
        self.frame_num = frame_num
        
    def setPositionNum(self, pos_num):
        self.pos_num = pos_num

    def setWavelength(self, wavelength, sim_parameters):
        self.LaserWL = wavelength
        if self.LaserWL == 488:
            self.h.wavelength = sim_parameters.wavelength_1
        elif self.LaserWL == 561:
            self.h.wavelength = sim_parameters.wavelength_3
        elif self.LaserWL == 640:
            self.h.wavelength = sim_parameters.wavelength_2

    def reconstructSIMStackBackground(self, mStack):
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
        SIMReconstruction = self.reconstruct(mStack)

        # save images eventually
        if self.isRecording:
            def saveImageInBackground(image, filename = None):
                try:
                    self.folder = SIMParameters.path
                    self.filename = os.path.join(self.folder,filename) #FIXME: Remove hardcoded path
                    tif.imwrite(self.filename, image)
                    self._logger.debug("Saving file: "+self.filename)
                except  Exception as e:
                    self._logger.error(e)
            mFilenameRecon = f"{self.date}_SIM_Reconstruction_{self.LaserWL}nm.tif"
            threading.Thread(target=saveImageInBackground, args=(SIMReconstruction, mFilenameRecon,)).start()

        self.parent.sigSIMProcessorImageComputed.emit(np.array(SIMReconstruction), "SIM Reconstruction"+f"{self.LaserWL}"[2:])
        
        self.isReconstructing = False
        
    def reconstructSIMStackBackgroundLBF(self, mStack, date, frame_num, pos_num):
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
        SIMReconstruction = self.reconstruct(mStack)

        # save images eventually
        if self.isRecording:
            def saveImageInBackground(image, filename = None):
                try:
                    # TODO: Remove if not in use
                    # self.folder = SIMparameters.path
                    # TODO: Check if speed is affected, delete if it is
                    # Dedicated reconstruction folder
                    folder = os.path.join(self.path, "recon")
                    if not os.path.exists(folder):
                        os.makedirs(folder)
                    self.folder = folder
                    
                    # self.folder = self.path
                    self.filename = os.path.join(self.folder,filename) #FIXME: Remove hardcoded path
                    tif.imwrite(self.filename, image)
                    self._logger.debug("Saving file: "+self.filename)
                except  Exception as e:
                    self._logger.error(e)
            # TODO: Revert back to date
            # date = self.date
            # date = f"frame_{self.frame_num:004}"
            date_out = f"{date}_frame_{frame_num:004}"
            # pos_num = self.pos_num # don't really work, not unique, changes to quick
            mFilenameRecon = f"{date_out}_pos_{pos_num:03}_SIM_Reconstruction_{int(self.LaserWL*1000):03}nm.tif"
            threading.Thread(target=saveImageInBackground, args=(SIMReconstruction, mFilenameRecon,)).start()

        self.parent.sigSIMProcessorImageComputed.emit(np.array(SIMReconstruction), f"SIM Reconstruction{int(self.LaserWL*1000):03}")
        
        self.isReconstructing = False


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

            return imageSIM

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

    def simSimulator(self, Nx=512, Ny=512, Nrot=3, Nphi=3):
        Isample = np.zeros((Nx,Ny))
        Isample[np.random.random(Isample.shape)>0.999]=1

        allImages = []
        for iRot in range(Nrot):
            for iPhi in range(Nphi):
                IGrating = 1+np.sin(((iRot/Nrot)*nip.xx((Nx,Ny))+(Nrot-iRot)/Nrot*nip.yy((Nx,Ny)))*np.pi/2+np.pi*iPhi/Nphi)
                allImages.append(nip.gaussf(IGrating*Isample,3))

        allImages=np.array(allImages)
        allImages-=np.min(allImages)
        allImages/=np.max(allImages)
        return allImages


class SIMClient:
    # Usage example
    # client = SIMClient(URL="169.254.165.4", PORT=8000)
    # client.start_viewer()
    # client.start_viewer_single_loop(5)
    # client.wait_for_viewer_completion()
    # client.set_pause(1.5)
    # client.stop_loop()
    # client.set_wavelength(1)
    def __init__(self, URL, PORT):
        self.base_url = f"http://{URL}:{PORT}"
        self.commands = {
            "start": "/start_viewer/",
            "single_run": "/start_viewer_single_loop/",
            "pattern_compeleted": "/wait_for_viewer_completion/",
            "pause_time": "/set_wait_time/",
            "stop_loop": "/stop_viewer/",
            "pattern_wl": "/change_wavelength/",
            "display_pattern": "/display_pattern/",
        }
        self.iseq = 60
        self.itime = 120
        self.laser_power = (400, 250)

    def get_request(self, url, timeout=0.3):
        try:
            response = requests.get(url, timeout=timeout)
            return response.json()
        except Exception as e:
            print(e)
            return -1

    def start_viewer(self):
        url = self.base_url + self.commands["start"]
        return self.get_request(url)

    def start_viewer_single_loop(self, number_of_runs, timeout=2):
        url = f"{self.base_url}{self.commands['single_run']}{number_of_runs}"
        return self.get_request(url, timeout=timeout)

    def wait_for_viewer_completion(self):
        url = self.base_url + self.commands["pattern_compeleted"]
        self.get_request(url)

    def set_pause(self, period):
        url = f"{self.base_url}{self.commands['pause_time']}{period}"
        self.get_request(url)

    def stop_loop(self):
        url = self.base_url + self.commands["stop_loop"]
        self.get_request(url)

    def set_wavelength(self, wavelength):
        url = f"{self.base_url}{self.commands['pattern_wl']}{wavelength}"
        self.get_request(url)

    def display_pattern(self, iPattern):
        url = f"{self.base_url}{self.commands['display_pattern']}{iPattern}"
        self.get_request(url)




# Copyright (C) 2020-2023 ImSwitch developers
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
