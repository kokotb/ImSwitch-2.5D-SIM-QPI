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
    sigToggleSLM = QtCore.Signal(bool)


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

        self.activate25DSLM = QCheckBox('Activate 2.5D SLM')
        self.activate25DSLM.stateChanged.connect(lambda value: self.sigToggleSLM.emit(value))
        self.slmPreview = QPushButton("Preview SLM")
        # self.slmPreview.clicked.connect(self.openSLMPreview)

        self.activate25DSLM.stateChanged.connect(lambda value: self.sigToggleSLM.emit(value))

        # parentLayout = QVBoxLayout()
        self.grid = QtWidgets.QGridLayout()
        self.setLayout(self.grid)
        # self.grid.addWidget(widgetName, row, column, rowspan, columln)
        self.grid.addWidget(self.activate25DSLM,0,0)
        self.grid.addWidget(self.slmPreview, 0, 3)
        self.grid.addWidget(self.slmFrameZernike, 1, 0, 3, 6)
        self.grid.addWidget(self.slmFrameCenter, 19, 0, 3, 6)
        self.grid.addWidget(self.slmFrame25d, 22, 0, 3, 6)



        self.axisValTypes = {"Gamma": float, "Psi": float, "Left Center-X": int, "Left Center-Y": int, "Right Center-X": int, "Right Center-Y": int, "Beam Diameter": float}
        self.pars = {}
        # SETTING PHASE MASK PARAMETERS =========================================================================
        self.numParams = 4
        self.ZernikeCoefficientNames = ["(0,0)", "(1,-1)", "(1,1)", "(2,-2)", "(2,0)", "(2,2)", "(3,-3)", "(3,-1)", "(3,1)", "(3,3)"]
        self.ZernikeAberrationNames = ["Pistion", "Y-tilt", "X-tilt", "Oblique Astigmatism", "Defocus", "Vertical Astigmatism", "Vertical Trefoil", "Vertical Coma", "Horizontal Coma", "Horizontal Trefoil"]
        for i in range(len(self.ZernikeCoefficientNames)):
            self.numParams += 1
            name = self.ZernikeCoefficientNames[i]
            labelNames = f'{self.ZernikeCoefficientNames[i]} - {self.ZernikeAberrationNames[i]}'
            self.axisValTypes[name] = float
            # StepInitialValue = "0.1"
            AbsInitialValue = "0.0"

            label = f'{labelNames}'

            #Define all widget items
            self.pars['Label' + name] = QtWidgets.QLabel(f'<strong>{label}</strong>')
            self.pars['Label' + name].setTextFormat(QtCore.Qt.RichText)
            self.pars['UpButton' + name] = guitools.BetterPushButton('+')
            self.pars['DownButton' + name] = guitools.BetterPushButton('-')
            # self.pars['StepEdit' + name] = QtWidgets.QLineEdit(StepInitialValue)
            # self.pars['StepEdit' + name].setFixedWidth(50)
            self.pars['AbsPosEdit' + name] = QtWidgets.QLineEdit(AbsInitialValue)
            self.pars['AbsPosEdit' + name].setFixedWidth(75)
            

            # Add to widget object
            self.grid.addWidget(self.pars['Label' + name], self.numParams, 0)
            self.grid.addWidget(self.pars['DownButton' + name], self.numParams,1)
            self.grid.addWidget(self.pars['UpButton' + name], self.numParams, 2)
            # self.grid.addWidget(self.pars['StepEdit' + name], self.numParams, 3)
            self.grid.addWidget(self.pars['AbsPosEdit' + name], self.numParams, 4)


            # Connect buttons to signals
            self.pars['UpButton' + name].clicked.connect(lambda *args, name=name: self.sigStepUpClickedZernike.emit(name))
            self.pars['DownButton' + name].clicked.connect(lambda *args, name=name: self.sigStepDownClickedZernike.emit(name))
            self.pars['AbsPosEdit' + name].returnPressed.connect(lambda *args, name=name: self.updateMaskZernike.emit(name))
            self.pars['AbsPosEdit' + name].editingFinished.connect(lambda *args, name=name: self.updateMaskZernike.emit(name))



        # SETTING PHASE MASK PARAMETERS =========================================================================
        self.numParams = 25
        self.paramNames = ["Gamma", "Psi", "Left Center-X","Left Center-Y", "Right Center-X", "Right Center-Y", "Beam Diameter"]
        AbsaxisInitialValues = {"Gamma": "0.5", "Psi": "0.5", "Left Center-X": "480", "Left Center-Y": "540", "Right Center-X": "1440", "Right Center-Y": "540", "Beam Diameter": "0.006"}
        StepaxisInitialValues = {"Gamma": "0.1", "Psi": "0.1", "Left Center-X": "20", "Left Center-Y": "20", "Right Center-X": "20", "Right Center-Y": "20", "Beam Diameter": "0.001"}
        UnitaxisInitialValues = {"Gamma": "-", "Psi": "-", "Left Center-X": "px", "Left Center-Y": "px", "Right Center-X": "px", "Right Center-Y": "px", "Beam Diameter": "mm"}
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
            self.pars['UpButton' + name].setFixedWidth(75)
            self.pars['DownButton' + name] = guitools.BetterPushButton('-')
            self.pars['DownButton' + name].setFixedWidth(75)
            self.pars['StepEdit' + name] = QtWidgets.QLineEdit(StepInitialValue)
            self.pars['StepEdit' + name].setFixedWidth(75)
            self.pars['StepUnit' + name] = QtWidgets.QLabel(self.unit)
            self.pars['AbsPosEdit' + name] = QtWidgets.QLineEdit(AbsInitialValue)
            self.pars['AbsPosEdit' + name].setFixedWidth(75)
            self.pars['AbsPosUnit' + name] = QtWidgets.QLabel(self.unit)

            # Add to widget object
            self.grid.addWidget(self.pars['Label' + name], self.numParams, 0)
            self.grid.addWidget(self.pars['DownButton' + name], self.numParams, 1)
            self.grid.addWidget(self.pars['UpButton' + name], self.numParams, 2)
            self.grid.addWidget(self.pars['StepEdit' + name], self.numParams, 3)
            self.grid.addWidget(self.pars['StepUnit' + name], self.numParams, 4)
            self.grid.addWidget(self.pars['AbsPosEdit' + name], self.numParams, 5)
            self.grid.addWidget(self.pars['AbsPosUnit' + name], self.numParams, 6)

            # Connect buttons to signals
            self.pars['UpButton' + name].clicked.connect(lambda *args, name=name: self.sigStepUpClicked.emit(name))
            self.pars['DownButton' + name].clicked.connect(lambda *args, name=name: self.sigStepDownClicked.emit(name))
            self.pars['AbsPosEdit' + name].returnPressed.connect(lambda *args, name=name: self.updateMaskZernike.emit(name))
            self.pars['AbsPosEdit' + name].editingFinished.connect(lambda *args, name=name: self.updateMaskZernike.emit(name))


        # self.stepLabel = QtWidgets.QLabel(f'<strong>Step</strong>')
        # self.stepLabel.setTextFormat(QtCore.Qt.RichText)
        # self.grid.addWidget(self.stepLabel, 4, 3)

        self.valLabel = QtWidgets.QLabel(f'<strong>Value</strong>')
        self.valLabel.setTextFormat(QtCore.Qt.RichText)
        self.grid.addWidget(self.valLabel, 4, 4)

        # Connect received signals to funcions
        self.sigStepUpClicked.connect(self.increment)
        self.sigStepDownClicked.connect(self.decrement)

        self.sigStepUpClickedZernike.connect(self.incrementZern)
        self.sigStepDownClickedZernike.connect(self.decrementZern)
        

    def increment(self, name):
        stepVal = self.axisValTypes[name](self.pars['StepEdit' + name].text())
        currentVal = self.axisValTypes[name](self.pars['AbsPosEdit' + name].text())
        newVal = str(round(currentVal+stepVal, 4))
        self.pars['AbsPosEdit' + name].setText(newVal)

    def incrementZern(self, name):
        stepVal = 0.1
        currentVal = self.axisValTypes[name](self.pars['AbsPosEdit' + name].text())
        newVal = str(round(currentVal+stepVal, 4))
        self.pars['AbsPosEdit' + name].setText(newVal)
        
    def decrement(self, name):
        stepVal = self.axisValTypes[name](self.pars['StepEdit' + name].text())
        currentVal = self.axisValTypes[name](self.pars['AbsPosEdit' + name].text())
        newVal = str(round(currentVal-stepVal,4))
        self.pars['AbsPosEdit' + name].setText(newVal)

    def decrementZern(self, name):
        stepVal = 0.1
        currentVal = self.axisValTypes[name](self.pars['AbsPosEdit' + name].text())
        newVal = str(round(currentVal-stepVal,4))
        self.pars['AbsPosEdit' + name].setText(newVal)

    # def openSLMPreview(self):
    #     showSLMPreview.showSLMPreview(self.slm, scale=0.0)



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
