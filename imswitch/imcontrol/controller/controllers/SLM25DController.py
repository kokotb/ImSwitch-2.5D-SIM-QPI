import json
import os

import numpy as np
import matplotlib.pyplot as plt

from imswitch.imcommon.model import dirtools, initLogger
from imswitch.imcontrol.model.managers.SLM25DManager import MaskMode, Direction
from ..basecontrollers import ImConWidgetController
import zernpol


class SLM25DController(ImConWidgetController):
    """Linked to SLM25DWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)
        # self.pars = self._widget.pars
        # self.axes = self._widget.axes
        self.axisValTypes = self._widget.axisValTypes
        self.paramNames = self._widget.paramNames
        if self._setupInfo.SLM25D is None:
            self._widget.replaceWithError('SLM is not configured in your setup file.')
            return

        self.zernikeParametersOld = self.getAllZernikeParams()
        self.ZernikeAllMasksSumFloat = np.zeros((1920,1080))

        # Connect CommunicationChannel signals
        self._commChannel.sigSLMMaskUpdated.connect(lambda mask: self.displayMask(mask))
        self.Params = self.getAllWidgetParams()
        self.matrix25d = self._widget.matrix25d
            
        self._widget.updateMask.connect(self.updateCenterPhaseMask)
        self._widget.sigStepUpClicked.connect(self.updateCenterPhaseMask)
        self._widget.sigStepDownClicked.connect(self.updateCenterPhaseMask)

        self._widget.updateMask.connect(self.updatePhaseMask)
        self._widget.sigStepUpClicked.connect(self.updatePhaseMask)
        self._widget.sigStepDownClicked.connect(self.updatePhaseMask)

        self._widget.updateMaskZernike.connect(self.updateZernikePhaseMask)
        self._widget.sigStepUpClickedZernike.connect(self.updateZernikePhaseMask)
        self._widget.sigStepDownClickedZernike.connect(self.updateZernikePhaseMask)

        self._widget.updateMaskZernike.connect(self.projectZernike)
        self._widget.sigStepUpClickedZernike.connect(self.projectZernike)
        self._widget.sigStepDownClickedZernike.connect(self.projectZernike)

        self._widget.updateMask.connect(self.recalculateZernikePhaseMask)
        self._widget.sigStepUpClicked.connect(self.recalculateZernikePhaseMask)
        self._widget.sigStepDownClicked.connect(self.recalculateZernikePhaseMask)

        self.zPositioner = self._master.positionersManager._subManagers['Z']
        self._widget.sigDisplayZernike.connect(self.projectZernike)
        self.slm25DManager = self._master.slm25DManager


        # self.zPositioner.setPosition(SETVALUE, ['Z'])
        # currentPos = self.zPositioner.get_abs()

    def projectZernike(self, _):
        self.slm25DManager.projectMask(self.reshapeMask(self.ZernikeAllMasksSum))


    def reshapeMask(self, mask):
        maskFlipped = np.fliplr(mask)
        maskReshaped = np.reshape(maskFlipped,(1080, 1920), order='F')
        # maskFlipped = np.flipud(maskReshaped)

        return maskReshaped

    def getAllWidgetParams(self):

        valueList = {}
        for axis in self._widget.paramNames:
            name = 'AbsPosEdit' + axis
            widgetObject = self._widget.pars[name]
            valueList[axis] = self.axisValTypes[axis](widgetObject.text())

        # final = list(zip(self._widget.axes,valueList))
        # print(valueList)
        return valueList
    
    def getAllZernikeParams(self):

        valueList = {}
        for axis in self._widget.ZernikeCoefficientNames:
            name = 'AbsPosEdit' + axis
            widgetObject = self._widget.pars[name]
            valueList[axis] = self.axisValTypes[axis](widgetObject.text())

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
        zernikeParametersDifferences = {key: (self.zernikeParametersOld[key], zernikeParametersNew[key]) for key in self.zernikeParametersOld if self.zernikeParametersOld[key] != zernikeParametersNew[key]}
        # zernikeParametersDifferences = {"(0.,0.)": (old_value, new_value)}
        for name in zernikeParametersDifferences:
            order = eval(name)

            zernikeLeft = zernpol.Zernpol.func_cart(order, xleftnormalized, yleftnormalized)
            zernikeRight = zernpol.Zernpol.func_cart(order, xrightnormalized, yrightnormalized)
            zernikeMask = np.concatenate((zernikeLeft, zernikeRight), axis=1)
            zernikeMask[np.isnan(zernikeMask)] = 0

            # Normalize and transpose
            zernikeMask = (zernikeMask-np.min(zernikeMask))/(np.max(zernikeMask)-np.min(zernikeMask))
            zernikeMask = zernikeMask.transpose()

            # add to mask
            self.ZernikeAllMasksSumFloat += zernikeMask * (zernikeParametersNew[name] - self.zernikeParametersOld[name]) * 255

        self.ZernikeAllMasksSum = self.ZernikeAllMasksSumFloat.astype(np.uint8) % 255
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
        self.ZernikeAllMasksSumFloat = np.zeros((1920,1080))
        for name in zernikeParametersNew:
            order = eval(name)

            zernikeLeft = zernpol.Zernpol.func_cart(order, xleftnormalized, yleftnormalized)
            zernikeRight = zernpol.Zernpol.func_cart(order, xrightnormalized, yrightnormalized)
            zernikeMask = np.concatenate((zernikeLeft, zernikeRight), axis=1)
            zernikeMask[np.isnan(zernikeMask)] = 0

            # Normalize and transpose
            zernikeMask = (zernikeMask-np.min(zernikeMask))/(np.max(zernikeMask)-np.min(zernikeMask))
            zernikeMask = zernikeMask.transpose()

            # add to mask
            self.ZernikeAllMasksSumFloat += zernikeMask * zernikeParametersNew[name] * 255

        self.ZernikeAllMasksSum = self.ZernikeAllMasksSumFloat.astype(np.uint8) % 255
        self.zernikeParametersOld = zernikeParametersNew
        return self.ZernikeAllMasksSum


    def calculateCenterPhaseMask(self):
        parameters = self.getAllWidgetParams()
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

        rhomatrixleft = np.sqrt((x_coordsleft - xleftcenter)**2 + (y_coordsleft - yleftcenter)**2) / rhoPupilAperturePix
        rhomatrixright = np.sqrt((x_coordsright - xrightcenter)**2 + (y_coordsright - yrightcenter)**2) / rhoPupilAperturePix

        rhomatrix = np.concatenate((rhomatrixleft, rhomatrixright),axis=1)
        # ====================================================================================================================================

        blurmatrixleft = x_coordsleft + y_coordsleft
        blurmatrixright = x_coordsright + y_coordsright
        blurMask = np.concatenate((blurmatrixleft, blurmatrixright),axis=1)
        blurMask = np.where(blurMask % 2 == 0, 0, 255)
        blurMask = blurMask.astype(np.uint8)
        blurMask = blurMask.transpose()

        maskbinary = np.where(rhomatrix >= 1., 50, 255)
        maskbinary = maskbinary.astype(np.uint8)
        maskbinary = maskbinary.transpose()

        return maskbinary


    
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
        gamma = parameters["gamma"]
        psi = parameters["psi"]

        
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
        maskbinary = np.where(mask >= 0, 0, 255)
        maskbinary = maskbinary.astype(np.uint8)
        maskbinary = maskbinary.transpose()

        return maskbinary
    
    def updatePhaseMask(self):
        self._widget.matrix25d = self.calculatePhaseMask()
        #self._widget.img25d.setImage(self._widget.matrix25d, autoLevels=True, autoDownsample=True, autoRange=True)
        self._widget.img25d.setImage(self._widget.matrix25d, autoLevels=False, autoDownsample=False, autoRange=False)
        self._widget.vb25d.addItem(self._widget.img25d)
        self._widget.vb25d.setAspectLocked(True)
    
    def updateCenterPhaseMask(self):
        self._widget.matrixCenter = self.calculateCenterPhaseMask()
        #self._widget.imgCenter.setImage(self._widget.matrixCenter, autoLevels=True, autoDownsample=True, autoRange=True)
        self._widget.imgCenter.setImage(self._widget.matrixCenter, autoLevels=False, autoDownsample=False, autoRange=False)
        self._widget.vbCenter.addItem(self._widget.imgCenter)
        self._widget.vbCenter.setAspectLocked(True)

    def updateZernikePhaseMask(self):
        self._widget.matrixZernike = self.calculateZernikePhaseMask()
        #self._widget.imgCenter.setImage(self._widget.matrixCenter, autoLevels=True, autoDownsample=True, autoRange=True)
        self._widget.imgZernike.setImage(self._widget.matrixZernike, autoLevels=False, autoDownsample=False, autoRange=False)
        self._widget.vbZernike.addItem(self._widget.imgZernike)
        self._widget.vbZernike.setAspectLocked(True)

    def recalculateZernikePhaseMask(self):
        self._widget.matrixZernike = self.calculateNewZernikePhaseMask()
        #self._widget.imgCenter.setImage(self._widget.matrixCenter, autoLevels=True, autoDownsample=True, autoRange=True)
        self._widget.imgZernike.setImage(self._widget.matrixZernike, autoLevels=False, autoDownsample=False, autoRange=False)
        self._widget.vbZernike.addItem(self._widget.imgZernike)
        self._widget.vbZernike.setAspectLocked(True)

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