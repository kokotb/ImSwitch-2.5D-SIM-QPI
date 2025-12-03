import json
import os
import threading
import numpy as np
import matplotlib.pyplot as plt
from qtpy import QtCore, QtWidgets
import cv2

from imswitch.imcommon.model import dirtools, initLogger
from imswitch.imcontrol.model.managers.SLM25DManager import MaskMode, Direction
from ..basecontrollers import ImConWidgetController
import zernpol
from scipy.ndimage import center_of_mass
from scipy.signal import peak_widths

from PIL import Image, ImageDraw
import pyqtgraph as pg
from PyQt5.QtWidgets import QFileDialog

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
from PIL import Image
import time
import re



class SLM25DController(ImConWidgetController):
    """Linked to SLM25DWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)
        # self.pars = self._widget.pars
        # self.axes = self._widget.axes
        #self.autoZernCalibValues = [-0.7, -0.6, -0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        #self._commChannel.autoZernCalibValues = self.autoZernCalibValues
        self.slmActive = False
        self.axisValTypes = self._widget.axisValTypes
        self.paramNames = self._widget.paramNames
        if self._setupInfo.SLM25D is None:
            self._widget.replaceWithError('2.5D SLM is not configured in your setup file.')
            return

        self.ZernikeAllMasksSumFloatRight = np.zeros((1080, 960))
        self.ZernikeAllMasksSumFloatLeft = np.zeros((1080, 960))
        self.ZernikeAllMasksSumFloat = np.zeros((1920, 1080))

        self.centerMaskLeft = np.zeros((1080, 960))
        self.centerMaskRight = np.zeros((1080, 960))
        

        self.mask25dbinaryLeft = np.zeros((1080, 960))
        self.mask25dbinaryRight = np.zeros((1080, 960))
        
        # self._widget.start25D.toggled.connect(self._commChannel.sig25DAcqToggled.emit())
        # self._widget.start25D.toggled.connect(lambda value: self._commChannel.sig25DAcqToggled.emit(value))


        # Connect CommunicationChannel signals
        # self._commChannel.sigSLMMaskUpdated.connect(lambda mask: self.displayMask(mask))
        self._commChannel.sigSetAutoZern.connect(self.setAutoZern)
        self._commChannel.sigStartAutoZern.connect(self.startAutoZern)
        self._commChannel.sigSetOptimalZern.connect(self.setOptimalZern)
        # self._commChannel.sigAutoZernCalc.connect(self.calcAutoZern)
        # self._commChannel.sigToggleAutoZern.connect(self.toggleAutoZern)

        self.matrix25d = self._widget.matrix25d

        # {(order) : (min, max), ..... }:
        self.zernikeNormalizationDict = {(0, 0): (1.0, 1.0), (1, -1): (-1.9968000000000001, 1.9968000000000001), (1, 1): (-1.9968000000000001, 1.9968), (2, -2): (-2.4390490377035388, 2.4390490377035388),
          (2, 0): (-1.7320508075688772, 1.7319000498665866), (2, 2): (-2.441657646300013, 2.441657646300013), (3, -3): (-2.826475232346454, 2.826475232346454),
            (3, -1): (-2.8218846978382803, 2.8218846978382803), (3, 1): (-2.8218846978382803, 2.8218846978382803), (3, 3): (-2.826475232346454, 2.826475232346454),
             (4, -4): (-3.1570215166935713, 3.1570215166935713), (4, -2): (-3.130426605396449, 3.130426605396449), (4, 0): (-1.1180339823972583, 2.23606797749979),
               (4, 2): (-3.13981519001373, 3.13981519001373), (4, 4): (-3.1353128402711548, 3.1420876039381285)}
        
        self._widget.start25D.clicked.connect(self._commChannel.sig25DAcqToggled.emit)
        self._widget.updateDiameterMask.connect(self.updateAll)
        self._widget.sigStepUpDiameterClicked.connect(self.updateAll)
        self._widget.sigStepDownDiameterClicked.connect(self.updateAll) #!!! fix this

        self._widget.updateCenterMask.connect(self.combineAndProject)
        self._widget.sigStepUpCenterClicked.connect(self.combineAndProject)
        self._widget.sigStepDownCenterClicked.connect(self.combineAndProject)

        self._widget.update25DMask.connect(self.updatePhaseMask)
        self._widget.sigStepUp25DMask.connect(self.updatePhaseMask)
        self._widget.sigStepDown25DMask.connect(self.updatePhaseMask)
    
        self._widget.sigUpdateZernikeMask.connect(self.updateZernike)
        self._widget.sigStepUpZernikeLeft.connect(self.updateZernike)
        self._widget.sigStepDownZernikeLeft.connect(self.updateZernike)
        self._widget.sigStepUpZernikeRight.connect(self.updateZernike)
        self._widget.sigStepDownZernikeRight.connect(self.updateZernike)
        self._widget.autoZernCheckbox.clicked.connect(self.autoZernChecked)
        self._widget.autoZernCheckboxNew.clicked.connect(self.autoZernCheckedNew)

        self._widget.projectZernike.stateChanged.connect(self.combineAndProject)
        self._widget.project25D.stateChanged.connect(self.combineAndProject)
        self._widget.projectCenter.stateChanged.connect(self.combineAndProject)

        self.slm25DManager = self._master.slm25DManager

        self._widget.sigToggleSLM.connect(self.toggleSLMFromButton)
        self._widget.sigOpenPreviewButton.connect(self.openPreviewWindow)
        self._widget.sig25DParamChanged.connect(self.valueChanged25D)
        self._widget.sigZernParamChanged.connect(self.valueChangedZern)
        self._commChannel.sigModuleSettings.connect(self.loadZernSettings)
        self._commChannel.sigModuleSettings.connect(self.load25DSettings)
        self._commChannel.sigSIMAcqToggled.connect(self._widget.SIMToggled)
        self._widget.stop25D.clicked.connect(self._commChannel.updateStop25DCommand)
        self._widget.beginAZbutton.clicked.connect(self.initiateAZWithButton)
        self._widget.loadImgToSLMbutton.clicked.connect(self.openFileDialog)


        self._commChannel.sigBeginAutoZern.connect(self.beginAutoZernThread)
        self._commChannel.sigBeginAutoZernNew.connect(lambda selected_frame: self.beginAutoZernThreadNew(selected_frame))


        # self._commChannel.sig25DAcqToggled.connect(self._widget.toggled25D)
        # self._widget.stop25D

        #self._widget.autoZernCheckbox2.stateChanged.connect(self.combineAndProject)
        self.mask25D = np.zeros((1920, 1080))
        self.centerMask = np.zeros((1920, 1080))
        self.zernikeParametersOld = self.getAllZernikeParams()
        #self.sigZernMaskProjected = False # used to check if mask was projected yet

        self.init25DWidgetValues()
        self.updateAll() #This line is needed to initialize a 2.5D mask. This helps with later calculation. Leave it here.


        self.fullZernList = self.createFullZernList1stLoop()

        self.detectors = []
        self.retrieveDetectors()

    def openFileDialog(self):
        dialog = QFileDialog(self._widget)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("PNG (*.png)")
        path = self._commChannel.sharedAttrs._data[('User Dir Info', 'Working Directory')]
        dialog.setDirectory(path)
        if dialog.exec():
            filename = dialog.selectedFiles()
            img = Image.open(filename[0])
            arr = np.array(img)
            if arr.shape[2] != 1:
                arr = arr[:,:,0]
            #arr = np.ascontiguousarray(arr)
            if self.slmActive:
                self.slm25DManager.projectMask(self.reshapeMask(np.rot90(arr)))
        else:
           filename = None
        return filename
        
    def loadPath(self):

        jsonPath = self.openFileDialog(self.filePath.text())
        if jsonPath != None:
            self.filePath.setText(jsonPath[0])
        else: pass


    def retrieveDetectors(self):
        for detector in self._master.detectorsManager: #detector object list
            if detector[1]._DetectorManager__forAcquisition:
                fullName = detector[0]
                shortName = fullName[:5].replace(" ", "")
                detector[1].handle = shortName
                self.detectors.append(detector[1])

    def beginAutoZernThread(self):
        threading.Thread(target=self.AutoZernLoop, args=(), daemon=True).start()

    def beginAutoZernThreadNew(self, selected_frame):
        threading.Thread(target=self.AutoZernLoopNew, args=(selected_frame, ), daemon=True).start()

    def AutoZernLoop(self):

        print('autozern started')

        self._widget.projectZernike.setChecked(True)
        self._widget.projectZernike.setEnabled(False)
        self._widget.project25D.setChecked(False)
        self._widget.project25D.setEnabled(False)
        self._widget.projectCenter.setChecked(False)
        self._widget.projectCenter.setEnabled(False)

        self.startAutoZern()
        # for rep in range(self.numAZAlltestPoints):
        # #self.numAZTestValuesPerZernCoeff
        # #while self._commChannel.autoZernChecked:
        #     self._widget.pars[self.fullZernList[rep][0]].blockSignals(True)
        #     self._widget.pars[self.fullZernList[rep][0]].setStyleSheet("border: 3px solid green;")
        #     self._widget.pars[self.fullZernList[rep][0]].setValue(self.fullZernList[rep][1])
        #     print(self.fullZernList[rep][1])
        #     self._widget.pars[self.fullZernList[rep][0]].blockSignals(False)
        #     cajt = time.perf_counter()
        #     self.updateZernike()
        #     print('took ' + str(round(time.perf_counter() - cajt,3)) + ' seconds to project a mask')
        #     time.sleep(0.015)
        #     # while not self.sigZernMaskProjected:
        #     #     time.sleep(0.02)
            
        #     #self.sigZernMaskProjected = False

        #     self._master.arduinoManager.trigger25DWriteOnly()
            
        #     rawImg = self.detectors[2]._camera.grabFrame25D(1)
        #     # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
        #     self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
            
        #     self._master.slm25DManager.calcAutoZern(rawImg) # !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)

        #     if ((rep + 1) % self.numAZTestValuesPerZernCoeff == 0): #!!! put 7 instead of 21 again - later have it un-hadrcoded ####and (autoZernRep != -1)
        #             # look at the list, fit parabola, get best value, set value, continue
        #             optimalCoefficientMax = self._master.slm25DManager.optimalCoeffValueMax(list(self.autoZernCalibValuesDict.values())[((rep + 1) // self.numAZTestValuesPerZernCoeff) - 1])
        #             self._widget.pars[self.fullZernList[rep][0]].blockSignals(True)
        #             self._widget.pars[self.fullZernList[rep][0]].setValue(optimalCoefficientMax)
        #             self._widget.pars[self.fullZernList[rep][0]].blockSignals(False)
        #             self.updateZernike()
        #             time.sleep(0.015)
        #             self._master.slm25DManager.resetList()
            
        #     self._widget.pars[self.fullZernList[rep][0]].setStyleSheet('')

        #     if self._commChannel.stop25DNow: #allows exit of the loop
        #         self._commChannel.autoZernChecked = False
        #         break

        for key in self.autoZernCalibValuesDict:
            testvalues = list(self.autoZernCalibValuesDict[key])
            for testvalue in testvalues:

                self._widget.pars["AbsPosEdit" + key].blockSignals(True)
                self._widget.pars["AbsPosEdit" + key].setStyleSheet("border: 3px solid green;")
                self._widget.pars["AbsPosEdit" + key].setValue(testvalue)
                self._widget.pars["AbsPosEdit" + key].blockSignals(False)

                cajt = time.perf_counter()
                self.updateZernike()
                print('took ' + str(round(time.perf_counter() - cajt,3)) + ' seconds to project a mask')
                time.sleep(0.015)
                # while not self.sigZernMaskProjected:
                #     time.sleep(0.02)
                
                #self.sigZernMaskProjected = False

                self._master.arduinoManager.trigger25DWriteOnly()
                # waitingBuffers = self.detectors[2]._camera.getBufferValue('25D') # Arguement is unused by method.
                # print(waitingBuffers)
                # startBufferTime = time.time()
                # totalBufferTime = 0
                # while waitingBuffers != 1:
                #     endBufferTime = time.time()
                #     totalBufferTime = endBufferTime - startBufferTime
                #     waitingBuffers = self.detectors[2]._camera.getBufferValue('25D')
                #     # time.sleep(0.002)

                #     print(waitingBuffers)


                rawImg = self.detectors[2]._camera.grabFrame25D(1)
                # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
                self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
                
                self._master.slm25DManager.calcAutoZern(rawImg) # !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)
                
                if self._commChannel.stop25DNow: #allows exit of the loop
                    self._commChannel.autoZernChecked = False
                    break

            optimalCoefficientMax = self._master.slm25DManager.optimalCoeffValueMax(testvalues)
            self._widget.pars["AbsPosEdit" + key].blockSignals(True)
            self._widget.pars["AbsPosEdit" + key].setValue(optimalCoefficientMax)
            self._widget.pars["AbsPosEdit" + key].blockSignals(False)
            self.updateZernike()
            time.sleep(0.015)
            self._master.slm25DManager.resetList()
                
            self._widget.pars["AbsPosEdit" + key].setStyleSheet('')

                

        # self._commChannel.sigToggleAutoZern.emit(False)
        self.toggleAutoZern(False)
        self._commChannel.autoZernChecked = False

        self._widget.projectZernike.setEnabled(True)
        self._widget.project25D.setEnabled(True)
        self._widget.projectCenter.setEnabled(True)

        # self._widget.stop_button.setChecked(False) # probably dont need this here
        # self.stop25D()    

        #self._commChannel.sigAutoZernikeFinished.emit()













    def initiateAZWithButton(self):
        self._commChannel.sigGetAZFrameCoords.emit()

    def waitingForBuffers(self):
        waitingBuffers = self.detectors[2]._camera.getBufferValue('25D')
        while waitingBuffers != 1:
            time.sleep(0.01)
            waitingBuffers = self.detectors[2]._camera.getBufferValue('25D')
            self._master.arduinoManager.trigger25DWriteOnly()
            waitingBuffers = self.detectors[2]._camera.getBufferValue('25D')
        return

    def AutoZernLoopNew(self, selected_frame):
        '''Only for right half of zern mask, MUST USE LIGHT POLARIZER!!!'''

        print('autozern started')
        self._master.arduinoManager.activate25DWriteOnly()
        self._master.detectorsManager._subManagers["640 Fluor"].startAcquisition25D()

        self._widget.projectZernike.setChecked(True)
        self._widget.projectZernike.setEnabled(False)
        # self._widget.project25D.setChecked(False)
        self._widget.project25D.setEnabled(False)
        self._widget.projectCenter.setChecked(False)
        self._widget.projectCenter.setEnabled(False)

        ymin, ymax, xmin, xmax = selected_frame[0][1], selected_frame[1][1], selected_frame[0][2], selected_frame[1][2]
        self.startAutoZern()
        zPosFocus = self._master.positionersManager._subManagers['Z']._position['Z']

        self.detectors[2]._camera.setBufferTimeout(2000)

        zPosFocus = self.sphericalAberrationLoop(zPosFocus, ymin, ymax, xmin, xmax)  # find optimal SA and corrects focus
        zPosFocus = self.correct_focus(zPosFocus, ymin, ymax, xmin, xmax)
        print("Astigmatism 1 ====================================================")
        self.verticalAstigmatismLoop(zPosFocus, ymin, ymax, xmin, xmax, flag25dOn=True)
        self.obliqueAstigmatismLoop(zPosFocus, ymin, ymax, xmin, xmax, flag25dOn=True)
        print("refocus ====================================================")
        zPosFocus = self.correct_focus(zPosFocus, ymin, ymax, xmin, xmax)
        print("Coma 1 ====================================================")
        self.verticalComaLoop(zPosFocus, ymin, ymax, xmin, xmax, bananaMetric=False)
        self.horizontalComaLoop(zPosFocus, ymin, ymax, xmin, xmax, bananaMetric=False)
        self.verticalComaLoop(zPosFocus, ymin, ymax, xmin, xmax, bananaMetric=False)
        self.horizontalComaLoop(zPosFocus, ymin, ymax, xmin, xmax, bananaMetric=False)
        print("refocus ====================================================")
        zPosFocus = self.correct_focus(zPosFocus, ymin, ymax, xmin, xmax)
        print("Astigmatism 2 ====================================================")
        self.verticalAstigmatismLoop(zPosFocus, ymin, ymax, xmin, xmax, flag25dOn=False)
        self.obliqueAstigmatismLoop(zPosFocus, ymin, ymax, xmin, xmax, flag25dOn=False)
        print("refocus ====================================================")
        zPosFocus = self.correct_focus(zPosFocus, ymin, ymax, xmin, xmax)
        print("trefoil ====================================================")
        #self.trefoilLoop(zPosFocus, ymin, ymax, xmin, xmax)
        self.trefoilLoop(zPosFocus, ymin, ymax, xmin, xmax)
        print("refocus ====================================================")
        zPosFocus = self.correct_focus(zPosFocus, ymin, ymax, xmin, xmax)
        print("Coma 2 banana ====================================================")
        self.verticalComaLoop(zPosFocus, ymin, ymax, xmin, xmax, bananaMetric=False)
        self.horizontalComaLoop(zPosFocus, ymin, ymax, xmin, xmax, bananaMetric=False)
        print("refocus ====================================================")
        zPosFocus = self.correct_focus(zPosFocus, ymin, ymax, xmin, xmax)
        print("trefoil ====================================================")
        self.trefoilLoop(zPosFocus, ymin, ymax, xmin, xmax)
        print("refocus ====================================================")
        zPosFocus = self.correct_focus(zPosFocus, ymin, ymax, xmin, xmax)
        print("Astigmatism 3 ====================================================")
        self.verticalAstigmatismLoop(zPosFocus, ymin, ymax, xmin, xmax, flag25dOn=False)
        self.obliqueAstigmatismLoop(zPosFocus, ymin, ymax, xmin, xmax, flag25dOn=False)
        print("refocus ====================================================")
        zPosFocus = self.correct_focus(zPosFocus, ymin, ymax, xmin, xmax)
        print("trefoil ====================================================")
        self.trefoilLoop(zPosFocus, ymin, ymax, xmin, xmax)

        


        # self._commChannel.sigToggleAutoZern.emit(False)
        self.toggleAutoZernNew(False)
        self._commChannel.autoZernCheckedNew = False

        self._widget.projectZernike.setEnabled(True)
        self._widget.project25D.setEnabled(True)
        self._widget.projectCenter.setEnabled(True)

        # self._widget.stop_button.setChecked(False) # probably dont need this here
        # self.stop25D()    
        self._master.arduinoManager.deactivateSLMWriteOnly()
        self._master.detectorsManager._subManagers["640 Fluor"].stopAcquisition()

        self._commChannel.sigAutoZernikeFinished.emit()

    def correct_focus(self, zPosFocus, ymin, ymax, xmin, xmax):
        zPositions = np.linspace(-4., 4., 17)
        images = []
        Zmaxprofile = []
        scores = []
        for offset in zPositions:
            self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus + offset , 'Z')
            # !!! POSSIBLE THAT SLEEP WILL BE NEEDED HERE
            self._master.arduinoManager.trigger25DWriteOnly()
            self.waitingForBuffers()
            rawImg = self.detectors[2]._camera.grabFrame25D(1)
            # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
            self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
            beadImgAnalysis = rawImg[ymin:ymax, xmin:xmax]
            images.append(beadImgAnalysis)
            Zmaxprofile.append(np.max(beadImgAnalysis))
            if not (self._widget.autoZernCheckboxNew): #allows exit of the loop
                self.toggleAutoZernNew(False)
                self._commChannel.autoZernCheckedNew = False
                break
        

        ZFWHM, ZHM, ZLeft, ZRight = peak_widths(Zmaxprofile, np.array([np.argmax(Zmaxprofile)]), rel_height=0.5)
        zcenter = (ZLeft[0] + ZRight[0])/2.
        z_offset = np.interp(zcenter, np.arange(len(zPositions)), zPositions)
        NewFocus = zPosFocus + z_offset
        self._master.positionersManager._subManagers['Z'].setPosition(NewFocus, 'Z')

        return NewFocus
        
          

    
    def sphericalAberrationLoop(self, zPosFocus, ymin, ymax, xmin, xmax):
        # Oblique Astigmatism 
        key = '(4,0)Right'
        current = self._widget.pars['AbsPosEdit' + key].value()
        testvalues = np.linspace(current - 0.5, current + 0.5, 21)
        scores = []
        profiles = []
        images = []
        for testvalue in testvalues:
            
            self._widget.pars["AbsPosEdit" + key].blockSignals(True)
            self._widget.pars["AbsPosEdit" + key].setStyleSheet("border: 3px solid green;")
            self._widget.pars["AbsPosEdit" + key].setValue(testvalue)
            self._widget.pars["AbsPosEdit" + key].blockSignals(False)

            self.updateZernike()
            time.sleep(0.015)

            Zmaxprofile = []
            zPositions = np.linspace(-2., 2., 9)
            for offset in zPositions:
                self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus + offset , 'Z')
                # !!! POSSIBLE THAT SLEEP WILL BE NEEDED HERE
                self._master.arduinoManager.trigger25DWriteOnly()
                self.waitingForBuffers()
                rawImg = self.detectors[2]._camera.grabFrame25D(1)
                # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
                self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
                beadImgAnalysis = rawImg[ymin:ymax, xmin:xmax]
                images.append(beadImgAnalysis)
                Zmaxprofile.append(np.max(beadImgAnalysis))
                if not (self._widget.autoZernCheckboxNew): #allows exit of the loop
                    self.toggleAutoZernNew(False)
                    self._commChannel.autoZernCheckedNew = False
                    break
            

            ZFWHM, ZHM, ZLeft, ZRight = peak_widths(Zmaxprofile, np.array([np.argmax(Zmaxprofile)]), rel_height=0.5)
            # scores.append(ZFWHM[0])  
            scores.append(max(Zmaxprofile))  
            profiles.append(Zmaxprofile)  
        
        self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus, 'Z')

        print(scores)
        # SAOptimal = testvalues[scores.index(min(scores))]
        SAOptimal = testvalues[scores.index(max(scores))]

        self._widget.pars["AbsPosEdit" + key].blockSignals(True)
        self._widget.pars["AbsPosEdit" + key].setValue(SAOptimal)
        self._widget.pars["AbsPosEdit" + key].blockSignals(False)
        self.updateZernike()
        time.sleep(0.015)
            
        self.show_images_grid(images)
        self._widget.pars["AbsPosEdit" + key].setStyleSheet('')
        #self._widget.stop25D.setEnabled(False)
        #self._widget.start25D.setEnabled(True)

        ZProfileOptimal = profiles[scores.index(min(scores))]
        ZFWHM, ZHM, ZLeft, ZRight = peak_widths(ZProfileOptimal, np.array([np.argmax(ZProfileOptimal)]), rel_height=0.5)
        zcenter = (ZLeft[0] + ZRight[0])/2.
        z_offset = np.interp(zcenter, np.arange(len(zPositions)), zPositions)
        NewFocus = zPosFocus + z_offset
        self._master.positionersManager._subManagers['Z'].setPosition(NewFocus, 'Z')
        return NewFocus


    # Loops =======================================================================
    def obliqueAstigmatismLoop(self, zPosFocus, ymin, ymax, xmin, xmax, flag25dOn):

        # set 25d mask and project it stronger aberration effects
        if flag25dOn:
            self._widget.pars["AbsPosEditGamma"].blockSignals(True)
            self._widget.pars["AbsPosEditGamma"].setText("2.0")
            self._widget.pars["AbsPosEditGamma"].blockSignals(False)
            self._widget.pars["AbsPosEditPsi"].blockSignals(True)
            self._widget.pars["AbsPosEditPsi"].setText("0.0")
            self._widget.pars["AbsPosEditPsi"].blockSignals(False)
            self.updatePhaseMask()
            self._widget.project25D.setChecked(True)
            time.sleep(0.015)

        # Oblique Astigmatism 
        key = '(2,-2)Right'
        current = self._widget.pars['AbsPosEdit' + key].value()
        if flag25dOn:
            testvalues = np.linspace(current - 1.2, current + 1.2, 25)
        else:
            testvalues = np.linspace(current - 0.7, current + 0.7, 15)
        oblAstigScores = []
        images = []
        for testvalue in testvalues:

            
            self._widget.pars["AbsPosEdit" + key].blockSignals(True)
            self._widget.pars["AbsPosEdit" + key].setStyleSheet("border: 3px solid green;")
            self._widget.pars["AbsPosEdit" + key].setValue(testvalue)
            self._widget.pars["AbsPosEdit" + key].blockSignals(False)

            self.updateZernike()
            time.sleep(0.015)

            sigmas12 = []
            for offset in [-2., 2.]:
                self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus + offset , 'Z')
                # !!! POSSIBLE THAT SLEEP WILL BE NEEDED HERE
                self._master.arduinoManager.trigger25DWriteOnly()
                self.waitingForBuffers()
                rawImg = self.detectors[2]._camera.grabFrame25D(1)
                # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
                self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
                beadImgAnalysis = rawImg[ymin:ymax, xmin:xmax]
                images.append(beadImgAnalysis)
                sigma1, sigma2 = self.obliqueAstigmatism_metric(beadImgAnalysis, threshold=0.2) # !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)
                sigmas12.append([sigma1, sigma2])
                if not (self._widget.autoZernCheckboxNew): #allows exit of the loop
                    self.toggleAutoZernNew(False)
                    self._commChannel.autoZernCheckedNew = False
                    break
            

            astigMetric = abs(sigmas12[1][0] - sigmas12[1][1]) + abs(sigmas12[0][0] - sigmas12[0][1])
            oblAstigScores.append(astigMetric)  
        
        self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus, 'Z')

        print(oblAstigScores)
        oblAstigOptimal = testvalues[oblAstigScores.index(min(oblAstigScores))]

        self._widget.pars["AbsPosEdit" + key].blockSignals(True)
        self._widget.pars["AbsPosEdit" + key].setValue(oblAstigOptimal)
        self._widget.pars["AbsPosEdit" + key].blockSignals(False)
        self.updateZernike()
        time.sleep(0.015)
            
        self._widget.pars["AbsPosEdit" + key].setStyleSheet('')
        self._widget.project25D.setChecked(False)
        self.show_images_grid(images)
        #self._widget.stop25D.setEnabled(False)
        #self._widget.start25D.setEnabled(True)


    def verticalAstigmatismLoop(self, zPosFocus, ymin, ymax, xmin, xmax, flag25dOn):

        # set 25d mask and project it stronger aberration effects =============================================
        if flag25dOn:
            self._widget.pars["AbsPosEditGamma"].blockSignals(True)
            self._widget.pars["AbsPosEditGamma"].setText("2.0")
            self._widget.pars["AbsPosEditGamma"].blockSignals(False)
            self._widget.pars["AbsPosEditPsi"].blockSignals(True)
            self._widget.pars["AbsPosEditPsi"].setText("0.0")
            self._widget.pars["AbsPosEditPsi"].blockSignals(False)
            self.updatePhaseMask()
            self._widget.project25D.setChecked(True)
            time.sleep(0.015)
        # =======================================================================================================

        # Vertical Astigmatism 
        key = '(2,2)Right'
        current = self._widget.pars['AbsPosEdit' + key].value()
        if flag25dOn:
            testvalues = np.linspace(current - 1.2, current + 1.2, 25)
        else:
            testvalues = np.linspace(current - 0.7, current + 0.7, 15)
        vertAstigScores = []
        images = []
        for testvalue in testvalues:

            self._widget.pars["AbsPosEdit" + key].blockSignals(True)
            self._widget.pars["AbsPosEdit" + key].setStyleSheet("border: 3px solid green;")
            self._widget.pars["AbsPosEdit" + key].setValue(testvalue)
            self._widget.pars["AbsPosEdit" + key].blockSignals(False)

            self.updateZernike()
            time.sleep(0.015)

            sigmasXY = []
            for offset in [-2.0, 2.0]:
                self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus + offset , 'Z')
                # !!! POSSIBLE THAT SLEEP WILL BE NEEDED HERE
                self._master.arduinoManager.trigger25DWriteOnly()
                self.waitingForBuffers()
                rawImg = self.detectors[2]._camera.grabFrame25D(1)
                # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
                self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
                beadImgAnalysis = rawImg[ymin:ymax, xmin:xmax]
                images.append(beadImgAnalysis)
                sigmaX, sigmaY = self.verticalAstigmatism_metric(beadImgAnalysis, threshold=0.2) # !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)
                sigmasXY.append([sigmaX, sigmaY])
                if not (self._widget.autoZernCheckboxNew):#allows exit of the loop
                    self.toggleAutoZernNew(False)
                    self._commChannel.autoZernCheckedNew = False
                    break
            

            astigMetric = abs(sigmasXY[1][0] - sigmasXY[1][1]) + abs(sigmasXY[0][0] - sigmasXY[0][1])
            vertAstigScores.append(astigMetric)  
        

        self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus, 'Z')

        print(vertAstigScores)
        vertAstigOptimal = testvalues[vertAstigScores.index(min(vertAstigScores))]

        self._widget.pars["AbsPosEdit" + key].blockSignals(True)
        self._widget.pars["AbsPosEdit" + key].setValue(vertAstigOptimal)
        self._widget.pars["AbsPosEdit" + key].blockSignals(False)
        self.updateZernike()
        time.sleep(0.015)
        self.show_images_grid(images)
            
        self._widget.pars["AbsPosEdit" + key].setStyleSheet('')
        self._widget.project25D.setChecked(False)
        #self._widget.stop25D.setEnabled(False)
        #self._widget.start25D.setEnabled(True)


    def show_images_grid(self, images, cols=6, titles=None, thresholds=[0.1, 0.2,0.3,0.4,0.5,0.6,0.7,0.8, 0.9], cmap='gray'):
        n = len(images)
        rows = int(np.ceil(n / cols))
        h, w = images[0].shape  # predpostavimo, da so vse slike iste velikosti

        def make_grid(img_list):
            grid_img = Image.new('L', (cols * w, rows * h), color=0)  # 'L' = grayscale
            for idx, img in enumerate(img_list):
                r = idx // cols
                c = idx % cols
                im = Image.fromarray((img*255).astype(np.uint8))
                grid_img.paste(im, (c*w, r*h))
            return grid_img

        # Originalne slike
        grid = make_grid(images)
        grid.save("images.png")

        # Različni threshold-i
        for thr in thresholds:
            masked_images = [(img > img.max()*thr).astype(np.uint8) for img in images]
            grid_masked = make_grid(masked_images)
            grid_masked.save(f"images_{thr:.1f}.png")

        

    def horizontalComaLoop(self, zPosFocus, ymin, ymax, xmin, xmax, bananaMetric):
        # Horizontal Comma
        key = '(3,1)Right'
        testvalues = list(self.autoZernCalibValuesDict[key])
        horCommaScores = []
        horCommaScores2 = []
        images = []

        # current = self._widget.pars['AbsPosEdit' + key].value()
        # testvalues = np.linspace(current - 1.2, current + 1.2, 25)
        # scores = []
        # for testvalue in testvalues:
            
        #     self._widget.pars["AbsPosEdit" + key].blockSignals(True)
        #     self._widget.pars["AbsPosEdit" + key].setStyleSheet("border: 3px solid green;")
        #     self._widget.pars["AbsPosEdit" + key].setValue(testvalue)
        #     self._widget.pars["AbsPosEdit" + key].blockSignals(False)

        #     self.updateZernike()
        #     time.sleep(0.015)

        #     self._master.arduinoManager.trigger25DWriteOnly()
        #     self.waitingForBuffers()
        #     rawImg = self.detectors[2]._camera.grabFrame25D(1)
        #     # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
        #     self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
        #     beadImgAnalysis = rawImg[ymin:ymax, xmin:xmax]
        #     sigma = self.general_area_metric(beadImgAnalysis, threshold=0.25) # !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)
        #     scores.append(sigma)
        #     if not (self._widget.autoZernCheckboxNew): #allows exit of the loop
        #         self.toggleAutoZernNew(False)
        #         self._commChannel.autoZernCheckedNew = False
        #         break

        # print(scores)
        # horCommaOptimal = testvalues[scores.index(min(scores))]

        # self._widget.pars["AbsPosEdit" + key].blockSignals(True)
        # self._widget.pars["AbsPosEdit" + key].setValue(horCommaOptimal)
        # self._widget.pars["AbsPosEdit" + key].blockSignals(False)
        # self.updateZernike()
        # time.sleep(0.015)
            
        # self._widget.pars["AbsPosEdit" + key].setStyleSheet('')
        # #self._widget.stop25D.setEnabled(False)
        # #self._widget.start25D.setEnabled(True)


        current = self._widget.pars['AbsPosEdit' + key].value()
        if bananaMetric:
            testvalues = np.linspace(current - 0.7, current + 0.7, 15)
        else:
            testvalues = np.linspace(current - 1.2, current + 1.2, 25)
        scores = []
        scores = []
        for testvalue in testvalues:
            
            self._widget.pars["AbsPosEdit" + key].blockSignals(True)
            self._widget.pars["AbsPosEdit" + key].setStyleSheet("border: 3px solid green;")
            self._widget.pars["AbsPosEdit" + key].setValue(testvalue)
            self._widget.pars["AbsPosEdit" + key].blockSignals(False)

            self.updateZernike()
            time.sleep(0.015)

            sigmasXY = []
            if bananaMetric:
                offsets = [-3., 0., 3.]
            else:
                offsets = [0.]
            for offset in offsets:
                self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus + offset , 'Z')
                self._master.arduinoManager.trigger25DWriteOnly()
                self.waitingForBuffers()
                rawImg = self.detectors[2]._camera.grabFrame25D(1)
                # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
                self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
                beadImgAnalysis = rawImg[ymin:ymax, xmin:xmax]
                images.append(beadImgAnalysis)
                sigmaX, sigmaY = self.comma_metric(beadImgAnalysis, threshold=0.9) # !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)
                sigmasXY.append([sigmaX, sigmaY])
                #score = self.general_area_metric(beadImgAnalysis, threshold=0.1)
                score = self.coma_metric2(beadImgAnalysis, threshold=0.1)[0]
                if (offset == 0.):
                    scores.append(score)
                if not (self._widget.autoZernCheckboxNew): #allows exit of the loop
                    self.toggleAutoZernNew(False)
                    self._commChannel.autoZernCheckedNew = False
                    break
            

            commaMetric = abs((sigmasXY[2][0] - sigmasXY[1][0]) + (sigmasXY[0][0] - sigmasXY[1][0]))
            #commaMetric = abs(sigmasXY[2][0] - sigmasXY[2][1]) + abs(sigmasXY[0][0] - sigmasXY[0][1]) # for astig metric
            commaMetric2 = abs((sigmasXY[2][1] - sigmasXY[1][1]) + (sigmasXY[0][1] - sigmasXY[1][1]))
            horCommaScores.append(commaMetric)  
            horCommaScores2.append(commaMetric2)
        
        self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus, 'Z')

        if (bananaMetric == True):
            print(horCommaScores)
            horCommaOptimal = testvalues[horCommaScores.index(min(horCommaScores))]
        else:
            print(scores)
            horCommaOptimal = testvalues[scores.index(min(scores))]

        self._widget.pars["AbsPosEdit" + key].blockSignals(True)
        self._widget.pars["AbsPosEdit" + key].setValue(horCommaOptimal)
        self._widget.pars["AbsPosEdit" + key].blockSignals(False)
        self.updateZernike()
        time.sleep(0.015)
        self.show_images_grid(images)
            
        self._widget.pars["AbsPosEdit" + key].setStyleSheet('')
        #self._widget.stop25D.setEnabled(False)
        #self._widget.start25D.setEnabled(True)
    

    def verticalComaLoop(self, zPosFocus, ymin, ymax, xmin, xmax, bananaMetric):
        # Vertical Comma 
        key = '(3,-1)Right'
        testvalues = list(self.autoZernCalibValuesDict[key])
        vertCommaScores = []
        images = []
        

        # current = self._widget.pars['AbsPosEdit' + key].value()
        # testvalues = np.linspace(current - 1.2, current + 1.2, 25)
        # scores = []
        # scores35 = []
        # scores60 = []
        # scores70 = []
        # scores80 = []

        # for testvalue in testvalues:
            
        #     self._widget.pars["AbsPosEdit" + key].blockSignals(True)
        #     self._widget.pars["AbsPosEdit" + key].setStyleSheet("border: 3px solid green;")
        #     self._widget.pars["AbsPosEdit" + key].setValue(testvalue)
        #     self._widget.pars["AbsPosEdit" + key].blockSignals(False)

        #     self.updateZernike()
        #     time.sleep(0.015)

        #     self._master.arduinoManager.trigger25DWriteOnly()
        #     self.waitingForBuffers()
        #     rawImg = self.detectors[2]._camera.grabFrame25D(1)
        #     # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
        #     self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
        #     beadImgAnalysis = rawImg[ymin:ymax, xmin:xmax]
        #     sigma = self.general_area_metric(beadImgAnalysis, threshold=0.25) # !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)
        #     scores.append(sigma)
        #     scores35.append(self.general_area_metric(beadImgAnalysis, threshold=0.35))
        #     scores60.append(self.general_area_metric(beadImgAnalysis, threshold=0.6))
        #     scores70.append(self.general_area_metric(beadImgAnalysis, threshold=0.7))
        #     scores80.append(self.general_area_metric(beadImgAnalysis, threshold=0.8))
        #     if not (self._widget.autoZernCheckboxNew): #allows exit of the loop
        #         self.toggleAutoZernNew(False)
        #         self._commChannel.autoZernCheckedNew = False
        #         break

        # print(scores)
        # print(scores35)
        # print(scores60)
        # print(scores70)
        # print(scores80)
        # vertCommaOptimal = testvalues[scores.index(min(scores))]

        # self._widget.pars["AbsPosEdit" + key].blockSignals(True)
        # self._widget.pars["AbsPosEdit" + key].setValue(vertCommaOptimal)
        # self._widget.pars["AbsPosEdit" + key].blockSignals(False)
        # self.updateZernike()
        # time.sleep(0.015)
            
        # self._widget.pars["AbsPosEdit" + key].setStyleSheet('')
        # #self._widget.stop25D.setEnabled(False)
        # #self._widget.start25D.setEnabled(True)

        current = self._widget.pars['AbsPosEdit' + key].value()
        if bananaMetric:
            testvalues = np.linspace(current - 0.5, current + 0.5, 11)
        else:
            testvalues = np.linspace(current - 1.2, current + 1.2, 25)
        scores = []
        for testvalue in testvalues:

            self._widget.pars["AbsPosEdit" + key].blockSignals(True)
            self._widget.pars["AbsPosEdit" + key].setStyleSheet("border: 3px solid green;")
            self._widget.pars["AbsPosEdit" + key].setValue(testvalue)
            self._widget.pars["AbsPosEdit" + key].blockSignals(False)

            self.updateZernike()
            time.sleep(0.015)

            sigmasXY = []
            if bananaMetric:
                offsets = [-3., 0., 3.]
            else:
                offsets = [0.]
            
            for offset in offsets:
                self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus + offset , 'Z')
                # !!! POSSIBLE THAT SLEEP WILL BE NEEDED HERE
                
                self._master.arduinoManager.trigger25DWriteOnly()
                self.waitingForBuffers()

                rawImg = self.detectors[2]._camera.grabFrame25D(1)
                # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
                self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
                beadImgAnalysis = rawImg[ymin:ymax, xmin:xmax]
                images.append(beadImgAnalysis)
                sigmaX, sigmaY = self.comma_metric(beadImgAnalysis, threshold=0.9) # !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)
                sigmasXY.append([sigmaX, sigmaY])
                # score = self.general_area_metric(beadImgAnalysis, threshold=0.1)
                score = self.coma_metric2(beadImgAnalysis, threshold=0.1)[1]
                if (offset == 0.):
                    scores.append(score)
                if not (self._widget.autoZernCheckboxNew): #allows exit of the loop
                    self.toggleAutoZernNew(False)
                    self._commChannel.autoZernCheckedNew = False
                    break
            
            try:
                commaMetric = abs(abs(sigmasXY[2][1] - sigmasXY[1][1]) + abs(sigmasXY[0][1] - sigmasXY[1][1]))
                #commaMetric = abs(sigmasXY[2][0] - sigmasXY[2][1]) + abs(sigmasXY[0][0] - sigmasXY[0][1]) #for astig metric
                vertCommaScores.append(commaMetric)  
            except:
                pass
        
        self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus, 'Z')

        if (bananaMetric == True):
            print(vertCommaScores)
            vertCommaOptimal = testvalues[vertCommaScores.index(min(vertCommaScores))]
        else:
            print(scores)
            vertCommaOptimal = testvalues[scores.index(min(scores))]

        self._widget.pars["AbsPosEdit" + key].blockSignals(True)
        self._widget.pars["AbsPosEdit" + key].setValue(vertCommaOptimal)
        self._widget.pars["AbsPosEdit" + key].blockSignals(False)
        self.updateZernike()
        time.sleep(0.015)
            
        self.show_images_grid(images)
        self._widget.pars["AbsPosEdit" + key].setStyleSheet('')
        #self._widget.stop25D.setEnabled(False)
        #self._widget.start25D.setEnabled(True)


    def trefoilLoop(self, zPosFocus, ymin, ymax, xmin, xmax):
        # Vertical Comma 
        for key in ['(3,-3)Right', '(3,3)Right']:
        #for key in ['(3,-3)Right', '(3,3)Right', '(3,-1)Right', '(3,1)Right', '(2,2)Right', '(2,-2)Right']:
            current = self._widget.pars['AbsPosEdit' + key].value()
            testvalues = np.linspace(current - 0.7, current + 0.7, 15)
            scores = []
            images = []
            # self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus + 1. , 'Z')
            self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus, 'Z')
            for testvalue in testvalues:
                
                self._widget.pars["AbsPosEdit" + key].blockSignals(True)
                self._widget.pars["AbsPosEdit" + key].setStyleSheet("border: 3px solid green;")
                self._widget.pars["AbsPosEdit" + key].setValue(testvalue)
                self._widget.pars["AbsPosEdit" + key].blockSignals(False)

                self.updateZernike()
                time.sleep(0.015)

                self._master.arduinoManager.trigger25DWriteOnly()
                self.waitingForBuffers()
                rawImg = self.detectors[2]._camera.grabFrame25D(1)
                # self._commChannel.sigGetLastRawImgs.emit(rawImg, self.detectors[2].handle)
                self._commChannel.saveLastRawImgs(rawImg, self.detectors[2].handle)
                beadImgAnalysis = rawImg[ymin:ymax, xmin:xmax]

                # tenegradm metric =================
                #beadImgAnalysis = np.where(beadImgAnalysis > 0.1 * beadImgAnalysis.max(), beadImgAnalysis, 0)
                sobel_x = cv2.Sobel(beadImgAnalysis, cv2.CV_64F, 1, 0, ksize=3)  # Sobel filter in X direction
                sobel_y = cv2.Sobel(beadImgAnalysis, cv2.CV_64F, 0, 1, ksize=3)  # Sobel filter in Y direction
                tenengrad = np.sqrt(sobel_x**2 + sobel_y**2)  # Compute gradient magnitude
                score = np.mean(tenengrad)


                images.append(beadImgAnalysis)
                #score = self.general_area_metric(beadImgAnalysis, threshold=0.1)# !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)
                #sigma = self.universal_r2_metric(beadImgAnalysis, threshold=0.25) # !!! rawImg is 1024x1024 1 color only !!!  affects later code (slm25DManager.optimalCoeffValueMax)
                #scores.append(sigma)
                scores.append(score)
                if not (self._widget.autoZernCheckboxNew): #allows exit of the loop
                    self.toggleAutoZernNew(False)
                    self._commChannel.autoZernCheckedNew = False
                    break

            print(scores)
            #trefoilOptimal = testvalues[scores.index(min(scores))]
            trefoilOptimal = testvalues[scores.index(max(scores))]

            self._widget.pars["AbsPosEdit" + key].blockSignals(True)
            self._widget.pars["AbsPosEdit" + key].setValue(trefoilOptimal)
            self._widget.pars["AbsPosEdit" + key].blockSignals(False)
            self.updateZernike()
            time.sleep(0.015)
                
            self._widget.pars["AbsPosEdit" + key].setStyleSheet('')
            #self._widget.stop25D.setEnabled(False)
            #self._widget.start25D.setEnabled(True)
            self.show_images_grid(images)
            
            self._master.positionersManager._subManagers['Z'].setPosition(zPosFocus, 'Z')



    # AZ metrics ==================================================================================================================
    def verticalAstigmatism_metric(self, XYslice, threshold):
        '''set threshold and flat or intensity mode'''

        thr = XYslice.max() * threshold   # treshold

        #masked = np.where(XYslice > thr, XYslice, 0)    # Intensity mode
        masked = np.where(XYslice > thr, 1, 0)  # Flat mode
        area = sum(sum(masked))
        y_com, x_com = center_of_mass(masked)

        Y, X = np.indices(XYslice.shape)
        dx = X - x_com
        dy = Y - y_com

        sigma_x = np.sqrt(np.sum(masked * dx**2) / area)
        sigma_y = np.sqrt(np.sum(masked * dy**2) / area)

        return sigma_x, sigma_y

    def obliqueAstigmatism_metric(self, XYslice, threshold):
        '''set threshold and flat or intensity mode'''

        thr = XYslice.max() * threshold   # treshold

        #masked = np.where(XYslice > thr, XYslice, 0)    # Intensity mode
        masked = np.where(XYslice > thr, 1, 0)  # Flat mode
        area = sum(sum(masked))
        y_com, x_com = center_of_mass(masked)

        Y, X = np.indices(XYslice.shape)
        dx = X - x_com
        dy = Y - y_com

        sigma_plus45 = np.sqrt(np.sum(masked * ((dx + dy)/2.**0.5)**2) / area)
        sigma_minus45 = np.sqrt(np.sum(masked * ((dx - dy)/2.**0.5)**2) / area)

        return sigma_plus45, sigma_minus45
    
    
    def comma_metric(self, XYslice, threshold):
        '''set threshold and flat or intensity mode'''

        thr = XYslice.max() * threshold   # treshold

        masked = np.where(XYslice > thr, XYslice, 0)    # Intensity mode
        #masked = np.where(XYslice > thr, 1, 0)  # Flat mode
        y_com, x_com = center_of_mass(masked)
        return x_com, y_com
    
    def coma_metric2(self, XYslice, threshold=0.1):
        #masked10 = np.where(XYslice > thr, XYslice, 0)    # Intensity mode
        masked10 = np.where(XYslice > XYslice.max() * 0.1, 1, 0)  # Flat mode
        masked90 = np.where(XYslice > XYslice.max() * 0.8, 1, 0)  # Flat mode
        y_com10, x_com10 = center_of_mass(masked10)
        y_com90, x_com90 = center_of_mass(masked90)
        return abs(x_com90 - x_com10), abs(y_com90 - y_com10)
        #return np.sum(masked90), np.sum(masked90)
    
    def general_area_metric(self, XYslice, threshold):
        thr = XYslice.max() * threshold   # treshold

        #masked = np.where(XYslice > thr, XYslice, 0)    # Intensity mode
        masked = np.where(XYslice > thr, 1, 0)  # Flat mode
        area = np.sum(masked)
        return area
    
    def universal_r2_metric(self, XYslice, threshold):
        thr = XYslice.max() * threshold   # treshold

        masked = np.where(XYslice > thr, XYslice, 0)    # Intensity mode
        #masked = np.where(XYslice > thr, 1, 0)  # Flat mode
        area = sum(sum(masked))
        y_com, x_com = center_of_mass(masked)

        Y, X = np.indices(XYslice.shape)
        dx = X - x_com
        dy = Y - y_com

        sigma_x = np.sqrt(np.sum(masked * dx**2) / area)
        sigma_y = np.sqrt(np.sum(masked * dy**2) / area)

        return np.sqrt(sigma_x**2. +  sigma_y**2.)


    # ===============================================================================================================













    def toggleAutoZern(self, state):
        self._widget.autoZernCheckbox.setChecked(state)

    def toggleAutoZernNew(self, state):
        self._widget.autoZernCheckboxNew.setChecked(state)

    def autoZernChecked(self, state):
        self._commChannel.autoZernChecked = state

    def autoZernCheckedNew(self, state):
        # self._commChannel.autoZernCheckedNew = state
        # self._commChannel.stop25DNow = True
        if state:
            pointSelected = self._widget.askYesNoQuestion()
            if pointSelected == True:
                self._commChannel.autoZernCheckedNew = state
                self._commChannel.stop25DNow = True
                # if not self._commChannel.simActive:
                #     self._commChannel.sigStart25D.emit()
            else:
                self._widget.autoZernCheckboxNew.setChecked(False)
                self._commChannel.autoZernCheckedNew = False
                self.toggleAutoZernNew(False)
                self._logger.warning('Please select single isolated bead before aberration correction.')


    def init25DWidgetValues(self):
        strippedNames = []
        self._widget.valueDict25D = dict()
        for i in range(len(self._widget.paramNames)):
            spaceStripped = self._widget.paramNames[i].replace(' ','')
            dashStripped = spaceStripped.replace('-','')
            strippedNames.append(dashStripped)
        for i in range(len(strippedNames)):
            self._widget.pars['AbsPosEdit' + self._widget.paramNames[i]].setText(str(self._setupInfo.SLM25D.__getattribute__(strippedNames[i])))
            self._widget.valueDict25D[self._widget.paramNames[i]] = str(self._setupInfo.SLM25D.__getattribute__(strippedNames[i]))

        strippedNames = []
        self._widget.valueDictZern25D = dict()
        for i in range(len(self._widget.ZernikeAberrationNames)):
            spaceStripped = self._widget.ZernikeAberrationNames[i].replace(' ','')
            dashStripped = spaceStripped.replace('-','')
            strippedNames.append(dashStripped)
        for i in range(len(strippedNames)):
            for side in  self._widget.ZernikeSides:
                self._widget.pars['AbsPosEdit' + self._widget.ZernikeCoefficientNames[i] + side].setValue(self._setupInfo.SLM25D.__getattribute__(side+strippedNames[i])) #Set value in widget
                self._widget.valueDictZern25D[self._widget.ZernikeCoefficientNames[i] + side] = self._setupInfo.SLM25D.__getattribute__(side+strippedNames[i]) #Initial value dictionary to reset to when 'Reset' is rpessed.
        
        self._widget.autoZernCheckbox.setChecked(False)
        self._widget.autoZernCheckboxNew.setChecked(False)
            

    def updateZernike(self):
        self.updateZernikePhaseMask()
        if self.slmActive:
            self.combineAndProject()
        #self.sigZernMaskProjected = True

    def updateAll(self):
        self.updatePhaseMask(False) # False tell this function to not combineAndProject, as that is handled 2 lines later.
        self.recalculateZernikePhaseMask()
        if self.slmActive:
            self.combineAndProject()

    def updatePhaseMask(self , recalc = True):
        self.calculatePhaseMask()

        # initial values
        xleftcenter = int(self._widget.valueDict25D["Left Center-X"])
        yleftcenter = int(self._widget.valueDict25D["Left Center-Y"])
        xrightcenter = int(self._widget.valueDict25D["Right Center-X"])
        yrightcenter = int(self._widget.valueDict25D["Right Center-Y"])

        # current values 
        parameters = self.getAllWidgetParams()
        xleftcenterC = parameters["Left Center-X"]
        yleftcenterC = parameters["Left Center-Y"]
        xrightcenterC = parameters["Right Center-X"]
        yrightcenterC = parameters["Right Center-Y"]

        xleftShift = xleftcenterC - xleftcenter
        yleftShift = yleftcenterC - yleftcenter
        xrightShift = xrightcenterC - xrightcenter
        yrightShift = yrightcenterC - yrightcenter

        projectImageLeft = np.zeros((1080, 960))
        projectImageRight = np.zeros((1080, 960))


        if (xleftShift != 0) or (yleftShift != 0) or (xrightShift != 0) or (yrightShift != 0):
            projectImageLeft += self.shiftMaskZeroPad(self.mask25dbinaryLeft, xleftShift, yleftShift)
            projectImageRight += self.shiftMaskZeroPad(self.mask25dbinaryRight, xrightShift, yrightShift)
        else:
            projectImageLeft += self.mask25dbinaryLeft
            projectImageRight += self.mask25dbinaryRight

        projImg = np.concatenate((projectImageLeft,projectImageRight), axis=1).transpose()
        projImg = projImg.astype(np.uint8)
        
        self._widget.matrix25d = projImg
        self._widget.img25d.setImage(self._widget.matrix25d)
        self.mask25D = self._widget.matrix25d
        # self._widget.vb25D.setAspectLocked(True)
        self.createCenterDotImage()

        if recalc:
            self.combineAndProject()

    def openPreviewWindow(self):
        self.slm25DManager.openPreviewWindow()

    def toggleSLMFromButton(self, state):
        self.toggleSLMResource(state)



    def toggleSLMResource(self, state):
        try:
            self.slmActive = self.slm25DManager.toggleSLMResource(state)
        except:
            self._widget.activate25DSLM.setChecked(False)

        if self.slmActive == True:
            self._widget.enableAll()
            self.combineAndProject()
        if self.slmActive == False:
            self._widget.disableAll()

    def reshapeMask(self, mask):
        maskFlipped = np.fliplr(mask)
        maskReshaped = np.reshape(maskFlipped,(1080, 1920), order='F')

        return maskReshaped

    def getAllWidgetParams(self): #is there a loop somewhere

        valueList = {}
        for index in self._widget.paramNames:
            name = 'AbsPosEdit' + index
            widgetObject = self._widget.pars[name]
            if index == 'Beam Diameter': # Want beam diamter in meters, but entry box in millimeters.
                valueList[index] = self.axisValTypes[index](widgetObject.text()) / 1000
            else:
                valueList[index] = self.axisValTypes[index](widgetObject.text())

        return valueList
    
    def createCenterDotImage(self):
        lx, ly, rx, ry = self.getCurrentCenters()

        ly = 1080-ly #The pixels are counted from bottom left in other system, so Y needs to be inverted.
        ry = 1080-ry

        llx = lx - 20 #left side of the left half X. These values of 20 are controlling the size of the erd dots.
        rlx = lx + 20
        lrx = rx - 20
        rrx = rx + 20

        toply = ly + 20 #left side of the left half X
        bly = ly - 20
        topry = ry + 20
        bry = ry - 20

        im = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))

        parameters = self.getAllWidgetParams()
        rho = parameters["Beam Diameter"]
        pszSLM = 0.000008 # (in m, 8 um) pixel size
        rhoPupilAperture = rho/2  #(in m, 2Rbeam = 6 mm, current estimation)
        radious = rhoPupilAperture/pszSLM # [pixels]

        draw = ImageDraw.Draw(im)
        draw.ellipse([llx, bly, rlx, toply], fill=(255, 0, 0))
        draw.ellipse([lrx, bry, rrx, topry], fill=(255, 0, 0))
        draw.ellipse([lx - radious, ly - radious, lx + radious, ly + radious], fill=(255, 0, 0, 100))
        draw.ellipse([rx - radious, ry - radious, rx + radious, ry + radious], fill=(255, 0, 0, 100))
        centerArray = np.array(im)
        centerArray = np.rot90(centerArray, 3)
        # self.overlayImg25D = pg.ImageItem(centerArray, opacity=0.5)
        # self._widget.vb25D.addItem(self.overlayImg25D)
        self._widget.overlayImg25D.setImage(centerArray)

    
    def getAllZernikeParams(self):

        valueList = {}
        for index in self._widget.ZernikeCoefficientNames:
            for side in self._widget.ZernikeSides:
                name = 'AbsPosEdit' + index + side
                widgetObject = self._widget.pars[name]
                valueList[index + side] = self.axisValTypes[index + side](widgetObject.value())

        # final = list(zip(self._widget.axes,valueList))
        # print(valueList)
        return valueList
    
    def calculateZernikePhaseMask(self):
        parameters = self.getAllWidgetParams()

        # Beam size and position parameters
        rho = parameters["Beam Diameter"]
        xleftcenter = int(self._widget.valueDict25D["Left Center-X"])
        yleftcenter = int(self._widget.valueDict25D["Left Center-Y"])
        xrightcenter = int(self._widget.valueDict25D["Right Center-X"])
        yrightcenter = int(self._widget.valueDict25D["Right Center-Y"])

        # SLM screen size parameters
        numberXpix = 1920
        numberYpix = 1080
        pszSLM = 0.000008 # (in m, 8 um) pixel size
        rhoPupilAperture = rho/2  #(in m, 2Rbeam = 6 mm, current estimation)
        rhoPupilAperturePix = rhoPupilAperture/pszSLM
        
        # ====================================================================================================================================
        y_coordsleft, x_coordsleft = np.indices((numberYpix, numberXpix//2))
        y_coordsright, x_coordsright = np.indices((numberYpix, numberXpix//2))
        x_coordsright += 960

        xleftnormalized, yleftnormalized = (x_coordsleft - xleftcenter) / rhoPupilAperturePix , (y_coordsleft - yleftcenter) / rhoPupilAperturePix
        xrightnormalized, yrightnormalized = (x_coordsright - xrightcenter) / rhoPupilAperturePix , (y_coordsright - yrightcenter) / rhoPupilAperturePix
        # ====================================================================================================================================

        zernikeParametersNew = self.getAllZernikeParams()
################################
        # if self._widget.invert.isChecked():
        #     for key in zernikeParametersNew.keys():
        #         zernikeParametersNew[key] = - zernikeParametersNew[key]
################################


        allZeros = all(value == 0.0 for value in zernikeParametersNew.values())
        zernikeParametersDifferences = {key: zernikeParametersNew[key] - self.zernikeParametersOld[key] for key in self.zernikeParametersOld if self.zernikeParametersOld[key] != zernikeParametersNew[key]}
        if not allZeros:
            if zernikeParametersDifferences != {}:
                for name in zernikeParametersDifferences:
                    bullshit = re.search(r"\((-?\d+),(-?\d+)\)(\w+)", name)
                    order = (int(bullshit.group(1)), int(bullshit.group(2)))  
                    side = bullshit.group(3)

                    
                    
                    
                    # if np.nanmin(zernikeMask) == np.nanmax(zernikeMask):
                    #     zernikeMask[np.isnan(zernikeMask)] = 0
                    # else: 
                    #     zernikeMask[np.isnan(zernikeMask)] = np.nanmin(zernikeMask)

                    # Normalize and transpose

                    if side == "Left":
                        # if name == '(0,0)':
                        if order == (0,0):
                            zernikeLeft = zernpol.Zernpol.func_cart(order, xleftnormalized, yleftnormalized, masked=False)
                            self.ZernikeAllMasksSumFloatLeft += zernikeLeft * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) *256
                        else:
                            zernikeLeft = zernpol.Zernpol.func_cart(order, xleftnormalized, yleftnormalized, masked=False)
                            zernikeLeft = (zernikeLeft-self.zernikeNormalizationDict[order][0])/(self.zernikeNormalizationDict[order][1]-self.zernikeNormalizationDict[order][0])
                            self.ZernikeAllMasksSumFloatLeft += zernikeLeft * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) * 256
                            
                    elif side == "Right":
                        # if name == '(0,0)':
                        if order == (0,0):
                            zernikeRight = zernpol.Zernpol.func_cart(order, xrightnormalized, yrightnormalized, masked=False)
                            self.ZernikeAllMasksSumFloatRight += zernikeRight * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) * 256
                        else:
                            zernikeRight = zernpol.Zernpol.func_cart(order, xrightnormalized, yrightnormalized, masked=False)
                            zernikeRight = (zernikeRight-self.zernikeNormalizationDict[order][0])/(self.zernikeNormalizationDict[order][1]-self.zernikeNormalizationDict[order][0])
                            self.ZernikeAllMasksSumFloatRight += zernikeRight * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) * 256
                            
                self.zernikeMask = np.concatenate((self.ZernikeAllMasksSumFloatLeft, self.ZernikeAllMasksSumFloatRight), axis=1)
                self.zernikeMask = self.zernikeMask.transpose()
                self.ZernikeAllMasksSumFloat += self.zernikeMask

        else:
            self.ZernikeAllMasksSumFloat = np.zeros((1920, 1080))
            self.ZernikeAllMasksSumFloatLeft = np.zeros((1080, 960))
            self.ZernikeAllMasksSumFloatRight = np.zeros((1080, 960))

        #zernikeMask = np.concatenate((zernikeLeft, zernikeRight), axis=1)
        #self.zernikeMask = zernikeMask.transpose()
        self.ZernikeAllMasksSum = np.round(self.ZernikeAllMasksSumFloat).astype(np.uint8)
        self.zernikeParametersOld = zernikeParametersNew
        return self.ZernikeAllMasksSum

    def calculateNewZernikePhaseMask(self):
        parameters = self.getAllWidgetParams()

        # Beam size and position parameters
        rho = parameters["Beam Diameter"]
        xleftcenter = int(self._widget.valueDict25D["Left Center-X"])
        yleftcenter = int(self._widget.valueDict25D["Left Center-Y"])
        xrightcenter = int(self._widget.valueDict25D["Right Center-X"])
        yrightcenter = int(self._widget.valueDict25D["Right Center-Y"])

        # SLM screen size parameters
        numberXpix = 1920
        numberYpix = 1080
        pszSLM = 0.000008 # (in m, 8 um) pixel sizeupdateZernikeMask
        rhoPupilAperture = rho/2  #(in m, 2Rbeam = 6 mm, current estimation)
        rhoPupilAperturePix = rhoPupilAperture/pszSLM
        
        # ====================================================================================================================================
        y_coordsleft, x_coordsleft = np.indices((numberYpix, numberXpix//2))
        y_coordsright, x_coordsright = np.indices((numberYpix, numberXpix//2))
        x_coordsright += 960

        xleftnormalized, yleftnormalized = (x_coordsleft - xleftcenter) / rhoPupilAperturePix , (y_coordsleft - yleftcenter) / rhoPupilAperturePix
        xrightnormalized, yrightnormalized = (x_coordsright - xrightcenter) / rhoPupilAperturePix , (y_coordsright - yrightcenter) / rhoPupilAperturePix
        
        rholeft = np.sqrt(xleftnormalized**2 + yleftnormalized**2)
        phileft = np.arctan2(yleftnormalized, xleftnormalized)
        rhoright = np.sqrt(xrightnormalized**2 + yrightnormalized**2)
        phiright = np.arctan2(yrightnormalized, xrightnormalized)
        
        # ====================================================================================================================================
        zernikeParametersNew = self.getAllZernikeParams()

        self.ZernikeAllMasksSumFloat = np.zeros((1920,1080)) #CTNOTE
        self.ZernikeAllMasksSumFloatLeft = np.zeros((1080, 960)) #CTNOTE
        self.ZernikeAllMasksSumFloatRight = np.zeros((1080, 960)) #CTNOTE
        for name in zernikeParametersNew:
            bullshit = re.search(r"\((-?\d+),(-?\d+)\)(\w+)", name)
            order = (int(bullshit.group(1)), int(bullshit.group(2)))  
            side = bullshit.group(3)

            if side == "Left":
                # if name == '(0,0)':
                if order == (0,0):
                    zernikeLeft = zernpol.Zernpol.func(order, rholeft, phileft, masked=False)
                    self.ZernikeAllMasksSumFloatLeft += zernikeLeft * (zernikeParametersNew[name]) * 256
                else:
                    zernikeLeft = zernpol.Zernpol.func(order, rholeft, phileft, masked=False)
                    zernikeLeft = (zernikeLeft-self.zernikeNormalizationDict[order][0])/(self.zernikeNormalizationDict[order][1]-self.zernikeNormalizationDict[order][0])
                    self.ZernikeAllMasksSumFloatLeft += zernikeLeft * (zernikeParametersNew[name]) * 256
                    
            elif side == "Right":
                # if name == '(0,0)':
                if order == (0,0):
                    zernikeRight = zernpol.Zernpol.func(order, rhoright, phiright, masked=False)
                    self.ZernikeAllMasksSumFloatRight += zernikeRight * (zernikeParametersNew[name]) * 256
                else:
                    zernikeRight = zernpol.Zernpol.func(order, rhoright, phiright, masked=False)
                    zernikeRight = (zernikeRight-self.zernikeNormalizationDict[order][0])/(self.zernikeNormalizationDict[order][1]-self.zernikeNormalizationDict[order][0])
                    self.ZernikeAllMasksSumFloatRight += zernikeRight * (zernikeParametersNew[name]) * 256
                    

        zernikeMask = np.concatenate((self.ZernikeAllMasksSumFloatLeft, self.ZernikeAllMasksSumFloatRight), axis=1)
        self.zernikeMask = zernikeMask.transpose()
        self.ZernikeAllMasksSumFloat = self.zernikeMask

        self.ZernikeAllMasksSum = self.ZernikeAllMasksSumFloat.astype(np.uint8)
        self.zernikeParametersOld = zernikeParametersNew

        return self.ZernikeAllMasksSum
    
    # def combineAndProject(self):
    #     projZernike = self._widget.projectZernike.checkState()
    #     proj25D = self._widget.project25D.checkState()
    #     projCenter = self._widget.projectCenter.checkState()

    #     if (projZernike == 2) and (proj25D == 2):
    #         #if ((self._widget.matrixZernike == 0).all()):
    #             #self._widget.matrixZernike = np.ones((1920, 1080))
    #         projImg = self.mask25D + self._widget.matrixZernike 

    #         if self.slmActive:
    #             self.slm25DManager.projectMask(self.reshapeMask(projImg))

    #     elif (projZernike == 2) and (proj25D == 0) and (projCenter == 0):
    #         #if ((self._widget.matrixZernike == 0).all()):
    #             #self._widget.matrixZernike = np.ones((1920, 1080))
    #         projImg = self._widget.matrixZernike
    #         if self.slmActive:
    #             self.slm25DManager.projectMask(self.reshapeMask(projImg))

    #     elif (projZernike == 0) and (proj25D == 2):
    #         projImg = self.mask25D
    #         if self.slmActive:
    #             self.slm25DManager.projectMask(self.reshapeMask(projImg))

    #     elif (projZernike == 0) and (proj25D == 0) and (projCenter == 0):
    #         projImg = np.zeros((1920, 1080))
    #         if self.slmActive:
    #             self.slm25DManager.projectMask(self.reshapeMask(projImg))

    #     elif (projCenter == 2) and (projZernike == 0): # always center mask only!
    #         self.centerMask = self.createCenterMask()
    #         projImg = self.centerMask
    #         if self.slmActive:
    #             self.slm25DManager.projectMask(self.reshapeMask(projImg))

    #     elif (projZernike == 2) and (projCenter == 2):
    #         #if ((self._widget.matrixZernike == 0).all()):
    #             #self._widget.matrixZernike = np.ones((1920, 1080))
    #         self.centerMask = self.createCenterMask()
    #         projImg = self.centerMask + self._widget.matrixZernike 

    #         if self.slmActive:
    #             self.slm25DManager.projectMask(self.reshapeMask(projImg))

    #     else:
    #         print('Center mask can be projected alone only')

    import numpy as np

    def shiftMaskZeroPad(self, mask, x_shift: int, y_shift: int):
        shifted = np.zeros_like(mask)
        h, w = mask.shape

        if x_shift >= 0:
            x_src_start, x_src_end = 0, w - x_shift
            x_dst_start, x_dst_end = x_shift, w
        else:
            x_src_start, x_src_end = -x_shift, w
            x_dst_start, x_dst_end = 0, w + x_shift

        if y_shift >= 0:
            y_src_start, y_src_end = 0, h - y_shift
            y_dst_start, y_dst_end = y_shift, h
        else:
            y_src_start, y_src_end = -y_shift, h
            y_dst_start, y_dst_end = 0, h + y_shift

        shifted[y_dst_start:y_dst_end, x_dst_start:x_dst_end] = mask[y_src_start:y_src_end, x_src_start:x_src_end]

        return shifted




    def combineAndProject(self):

        self.createCenterDotImage()
        # initial values
        xleftcenter = int(self._widget.valueDict25D["Left Center-X"])
        yleftcenter = int(self._widget.valueDict25D["Left Center-Y"])
        xrightcenter = int(self._widget.valueDict25D["Right Center-X"])
        yrightcenter = int(self._widget.valueDict25D["Right Center-Y"])

        # current values 
        parameters = self.getAllWidgetParams()
        xleftcenterC = parameters["Left Center-X"]
        yleftcenterC = parameters["Left Center-Y"]
        xrightcenterC = parameters["Right Center-X"]
        yrightcenterC = parameters["Right Center-Y"]

        xleftShift = xleftcenterC - xleftcenter
        yleftShift = yleftcenterC - yleftcenter
        xrightShift = xrightcenterC - xrightcenter
        yrightShift = yrightcenterC - yrightcenter


        projZernike = self._widget.projectZernike.checkState()
        proj25D = self._widget.project25D.checkState()
        projCenter = self._widget.projectCenter.checkState()

        projectImageLeft = np.zeros((1080, 960))
        projectImageRight = np.zeros((1080, 960))

        if (proj25D == 2):
            if (xleftShift != 0) or (yleftShift != 0) or (xrightShift != 0) or (yrightShift != 0):
                projectImageLeft += self.shiftMaskZeroPad(self.mask25dbinaryLeft, xleftShift, yleftShift)
                projectImageRight += self.shiftMaskZeroPad(self.mask25dbinaryRight, xrightShift, yrightShift)
                
                widget25dMask = np.concatenate((self.shiftMaskZeroPad(self.mask25dbinaryLeft, xleftShift, yleftShift),self.shiftMaskZeroPad(self.mask25dbinaryRight, xrightShift, yrightShift)), axis=1).transpose()
                widget25dMask = widget25dMask.astype(np.uint8)
        
                self._widget.matrix25d = widget25dMask  
                self._widget.img25d.setImage(self._widget.matrix25d)
                self.mask25D = self._widget.matrix25d
            else:
                projectImageLeft += self.mask25dbinaryLeft
                projectImageRight += self.mask25dbinaryRight

                widget25dMask = np.concatenate((self.mask25dbinaryLeft,self.mask25dbinaryRight), axis=1).transpose()
                widget25dMask = widget25dMask.astype(np.uint8)
        
                self._widget.matrix25d = widget25dMask   
                self._widget.img25d.setImage(self._widget.matrix25d)
                self.mask25D = self._widget.matrix25d

        if (projZernike == 2):
            if (xleftShift != 0) or (yleftShift != 0) or (xrightShift != 0) or (yrightShift != 0):
                projectImageLeft += self.shiftMaskZeroPad(self.ZernikeAllMasksSumFloatLeft, xleftShift, yleftShift)
                projectImageRight += self.shiftMaskZeroPad(self.ZernikeAllMasksSumFloatRight, xrightShift, yrightShift)
            
                widgetZernikeMask = np.concatenate((self.shiftMaskZeroPad(self.ZernikeAllMasksSumFloatLeft, xleftShift, yleftShift),self.shiftMaskZeroPad(self.ZernikeAllMasksSumFloatRight, xrightShift, yrightShift)), axis=1).transpose()
                widgetZernikeMask = widgetZernikeMask.astype(np.uint8)
        
                self._widget.matrixZernike = widgetZernikeMask
                self._widget.imgZernike.setImage(self._widget.matrixZernike)
                self.maskZernike = self._widget.matrixZernike

            else:
                projectImageLeft += self.ZernikeAllMasksSumFloatLeft
                projectImageRight += self.ZernikeAllMasksSumFloatRight

                widgetZernikeMask = np.concatenate((self.ZernikeAllMasksSumFloatLeft, self.ZernikeAllMasksSumFloatRight), axis=1).transpose()
                widgetZernikeMask = widgetZernikeMask.astype(np.uint8)
        
                self._widget.matrixZernike = widgetZernikeMask
                self._widget.imgZernike.setImage(self._widget.matrixZernike)
                self.maskZernike = self._widget.matrixZernike

        if (projCenter == 2):
            self.createCenterMask()
            if (xleftShift != 0) or (yleftShift != 0) or (xrightShift != 0) or (yrightShift != 0):
                projectImageLeft += self.shiftMaskZeroPad(self.centerMaskLeft, xleftShift, yleftShift)
                projectImageRight += self.shiftMaskZeroPad(self.centerMaskRight, xrightShift, yrightShift)
            else:
                projectImageLeft += self.centerMaskLeft
                projectImageRight += self.centerMaskRight


        projImg = np.concatenate((projectImageLeft,projectImageRight), axis=1).transpose()
        projImg = projImg.astype(np.uint8)

        if self.slmActive:
            self.slm25DManager.projectMask(self.reshapeMask(projImg))

        else:
            pass
            print('No masks projected')
        
        

    def getCurrentCenters(self):
        valueList = []
        wantedParams = ["Left Center-X","Left Center-Y", "Right Center-X", "Right Center-Y"]
        for index in self._widget.paramNames:
            if index in wantedParams:
                name = 'AbsPosEdit' + index
                widgetObject = self._widget.pars[name]
                valueList.append(self.axisValTypes[index](widgetObject.text()))

        return valueList[0], valueList[1], valueList[2], valueList[3], 

    def createCenterMask(self):
        #xLeft, yLeft, xRight, yRight = self.getCurrentCenters()

        xLeft = int(self._widget.valueDict25D["Left Center-X"])
        yLeft = int(self._widget.valueDict25D["Left Center-Y"])
        xRight = int(self._widget.valueDict25D["Right Center-X"])
        yRight = int(self._widget.valueDict25D["Right Center-Y"])


        # SLM screen size parameters
        numberXpix = 1920
        numberYpix = 1080
        pszSLM = 0.000008 # (in m, 8 um) pixel size
        rhoPupilAperture = self.getAllWidgetParams()['Beam Diameter']  # Adjust manually for calibration to the beam center (rho = 3 is normal for operational microscope)
        rhoPupilAperturePix = rhoPupilAperture/pszSLM
        
        # ====================================================================================================================================
        y_coordsleft, x_coordsleft = np.indices((numberYpix, numberXpix//2))
        y_coordsright, x_coordsright = np.indices((numberYpix, numberXpix//2))
        x_coordsright += 960

        rhomatrixleft = np.sqrt((x_coordsleft - xLeft)**2 + (y_coordsleft - yLeft)**2) / rhoPupilAperturePix
        rhomatrixright = np.sqrt((x_coordsright - xRight)**2 + (y_coordsright - yRight)**2) / rhoPupilAperturePix

        with np.errstate(invalid ='ignore', divide='ignore'):
            thetamatrixleft = np.arctan((x_coordsleft - xLeft) / (y_coordsleft - yLeft))
            thetamatrixleft[np.isnan(thetamatrixleft)] = - np.pi / 2 
            thetamatrixleft[(y_coordsleft - yLeft) < 0] += np.pi
            thetamatrixright = np.arctan((x_coordsright - xRight) / (y_coordsright - yRight))
            thetamatrixright[np.isnan(thetamatrixright)] = - np.pi / 2 
            thetamatrixright[(y_coordsright - yRight) < 0] += np.pi

        
        

        rhomatrix = np.concatenate((rhomatrixleft, rhomatrixright),axis=1)
        thetamatrix = np.concatenate((thetamatrixleft, thetamatrixright),axis=1)
        # ====================================================================================================================================

        #circularMask = np.where(rhomatrix > 0.001, 0, 1)
        stripe_width = 130
        XmatrixLeft = x_coordsleft + stripe_width//2 - xLeft
        XmatrixRight =  x_coordsright + stripe_width//2 - xRight
        stripe_maskLeft = XmatrixLeft % stripe_width
        stripe_maskRight = XmatrixRight % stripe_width
        helicalmaskLeft = thetamatrixleft * 255 * 1 / (2.* np.pi)
        helicalmaskRight = thetamatrixright * 255 * 1 / (2.* np.pi)
        self.centerMaskLeft =  (stripe_maskLeft * 255 / stripe_width  + helicalmaskLeft) #* circularMask
        self.centerMaskRight =  (stripe_maskRight * 255 / stripe_width  + helicalmaskRight)
        
        #return np.transpose(finalMask.astype(np.uint8))
    
    def phase_function_fast(self, gamma, psi, rhomatrix):
        return np.cos(2* np.pi * (gamma * (rhomatrix)**4 + psi * (rhomatrix))**2)

    def calculatePhaseMask(self): 

        # Returns Phase mask in shape of 1080x1920 numpy array
        
        # TO DO: connect these input parameters with GUI 
        parameters = self.getAllWidgetParams()

        rho = parameters["Beam Diameter"]
        # xleftcenter = parameters["Left Center-X"]
        # yleftcenter = parameters["Left Center-Y"]
        # xrightcenter = parameters["Right Center-X"]
        # yrightcenter = parameters["Right Center-Y"]
        xleftcenter = int(self._widget.valueDict25D["Left Center-X"])
        yleftcenter = int(self._widget.valueDict25D["Left Center-Y"])
        xrightcenter = int(self._widget.valueDict25D["Right Center-X"])
        yrightcenter = int(self._widget.valueDict25D["Right Center-Y"])
        gamma = parameters["Gamma"]
        psi = parameters["Psi"]


        # SLM screen size parameters
        numberXpix = 1920
        numberYpix = 1080
        pszSLM = 0.000008 # (in m, 8 um) pixel size
        rhoPupilAperture = rho/2  #(in m, 2Rbeam = 6 mm, current estimation)
        rhoPupilAperturePix = rhoPupilAperture/pszSLM
        
        # ====================================================================================================================================
        y_coordsleft, x_coordsleft = np.indices((numberYpix, numberXpix//2))
        y_coordsright, x_coordsright = np.indices((numberYpix, numberXpix//2))
        x_coordsright += 960

        rhomatrixleft = np.sqrt((x_coordsleft - xleftcenter)**2 + (y_coordsleft - yleftcenter)**2) / rhoPupilAperturePix
        rhomatrixright = np.sqrt((x_coordsright - xrightcenter)**2 + (y_coordsright - yrightcenter)**2) / rhoPupilAperturePix

        rhomatrix = np.concatenate((rhomatrixleft, rhomatrixright),axis=1)
        # ====================================================================================================================================

        maskLeft = self.phase_function_fast(gamma, psi, rhomatrixleft) 
        maskRight = self.phase_function_fast(gamma, psi, rhomatrixright) 

        # binarization (to 0 and 255; for 8 bit format)?????  
        self.mask25dbinaryLeft = np.where(maskLeft >= 0, 127, 0)
        self.mask25dbinaryRight = np.where(maskRight >= 0, 127, 0)
        # maskbinary = maskbinary.astype(np.uint8)
        # maskbinary = maskbinary.transpose()

        #return maskbinary
    

    
    def updateZernikePhaseMask(self):

        self.calculateZernikePhaseMask()
        # initial values
        xleftcenter = int(self._widget.valueDict25D["Left Center-X"])
        yleftcenter = int(self._widget.valueDict25D["Left Center-Y"])
        xrightcenter = int(self._widget.valueDict25D["Right Center-X"])
        yrightcenter = int(self._widget.valueDict25D["Right Center-Y"])

        # current values 
        parameters = self.getAllWidgetParams()
        xleftcenterC = parameters["Left Center-X"]
        yleftcenterC = parameters["Left Center-Y"]
        xrightcenterC = parameters["Right Center-X"]
        yrightcenterC = parameters["Right Center-Y"]

        xleftShift = xleftcenterC - xleftcenter
        yleftShift = yleftcenterC - yleftcenter
        xrightShift = xrightcenterC - xrightcenter
        yrightShift = yrightcenterC - yrightcenter


        projectImageLeft = np.zeros((1080, 960))
        projectImageRight = np.zeros((1080, 960))

        if (xleftShift != 0) or (yleftShift != 0) or (xrightShift != 0) or (yrightShift != 0):
            projectImageLeft += self.shiftMaskZeroPad(self.ZernikeAllMasksSumFloatLeft, xleftShift, yleftShift)
            projectImageRight += self.shiftMaskZeroPad(self.ZernikeAllMasksSumFloatRight, xrightShift, yrightShift)
        else:
            projectImageLeft += self.ZernikeAllMasksSumFloatLeft
            projectImageRight += self.ZernikeAllMasksSumFloatRight

        projImg = np.concatenate((projectImageLeft,projectImageRight), axis=1).transpose()
        projImg = projImg.astype(np.uint8)
        
        self._widget.matrixZernike = projImg
        self._widget.imgZernike.setImage(self._widget.matrixZernike, levels=(0,255))
        # self._widget.vbZernike.addItem(self._widget.imgZernike)
        # self._widget.vbZernike.setAspectLocked(True)

    def recalculateZernikePhaseMask(self):
        self.calculateNewZernikePhaseMask()
        # initial values
        xleftcenter = int(self._widget.valueDict25D["Left Center-X"])
        yleftcenter = int(self._widget.valueDict25D["Left Center-Y"])
        xrightcenter = int(self._widget.valueDict25D["Right Center-X"])
        yrightcenter = int(self._widget.valueDict25D["Right Center-Y"])

        # current values 
        parameters = self.getAllWidgetParams()
        xleftcenterC = parameters["Left Center-X"]
        yleftcenterC = parameters["Left Center-Y"]
        xrightcenterC = parameters["Right Center-X"]
        yrightcenterC = parameters["Right Center-Y"]

        xleftShift = xleftcenterC - xleftcenter
        yleftShift = yleftcenterC - yleftcenter
        xrightShift = xrightcenterC - xrightcenter
        yrightShift = yrightcenterC - yrightcenter


        projectImageLeft = np.zeros((1080, 960))
        projectImageRight = np.zeros((1080, 960))

        if (xleftShift != 0) or (yleftShift != 0) or (xrightShift != 0) or (yrightShift != 0):
            projectImageLeft += self.shiftMaskZeroPad(self.ZernikeAllMasksSumFloatLeft, xleftShift, yleftShift)
            projectImageRight += self.shiftMaskZeroPad(self.ZernikeAllMasksSumFloatRight, xrightShift, yrightShift)
        else:
            projectImageLeft += self.ZernikeAllMasksSumFloatLeft
            projectImageRight += self.ZernikeAllMasksSumFloatRight

        projImg = np.concatenate((projectImageLeft,projectImageRight), axis=1).transpose()
        projImg = projImg.astype(np.uint8)
        
        self._widget.matrixZernike = projImg
        self._widget.imgZernike.setImage(self._widget.matrixZernike, levels=(0,255))
        # self._widget.vbZernike.addItem(self._widget.imgZernike)
        # self._widget.vbZernike.setAspectLocked(True)

    def createFullZernList1stLoop(self):
        tempZernList = []
        self.autoZernCalibValuesDict = {}
        testValues = [-1., -0.6, -0.2, 0., 0.2, 0.6, 1.]
        testValues = [-0.7, -0.6, -0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        testValues = [-1., 1.] # fast for test runs
        

        for name in ['(2,-2)', '(2,2)']: # this loop makes astigmatisms the first 2 abberations in AZ loop
            for side in self._widget.ZernikeSides:   
                current = self._widget.pars['AbsPosEdit' + name + side].value()
                testValues = np.linspace(current - 1.2, current + 1.2, 25) #!!! Might be a probleem in future => look at startAutoZern
                self.autoZernCalibValuesDict[name + side] = testValues
                for testValue in testValues:
                    tempZernList.append(('AbsPosEdit' + name + side,testValue))

        for name in self._widget.ZernikeCoefficientNames:
            if name == '(0,0)' or name == '(2,0)':# or name == '(1,-1)' or name == '(1,1)': #!!! test which of those (piston, xtilt, ytilt) u mant to leave out

                pass
            elif name == '(2,-2)' or name == '(2,2)':

                pass
            else:
                for side in self._widget.ZernikeSides:   
                    current = self._widget.pars['AbsPosEdit' + name + side].value()
                    testValues = np.linspace(current-0.7, current+0.7, 15) #!!! Might be a probleem in future => look at startAutoZern
                    self.autoZernCalibValuesDict[name + side] = testValues
                    for testValue in testValues:
                        tempZernList.append(('AbsPosEdit' + name + side,round(testValue, 3)))
        
        return tempZernList
    
    
    # def createFullZernListFinerLoop(self):
    #     # this version takes curent value
    #     tempZernList = []
    #     self.autoZernCalibValuesDict = {}
    #     for name in self._widget.ZernikeCoefficientNames:
    #         if name == '(0,0)' or name == '(1,-1)' or name == '(1,1)': #!!! test which of those (piston, xtilt, ytilt) u mant to leave out
    #             pass
    #         else:
    #             for side in self._widget.ZernikeSides:   
    #                 current = self._widget.pars['AbsPosEdit' + name + side].value()
    #                 testValues = np.linspace(current-0.5, current+0.5, 11) #!!! Might be a probleem in future => look at startAutoZern
    #                 self.autoZernCalibValuesDict[name + side] = testValues
    #                 for testValue in testValues:
    #                     tempZernList.append(('AbsPosEdit' + name + side,testValue))
        
    #     return tempZernList
    

    # def setAutoZern(self, rep):
    #     try:
    #         self._widget.pars[self.fullZernList[rep][0]].setValue(self.fullZernList[rep][1])
    #         print('set '+str(rep))
    #     except IndexError:
    #         pass

    def setAutoZern(self, rep):
        self._widget.pars[self.fullZernList[rep][0]].setValue(self.fullZernList[rep][1])
        print('set ' + str(rep))


    def setOptimalZern(self, rep, optimalValue):
        self._widget.pars[self.fullZernList[rep][0]].setValue(optimalValue)

    def startAutoZern(self):
        self.fullZernList = self.createFullZernList1stLoop()
        numAZAlltestPoints = len(self.fullZernList)
        self._commChannel.autoZernCalibValuesDict = self.autoZernCalibValuesDict
        numAZTestValuesPerZernCoeff = len(self.autoZernCalibValuesDict["(4,0)" + "Left"]) # !!!refers to the last value (Spherical, right), assumes all parameters will have the same number of test values
        self._commChannel.numAZAlltestPoints = numAZAlltestPoints
        self._commChannel.numAZTestValuesPerZernCoeff = numAZTestValuesPerZernCoeff
        self.numAZAlltestPoints = numAZAlltestPoints
        self.numAZTestValuesPerZernCoeff = numAZTestValuesPerZernCoeff
        # time.sleep(0.1) # makes sure this last signal is executed before countiniouing
        print("AZ signal called properly")

    def startAutoZernFinerLoop(self):
        self.fullZernList = self.createFullZernListFinerLoop()
        numAZAlltestPoints = len(self.fullZernList)
        self._commChannel.autoZernCalibValuesDict = self.autoZernCalibValuesDict
        numAZTestValuesPerZernCoeff = len(self.autoZernCalibValuesDict["(4,0)" + "Left"]) # !!!refers to the last value (Spherical, right), assumes all parameters will have the same number of test values
        self._commChannel.numAZAlltestPoints = numAZAlltestPoints
        self._commChannel.numAZTestValuesPerZernCoeff = numAZTestValuesPerZernCoeff
        print("AZ signal called properly")


    # def autoZernikeThread(self):
    #     threading.Thread(target=self.autoZernike, args=(), daemon=True).start()

    # def calcAutoZern(self, rep):

    #     image = self._commChannel.lastImgDict[640]
    #     print('scored '+str(rep))
    #     # self.evaluateImageQuality(image)  # set image quality metric here
































    def loadZernSettings(self, moduleDict):
        try:
            loadBool = moduleDict['zernike']
        except KeyError:
            loadBool = 0
        if loadBool:
            params = self._commChannel.loadedSettings["Zernike SLM Parameters"]

            for i in range(len(self._widget.elementListZern)):
                if self._widget.elementListZern[i]._side == 'Left':
                    leftParams = params['Left']
                    self._widget.elementListZern[i].setValue(float(leftParams[self._widget.elementListZern[i]._name]))
                    
                if self._widget.elementListZern[i]._side == 'Right':
                    rightParams = params['Right']
                    self._widget.elementListZern[i].setValue(float(rightParams[self._widget.elementListZern[i]._name]))


    def load25DSettings(self, moduleDict):
        try:
            loadBool = moduleDict['parameters25D']
        except KeyError:
            loadBool = 0
        if loadBool:
            params = self._commChannel.loadedSettings["25D SLM Parameters"]

            for i in range(len(self._widget.elementList25D)):
                if self._widget.elementList25D[i]._type == 'str':
                    self._widget.elementList25D[i].setText(params[self._widget.elementList25D[i]._name])




    def valueChanged25D(self, attrCategory, parameterName, value):
        self.setSharedAttr25D(attrCategory, parameterName, value)

    def setSharedAttr25D(self, attrCategory, parameterName, value):
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

    def valueChangedZern(self, attrCategory, subCategory, parameterName, value):
        self.setSharedAttrZern(attrCategory, subCategory, parameterName, value)

    def setSharedAttrZern(self, attrCategory, subCategory, parameterName, value):
        """Sending attribute to shared attributes

        Args:
            parameterName (str): name of a parameter passed from wdiget
            attr (_type_): type of a attribute (value, enabled, ...)
            value (_type_): value of the parameter read from wdiget
        """
        self.settingAttr = True
        try:
            self._commChannel.sharedAttrs[(attrCategory, subCategory, parameterName)] = value
        finally:
            self.settingAttr = False


































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