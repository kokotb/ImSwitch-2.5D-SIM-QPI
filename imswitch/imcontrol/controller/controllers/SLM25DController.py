import json
import os
import threading
import numpy as np
import matplotlib.pyplot as plt

from imswitch.imcommon.model import dirtools, initLogger
from imswitch.imcontrol.model.managers.SLM25DManager import MaskMode, Direction
from ..basecontrollers import ImConWidgetController
import zernpol

from PIL import Image, ImageDraw
import pyqtgraph as pg

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
        # self._widget.start25D.toggled.connect(self._commChannel.sig25DAcqToggled.emit())
        # self._widget.start25D.toggled.connect(lambda value: self._commChannel.sig25DAcqToggled.emit(value))


        # Connect CommunicationChannel signals
        # self._commChannel.sigSLMMaskUpdated.connect(lambda mask: self.displayMask(mask))
        self._commChannel.sigSetAutoZern.connect(self.setAutoZern)
        self._commChannel.sigStartAutoZern.connect(self.startAutoZern)
        self._commChannel.sigStartAutoZernFinerLoop.connect(self.startAutoZernFinerLoop)
        self._commChannel.sigSetOptimalZern.connect(self.setOptimalZern)
        # self._commChannel.sigAutoZernCalc.connect(self.calcAutoZern)
        self._commChannel.sigToggleAutoZern.connect(self.toggleAutoZern)

        self.matrix25d = self._widget.matrix25d

        # {(order) : (min, max), ..... }:
        self.zernikeNormalizationDict = {(0, 0): (1.0, 1.0), (1, -1): (-1.9968000000000001, 1.9968000000000001), (1, 1): (-1.9968000000000001, 1.9968), (2, -2): (-2.4390490377035388, 2.4390490377035388),
          (2, 0): (-1.7320508075688772, 1.7319000498665866), (2, 2): (-2.441657646300013, 2.441657646300013), (3, -3): (-2.826475232346454, 2.826475232346454),
            (3, -1): (-2.8218846978382803, 2.8218846978382803), (3, 1): (-2.8218846978382803, 2.8218846978382803), (3, 3): (-2.826475232346454, 2.826475232346454),
             (4, -4): (-3.1570215166935713, 3.1570215166935713), (4, -2): (-3.130426605396449, 3.130426605396449), (4, 0): (-1.1180339823972583, 2.23606797749979),
               (4, 2): (-3.13981519001373, 3.13981519001373), (4, 4): (-3.1353128402711548, 3.1420876039381285)}
        
        self._widget.start25D.clicked.connect(self._commChannel.sig25DAcqToggled.emit)
        self._widget.updateCenterMask.connect(self.updateAll)
        self._widget.sigStepUpCenterClicked.connect(self.updateAll)
        self._widget.sigStepDownCenterClicked.connect(self.updateAll)

        self._widget.update25DMask.connect(self.updatePhaseMask)
        self._widget.sigStepUp25DMask.connect(self.updatePhaseMask)
        self._widget.sigStepDown25DMask.connect(self.updatePhaseMask)
    
        self._widget.sigUpdateZernikeMask.connect(self.updateZernike)
        self._widget.sigStepUpZernikeLeft.connect(self.updateZernike)
        self._widget.sigStepDownZernikeLeft.connect(self.updateZernike)
        self._widget.sigStepUpZernikeRight.connect(self.updateZernike)
        self._widget.sigStepDownZernikeRight.connect(self.updateZernike)
        # self._widget.autoZernCheckbox.clicked.connect(self.autoZernikeThread)

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
        self._widget.stop25D.clicked.connect(self._commChannel.sigStop25D.emit)
        # self._commChannel.sig25DAcqToggled.connect(self._widget.toggled25D)
        # self._widget.stop25D

        #self._widget.autoZernCheckbox2.stateChanged.connect(self.combineAndProject)
        self.mask25D = np.zeros((1920, 1080))
        self.centerMask = np.zeros((1920, 1080))
        self.zernikeParametersOld = self.getAllZernikeParams()
        self.init25DWidgetValues()

        self.updateAll() #This line is needed to initialize a 2.5D mask. This helps with later calculation. Leave it here.
        self.fullZernList = self.createFullZernList1stLoop()
        
    def toggleAutoZern(self, state):
        self._widget.autoZernCheckbox.setChecked(state)


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
            

    def updateZernike(self):
        self.updateZernikePhaseMask()
        self.combineAndProject()

    def updateAll(self):
        self.updatePhaseMask(False) # False tell this function to not combineAndProject, as that is handled 2 lines later.
        self.recalculateZernikePhaseMask()
        self.combineAndProject()

    def updatePhaseMask(self , recalc = True):
        self._widget.matrix25d = self.calculatePhaseMask()
        
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

        draw = ImageDraw.Draw(im)
        draw.ellipse([llx, bly, rlx, toply], fill=(255, 0, 0))
        draw.ellipse([lrx, bry, rrx, topry], fill=(255, 0, 0))
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
        xleftcenter = parameters["Left Center-X"]
        yleftcenter = parameters["Left Center-Y"]
        xrightcenter = parameters["Right Center-X"]
        yrightcenter = parameters["Right Center-Y"]

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
                            self.ZernikeAllMasksSumFloatLeft = zernikeLeft * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) *256
                        else:
                            zernikeLeft = zernpol.Zernpol.func_cart(order, xleftnormalized, yleftnormalized, masked=False)
                            zernikeLeft = (zernikeLeft-self.zernikeNormalizationDict[order][0])/(self.zernikeNormalizationDict[order][1]-self.zernikeNormalizationDict[order][0])
                            self.ZernikeAllMasksSumFloatLeft = zernikeLeft * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) * 256
                            
                    elif side == "Right":
                        # if name == '(0,0)':
                        if order == (0,0):
                            zernikeRight = zernpol.Zernpol.func_cart(order, xrightnormalized, yrightnormalized, masked=False)
                            self.ZernikeAllMasksSumFloatRight = zernikeRight * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) * 256
                        else:
                            zernikeRight = zernpol.Zernpol.func_cart(order, xrightnormalized, yrightnormalized, masked=False)
                            zernikeRight = (zernikeRight-self.zernikeNormalizationDict[order][0])/(self.zernikeNormalizationDict[order][1]-self.zernikeNormalizationDict[order][0])
                            self.ZernikeAllMasksSumFloatRight = zernikeRight * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) * 256
                            
                            
                if side == 'Left':
                    zernikeMaskupdate = np.concatenate((self.ZernikeAllMasksSumFloatLeft, np.zeros((1080, 960))), axis=1)
                elif side == 'Right':
                    zernikeMaskupdate = np.concatenate(( np.zeros((1080, 960)), self.ZernikeAllMasksSumFloatRight), axis=1)
                # zernikeMaskupdate = np.concatenate((self.ZernikeAllMasksSumFloatLeft, self.ZernikeAllMasksSumFloatRight), axis=1)
                self.zernikeMask = zernikeMaskupdate.transpose()
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
        xleftcenter = parameters["Left Center-X"]
        yleftcenter = parameters["Left Center-Y"]
        xrightcenter = parameters["Right Center-X"]
        yrightcenter = parameters["Right Center-Y"]

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
    
    def combineAndProject(self):
        projZernike = self._widget.projectZernike.checkState()
        proj25D = self._widget.project25D.checkState()
        projCenter = self._widget.projectCenter.checkState()

        if (projZernike == 2) and (proj25D == 2):
            #if ((self._widget.matrixZernike == 0).all()):
                #self._widget.matrixZernike = np.ones((1920, 1080))
            projImg = self.mask25D + self._widget.matrixZernike 

            if self.slmActive:
                self.slm25DManager.projectMask(self.reshapeMask(projImg))

        elif (projZernike == 2) and (proj25D == 0):
            #if ((self._widget.matrixZernike == 0).all()):
                #self._widget.matrixZernike = np.ones((1920, 1080))
            projImg = self._widget.matrixZernike
            if self.slmActive:
                self.slm25DManager.projectMask(self.reshapeMask(projImg))

        elif (projZernike == 0) and (proj25D == 2):
            projImg = self.mask25D
            if self.slmActive:
                self.slm25DManager.projectMask(self.reshapeMask(projImg))

        elif (projZernike == 0) and (proj25D == 0) and (projCenter == 0):
            projImg = np.zeros((1920, 1080))
            if self.slmActive:
                self.slm25DManager.projectMask(self.reshapeMask(projImg))

        elif (projCenter == 2): # always center mask only!
            self.centerMask = self.createCenterMask()
            projImg = self.centerMask
            if self.slmActive:
                self.slm25DManager.projectMask(self.reshapeMask(np.transpose(projImg)))

        else:
            print('Center mask can be projected alone only')
        
        

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
        xLeft, yLeft, xRight, yRight = self.getCurrentCenters()

        # SLM screen size parameters
        numberXpix = 1920
        numberYpix = 1080
        pszSLM = 0.000008 # (in m, 8 um) pixel size
        rhoPupilAperture = 3.  # Adjust manually for calibration to the beam center (rho = 3 is normal for operational microscope)
        rhoPupilAperturePix = rhoPupilAperture/pszSLM
        
        # ====================================================================================================================================
        y_coordsleft, x_coordsleft = np.indices((numberYpix, numberXpix//2))
        y_coordsright, x_coordsright = np.indices((numberYpix, numberXpix//2))
        x_coordsright += 960

        rhomatrixleft = np.sqrt((x_coordsleft - xLeft)**2 + (y_coordsleft - yLeft)**2) / rhoPupilAperturePix
        rhomatrixright = np.sqrt((x_coordsright - xRight)**2 + (y_coordsright - yRight)**2) / rhoPupilAperturePix

        rhomatrix = np.concatenate((rhomatrixleft, rhomatrixright),axis=1)
        # ====================================================================================================================================

        circularMask = np.where(rhomatrix > 0.001, 0, 1)
        Xmatrix = np.concatenate((x_coordsleft, x_coordsright),axis=1)
        stripe_width = 50
        stripe_mask = Xmatrix % stripe_width
        finalMask = circularMask * stripe_mask * 255 / stripe_width
        
        return finalMask.astype(np.uint8)
    
    def phase_function_fast(self, gamma, psi, rhomatrix):
        return np.cos(2* np.pi * (gamma * (rhomatrix)**4 + psi * (rhomatrix))**2)

    def calculatePhaseMask(self): 

        # Returns Phase mask in shape of 1080x1920 numpy array
        
        # TO DO: connect these input parameters with GUI 
        parameters = self.getAllWidgetParams()

        rho = parameters["Beam Diameter"]
        xleftcenter = parameters["Left Center-X"]
        yleftcenter = parameters["Left Center-Y"]
        xrightcenter = parameters["Right Center-X"]
        yrightcenter = parameters["Right Center-Y"]
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

        mask = self.phase_function_fast(gamma, psi, rhomatrix) 

        # binarization (to 0 and 255; for 8 bit format)?????  
        maskbinary = np.where(mask >= 0, 127, 0)
        maskbinary = maskbinary.astype(np.uint8)
        maskbinary = maskbinary.transpose()

        return maskbinary
    

    
    def updateZernikePhaseMask(self):
        self._widget.matrixZernike = self.calculateZernikePhaseMask()
        self._widget.imgZernike.setImage(self._widget.matrixZernike, levels=(0,255))
        # self._widget.vbZernike.addItem(self._widget.imgZernike)
        # self._widget.vbZernike.setAspectLocked(True)

    def recalculateZernikePhaseMask(self):
        self._widget.matrixZernike = self.calculateNewZernikePhaseMask()
        self._widget.imgZernike.setImage(self._widget.matrixZernike, levels=(0,255))
        # self._widget.vbZernike.addItem(self._widget.imgZernike)
        # self._widget.vbZernike.setAspectLocked(True)

    def createFullZernList1stLoop(self):
        tempZernList = []
        self.autoZernCalibValuesDict = {}
        testValues = [-1., -0.6, -0.2, 0., 0.2, 0.6, 1.]
        for name in self._widget.ZernikeCoefficientNames:
            if name == '(0,0)':# or name == '(1,-1)' or name == '(1,1)': #!!! test which of those (piston, xtilt, ytilt) u mant to leave out
                pass
            else:
                for side in self._widget.ZernikeSides:
                    self.autoZernCalibValuesDict[name + side] = testValues        
                    for testValue in testValues:
                        tempZernList.append(('AbsPosEdit' + name + side,testValue))
        
        return tempZernList
    
    def createFullZernListFinerLoop(self):
        # this version takes curent value
        tempZernList = []
        self.autoZernCalibValuesDict = {}
        for name in self._widget.ZernikeCoefficientNames:
            if name == '(0,0)':# or name == '(1,-1)' or name == '(1,1)': #!!! test which of those (piston, xtilt, ytilt) u mant to leave out
                pass
            else:
                for side in self._widget.ZernikeSides:   
                    current = self._widget.pars['AbsPosEdit' + name + side].value()
                    testValues = np.linspace(current-0.5, current+0.5, 11) #!!! Might be a probleem in future => look at startAutoZern
                    self.autoZernCalibValuesDict[name + side] = testValues
                    for testValue in testValues:
                        tempZernList.append(('AbsPosEdit' + name + side,testValue))
        
        return tempZernList
    

    # def setAutoZern(self, rep):
    #     try:
    #         self._widget.pars[self.fullZernList[rep][0]].setValue(self.fullZernList[rep][1])
    #         print('set '+str(rep))
    #     except IndexError:
    #         pass

    def setAutoZern(self, rep):
        self._widget.pars[self.fullZernList[rep][0]].setValue(self.fullZernList[rep][1])
        print('set '+str(rep))


    def setOptimalZern(self, rep, optimalValue):
        self._widget.pars[self.fullZernList[rep][0]].setValue(optimalValue)

    def startAutoZern(self):
        self.fullZernList = self.createFullZernList1stLoop()
        numAZtestPoints = len(self.fullZernList)
        self._commChannel.autoZernCalibValuesDict = self.autoZernCalibValuesDict
        numTestValues = len(self.autoZernCalibValuesDict["(4,0)" + "Left"]) # !!!refers to the last value (Spherical, right), assumes all parameters will have the same number of test values
        self._commChannel.sigSendAutoZernListLen.emit(numAZtestPoints, numTestValues)
        time.sleep(0.1) # makes sure this last signal is executed before countiniouing
        print("AZ signal called properly")

    def startAutoZernFinerLoop(self):
        self.fullZernList = self.createFullZernListFinerLoop()
        numAZtestPoints = len(self.fullZernList)
        self._commChannel.autoZernCalibValuesDict = self.autoZernCalibValuesDict
        numTestValues = len(self.autoZernCalibValuesDict["(4,0)" + "Left"]) # !!!refers to the last value (Spherical, right), assumes all parameters will have the same number of test values
        self._commChannel.sigSendAutoZernListLen.emit(numAZtestPoints, numTestValues)
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