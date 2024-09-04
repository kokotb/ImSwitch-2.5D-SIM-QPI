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
        # self.IS_FASTAPISIM=False
        # self.IS_HAMAMATSU=False
        # switch to detect if a recording is in progress
        self.isRecordingRaw = False
        self.isReconstruction = False
        self.isRecordRecon = False
        self.simFrameVal = 0
        self.nsimFrameSyncVal = 3

        # Choose which laser will be recorded
        self.is488 = True
        self.is561 = True
        self.is640 = True
        self.processors = []
        

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
        # Set mock value in widget
        self._widget.setMockValue(self.mock)

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
        # self.detector = self._master.detectorsManager[allDetectorNames[0]]
        # Get all detector objects
        self.detectors = []
        for detector_name in allDetectorNames:
            self.detectors.append(self._master.detectorsManager[detector_name])
        # if self.detector.model == "CameraPCO":
        #     # here we can use the buffer mode
        #     self.isPCO = True
        # else:
        #     # here we need to capture frames consecutively
        #     self.isPCO = False
            
        # # Pull magnifications from config file
        # for detector in self.detectors:
        #     magnification_key = 'ExposureTime' # Just for testing, change to mag once implemented
        #     self.magnification = detector.setupInfo[magnification_key]
            
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
        # self._commChannel.sharedAttrs.sigAttributeSet.connect(self.attrChanged)
        self._commChannel.sigAdjustFrame.connect(self.updateROIsize)

        self._widget.start_button.clicked.connect(self.startSIM)
        self._widget.stop_button.clicked.connect(self.stopSIM)

        self._widget.checkbox_record_raw.stateChanged.connect(self.toggleRecording)
        self._widget.checkbox_record_reconstruction.stateChanged.connect(self.toggleRecordReconstruction)
        self._widget.checkbox_mock.stateChanged.connect(self.toggleMockUse)
        #self._widget.sigPatternID.connect(self.patternIDChanged)
        # self._widget.number_dropdown.currentIndexChanged.connect(self.patternIDChanged)
        self._widget.checkbox_reconstruction.stateChanged.connect(self.toggleReconstruction)
        # read parameters from the widget
        # self._widget.start_timelapse_button.clicked.connect(self.startTimelapse)
        # self._widget.start_zstack_button.clicked.connect(self.startZstack)
        self._widget.openFolderButton.clicked.connect(self.openFolder)
        self.folder = self._widget.getRecFolder()


        #Get RO names from SIMslmManager and send values to widget function to populate RO list.
        roNameList = self._master.simslmManager.getAllRONames()
        for i in range(len(roNameList)):
            self._widget.addROName(i,roNameList[i])











    def performSIMExperimentThread(self, sim_parameters):
        """
        Select a sequence on the SLM that will choose laser combination.
        Run the sequence by sending the trigger to the SLM.
        Run continuous on a single frame. 
        Run snake scan for larger FOVs.
        """
        ###################################################
        # -------Parameters - still in development------- #
        ###################################################
        
        # Newly added, prep for SLM integration
        mock = self.mock


        dic_wl_dev = {488:0, 561:1, 640:2}
        # FIXME: Correct for how the cams are wired
        dic_det_names = {488:'55Camera', 561:'66Camera', 640:'65Camera'} 
        # TODO: Delete after development is done - here to help get devices 
        # names
        detector_names_connected = self._master.detectorsManager.getAllDeviceNames()

        # dic_wl_in = [488, 561, 640]
        dic_laser_present = {488:self.is488, 561:self.is561, 640:self.is640}
        processors_dic = {488:self.SimProcessorLaser1,561:self.SimProcessorLaser2,640:self.SimProcessorLaser3}
        
        self.isReconstructing = False
        
        # Check if lasers are set and have power in them select only lasers with powers
        dic_wl = []
        laser_ID = []
        # num_lasers = 0            
        for dic in list(dic_wl_dev):
            if self.lasers[dic_wl_dev[dic]].power > 0.0:
                dic_wl.append(dic) #List of wavelengths actually powered
                laser_ID.append(dic_wl_dev[dic])
                # num_lasers += 1
        
        # Check if detector is present comparing hardcoded names to connected 
        # names, detector names are used only for pulling imageSize from the 
        # detector
        # FIXME: Check again if this laser checkup makes sense
        det_names = []
        if dic_wl != []:
            for dic in dic_wl:
                det_name = dic_det_names[dic]
                if det_name in detector_names_connected:
                    det_names.append(det_name)
                else:
                    self._logger.debug(f"Specified detector {det_name} for {dic} nm laser not present in \n{detector_names_connected} - correct hardcoded names. Defaulting to detector No. 0.")
                    if len(dic_wl) > len(detector_names_connected):
                        self._logger.debug(f"Not enough detectors configured in config file: {detector_names_connected} for all laser wavelengths selected {dic_wl}")
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
        image_sizes_px = []
        
        if det_names != []:
            for det_name in det_names:
                detector = self._master.detectorsManager[det_name]
                self.detectors.append(detector)
                image_sizes_px.append(detector.shape)
        else:
            self._logger.debug(f"Lasers not enabled. Setting image_size_px to default 512x512.")
            image_sizes_px = [[512,512]]


        imageLeastCommonSize = self.smallestXYForGridSpacing(image_sizes_px)

        
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
        
        
        
        
        
        
        # Make processors object attribute so calibration can be changed when 
        # detector size is changed.
        self.processors = processors
        magnification = sim_parameters.magnification
        camPixelSize = 2.74
        projCamPixelSize = camPixelSize/magnification
                        
        positions = self.createXYGridPositionArray(imageLeastCommonSize,projCamPixelSize)

        # TODO: Check if it affects speed, remove if it does
        # move to top where all this is handled
        # Set stacks to be saved into separate folder
        folder = os.path.join(sim_parameters.path, "astack")
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.folder = folder
        
        # Creating a unique identifier for experiment name generated 
        # before a grid scan is acquired
        date_in = datetime.now().strftime("%Y_%m_%d-%H-%M-%S")
        # Set file-path read from GUI for each processor
        for processor in processors:
            processor.setPath(sim_parameters.path)
            
        # Set count for frames to 0
        count = 0
        
        # -------------------Set-up SLM-------------------
        # Set running order


        roID = self._widget.getSelectedRO()
        self._master.simslmManager.setRunningOrder(roID)
        # -------------------Set-up SLM-------------------
        

        # -------------------Set-up cams-------------------

        # FIXME: Automate buffer size calculation based on image size, it did not work before
        total_buffer_size_MB = 350 # in MBs
        for detector in self.detectors:
            image_size = detector.shape
            image_size_MB = (2*image_size[0]*image_size[1]/(1024**2))
            buffer_size, decimal = divmod(total_buffer_size_MB/image_size_MB,1)
            # buffer_size = 500
            self.setCamForExperiment(detector, int(buffer_size))
        
        if not mock:
            for ID in laser_ID:
                self.lasers[ID].setEnabled(True)

        droppedFrameSets = 0
        time_whole_start = time.time()
        self._master.arduinoManager.activateSLM()
        while self.active and not mock and dic_wl != []:

        
        # while count == 0:
            wfImages = []
            stackSIM = [] 
            for k in range(len(processors)):
                wfImages.append([])
                stackSIM.append([]) 
            # TODO: SLM drives laser powers, do lasers really need to be 
            # enabled?

                
            # Set frame number - prepared for time-lapse
            # frame_num = 0
            frame_num = count
            dt_export_string = "" # no time duration between frames is needed
            
            
            # Generate time_step
            if count == 0:
                dt_export = 0.0
            else:
                dt_export = time.time() - self.timelapse_old
            
            integer, decimal = divmod(dt_export,1) # *1000 in ms
            dt_export_string = f"{int(integer):04}p{int(decimal*10000):04}s"
            self.timelapse_old = time.time()
            
            # Scan over all positions generated for grid
            for j, pos in enumerate(positions):
                
                # FIXME: Remove after development is completed
                times_color = []
                time_color_start = time.time()
                # Move stage
                x_set = pos[0]
                y_set = pos[1]
                # tDebounceXY = 0 # prepared in case we need it
                self.positionerXY.setPositionXY(x_set, y_set)
                # time.sleep(tDebounceXY) # prepared in case we need it
                time_color_end = time.time()
                time_color_total = time_color_end-time_color_start
                times_color.append(["{:0.3f} ms".format(time_color_total*1000),"move stage"])
                                
                # Trigger SIM set acquisition for all present lasers
                time_color_start = time.time()
                self._master.arduinoManager.trigOneSequenceWriteOnly()            
                time_color_end = time.time()
                time_color_total = time_color_end-time_color_start
                times_color.append(["{:0.3f} ms".format(time_color_total*1000),"startOneSequence"])
             
                # Loop over channels
                for k, processor in enumerate(processors):
                    # Setting a reconstruction processor for current laser
                    processor.setParameters(sim_parameters)
                    self.LaserWL = processor.wavelength
                    
                    # Set current detector being used
                    detector = self.detectors[k]
                    
                    # FIXME: Remove after development is completed


                    time_color_start = time.time()
                    
                    # 3 angles 3 phases
                    framesPerDetector = 9


                    waitingBuffers = 0
                    waitingBuffersEnd = 0
                    bufferStartTime = time.time()
                    while waitingBuffers != 9:
                        time.sleep(.02)
                        
                        waitingBuffers = detector._camera.tl_stream_nodemap['StreamOutputBufferCount'].value #FIXME This logic does not include a way to remove saved images for first 2 cams if for example the thrid cam fails
                        
                        if waitingBuffers != waitingBuffersEnd:
                            bufferStartTime = time.time()
                            bufferEndTime = time.time()
                        else: 
                            bufferEndTime = time.time()

                        bufferTotalTime = bufferEndTime-bufferStartTime

                        # print(bufferTotalTime)
                        # print(waitingBuffers)
                        waitingBuffersEnd = waitingBuffers
                        broken = False
                        if waitingBuffers != 9 and bufferTotalTime > .1:
                            for detector in self.detectors:
                                detector._camera.clearBuffers()
                            self._logger.error(f'Frameset thrown in trash. Buffer available is {waitingBuffers}')
                            broken = True
                            break

                    if broken == True:
                        droppedFrameSets += 1
                        # print(f'Number of dropped frame set(s): {droppedFrameSets}')
                        break

                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"buffer filling"])

                    time_color_start = time.time()
                    self.SIMStack = detector._camera.grabFrameSet(framesPerDetector)
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"grab_stack"])

                    time_color_start = time.time()

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
                    processor.setRecordingMode(self.isRecordRecon)
                    processor.setReconstructionMode(self.isReconstruction)
                    processor.setWavelength(self.LaserWL, sim_parameters)
                    
                    # FIXME: Remove after development is completed
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"acquire data"])

                    time_color_start = time.time()
                    if self.isRecordingRaw:
                        date = f"{date_in}_t_{frame_num:004}" # prepped for timelapse
                        processor.setDate(date)
                        mFilenameStack = f"{date}_pos_{j:03}_SIM_Stack_{int(self.LaserWL*1000):03}nm-{dt_export_string}.tif"
                        threading.Thread(target=self.saveImageInBackground, args=(self.SIMStack, mFilenameStack,), daemon=True).start()
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"save data"])

                    time_color_start = time.time()
                    num_skip_frames = self._widget.getSkipFrames() + 1
                    if count == 0:
                        div_1 = 0
                    else:                        
                        int_1, div_1  = divmod(count, num_skip_frames)
                    
                    # if self.isReconstruction and div_1 == 0:
                    if self.isReconstruction and div_1 == 0:
                        threading.Thread(target=processor.reconstructSIMStackLBF(date_in, frame_num, j, dt_export_string), args=(date_in, frame_num, j, dt_export_string, ), daemon=True).start()
                        # processor.reconstructSIMStackLBF(date_in, frame_num, j, dt_export_string)
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"reconstruct data"])

                    processor.clearStack()                    



                print(f'Number of dropped frame set(s): {droppedFrameSets}')
                self._logger.debug(f"{times_color}")
                
                count += 1
                # Timing of the process for testing purposes
                time_whole_end = time.time()
                time_whole_total = time_whole_end-time_whole_start
                
                self._logger.debug('Done!\nIt took: {:.2f} sec\n--'.format(time_whole_total))
                time_whole_start = time.time()
















    # def timeMe(self, timedList, function):
    #         time_color_start = time.time()
    #         function         
    #         time_color_total = time.time()-time_color_start
    #         timedList.append(["{:0.3f} ms".format(time_color_total*1000),"startOneSequence"])
    #         return timedList

    def smallestXYForGridSpacing(self,image_sizes_px):
        imageLeastCommonSize = [] 
        # Check if image-sizes on all detectors are the same
        if image_sizes_px.count(image_sizes_px[0]) == len(image_sizes_px):
            imageLeastCommonSize = image_sizes_px[0]
        else:
            self._logger.debug(f"Check detector settings. Not all colors have same image size on the detectors. Defaulting to smallest size in each dimension.")
            # size = 0
            # Set desired
            image_size_x = image_sizes_px[0][0]
            image_size_y = image_sizes_px[0][1]
            for image_size_px in image_sizes_px:
                if image_size_px[0] < image_size_x:
                    image_size_x = image_size_px[0]
                if image_size_px[1] < image_size_y:
                    image_size_y = image_size_px[1]
            imageLeastCommonSize = [image_size_x, image_size_y]

        return imageLeastCommonSize

    def createXYGridPositionArray(self, imageLeastCommonSize,projCamPixelSize):
        imageSizePixelsX, imageSizePixelsY = imageLeastCommonSize
        #Pulled from SIM GUI
        grid_x_num = self.num_grid_x
        grid_y_num = self.num_grid_y
        overlap_xy = self.overlap
        xy_scan_type = 'snake' # or 'quad', not sure what that does yet...
        count_limit = 101

        # Grab starting position that we can return to
        start_position_x, start_position_y = self.positionerXY.get_abs()
        x_start, y_start = [float(start_position_x), float(start_position_y)]
        
        # Determine stage travel range, stage accepts values in microns
        frame_size_x = imageSizePixelsX*projCamPixelSize
        frame_size_y = imageSizePixelsY*projCamPixelSize
        
        # Step-size based on overlap info
        x_step = (1 - overlap_xy) * frame_size_x
        y_step = (1 - overlap_xy) * frame_size_y
        assert x_step != 0 and y_step != 0, 'xy_step == 0 - check that xy_overlap is < 1, and that frame_size is > 0'
        positions = []
        y_list = list(np.arange(0, grid_y_num, 1)*y_step+y_start)
        # ------------Grid scan------------
        # Generate positions for each row
        for y in y_list:
            # Where to start this row

            if xy_scan_type == 'snake':
                # Generate x coordinates
                x_list = list(np.arange(0, -grid_x_num, -1)*x_step+x_start)

                
            # Run every other row backwards to minimize stage movement
            if y_list.index(y) % 2 == 1:
                x_list.reverse()
            
            # Populate the final list
            for x in x_list:
                positions.append([x,y])
                
            # Truncate the list if the length/the number of created
            # positions exceeds the specified limit
            if len(positions) > count_limit:
                positions = positions[:count_limit]
                self.logger.warning(f"Number fo positions was reduced to {count_limit}!")
        return positions

    def toggleReconstruction(self):
        self.isReconstruction = not self.isReconstruction
        if not self.isReconstruction:
            self.isActive = False
    
    def toggleRecording(self):
        self.isRecordingRaw = not self.isRecordingRaw
        if not self.isRecordingRaw:
            self.isActive = False

    def toggleRecordReconstruction(self):
        self.isRecordRecon = not self.isRecordRecon
        if not self.isRecordRecon:
            self.isActive = False
            
    def toggleMockUse(self):
        self.mock = self._widget.checkbox_mock.isChecked()

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

    def displayImage(self, im, name="SIM Reconstruction"):
        """ Displays the image in the view. """
        self._widget.setImage(im, name=name)
    
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
        self.active = False
        self.simThread.join()
        for laser in self.lasers:
            laser.setEnabled(False)
        self._master.arduinoManager.deactivateSLM()





    def startSIM(self):

        # start the background thread
        self.active = True
        sim_parameters = self.getSIMParametersFromGUI()
        #sim_parameters["reconstructionMethod"] = self.getReconstructionMethod()
        #sim_parameters["useGPU"] = self.getIsUseGPU()
        
        # # Load experiment parameters to object
        self.getExperimentSettings()
        mock = self.mock
        if mock:
            self.simThread = threading.Thread(target=self.performMockSIMExperimentThread, args=(sim_parameters,), daemon=True)
            self.simThread.start()
        else:    
            self.simThread = threading.Thread(target=self.performSIMExperimentThread, args=(sim_parameters,), daemon=True)
            self.simThread.start()



    # TODO: for timelapse and zstack, check running is still needed also stop

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
        
        # self.exposure = float(parameter_dict['exposure'])

    def getParameterValue(self, detector, parameter_name):
        detector_name = detector._DetectorManager__name
        shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
        if parameter_name == 'ExposureTime':
            value = float(shared_attributes[('Detector', detector_name, 'Param', parameter_name)])
        else:
            self._logger.warning("Debuging needed.")
            self._logger.debug(f"Parameter {parameter_name} not set up in getParameterValue!")
        return value
    
    def setCamForExperiment(self, detector, num_buffers):
        # self.getExperimentSettings()
        # detector_names_connected = self._master.detectorsManager.getAllDeviceNames()
        # detectors = []
        # for det_name in detector_names_connected:
        #     detectors.append(self._master.detectorsManager[det_name]._camera)
        # Hardcoded parameters at the moment

        trigger_source = 'Line2'
        trigger_mode = 'On'
        exposure_auto = 'Off'
        # FIXME: There must be a neater, better, more stable way to do this
        # Pull the exposure time from settings widget
        exposure_time = self.getParameterValue(detector, 'ExposureTime')

        # exposure_time = self.exposure # anything < 19 ms
        pixel_format = 'Mono16'
        bit_depth = 'Bits12' # FIXME: maybe syntax not exactly right
        frame_rate_enable = True
        frame_rate = 190.0 # Needs to be faster than trigger rate
        buffer_mode = "OldestFirst"
        # width, height, offsetX, offsetY - is all taken care of with SettingsWidget

        # Check if exposure is low otherwise set to max value
        exposure_limit = 5000 # us
        if exposure_time > exposure_limit:
            exposure_time = float(exposure_limit)
            self.exposure = exposure_time
            self._logger.warning(f"Exposure time set > {exposure_limit/1000:.2f} ms. Setting exposure tme to {exposure_limit/1000:.2f} ms")
        
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


    def saveImageInBackground(self, image, filename = None):
        if filename is None:
            date = datetime.now().strftime("%Y_%m_%d-%H-%M-%S")
            filename = f"{date}_SIM_Stack.tif"
        try:
            # self.folder = self._widget.getRecFolder()
            self.filename = os.path.join(self.folder,filename) #FIXME: Remove hardcoded path
            image = np.array(image)
            tif.imwrite(self.filename, image, imagej=True)
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


    def performMockSIMExperimentThread(self, sim_parameters):

        ##################################################
        # -----------------Mocker start----------------- #
        ##################################################
        # Creating a mocker
        print("Activating mocker for our SIM implementation.")
                ###################################################
        # -------Parameters - still in development------- #
        ###################################################
        time_whole_start = time.time()
        # Newly added, prep for SLM integration
        mock = self.mock


        dic_wl_dev = {488:0, 561:1, 640:2}
        # FIXME: Correct for how the cams are wired
        dic_det_names = {488:'55Camera', 561:'66Camera', 640:'65Camera'} 
        # TODO: Delete after development is done - here to help get devices 
        # names
        detector_names_connected = self._master.detectorsManager.getAllDeviceNames()


        # dic_wl_in = [488, 561, 640]
        dic_laser_present = {488:self.is488, 561:self.is561, 640:self.is640}
        processors_dic = {488:self.SimProcessorLaser1,561:self.SimProcessorLaser2,640:self.SimProcessorLaser3}
        
        self.isReconstructing = False
        
        # Check if lasers are set and have power in them select only lasers with powers
        dic_wl = []
        laser_ID = []
        # num_lasers = 0            
        for dic in list(dic_wl_dev):
            if self.lasers[dic_wl_dev[dic]].power > 0.0:
                dic_wl.append(dic) #List of wavelengths actually powered
                laser_ID.append(dic_wl_dev[dic])
                # num_lasers += 1
        
        # Check if detector is present comparing hardcoded names to connected 
        # names, detector names are used only for pulling imageSize from the 
        # detector
        # FIXME: Check again if this laser checkup makes sense
        det_names = []
        if dic_wl != []:
            for dic in dic_wl:
                det_name = dic_det_names[dic]
                if det_name in detector_names_connected:
                    det_names.append(det_name)
                else:
                    self._logger.debug(f"Specified detector {det_name} for {dic} nm laser not present in \n{detector_names_connected} - correct hardcoded names. Defaulting to detector No. 0.")
                    if len(dic_wl) > len(detector_names_connected):
                        self._logger.debug(f"Not enough detectors configured in config file: {detector_names_connected} for all laser wavelengths selected {dic_wl}")
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
        image_sizes_px = []
        
        if det_names != []:
            for det_name in det_names:
                detector = self._master.detectorsManager[det_name]
                self.detectors.append(detector)
                image_sizes_px.append(detector.shape)
        else:
            self._logger.debug(f"Lasers not enabled. Setting image_size_px to default 512x512.")
            image_sizes_px = [[512,512]]


        imageLeastCommonSize = self.smallestXYForGridSpacing(image_sizes_px)

        
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
        
        
        
        
        
        
        # Make processors object attribute so calibration can be changed when 
        # detector size is changed.
        self.processors = processors
        magnification = sim_parameters.magnification
        camPixelSize = 2.74
        projCamPixelSize = camPixelSize/magnification
                        
        positions = self.createXYGridPositionArray(imageLeastCommonSize,projCamPixelSize)

        # TODO: Check if it affects speed, remove if it does
        # move to top where all this is handled
        # Set stacks to be saved into separate folder
        folder = os.path.join(sim_parameters.path, "astack")
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.folder = folder
        
        # Creating a unique identifier for experiment name generated 
        # before a grid scan is acquired
        date_in = datetime.now().strftime("%Y_%m_%d-%H-%M-%S")
        # Set file-path read from GUI for each processor
        for processor in processors:
            processor.setPath(sim_parameters.path)
            
        # Set count for frames to 0
        count = 0
        
        # -------------------Set-up SLM-------------------
        # Set running order
        orderID = 0
        self._master.simslmManager.set_running_order(orderID)

        # -------------------Set-up SLM-------------------
        

        # -------------------Set-up cams-------------------

        # FIXME: Automate buffer size calculation based on image size, it did not work before
        total_buffer_size_MB = 350 # in MBs
        for detector in self.detectors:
            image_size = detector.shape
            image_size_MB = (2*image_size[0]*image_size[1]/(1024**2))
            buffer_size, decimal = divmod(total_buffer_size_MB/image_size_MB,1)
            # buffer_size = 500
            self.setCamForExperiment(detector, int(buffer_size))
        
        if not mock:
            for ID in laser_ID:
                self.lasers[ID].setEnabled(True)

        droppedFrameSets = 0
        # # If no laser present do nothing
        while self.active and mock and dic_wl != []:
        # TODO: Remove after development is finished.
        # run only once
        # while count == 0:
            ##################################################
            # ------Import mock data or generate data------- #
            ##################################################
            
            # Generate empty vectors to save data
            # TODO: check if some of this are redundant or obsolete and delete
            wfImages = []
            stackSIM = []  
            for k in range(0, len(processors)):
                wfImages.append([])
                stackSIM.append([])
            
            color_stacks_simulated = []
            import_simu_switch = 1
            if import_simu_switch == 0:
            # Generate one image for each color to make testing code faster
            # Simulation takes 0.33 s for 512x512 image - the default of 
            # simSimulator (hardcoded in the simulator)
                for processor in processors:
                    stack_simulated = processor.simSimulator(imageSizePixelsX, imageSizePixelsY)
                    color_stacks_simulated.append(stack_simulated)
            elif import_simu_switch == 1:
                # Import our set of images for testing
                for num, processor in enumerate(processors):
                    # Hardcoded path
                    path_current_py = os.path.dirname(os.path.realpath(__file__))
                    # Three parents above to get to imswitch folder
                    path_parent = os.path.abspath(os.path.join(os.path.abspath(os.path.join(os.path.abspath(os.path.join(path_current_py, os.pardir)), os.pardir)), os.pardir))
                    # Hardcoded folder but same an all machines
                    path_child = "_data\\test_data_ImSwitch"
                    # Create the path
                    path_in = os.path.join(path_parent, path_child)
                    names_import = glob.glob(f'{path_in}\\*{dic_wl[num]}*.tif*')
                    stack_mock_color = []
                    for name in names_import:
                        stack_mock_color.append(tif.imread(name))
                    color_stacks_simulated.append(stack_mock_color)
            else:
                self.logger.debug("Simulation switch not set right! Check hardcoded import_simu_switch.")
                break
            
            ##################################################
            # ------Import mock data or generate data------- #
            ##################################################
            
            # Set frame number - prepared for time-lapse
            # frame_num = 0
            frame_num = count
            dt_export_string = "" # no time duration between frames is needed
            
            times_color = []
            # Generate time_step
            if count == 0:
                dt_export = 0.0
            else:
                dt_export = time.time() - self.timelapse_old
            
            integer, decimal = divmod(dt_export,1) # *1000 in ms
            dt_export_string = f"{int(integer):04}p{int(decimal*10000):04}s"
            self.timelapse_old = time.time()
            
            # Scan over all positions generated for grid
            for j, pos in enumerate(positions):
                
                # FIXME: Remove after development is completed
                time_color_start = time.time()
                
                # Move stage
                x_set = pos[0]
                y_set = pos[1]
                # tDebounceXY = 0 # prepared in case we need it
                self.positionerXY.setPositionXY(x_set, y_set)
                # time.sleep(tDebounceXY) # prepared in case we need it
                # For development purposes
                # print(f"Move to x = {x_set}, y = {y_set}")
                
                # FIXME: Remove after development is completed
                time_color_end = time.time()
                time_color_total = time_color_end-time_color_start
                
                times_color.append(["{:0.3f} ms".format(time_color_total*1000),"move stage"])
                
                # Acquire SIM set for all present lasers
                # ----sub loop start----
                for k, processor in enumerate(processors):
                    # -----loop start-----
                    
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
                    processor.setRecordingMode(self.isRecordingRaw)
                    processor.setReconstructionMode(self.isReconstruction)
                    processor.setWavelength(self.LaserWL, sim_parameters)
                    
                    # FIXME: Remove after development is completed
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"acquire data"])
                    time_color_start = time.time()
                    
                    # Save the raw SIM stack
                    # TODO: Remove if obsolete, or move to before the loop?
                    # Maybe include in accompanying log file (exact times) 
                    # after recording is finished?
                    # date = datetime.now().strftime("%Y_%m_%d-%H-%M-%S")
                    # TODO: Remove? Our implementation feeds frame number and 
                    # position direct into the processor function (the only 
                    # way we could make it work reliably)
                    # Sets the date in processor for saving file
                    # processor.setDate(date) 
                    if self.isRecordingRaw:
                        date = f"{date_in}_t_{frame_num:004}" # prepped for timelapse
                        processor.setDate(date)
                        mFilenameStack = f"{date}_pos_{j:03}_SIM_Stack_{int(self.LaserWL*1000):03}nm-{dt_export_string}.tif"
                        threading.Thread(target=self.saveImageInBackground, args=(self.SIMStack, mFilenameStack,), daemon=True).start()
                        # TODO: Keep this just in case?
                        # if k == len(processors)-1:
                        #     # Save WF three color
                        #     mFilenameStack1 = f"{date}_pos_{j:03}_SIM_Stack_{'_'.join(map(str,dic_wl))}_wf.tif"
                        #     threading.Thread(target=self.saveImageInBackground, args=(wfImages, mFilenameStack1,), daemon=True).start()
                            
                            # TODO: Delete this, just for development purposes
                            # Export a stack for all three lasers in one file
                            # Did not seem very useful for further data
                            # processing
                            # mFilenameStack2 = f"{date}_SIM_Stack_pos_{j:03}_{'_'.join(map(str,dic_wl))}.tif"
                            # threading.Thread(target=self.saveImageInBackground, args=(stackSIM, mFilenameStack2,), daemon=True).start()
                    # -----loop end-----
                    # TODO: Remove this? Kept commented from original code.
                    # self.detector.stopAcquisitionSIM()
                    
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"save data"])
                    time_color_start = time.time()
                    
                    # Process the frames and display reconstructions
                    # FIXME: Testing threading, this solution below does the 
                    # same thing, takes the same amount of time
                    
                    # TODO: setting up not every frame is reconstructed
                    # +1, wording of the widget is how many frames to skip
                    # for skipping 0 frames we need to divide by 1
                    num_skip_frames = self._widget.getSkipFrames() + 1
                    if count == 0:
                        div_1 = 0
                    else:                        
                        int_1, div_1  = divmod(count, num_skip_frames)
                    
                    # if self.isReconstruction and div_1 == 0:
                    if self.isReconstruction and div_1 == 0:
                        threading.Thread(target=processor.reconstructSIMStackLBF(date_in, frame_num, j, dt_export_string), args=(date_in, frame_num, j, dt_export_string, ), daemon=True).start()
                        # processor.reconstructSIMStackLBF(date_in, frame_num, j, dt_export_string)
                    
                    # FIXME: Remove after development is completed
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"reconstruct data"])
                    time_color_start = time.time()
                    # reset the per-colour stack to add new frames in the next
                    # imaging series
                    processor.clearStack()
                    # ----sub loop end----
                    
                    # Timing of the process for testing purposes
                    time_color_end = time.time()
                    time_color_total = time_color_end-time_color_start
                    
                    times_color.append(["{:0.3f} ms".format(time_color_total*1000),"clear stack"])
                    # self._logger.debug('--Frame took: {:.2f} sec\n--'.format(time_color_total))
            self._logger.debug(f"{times_color}")
            # TODO: Delete this our keep. At least check.
            # Deactivate indefinite running of the experiment
            # self.active = False
            # print(count)
            # TODO: Remove this (left from openUC2 implementation)
            # Maybe good idea for longer time-lapse movies to do a "snapshot"
            # every couple of images and program this section to grab only one 
            # set of images on trigger - time-lapse to in two ways, snap-shot 
            # with wait times and continuous trigger mode (as fast as possible)
            # wait for the next round
            # time.sleep(timePeriod)
            
            count += 1
            # Timing of the process for testing purposes
            time_whole_end = time.time()
            time_whole_total = time_whole_end-time_whole_start
            
            self._logger.debug('--\nDone! It took: {:.2f} sec\n--'.format(time_whole_total))

            time_whole_start = time.time()
        ##################################################
        # -----------------Mocker end----------------- #
        ##################################################
        
        # # FIXME: Should we even do this?
        # # Set buffer mode back to normal cam operation
        # buffer_mode = "NewestOnly"
        # for detector in self.detectors:
        #     detector._camera.setPropertyValue('StreamBufferHandlingMode', buffer_mode)


