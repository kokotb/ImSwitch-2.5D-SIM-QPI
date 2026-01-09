from dataclasses import dataclass
from typing import Any, List, Tuple
from math import floor

import numpy as np
import time

from qtpy import QtWidgets

from imswitch.imcommon.model import APIExport
from imswitch.imcontrol.model import configfiletools
from imswitch.imcontrol.view import guitools as guitools
from ..basecontrollers import ImConWidgetController


@dataclass
class SettingsControllerParams:
    model: Any
    binning: Any
    frameMode: Any
    x0: Any
    y0: Any
    width: Any
    height: Any
    applyROI: Any
    newROI: Any
    abortROI: Any
    saveMode: Any
    deleteMode: Any
    allDetectorsFrame: Any


class SettingsController(ImConWidgetController):
    """ Linked to SettingsWidget. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settingAttr = False
        self.allParams = {}

        self.detectors = []

        self.fovOffsets = {"488": (0, 0), "561": (0, 0), "640": (0, 0)}
        self.fullImages = {"488": None, "561": None, "640": None}

        if not self._master.detectorsManager.hasDevices():
            return

        # Set up detectors
        for dName, dManager in self._master.detectorsManager:
            if not dManager.forAcquisition:
                continue

            self._widget.addDetector(
                dName, dManager.model, dManager.parameters, dManager.actions,
                dManager.supportedBinnings, self._setupInfo.rois
            )

        self.roiAdded = False
        self.initParameters()

        # Should be set in config file so all cams have the same
        # Global moves realitvely to frameStart - meant for tiny adjustments
        for detector in self._master.detectorsManager:
            frameStart_change = tuple(
                map(lambda i, j: i + j, detector[1].frameStart, detector[1].frameStartGlobal)
            )
            detector[1].setOffsetRelative(frameStart_change)


        # detector_names = self._master.detectorsManager.getAllDeviceNames()
        # tuple2 = self._master.detectorsManager[detector_names[0]].frameStart
        #
        # camOffsetX = []
        # camOffsetY = []
        #
        # globalOffsetX = []
        # globalOffsetY = []
        # for detector in self._master.detectorsManager:
        #     size = detector[1].frameStart
        #     camOffsetX.append(size[0])
        #     camOffsetY.append(size[1])
        #     size = detector[1].frameStartGlobal
        #     globalOffsetX.append(size[0])
        #     globalOffsetY.append(size[1])
        #
        # tuple2 = (max(camOffsetX)+max(globalOffsetX),
        #           max(camOffsetY)+max(globalOffsetY))
        #
        # for k, detector in enumerate(self._master.detectorsManager):
        #     tuple1 = detector[1].frameStartGlobal
        #     tuple_set = tuple(map(lambda i, j: i - j, tuple2, tuple1))
        #     self._master.detectorsManager[detector_names[k]].setOffsetRelative(tuple_set)

        execOnAll = self._master.detectorsManager.execOnAll
        execOnAll(lambda c: self.updateParamsFromDetector(detector=c),
                  condition=lambda c: c.forAcquisition)
        execOnAll(lambda c: self.adjustFrame(detector=c),
                  condition=lambda c: c.forAcquisition)
        execOnAll(lambda c: self.updateFrame(detector=c),
                  condition=lambda c: c.forAcquisition)
        execOnAll(lambda c: self.updateFrameActionButtons(detector=c),
                  condition=lambda c: c.forAcquisition)

        self.detectorSwitched(self._master.detectorsManager.getCurrentDetectorName())
        self.updateSharedAttrs()

        self._commChannel.sigDetectorSwitched.connect(self.detectorSwitched)
        self._commChannel.sharedAttrs.sigAttributeSet.connect(self.attrChanged)
        self._commChannel.sigWriteParamsFromCam.connect(self.writeParamsFromCamFunc)
        self._commChannel.sigSIMAcqToggled.connect(self._widget.toggleCheckboxes)

        self._widget.sigROIChanged.connect(self.ROIchanged)
        self._widget.sigDetectorChanged.connect(self.detectorSwitchClicked)
        self._widget.sigNextDetectorClicked.connect(self.detectorNextClicked)

        self._widget.scatterCamActive.stateChanged.connect(self.toggleScatterCam)
        if self._master.detectorsManager._subManagers['488 Scatter']._DetectorManager__model != 'mock':
            self._widget.scatterCamActive.setEnabled(True)

        self._widget.correctionButton.clicked.connect(self.open_fov_window)

    def retrieveDetectors(self):
        self.detectors = []
        for detector in self._master.detectorsManager:
            if detector[1]._DetectorManager__forAcquisition:
                fullName = detector[0]
                if fullName[-5:] == 'Fluor':
                    shortName = fullName[:5].replace(" ", "")
                    detector[1].handle = shortName
                    self.detectors.append(detector[1])

    def open_fov_window(self):
        self._logger.info('FOV correction window is opening...')
        self.retrieveDetectors()
        for detector in self.detectors:
            if detector.forAcquisition:
                detector.stopAcquisitionSIM()

        scatterDet = None
        showScatter = self._widget.scatterCamActive.isChecked()
        if showScatter:
            for dName, dManager in self._master.detectorsManager:
                if "Scatter" in dName:
                    scatterDet = dManager
                    break
            if scatterDet is None:
                showScatter = False

        roiCenters = {"488": None, "561": None, "640": None, "Scatter": None}
        for detector in self.detectors:
            fs = detector.frameStart
            sh = detector.shape
            if detector.handle == "488F":
                roiCenters["488"] = (fs[0] + sh[0] / 2.0, fs[1] + sh[1] / 2.0)
            if detector.handle == "561F":
                roiCenters["561"] = (fs[0] + sh[0] / 2.0, fs[1] + sh[1] / 2.0)
            if detector.handle == "640F":
                roiCenters["640"] = (fs[0] + sh[0] / 2.0, fs[1] + sh[1] / 2.0)

        dets = list(self.detectors)
        if showScatter and scatterDet is not None:
            fs = scatterDet.frameStart
            sh = scatterDet.shape
            roiCenters["Scatter"] = (fs[0] + sh[0] / 2.0, fs[1] + sh[1] / 2.0)
            dets.append(scatterDet)

        lastImgs = self.getOneSetImgs(dets)

        self.fullImages["488"] = (lastImgs[0] / 16).astype(np.uint8)
        self.fullImages["561"] = (lastImgs[1] / 16).astype(np.uint8)
        self.fullImages["640"] = (lastImgs[2] / 16).astype(np.uint8)

        scatterImg = None
        if showScatter and scatterDet is not None:
            scatterImg = (lastImgs[3] / 16).astype(np.uint8)

        self.fovOffsets = {"488": (0, 0), "561": (0, 0), "640": (0, 0)}
        if showScatter:
            self.fovOffsets["Scatter"] = (0, 0)

        self._widget.openFOVWindow(
            self.fullImages["488"],
            self.fullImages["561"],
            self.fullImages["640"],
            scatter=scatterImg,
            showScatter=showScatter
        )

        w = self._widget.openCorrectionWindow
        w.offsets = self.fovOffsets

        w.blueImage.parentLabel = "488"
        w.greenImage.parentLabel = "561"
        w.redImage.parentLabel = "640"
        if showScatter and getattr(w, "scatterImage", None) is not None:
            w.scatterImage.parentLabel = "Scatter"

        w.roiCenters = roiCenters

        w.blueImage.fullPoint  = roiCenters["488"]
        w.greenImage.fullPoint = roiCenters["561"]
        w.redImage.fullPoint   = roiCenters["640"]
        if showScatter and getattr(w, "scatterImage", None) is not None:
            w.scatterImage.fullPoint = roiCenters["Scatter"]

        w.updatePointsDisplay()
        w.applyRoiSize()

        try:
            w.cropButton.clicked.disconnect()
        except Exception:
            pass
        w.cropButton.clicked.connect(self.cropDetectors)




    def cropDetectors(self):
        w = self._widget.openCorrectionWindow
        if (w.blueImage.fullPoint is None or w.greenImage.fullPoint is None or w.redImage.fullPoint is None):
                QtWidgets.QMessageBox.warning(
                    w,
                    "Missing points",
                    "Click on all the images (488, 561, 640) before cropping"
                )
                return
            
        if w.buttonSIM.isChecked():
            roiSize = 512
        elif w.button25D.isChecked():
            roiSize = 1024
        half = roiSize // 2
        halfView = 600


        w.blueImage.setViewCenteredOnFullPoint(w.blueImage.fullPoint, half = half)
        w.greenImage.setViewCenteredOnFullPoint(w.greenImage.fullPoint, half = half)
        w.redImage.setViewCenteredOnFullPoint(w.redImage.fullPoint, half = half)
        if hasattr(w, "scatterImage") and w.scatterImage is not None and w.scatterImage.fullPoint is not None:
            w.scatterImage.setViewCenteredOnFullPoint(w.scatterImage.fullPoint, half=half)


        if w.align488.isChecked():
            ref = "488"
        elif w.align640.isChecked():
            ref = "640"
        else:
            ref = "561"

        pts = {
            "488": w.blueImage.fullPoint,
            "561": w.greenImage.fullPoint,
            "640": w.redImage.fullPoint,
        }



        refOx, refOy = map(lambda v: int(round(v)), pts[ref])

        fullH, fullW = self.fullImages["488"].shape[:2]
        maxX0 = fullW - roiSize
        maxY0 = fullH - roiSize

        lowX = 0
        highX = maxX0
        lowY = 0
        highY = maxY0

        for k, (ox, oy) in pts.items():
            dx = int(round(ox)) - refOx
            dy = int(round(oy)) - refOy
            lowX = max(lowX, -dx)
            highX = min(highX, maxX0 - dx)
            lowY = max(lowY, -dy)
            highY = min(highY, maxY0 - dy)

        desiredX0 = refOx - half
        desiredY0 = refOy - half

        if lowX <= highX:
            refX0 = int(min(max(desiredX0, lowX), highX))
        else:
            refX0 = int(min(max(desiredX0, 0), maxX0))

        if lowY <= highY:
            refY0 = int(min(max(desiredY0, lowY), highY))
        else:
            refY0 = int(min(max(desiredY0, 0), maxY0))

        x0 = {}
        y0 = {}
        for k, (ox, oy) in pts.items():
            dx = int(round(ox)) - refOx
            dy = int(round(oy)) - refOy
            x0[k] = refX0 + dx
            y0[k] = refY0 + dy


        for detector in self.detectors:
            if detector.handle == "488F":
                detector.crop(x0["488"], y0["488"], roiSize, roiSize)
            if detector.handle == "561F":
                detector.crop(x0["561"], y0["561"], roiSize, roiSize)
            if detector.handle == "640F":
                detector.crop(x0["640"], y0["640"], roiSize, roiSize)
        for detector in self.detectors:
            self.updateParamsFromDetector(detector=detector)

        w.updatePointsDisplay()

        w.blueImage._drawCross = True
        w.greenImage._drawCross = True
        w.redImage._drawCross = True



    def getParameterValue(self, detector, parameter_name):
        detector_name = detector._DetectorManager__name
        shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
        if parameter_name == 'ExposureTime':
            value = float(shared_attributes[('Detector', detector_name, 'Param', parameter_name)])
        else:
            self._logger.warning("Debugging needed.")
            self._logger.debug(f"Parameter {parameter_name} not set up in getParameterValue!")
        return value
        
        
    def getOneSetImgs(self, dets=None):
        if dets is None:
            dets = self.detectors

        self._master.arduinoManager.activate25DWriteOnly()
        for detector in dets:
            detector._prevShape = detector._shape
            detector._prevOffset = detector._frameStart
            self.setCamForFOVWindow(detector)

        self._master.arduinoManager.trigger25DWriteOnly()
        time.sleep(0.1)

        lastImgs = []
        for detector in dets:
            lastImgs.append(detector._camera.grabFrame25D(1))

        self._master.arduinoManager.deactivateSLMWriteOnly()

        for detector in dets:
            if detector.forAcquisition:
                detector.stopAcquisitionSIM(toPrint = False)
                detector.crop(detector._prevOffset[0],detector._prevOffset[1],detector._prevShape[0],detector._prevShape[1], toPrint = False)

        return lastImgs


    def setCamForFOVWindow(self, detector):

        # detector._camera.setPropertyValue('AcquisitionFrameRateEnable', True, False)        
        # detector._camera.setPropertyValue('AcquisitionFrameRate', 10.0)

        detector.crop(0,0,5320,4600, toPrint=False)
        # trigger_mode = 'On'
        # exposure_auto = 'Off'
        # trigger_source = 'Line0'
        # trigger_overlap = 'Off'

        # # # Pull the exposure time from settings widget
        # exposure_time = self.getParameterValue(detector, 'ExposureTime')

        # # # exposure_time = self.exposure # anything < 19 ms
        # frame_rate_enable = True
        # buffer_mode = "NewestOnly"
        # triggerSelector = 'FrameStart'

        # # Set cam parameters
        # dic_parameters = {'TriggerOverlap': trigger_overlap, 'TriggerSelector': triggerSelector,'TriggerSource':trigger_source,'TriggerMode':trigger_mode,'AcquisitionFrameRateEnable':frame_rate_enable, 'ExposureAuto':exposure_auto, 'ExposureTime': exposure_time,  'StreamBufferHandlingMode':buffer_mode}

        # # for detector in detectors:
        # for parameter_name in dic_parameters:
        #     # print(detector._camera.getPropertyValue(parameter_name))
        #     detector._camera.setPropertyValue(parameter_name, dic_parameters[parameter_name])
        #     if parameter_name == 'ExposureTime':
        #         self._commChannel.sigWriteParamsFromCam.emit(detector, dic_parameters[parameter_name])
        #     # print(detector._camera.getPropertyValue(parameter_name))
        # # detector.tl_stream_nodemap['StreamBufferHandlingMode'].value = buffer_mode
        detector.startAcquisition25D()


    def toggleScatterCam(self, state):
        self._commChannel.scatterCamActive = state


    def writeParamsFromCamFunc(self, detector, value):
        self._master.detectorsManager._subManagers[detector.name].parameters['ExposureTime'].value = value
        self._master.detectorsManager._subManagers[detector.name].parameters['TriggerMode'].value = 'On'
        self.updateParamsFromDetector(detector=detector)
        self.updateSharedAttrs()

    
    def addROI(self):
        """ Adds the ROI to ImageWidget viewbox through the CommunicationChannel. """
        if not self.roiAdded:
            self._commChannel.sigAddItemToVb.emit(self._widget.getROIGraphicsItem())
            self.roiAdded = True

    def toggleROI(self, b, position=None, size=None):
        """ Show or hide ROI. """
        if b:
            self.addROI()
            self._widget.showROI(position, size)
        else:
            self._widget.hideROI()

    def initParameters(self):
        """ Take parameters from the detector Tree map. """
        for detectorName in self._master.detectorsManager.getAllDeviceNames():
            if self._master.detectorsManager[detectorName].forAcquisition:
                detectorTree = self._widget.trees[detectorName]
                framePar = detectorTree.p.param('Image frame')
                self.allParams[detectorName] = SettingsControllerParams(
                    model=detectorTree.p.param('Model'),
                    binning=framePar.param('Binning'),
                    frameMode=framePar.param('Mode'),
                    x0=framePar.param('X0'),
                    y0=framePar.param('Y0'),
                    width=framePar.param('Width'),
                    height=framePar.param('Height'),
                    applyROI=framePar.param('Apply'),
                    newROI=framePar.param('New ROI'),
                    abortROI=framePar.param('Abort ROI'),
                    saveMode=framePar.param('Save mode'),
                    deleteMode=framePar.param('Delete mode'),
                    allDetectorsFrame=framePar.param('Update all detectors')
                )

                params = self.allParams[detectorName]
                params.binning.sigValueChanged.connect(self.updateBinning)
                params.frameMode.sigValueChanged.connect(self.updateFrame)
                params.applyROI.sigActivated.connect(self.adjustFrame)
                params.newROI.sigActivated.connect(self.updateFrame)
                params.abortROI.sigActivated.connect(self.abortROI)
                params.saveMode.sigActivated.connect(self.saveMode)
                params.deleteMode.sigActivated.connect(self.deleteMode)

                def syncFrameParamsWithoutUpdates(): self.syncFrameParams(False, False)
                params.x0.sigValueChanged.connect(syncFrameParamsWithoutUpdates)
                params.y0.sigValueChanged.connect(syncFrameParamsWithoutUpdates)
                params.width.sigValueChanged.connect(syncFrameParamsWithoutUpdates)
                params.height.sigValueChanged.connect(syncFrameParamsWithoutUpdates)
                params.allDetectorsFrame.sigValueChanged.connect(self.syncFrameParams)

        detectorsParameters = self._master.detectorsManager.execOnAll(
            lambda c: c.parameters, condition=lambda c: c.forAcquisition
        )
        for detectorName, detectorParameters in detectorsParameters.items():
            for parameterName, parameter in detectorParameters.items():
                paramInWidget = self._widget.trees[detectorName].p.param(parameter.group).param(
                    parameterName
                )
                paramInWidget.sigValueChanged.connect(
                    lambda _, value, detectorName=detectorName, parameterName=parameterName:
                    self.setDetectorParameter(detectorName, parameterName, value)
                )

        detectorsActions = self._master.detectorsManager.execOnAll(
            lambda c: c.actions, condition=lambda c: c.forAcquisition
        )
        for detectorName, detectorActions in detectorsActions.items():
            for actionName, action in detectorActions.items():
                paramInWidget = self._widget.trees[detectorName].p.param(action.group).param(
                    actionName
                )
                paramInWidget.sigActivated.connect(action.func)

    def adjustFrame(self, *, detector=None):
        """ Crop detector and adjust frame. """

        if detector is None:
            self.getDetectorManagerFrameExecFunc()(lambda c: self.adjustFrame(detector=c))
            return

        # Adjust frame
        # frameStart = detector.frameStart
        # shape = detector.shape
        # fullShape = detector.fullShape
        params = self.allParams[detector.name]
        binning = int(params.binning.value())
        width = params.width.value()
        height = params.height.value()
        x0 = params.x0.value()
        y0 = params.y0.value()

        # Round to closest "divisible by 4" value.
        hpos = binning * x0
        vpos = binning * y0
        hsize = binning * width
        vsize = binning * height

        detector.crop(hpos, vpos, hsize, vsize)

        # Final shape values might differ from the user-specified one because of detector limitation
        if detector.name == self._master.detectorsManager.getCurrentDetectorName():
            self._commChannel.sigAdjustFrame.emit(detector.shape)
            self._widget.hideROI()

        self.updateParamsFromDetector(detector=detector)
        self.updateSharedAttrs()

    def ROIchanged(self):
        """ Update parameters according to ROI. """
        # frameStart = self._master.detectorsManager.execOnCurrent(lambda c: c.frameStart)
        # ROI = self._widget.getROIGraphicsItem()
        # pos = ROI.position
        # size = ROI.size

        # currentParams = self.getCurrentParams()
        # currentParams.x0.setValue(frameStart[0] + int(pos[0]))
        # currentParams.y0.setValue(frameStart[1] + int(pos[1]))
        # currentParams.width.setValue(size[0])  # [0] is Width
        # currentParams.height.setValue(size[1])  # [1] is Height

        frameStart = self._master.detectorsManager.execOnCurrent(lambda c: c.frameStart)
        ROI = self._widget.getROIGraphicsItem()
        pos = ROI.position
        size = ROI.size

        currentParams = self.getCurrentParams()
        currentParams.x0.setValue(frameStart[0])
        currentParams.y0.setValue(frameStart[1])
        currentParams.width.setValue(size[0]) 
        currentParams.height.setValue(size[1])  

    def updateFrameActionButtons(self, *, detector=None):
        """ Shows the frame-related buttons appropriate for the current frame
        mode, and hides the others. """

        if detector is None:
            self.getDetectorManagerFrameExecFunc()(
                lambda c: self.updateFrameActionButtons(detector=c)
            )
            return

        params = self.allParams[detector.name]

        params.applyROI.hide()
        params.newROI.hide()
        params.abortROI.hide()
        params.saveMode.hide()
        params.deleteMode.hide()

        if params.frameMode.value() == 'Custom':
            params.applyROI.show()
##CTFIX removed these buttons for now as the yellow roi selection is disabled
            # params.newROI.show()
            # params.abortROI.show()
            params.saveMode.show()
        elif params.frameMode.value() != 'Full chip':
            params.deleteMode.show()

    def abortROI(self):
        """ Cancel and reset parameters of the ROI. """
        self.toggleROI(False)
        frameStart = self._master.detectorsManager.execOnCurrent(lambda c: c.frameStart)
        shapes = self._master.detectorsManager.execOnCurrent(lambda c: c.shape)

        currentParams = self.getCurrentParams()
        currentParams.x0.setValue(frameStart[0])
        currentParams.y0.setValue(frameStart[1])
        currentParams.width.setValue(shapes[0])
        currentParams.height.setValue(shapes[1])

    def saveMode(self):
        """ Save the current frame mode parameters to the mode list. """

        currentParams = self.getCurrentParams()
        x0, y0, width, height = (currentParams.x0.value(), currentParams.y0.value(),
                                 currentParams.width.value(), currentParams.height.value())

        name = guitools.askForTextInput(
            self._widget,
            'Add frame mode',
            f'Enter a name for this mode:\n(X0: {x0}; Y0: {y0}; Width: {width}; Height: {height})')

        if not name:  # No name provided
            return

        add = True
        alreadyExists = False
        if name in self._setupInfo.rois:
            alreadyExists = True
            add = guitools.askYesNoQuestion(
                self._widget,
                'Frame mode already exists',
                f'A frame mode with the name "{name}" already exists. Do you want to overwrite it"?'
            )

        if add:
            # Add in GUI
            if not alreadyExists:
                for params in self.allParams.values():
                    newModeItems = params.frameMode.opts['limits'].copy()
                    newModeItems.insert(len(newModeItems) - 1, name)
                    params.frameMode.setLimits(newModeItems)

            # Set in setup info
            self._setupInfo.setROI(name, x0, y0, width, height)
            configfiletools.saveSetupInfo(configfiletools.loadOptions()[0], self._setupInfo)

            # Update selected ROI in GUI
            for params in self.allParams.values():
                params.frameMode.setValue(name)

    def deleteMode(self):
        """ Delete the current frame mode from the mode list (if it's a saved
        custom ROI). """

        currentParams = self.getCurrentParams()
        modeToDelete = currentParams.frameMode.value()

        confirmationResult = guitools.askYesNoQuestion(
            self._widget,
            'Delete frame mode?',
            f'Are you sure you want to delete the mode "{modeToDelete}"?'
        )

        if confirmationResult:
            # Remove in GUI
            for params in self.allParams.values():
                newModeItems = params.frameMode.opts['limits'].copy()
                newModeItems = [value for value in newModeItems if value != modeToDelete]
                params.frameMode.setLimits(newModeItems)

            # Remove from setup info
            self._setupInfo.removeROI(modeToDelete)
            configfiletools.saveSetupInfo(configfiletools.loadOptions()[0], self._setupInfo)

    def updateBinning(self):
        """ Update a new binning to the detector. """
        self.getDetectorManagerFrameExecFunc()(
            lambda c: c.setBinning(int(self.allParams[c.name].binning.value()))
        )
        self.updateSharedAttrs()

    def updateParamsFromDetector(self, *, detector):
        """ Update the parameter values from the detector. """
        try: #CTNOTE put here to suppress AFCAM error. Keep eye.
            params = self.allParams[detector.name]
        except KeyError:
            return

        # Detector parameters
        for parameterName, parameter in detector.parameters.items():
            paramInWidget = self._widget.trees[detector.name].p.param(parameter.group).param(
                parameterName
            )
            paramInWidget.setValue(parameter.value)


        # Frame
        params.binning.setValue(detector.binning)
        frameStart = detector.frameStart
        shape = detector.shape
        # fullShape = detector.fullShape
        fullShapeSensor = detector.fullShapeSensor
        params.x0.setValue(frameStart[0])
        params.y0.setValue(frameStart[1])
        params.width.setValue(shape[0])
        params.width.setLimits((1, fullShapeSensor[0]))#CTNOTE Should the first index be 32?
        params.height.setValue(shape[1])
        params.height.setLimits((1, fullShapeSensor[1]))#CTNOTE Should the first index be 32?

        # Model
        params.model.setValue(detector.model)

    def updateFrame(self, *, detector=None):
        """ Change the image frame size and position in the sensor. """

        if detector is None:
            self.getDetectorManagerFrameExecFunc()(lambda c: self.updateFrame(detector=c))
            return

        params = self.allParams[detector.name]
        frameMode = self.getCurrentParams().frameMode.value()
        customFrame = frameMode == 'Custom'

        params.x0.setWritable(customFrame)
        params.y0.setWritable(customFrame)
        params.width.setWritable(customFrame)
        params.height.setWritable(customFrame)
        # Call .show() to prevent view alignment issues
        params.x0.show()
        params.y0.show()
        params.width.show()
        params.height.show()
        # frameStart = detector.frameStart
        # frameStart = (0,0) # ROIchanged() takes care of centerdeness 
        fullShapeSensor = detector.fullShapeSensor

        if customFrame:
            shape = detector.shape
            # ROIsize = (64, 64)
            # Grab ROIsize from config file - default ROI size is ROI of initial image
            # Make sense since we do not use full capacity of the sensor
            # FIXME: This is good for development. For final use mayb 1/2 or 1/4 of FOV?
            # FIXME: Might be we need to swap here too
            # ROIsize = (shape[0], shape[1])
            ROIpos = (detector.offsetRelative[0],detector.offsetRelative[1])
            # If I want to have ROI at the center of my initial FOV
            # --------New implementation-------
            # ROIcenter = (frameStart[1], frameStart[0])
            # ROIpos = (ROIcenter[0], ROIcenter[1])
            
            # If I want to have a ROI at the center of new ROI
            # Toggle between custom and fullChip sests us back to config center
            
            params.x0.setValue(ROIpos[0])
            params.y0.setValue(ROIpos[1])
            params.width.setValue(shape[0])#CTEDIT swapped indices
            params.height.setValue(shape[1])#CTEDIT
            # --------Old implementation-------
            # Grab center of the current view for ROI center
            # ROIcenter = self._commChannel.getCenterViewbox()
            # ROIpos = (ROIcenter[0] - 0.5 * ROIsize[0],
            #           ROIcenter[1] - 0.5 * ROIsize[1])

##CTFIX Got rid of the yellow ROI selector for now
            # self.toggleROI(True, ROIpos, ROIsize)
            # self.ROIchanged()

        else:
            if frameMode == 'Full chip':

                fullShapeSensor = detector.fullShapeSensor
                params.x0.setValue(0)
                params.y0.setValue(0)
                params.width.setValue(fullShapeSensor[0])
                params.height.setValue(fullShapeSensor[1])
                self.toggleROI(False)
            else:
                # FIXME: Reading from GUI? Check if we need another swap
                roiInfo = self._setupInfo.rois[frameMode]
                params.x0.setValue(roiInfo.x)
                params.y0.setValue(roiInfo.y)
                params.width.setValue(roiInfo.w)
                params.height.setValue(roiInfo.h)

            self.adjustFrame(detector=detector)

        self.syncFrameParams(doAdjustFrame=False)

    def detectorSwitched(self, newDetectorName, _=None):
        """ Called when the user switches to another detector. """
        self._widget.setDisplayedDetector(newDetectorName)
        self._widget.setImageFrameVisible(self._master.detectorsManager[newDetectorName].croppable)
        newDetectorShape = self._master.detectorsManager[newDetectorName].shape
        self._commChannel.sigAdjustFrame.emit(newDetectorShape)

    def detectorSwitchClicked(self, detectorName):
        """ Changes the current detector to the selected detector. """
        self._master.detectorsManager.setCurrentDetector(detectorName)

    def detectorNextClicked(self):
        """ Changes the current detector to the next detector. """
        self._widget.selectNextDetector()

    def syncFrameParams(self, doAdjustFrame=True, doUpdateFrameActionButtons=True):
        currentParams = self.getCurrentParams()
        shouldSync = currentParams.allDetectorsFrame.value()

        for params in self.allParams.values():
            params.allDetectorsFrame.setValue(shouldSync)
            if shouldSync:
                params.frameMode.setValue(currentParams.frameMode.value())
                params.x0.setValue(currentParams.x0.value())
                params.y0.setValue(currentParams.y0.value())
                params.width.setValue(currentParams.width.value())
                params.height.setValue(currentParams.height.value())

        if shouldSync and doAdjustFrame:
            self.adjustFrame()

        if doUpdateFrameActionButtons:
            self.updateFrameActionButtons()

    def getCurrentParams(self):
        return self.allParams[self._master.detectorsManager.getCurrentDetectorName()]

    def getDetectorManagerFrameExecFunc(self):
        """ Returns the detector manager exec function that should be used for
        frame-related changes. """
        currentParams = self.getCurrentParams()
        detectorsManager = self._master.detectorsManager
        return (detectorsManager.execOnAll if currentParams.allDetectorsFrame.value()
                else detectorsManager.execOnCurrent)

    def attrChanged(self, key, value):
        if self.settingAttr or len(key) < 3 or key[0] != _attrCategory:
            return

        detectorName = key[1]
        if len(key) == 3:
            if key[2] == _binningAttr:
                self.setDetectorBinning(detectorName, value)
            elif key[2] == _ROIAttr:
                self.setDetectorROI(detectorName, (value[0], value[1]), (value[2], value[3]))
        if len(key) == 4:
            if key[2] == _detectorParameterSubCategory:
                self.setDetectorParameter(detectorName, key[3], value)

    def setSharedAttr(self, detectorName, attr, value, *, isDetectorParameter=False):
        self.settingAttr = True
        try:
            if not isDetectorParameter:
                key = (_attrCategory, detectorName, attr)
            else:
                key = (_attrCategory, detectorName, _detectorParameterSubCategory, attr)
            self._commChannel.sharedAttrs[key] = value #CTNOTE possible not doing anything
        finally:
            self.settingAttr = False

    def updateSharedAttrs(self):
        for dName, dManager in self._master.detectorsManager:
            self.setSharedAttr(dName, _modelAttr, dManager.model)
            self.setSharedAttr(dName, _pixelSizeAttr, dManager.pixelSizeUm)
            self.setSharedAttr(dName, _binningAttr, dManager.binning)
            self.setSharedAttr(dName, _ROIAttr, [*dManager.frameStart, *dManager.shape])

            for parameterName, parameter in dManager.parameters.items():
                self.setSharedAttr(dName, parameterName, parameter.value, isDetectorParameter=True)

    @APIExport()
    def getDetectorNames(self) -> List[str]:
        """ Returns the device names of all detectors. These device names can
        be passed to other detector-related functions. """
        return self._master.detectorsManager.getAllDeviceNames()

    @APIExport(runOnUIThread=True)
    def setDetectorBinning(self, detectorName: str, binning: int) -> None:
        """ Sets binning value for the specified detector. """
        self.allParams[detectorName].binning.setValue(binning)
        self._master.detectorsManager[detectorName].setBinning(binning)

    @APIExport(runOnUIThread=True)
    def setDetectorROI(self, detectorName: str, frameStart: Tuple[int, int],
                       shape: Tuple[int, int]) -> None:
        """ Sets the ROI for the specified detector. frameStart is a tuple
        (x0, y0) and shape is a tuple (width, height). """

        detector = self._master.detectorsManager[detectorName]

        self.allParams[detectorName].frameMode.setValue('Custom')
        self.updateFrame(detector=detector)

        # FIXME: Another spot where region selection might be wrong
        self.allParams[detectorName].x0.setValue(frameStart[0])
        self.allParams[detectorName].y0.setValue(frameStart[1])
        self.allParams[detectorName].width.setValue(shape[0])
        self.allParams[detectorName].height.setValue(shape[1])
        self.adjustFrame(detector=detector)

    @APIExport(runOnUIThread=True)
    def setDetectorParameter(self, detectorName: str, parameterName: str, value: Any) -> None:
        """ Sets the specified detector-specific parameter to the specified
        value. """

        if parameterName == 'TriggerMode':
            # Special case for certain parameters that will follow the "update all detectors" option
            execFunc = self._master.detectorsManager.execOnAll
        else:
            def execFunc(f): self._master.detectorsManager.execOn(detectorName, f)

        execFunc(
            lambda c: (c.setParameter(parameterName, value) and
                       self.updateParamsFromDetector(detector=c))
        )
        self.updateSharedAttrs()


_attrCategory = 'Detector'
_modelAttr = 'Model'
_pixelSizeAttr = 'Pixel size'
_binningAttr = 'Binning'
_ROIAttr = 'ROI'
_detectorParameterSubCategory = 'Param'


# Copyright (C) 2020-2021 ImSwitch developers
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
