import json
import os

import numpy as np
import matplotlib.pyplot as plt

from imswitch.imcommon.model import dirtools, initLogger
from imswitch.imcontrol.model.managers.SLM25DManager import MaskMode, Direction
from ..basecontrollers import ImConWidgetController
import zernpol

from PIL import Image, ImageDraw
import pyqtgraph as pg

import time



class SLM25DController(ImConWidgetController):
    """Linked to SLM25DWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)
        # self.pars = self._widget.pars
        # self.axes = self._widget.axes
        self.slmActive = False
        self.axisValTypes = self._widget.axisValTypes
        self.paramNames = self._widget.paramNames
        if self._setupInfo.SLM25D is None:
            self._widget.replaceWithError('2.5D SLM is not configured in your setup file.')
            return


        self.ZernikeAllMasksSumFloat = np.zeros((1920,1080))

        # Connect CommunicationChannel signals
        # self._commChannel.sigSLMMaskUpdated.connect(lambda mask: self.displayMask(mask))

        self.matrix25d = self._widget.matrix25d
        
    
        self._widget.updateCenterMask.connect(self.updateAll)
        self._widget.sigStepUpCenterClicked.connect(self.updateAll)
        self._widget.sigStepDownCenterClicked.connect(self.updateAll)

        self._widget.update25DMask.connect(self.updatePhaseMask)
        self._widget.sigStepUp25DMask.connect(self.updatePhaseMask)
        self._widget.sigStepDown25DMask.connect(self.updatePhaseMask)
    
        self._widget.updateZernikeMask.connect(self.updateZernike)
        self._widget.sigStepUpZernike.connect(self.updateZernike)
        self._widget.sigStepDownZernike.connect(self.updateZernike)

        self._widget.projectZernike.stateChanged.connect(self.combineAndProject)
        self._widget.project25D.stateChanged.connect(self.combineAndProject)
       
        self.slm25DManager = self._master.slm25DManager

        self._widget.sigToggleSLM.connect(self.toggleSLMFromButton)
        self._widget.sigOpenPreviewButton.connect(self.openPreviewWindow)
        self._widget.sig25DParamChanged.connect(self.valueChanged)
        self._commChannel.sigModuleSettings.connect(self.loadZernSettings)
        self._commChannel.sigModuleSettings.connect(self.load25DSettings)
        self.mask25D = np.zeros((1920, 1080))
        self.zernikeParametersOld = self.getAllZernikeParams()
        self.init25DWidgetValues()

        self.updateAll() #This line is needed to initialize a 2.5D mask. This helps with later calculation. Leave it here.
        

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
            self._widget.pars['AbsPosEdit' + self._widget.ZernikeCoefficientNames[i]].setValue(self._setupInfo.SLM25D.__getattribute__(strippedNames[i]))
            self._widget.valueDictZern25D[self._widget.ZernikeCoefficientNames[i]] = self._setupInfo.SLM25D.__getattribute__(strippedNames[i])
            
        


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
            name = 'AbsPosEdit' + index
            widgetObject = self._widget.pars[name]
            valueList[index] = self.axisValTypes[index](widgetObject.value())

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
        zernikeParametersDifferences = {key: (self.zernikeParametersOld[key], zernikeParametersNew[key]) for key in self.zernikeParametersOld if self.zernikeParametersOld[key] != zernikeParametersNew[key]}
        if not allZeros:
            for name in zernikeParametersDifferences:
                order = eval(name)

                zernikeLeft = zernpol.Zernpol.func_cart(order, xleftnormalized, yleftnormalized, masked=False)
                zernikeRight = zernpol.Zernpol.func_cart(order, xrightnormalized, yrightnormalized, masked=False)
                zernikeMask = np.concatenate((zernikeLeft, zernikeRight), axis=1)
                # if np.nanmin(zernikeMask) == np.nanmax(zernikeMask):
                #     zernikeMask[np.isnan(zernikeMask)] = 0
                # else: 
                #     zernikeMask[np.isnan(zernikeMask)] = np.nanmin(zernikeMask)

                # Normalize and transpose
                if name == '(0,0)':
                     pass
                else:
                    zernikeMask = (zernikeMask-np.min(zernikeMask))/(np.max(zernikeMask)-np.min(zernikeMask)) 
                self.zernikeMask = zernikeMask.transpose()

                # add to mask
                self.ZernikeAllMasksSumFloat += self.zernikeMask * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) * 255
        else:
            self.ZernikeAllMasksSumFloat = np.zeros((1920, 1080))


        self.ZernikeAllMasksSum = self.ZernikeAllMasksSumFloat.astype(np.uint8)
        self.zernikeParametersOld = zernikeParametersNew
        return self.ZernikeAllMasksSum

    def calculateNewZernikePhaseMask(self):
        t0 = time.time()
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
        
        rholeft = np.sqrt(xleftnormalized**2 + yleftnormalized**2)
        phileft = np.arctan2(yleftnormalized, xleftnormalized)
        rhoright = np.sqrt(xrightnormalized**2 + yrightnormalized**2)
        phiright = np.arctan2(yrightnormalized, xrightnormalized)
        
        # ====================================================================================================================================
        zernikeParametersNew = self.getAllZernikeParams()
 


        self.ZernikeAllMasksSumFloat = np.zeros((1920,1080)) #CTNOTE
        for name in zernikeParametersNew:
            order = eval(name)

            zernikeLeft = zernpol.Zernpol.func(order, rholeft, phileft, masked=False)
            zernikeRight = zernpol.Zernpol.func(order, rhoright, phiright, masked=False)
            
            zernikeMask = np.concatenate((zernikeLeft, zernikeRight), axis=1)
            
            # if np.nanmin(zernikeMask) == np.nanmax(zernikeMask):
            #     zernikeMask[np.isnan(zernikeMask)] = 0
            # else: 
            #     zernikeMask[np.isnan(zernikeMask)] = np.nanmin(zernikeMask)


            # Normalize and transpose
            if np.max(zernikeMask) == np.min(zernikeMask):
                pass
            else:
                zernikeMask = (zernikeMask-np.min(zernikeMask))/(np.max(zernikeMask)-np.min(zernikeMask))
            self.zernikeMask = zernikeMask.transpose()

            # add to mask
            self.ZernikeAllMasksSumFloat += self.zernikeMask * zernikeParametersNew[name] * 255

        self.ZernikeAllMasksSum = self.ZernikeAllMasksSumFloat.astype(np.uint8)
        # self.ZernikeAllMasksSumFloat = np.zeros((1920,1080))
        self.zernikeParametersOld = zernikeParametersNew
        t1 = time.time()
        # print("Time to calculate new Zernike = " + str(t1 - t0))
        return self.ZernikeAllMasksSum
    
    def combineAndProject(self):
        projZernike = self._widget.projectZernike.checkState()
        proj25D = self._widget.project25D.checkState()

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

        elif (projZernike == 0) and (proj25D == 0):
            projImg = np.zeros((1920, 1080))
            if self.slmActive:
                self.slm25DManager.projectMask(self.reshapeMask(projImg))
        
        

    def getCurrentCenters(self):
        valueList = []
        wantedParams = ["Left Center-X","Left Center-Y", "Right Center-X", "Right Center-Y"]
        for index in self._widget.paramNames:
            if index in wantedParams:
                name = 'AbsPosEdit' + index
                widgetObject = self._widget.pars[name]
                valueList.append(self.axisValTypes[index](widgetObject.text()))

        return valueList[0], valueList[1], valueList[2], valueList[3], 

    
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
        self._widget.imgZernike.setImage(self._widget.matrixZernike)
        # self._widget.vbZernike.addItem(self._widget.imgZernike)
        # self._widget.vbZernike.setAspectLocked(True)

    def recalculateZernikePhaseMask(self):
        self._widget.matrixZernike = self.calculateNewZernikePhaseMask()
        self._widget.imgZernike.setImage(self._widget.matrixZernike)
        # self._widget.vbZernike.addItem(self._widget.imgZernike)
        # self._widget.vbZernike.setAspectLocked(True)

    def loadZernSettings(self, moduleDict):
        try:
            loadBool = moduleDict['zernike']
        except KeyError:
            loadBool = 0
        if loadBool:
            params = self._commChannel.loadedSettings["Zernike SLM Parameters"]

            for i in range(len(self._widget.elementListZern)):
                if self._widget.elementListZern[i]._type == 'flt':
                    self._widget.elementListZern[i].setValue(float(params[self._widget.elementListZern[i]._name]))


    def load25DSettings(self, moduleDict):
        try:
            loadBool = moduleDict['parameters25D']
        except KeyError:
            loadBool = 0
        if loadBool:
            params = self._commChannel.loadedSettings["25D SLM Parameters"]

            for i in range(len(self._widget.elementListZern)):
                if self._widget.elementListZern[i]._type == 'flt':
                    self._widget.elementListZern[i].setValue(float(params[self._widget.elementListZern[i]._name]))




    def valueChanged(self, attrCategory, parameterName, value):
        self.setSharedAttr(attrCategory, parameterName, value)

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