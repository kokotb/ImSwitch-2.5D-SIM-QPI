import numpy as np
import pyqtgraph as pg
from pyqtgraph.parametertree import ParameterTree
from qtpy import QtCore, QtWidgets
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import *


class SLM25DWidget(Widget):
    """ Widget containing slm interface. """

    sigStepUpClicked = QtCore.Signal(str)
    sigStepDownClicked = QtCore.Signal(str)
    updateMask = QtCore.Signal(str)

    sigStepUpClickedZernike = QtCore.Signal(str)
    sigStepDownClickedZernike = QtCore.Signal(str)
    updateMaskZernike = QtCore.Signal(str)
    sigDisplayZernike = QtCore.Signal()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Zernike mask image
        self.slmFrameZernike = pg.GraphicsLayoutWidget()
        self.vbZernike = self.slmFrameZernike.addViewBox(row=0, col=1)
        self.imgZernike = pg.ImageItem()
        self.matrixZernike = np.ones((1920, 1080)) * 255
        self.imgZernike.setImage(self.matrixZernike, autoLevels=True, autoDownsample=True,
                          autoRange=True)
        self.vbZernike.addItem(self.imgZernike)
        self.vbZernike.setAspectLocked(True)

        # Centering mask image
        self.slmFrameCenter = pg.GraphicsLayoutWidget()
        self.vbCenter = self.slmFrameCenter.addViewBox(row=13, col=1)
        self.imgCenter = pg.ImageItem()
        self.matrixCenter = np.ones((1920, 1080)) * 255
        self.imgCenter.setImage(self.matrixCenter, autoLevels=True, autoDownsample=True,
                          autoRange=True)
        self.vbCenter.addItem(self.imgCenter)
        self.vbCenter.setAspectLocked(True)
        
        # 2.5D mask image
        self.slmFrame25d = pg.GraphicsLayoutWidget()
        self.vb25d = self.slmFrame25d.addViewBox(row=14, col=1)
        self.img25d = pg.ImageItem()
        self.matrix25d = np.ones((1920, 1080)) * 255
        self.img25d.setImage(self.matrix25d, autoLevels=True, autoDownsample=True,
                          autoRange=True)
        self.vb25d.addItem(self.img25d)
        self.vb25d.setAspectLocked(True)


        # parentLayout = QVBoxLayout()
        self.grid = QtWidgets.QGridLayout()
        self.setLayout(self.grid)
        # self.grid.addWidget(widgetName, row, column, rowspan, columln)
        self.grid.addWidget(self.slmFrameZernike, 0, 0, 3, 8)
        self.grid.addWidget(self.slmFrameCenter, 19, 0, 3, 8)
        self.grid.addWidget(self.slmFrame25d, 22, 0, 3, 8)
        

        self.numParams = 25
        self.pars = {}
        # SETTING PHASE MASK PARAMETERS =========================================================================
        self.paramNames = ["gamma", "psi", "Left Center-X","Left Center-Y", "Right Center-X", "Right Center-Y", "Beam Diameter"]
        AbsaxisInitialValues = {"gamma": "0.5", "psi": "0.5", "Left Center-X": "480", "Left Center-Y": "540", "Right Center-X": "1440", "Right Center-Y": "540", "Beam Diameter": "0.006"}
        StepaxisInitialValues = {"gamma": "0.1", "psi": "0.1", "Left Center-X": "20", "Left Center-Y": "20", "Right Center-X": "20", "Right Center-Y": "20", "Beam Diameter": "0.001"}
        self.axisValTypes = {"gamma": float, "psi": float, "Left Center-X": int, "Left Center-Y": int, "Right Center-X": int, "Right Center-Y": int, "Beam Diameter": float}
        UnitaxisInitialValues = {"gamma": "-", "psi": "-", "Left Center-X": "pixels", "Left Center-Y": "pixels", "Right Center-X": "pixels", "Right Center-Y": "pixels", "Beam Diameter": "mm"}
        for i in range(len(self.paramNames)):
            self.numParams += 1
            name = self.paramNames[i]
            StepInitialValue = StepaxisInitialValues[name]
            AbsInitialValue = AbsaxisInitialValues[name]
            self.unit = UnitaxisInitialValues[name]

            label = f'{name}'

            #Define all widget items
            self.pars['Label' + name] = QtWidgets.QLabel(f'<strong>{label}</strong>')
            self.pars['Label' + name].setTextFormat(QtCore.Qt.RichText)
            self.pars['UpButton' + name] = guitools.BetterPushButton('+')
            self.pars['DownButton' + name] = guitools.BetterPushButton('-')
            self.pars['StepEdit' + name] = QtWidgets.QLineEdit(StepInitialValue)
            self.pars['StepUnit' + name] = QtWidgets.QLabel(self.unit)
            self.pars['AbsPos' + name] = QtWidgets.QLabel(f'<strong>Abs. Pos</strong>')
            self.pars['AbsPos' + name].setTextFormat(QtCore.Qt.RichText)
            self.pars['ButtonAbsPosEnter' + name] = guitools.BetterPushButton('Enter')
            self.pars['AbsPosEdit' + name] = QtWidgets.QLineEdit(AbsInitialValue)
            self.pars['AbsPosUnit' + name] = QtWidgets.QLabel(self.unit)

            # Add to widget object
            self.grid.addWidget(self.pars['Label' + name], self.numParams, 0)
            self.grid.addWidget(self.pars['UpButton' + name], self.numParams, 3)
            self.grid.addWidget(self.pars['DownButton' + name], self.numParams, 4)
            self.grid.addWidget(QtWidgets.QLabel('Step'), self.numParams, 5)
            self.grid.addWidget(self.pars['StepEdit' + name], self.numParams, 6)
            self.grid.addWidget(self.pars['StepUnit' + name], self.numParams, 7)
            self.grid.addWidget(self.pars['AbsPos' + name], self.numParams, 8)
            self.grid.addWidget(self.pars['AbsPosEdit' + name], self.numParams, 9)
            self.grid.addWidget(self.pars['AbsPosUnit' + name], self.numParams, 10)
            self.grid.addWidget(self.pars['ButtonAbsPosEnter' + name], self.numParams, 11)


            # Connect buttons to signals
            self.pars['UpButton' + name].clicked.connect(lambda *args, name=name: self.sigStepUpClicked.emit(name))
            self.pars['DownButton' + name].clicked.connect(lambda *args, name=name: self.sigStepDownClicked.emit(name))
            self.pars['ButtonAbsPosEnter' + name].clicked.connect(lambda *args, name=name: self.updateMask.emit(name))

        self.displayButton = guitools.BetterPushButton('Display')
        self.grid.addWidget(self.displayButton, 3, 12)
        self.displayButton.clicked.connect(self.sigDisplayZernike.emit)

        self.numParams = 2
        # SETTING PHASE MASK PARAMETERS =========================================================================
        self.ZernikeCoefficientNames = ["(0,0)", "(1,-1)", "(1,1)", "(2,-2)", "(2,0)", "(2,2)", "(3,-3)", "(3,-1)", "(3,1)", "(3,3)"]
        self.ZernikeAberrationNames = ["Pistion", "Y-tilt", "X-tilt", "Oblique Astigmatism", "Defocus", "Vertical Astigmatism", "Vertical Trefoil", "Vertical Coma", "Horizontal Coma", "Horizontal Trefoil"]
        for i in range(len(self.ZernikeCoefficientNames)):
            self.numParams += 1
            name = self.ZernikeCoefficientNames[i]
            self.axisValTypes[name] = float
            StepInitialValue = "0.1"
            AbsInitialValue = "0."

            label = f'{name}'

            #Define all widget items
            self.pars['Label' + name] = QtWidgets.QLabel(f'<strong>{label}</strong>')
            self.pars['Label' + name].setTextFormat(QtCore.Qt.RichText)
            self.pars['Label' + name].setToolTip(self.ZernikeAberrationNames[i])
            self.pars['UpButton' + name] = guitools.BetterPushButton('+')
            self.pars['DownButton' + name] = guitools.BetterPushButton('-')
            self.pars['StepEdit' + name] = QtWidgets.QLineEdit(StepInitialValue)
            self.pars['AbsPos' + name] = QtWidgets.QLabel(f'<strong>Abs. Pos</strong>')
            self.pars['AbsPos' + name].setTextFormat(QtCore.Qt.RichText)
            self.pars['ButtonAbsPosEnter' + name] = guitools.BetterPushButton('Enter')
            self.pars['AbsPosEdit' + name] = QtWidgets.QLineEdit(AbsInitialValue)

            # Add to widget object
            self.grid.addWidget(self.pars['Label' + name], self.numParams, 0)
            self.grid.addWidget(self.pars['UpButton' + name], self.numParams, 3)
            self.grid.addWidget(self.pars['DownButton' + name], self.numParams, 4)
            self.grid.addWidget(QtWidgets.QLabel('Step'), self.numParams, 5)
            self.grid.addWidget(self.pars['StepEdit' + name], self.numParams, 6)
            self.grid.addWidget(self.pars['AbsPos' + name], self.numParams, 7)
            self.grid.addWidget(self.pars['AbsPosEdit' + name], self.numParams, 8)
            self.grid.addWidget(self.pars['ButtonAbsPosEnter' + name], self.numParams, 10)


            # Connect buttons to signals
            self.pars['UpButton' + name].clicked.connect(lambda *args, name=name: self.sigStepUpClickedZernike.emit(name))
            self.pars['DownButton' + name].clicked.connect(lambda *args, name=name: self.sigStepDownClickedZernike.emit(name))
            self.pars['ButtonAbsPosEnter' + name].clicked.connect(lambda *args, name=name: self.updateMaskZernike.emit(name))
        # Update mask button =====================================================================================
        #self.pars['UpdateMask'] = guitools.BetterPushButton('Update Mask')
        #self.grid.addWidget(self.pars['UpdateMask'], 0, 12)
        #self.pars['UpdateMask'].clicked.connect(lambda *args, name=name: self.updateMask.emit(name))

        # Connect received signals to funcions
        self.sigStepUpClicked.connect(self.increment)
        self.sigStepDownClicked.connect(self.decrement)

        self.sigStepUpClickedZernike.connect(self.increment)
        self.sigStepDownClickedZernike.connect(self.decrement)
        

    def increment(self, name):
        stepVal = self.axisValTypes[name](self.pars['StepEdit' + name].text())
        currentVal = self.axisValTypes[name](self.pars['AbsPosEdit' + name].text())
        newVal = str(round(currentVal+stepVal, 4))
        self.pars['AbsPosEdit' + name].setText(newVal)
        


    def decrement(self, name):
        stepVal = self.axisValTypes[name](self.pars['StepEdit' + name].text())
        currentVal = self.axisValTypes[name](self.pars['AbsPosEdit' + name].text())
        newVal = str(round(currentVal-stepVal,4))
        self.pars['AbsPosEdit' + name].setText(newVal)



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