class SIMParameters(object):
    wavelength_1 = 0.488
    wavelength_2 = 0.561
    wavelength_3 = 0.640
    NA = 0.8
    n = 1.0
    magnification = 22.22
    pixelsize = 2.74
    eta = 0.6
    alpha = 0.5
    beta = 0.98#
    path = 'D:\\SIM_data\\test_export\\'



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
        self.use_gpu = isPytorch ##Pytorch boolen refernce
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

    # def getWF(self, mStack):
    #     # display the BF image
    #     bfFrame = np.sum(np.array(mStack[-3:]), 0)
    #     self.parent.sigSIMProcessorImageComputed.emit(bfFrame, f"Widefield SUM{int(self.wavelength*1000):03}")
        
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


    
    def reconstructSIMStackLBF(self, date, frame_num, pos_num, dt_frame):
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
            self.reconstructSIMStackBackgroundLBF(mStackCopy, date, frame_num, pos_num, dt_frame)

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
        
    def reconstructSIMStackBackgroundLBF(self, mStack, date, frame_num, pos_num, dt_frame):
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
                    folder = os.path.join(self.path, "arecon")
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
            date_out = f"{date}_t_{frame_num:004}"
            # pos_num = self.pos_num # don't really work, not unique, changes to quick
            mFilenameRecon = f"{date_out}_pos_{pos_num:03}_SIM_Reconstruction_{int(self.LaserWL*1000):03}nm-{dt_frame}.tif"
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

