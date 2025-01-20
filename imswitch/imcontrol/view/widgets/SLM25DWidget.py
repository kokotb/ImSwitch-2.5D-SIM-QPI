import numpy as np
import pyqtgraph as pg
from pyqtgraph.parametertree import ParameterTree
from qtpy import QtCore, QtWidgets
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QLocale
from PyQt5.QtGui import QWheelEvent , QDoubleValidator, QIntValidator


class SLM25DWidget(Widget):
    """ Widget containing 2.5D SLM interface. """

    sigStepUpClicked = QtCore.Signal(str)
    sigStepDownClicked = QtCore.Signal(str)

    sigStepUpCenterClicked = QtCore.Signal(str)
    sigStepDownCenterClicked = QtCore.Signal(str)

    updateMask = QtCore.Signal(str)
    updateCenterMask = QtCore.Signal(str)

    sigStepUpClickedZernike = QtCore.Signal(str)
    sigStepDownClickedZernike = QtCore.Signal(str)
    updateMaskZernike = QtCore.Signal(str)
    sigCheckValidityAbsPos = QtCore.Signal(str)
    sigCheckValidityStep = QtCore.Signal(str)
    sigResetZern = QtCore.Signal()
    sigReset25D = QtCore.Signal()
    
    # sigDisplayZernike = QtCore.Signal()

    sigToggleSLM = QtCore.Signal(bool)
    sigOpenPreviewButton = QtCore.Signal()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Zernike mask image
        self.slmFrame = pg.GraphicsLayoutWidget()
        self.slmFrame.setEnabled(False)
        self.slmFrame.addLabel('Zernike', angle=-90, row=0, col=0)
        self.vbZernike = self.slmFrame.addViewBox(row=0, col=1, enableMouse=False, border='w', lockAspect=True)
        self.slmFrame.addLabel('2.5D Mask', angle=-90, row=0, col=2)
        self.vb25D = self.slmFrame.addViewBox(row=0, col=3, enableMouse=False, border='w', lockAspect=True)
        self.imgZernike = pg.ImageItem()
        self.img25d = pg.ImageItem()

        self.matrixZernike = np.zeros((1920, 1080))
        self.matrix25d = np.zeros((1920, 1080))

        self.overlayMatrix25D =  np.ones((1920, 1080)) * 255
        self.overlayImg25D = pg.ImageItem(self.overlayMatrix25D, opacity=0.5)



        self.imgZernike.setImage(self.matrixZernike)
        self.img25d.setImage(self.matrix25d)
        
        self.vbZernike.addItem(self.imgZernike)

        self.vb25D.addItem(self.img25d) #This line must before addItem(self.overlayImg25D) so transparent overlay is on top of this layer.
        self.vb25D.addItem(self.overlayImg25D)
        




        self.activate25DSLM = QCheckBox('Activate 2.5D SLM')
        self.activate25DSLM.stateChanged.connect(lambda value: self.sigToggleSLM.emit(value))
    
        self.projectZernike = QCheckBox('Project Zernike')
        self.projectZernike.setChecked(True)
        self.projectZernike.setEnabled(False)

        self.project25D = QCheckBox('Project 2.5D Mask')
        self.project25D.setChecked(True)
        self.project25D.setEnabled(False)

        self.slmPreview = QPushButton("Preview SLM")
        self.slmPreview.setEnabled(False)
        self.slmPreview.clicked.connect(self.sigOpenPreviewButton.emit)
        self.slmPreview.setFixedWidth(250)

        self.resetZern = QPushButton("Reset")
        self.resetZern.setEnabled(False)
        self.resetZern.clicked.connect(self.sigResetZern.emit)

        self.reset25D = QPushButton("Reset")
        self.reset25D.setEnabled(False)
        self.reset25D.clicked.connect(self.sigReset25D.emit)


        # self.activate25DSLM.stateChanged.connect(lambda value: self.sigToggleSLM.emit(value))

        # parentLayout = QVBoxLayout()
        self.grid = QtWidgets.QGridLayout()
        self.setLayout(self.grid)
        # self.grid.addWidget(widgetName, row, column, rowspan, columln)
        self.grid.addWidget(self.activate25DSLM,0,0)
        self.grid.addWidget(self.projectZernike,0,1,1,2)
        self.grid.addWidget(self.project25D,0,3, 1, 2)
        self.grid.addWidget(self.slmPreview, 0, 5)
        self.grid.addWidget(self.slmFrame, 1, 0, 2, 7)
        self.grid.addWidget(self.resetZern, 4, 6)
        self.grid.addWidget(self.reset25D, 16, 6)
        # self.grid.addWidget(self.slmFrameCenter, 19, 0, 3, 6)
        # self.grid.addWidget(self.slmFrame25d, 22, 0, 3, 6)

        self.myframe = QFrame()
        self.myframe.setFrameShape(QFrame.HLine)
        self.myframe.setFrameShadow(QFrame.Plain)
        self.myframe.setLineWidth(200)
        self.grid.addWidget(self.myframe, 3, 0, 1, 7)
        self.myframe2 = QFrame()
        self.myframe2.setFrameShape(QFrame.HLine)
        self.myframe2.setFrameShadow(QFrame.Plain)
        self.myframe2.setLineWidth(200)
        self.grid.addWidget(self.myframe2, 15, 0, 1, 7)



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
            self.pars['Label' + name] = QtWidgets.QLabel(f'{label}')
            self.pars['Label' + name].setTextFormat(QtCore.Qt.RichText)
            self.pars['UpButton' + name] = guitools.BetterPushButton('+')
            self.pars['UpButton' + name].setFixedWidth(100)
            self.pars['DownButton' + name] = guitools.BetterPushButton('-')
            self.pars['DownButton' + name].setFixedWidth(100)
            self.pars['AbsPosEdit' + name] = QtWidgets.QLineEdit(AbsInitialValue)
            self.pars['AbsPosEdit' + name].setFixedWidth(75)

            self.pars['Label' + name].setEnabled(False)
            self.pars['UpButton' + name].setEnabled(False)
            self.pars['DownButton' + name].setEnabled(False)
            self.pars['AbsPosEdit' + name].setEnabled(False)


            self.validator = QDoubleValidator(0.0,10.0,1)
            self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
            self.pars['AbsPosEdit' + name].setValidator(self.validator)

            # self.validator = QDoubleValidator(-5.0,5.0,1)
            # self.pars['AbsPosEdit' + name].setValidator(self.validator)

            
            # Add to widget object
            self.grid.addWidget(self.pars['Label' + name], self.numParams, 0)
            self.grid.addWidget(self.pars['DownButton' + name], self.numParams,1)
            self.grid.addWidget(self.pars['UpButton' + name], self.numParams, 2)
            # self.grid.addWidget(self.pars['StepEdit' + name], self.numParams, 3)
            self.grid.addWidget(self.pars['AbsPosEdit' + name], self.numParams, 5)


            # Connect buttons to signals
            self.pars['UpButton' + name].clicked.connect(lambda *args, name=name: self.sigStepUpClickedZernike.emit(name))
            self.pars['DownButton' + name].clicked.connect(lambda *args, name=name: self.sigStepDownClickedZernike.emit(name))
            # self.pars['AbsPosEdit' + name].returnPressed.connect(lambda *args, name=name: self.updateMaskZernike.emit(name))
            self.pars['AbsPosEdit' + name].editingFinished.connect(lambda *args, name=name: self.updateMaskZernike.emit(name))
            self.pars['AbsPosEdit' + name].textChanged.connect(lambda *args, name=name: self.sigCheckValidityAbsPos.emit(name))



        # SETTING PHASE MASK PARAMETERS =========================================================================
        self.numParams = 16
        self.paramNames = ["Gamma", "Psi", "Left Center-X","Left Center-Y", "Right Center-X", "Right Center-Y", "Beam Diameter"]
        self.absAxisInitialValues = {"Gamma": "0.5", "Psi": "0.5", "Left Center-X": "480", "Left Center-Y": "540", "Right Center-X": "1440", "Right Center-Y": "540", "Beam Diameter": "6.0"}
        self.stepAxisInitialValues = {"Gamma": "0.1", "Psi": "0.1", "Left Center-X": "20", "Left Center-Y": "20", "Right Center-X": "20", "Right Center-Y": "20", "Beam Diameter": "0.5"}
        UnitaxisInitialValues = {"Gamma": "-", "Psi": "-", "Left Center-X": "px", "Left Center-Y": "px", "Right Center-X": "px", "Right Center-Y": "px", "Beam Diameter": "mm"}
        for i in range(len(self.paramNames)):
            self.numParams += 1
            name = self.paramNames[i]
            StepInitialValue = self.stepAxisInitialValues[name]
            AbsInitialValue = self.absAxisInitialValues[name]
            self.unit = UnitaxisInitialValues[name]

            label = f'{name}'

            #Define all widget items
            self.pars['Label' + name] = QtWidgets.QLabel(f'{label}')
            self.pars['Label' + name].setTextFormat(QtCore.Qt.RichText)
            self.pars['DownButton' + name] = guitools.BetterPushButton('-')
            self.pars['DownButton' + name].setFixedWidth(100)
            self.pars['UpButton' + name] = guitools.BetterPushButton('+')
            self.pars['UpButton' + name].setFixedWidth(100)
            self.pars['StepEdit' + name] = QtWidgets.QLineEdit(StepInitialValue)
            self.pars['StepEdit' + name].setFixedWidth(75)
            self.pars['StepUnit' + name] = QtWidgets.QLabel(self.unit)
            self.pars['AbsPosEdit' + name] = QtWidgets.QLineEdit(AbsInitialValue)
            self.pars['AbsPosEdit' + name].setFixedWidth(75)
            self.pars['AbsPosUnit' + name] = QtWidgets.QLabel(self.unit)

            self.pars['Label' + name].setEnabled(False)
            self.pars['UpButton' + name].setEnabled(False)
            self.pars['DownButton' + name].setEnabled(False)
            self.pars['StepEdit' + name].setEnabled(False)
            self.pars['StepUnit' + name].setEnabled(False)
            self.pars['AbsPosEdit' + name].setEnabled(False)
            self.pars['AbsPosUnit' + name].setEnabled(False)

            # Integer validator
            if (name == 'Left Center-X') or (name == 'Left Center-Y') or (name == 'Right Center-X') or (name == 'Right Center-Y'):
                self.validator = QIntValidator(1,100)
                self.pars['StepEdit' + name].setValidator(self.validator)
                self.validator = QIntValidator(1,1920)
                self.pars['AbsPosEdit' + name].setValidator(self.validator)
            # Double validator
            elif (name == 'Gamma') or (name == 'Psi'):
                self.validator = QDoubleValidator(0.1,1.0,1)
                self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
                self.pars['StepEdit' + name].setValidator(self.validator)
                self.validator = QDoubleValidator(0.0,5.0,1)
                self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
                self.pars['AbsPosEdit' + name].setValidator(self.validator)
            elif (name == 'Beam Diameter'):
                self.validator = QDoubleValidator(0.1,2.0,1)
                self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
                self.pars['StepEdit' + name].setValidator(self.validator)
                self.validator = QDoubleValidator(0.0,8.0,1)
                self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
                self.pars['AbsPosEdit' + name].setValidator(self.validator)

            # Add to widget object
            self.grid.addWidget(self.pars['Label' + name], self.numParams, 0)
            self.grid.addWidget(self.pars['DownButton' + name], self.numParams, 1)
            self.grid.addWidget(self.pars['UpButton' + name], self.numParams, 2)
            self.grid.addWidget(self.pars['StepEdit' + name], self.numParams, 3)
            self.grid.addWidget(self.pars['StepUnit' + name], self.numParams, 4)
            self.grid.addWidget(self.pars['AbsPosEdit' + name], self.numParams, 5)
            self.grid.addWidget(self.pars['AbsPosUnit' + name], self.numParams, 6)

            # Connect buttons to signals

            if (name == 'Gamma') or (name == 'Psi'):
                self.pars['UpButton' + name].clicked.connect(lambda *args, name=name: self.sigStepUpClicked.emit(name))
                self.pars['DownButton' + name].clicked.connect(lambda *args, name=name: self.sigStepDownClicked.emit(name))
                self.pars['AbsPosEdit' + name].editingFinished.connect(lambda *args, name=name: self.updateMask.emit(name))
                self.pars['AbsPosEdit' + name].textChanged.connect(lambda *args, name=name: self.sigCheckValidityAbsPos.emit(name))
                self.pars['StepEdit' + name].textChanged.connect(lambda *args, name=name: self.sigCheckValidityStep.emit(name))
            else:
                self.pars['UpButton' + name].clicked.connect(lambda *args, name=name: self.sigStepUpCenterClicked.emit(name))
                self.pars['DownButton' + name].clicked.connect(lambda *args, name=name: self.sigStepDownCenterClicked.emit(name))
                self.pars['AbsPosEdit' + name].editingFinished.connect(lambda *args, name=name: self.updateCenterMask.emit(name))
                self.pars['AbsPosEdit' + name].textChanged.connect(lambda *args, name=name: self.sigCheckValidityAbsPos.emit(name))
                self.pars['StepEdit' + name].textChanged.connect(lambda *args, name=name: self.sigCheckValidityStep.emit(name))




        # self.stepLabel = QtWidgets.QLabel(f'<strong>Step</strong>')
        # self.stepLabel.setTextFormat(QtCore.Qt.RichText)
        # self.grid.addWidget(self.stepLabel, 4, 3)

        self.valLabel = QtWidgets.QLabel(f'<strong>Value</strong>')
        self.valLabel.setEnabled(False)
        self.valLabel.setTextFormat(QtCore.Qt.RichText)
        self.grid.addWidget(self.valLabel, 4, 5)

        self.valLabel2 = QtWidgets.QLabel(f'<strong>Value</strong>')
        self.valLabel2.setEnabled(False)
        self.valLabel2.setTextFormat(QtCore.Qt.RichText)
        self.grid.addWidget(self.valLabel2, 16, 5)

        self.zernLabel = QtWidgets.QLabel(f'<strong>Zernike</strong>')
        self.zernLabel.setEnabled(False)
        self.zernLabel.setTextFormat(QtCore.Qt.RichText)
        self.grid.addWidget(self.zernLabel, 4, 0)

        self.label25D = QtWidgets.QLabel(f'<strong>2.5D Mask</strong>')
        self.label25D.setEnabled(False)
        self.label25D.setTextFormat(QtCore.Qt.RichText)
        self.grid.addWidget(self.label25D, 16, 0)

        self.label25DStep = QtWidgets.QLabel(f'<strong>Step</strong>')
        self.label25DStep.setEnabled(False)
        self.label25DStep.setTextFormat(QtCore.Qt.RichText)
        self.grid.addWidget(self.label25DStep, 16, 3)

        # Connect received signals to funcions
        self.sigStepUpClicked.connect(self.increment)
        self.sigStepDownClicked.connect(self.decrement)
        self.sigStepUpCenterClicked.connect(self.increment)
        self.sigStepDownCenterClicked.connect(self.decrement)

        self.sigStepUpClickedZernike.connect(self.incrementZern)
        self.sigStepDownClickedZernike.connect(self.decrementZern)
        self.sigCheckValidityAbsPos.connect(self.checkValidityAbsPos)
        self.sigCheckValidityStep.connect(self.checkValidityStep)
        self.sigResetZern.connect(self.resetZernToDefault)
        self.sigReset25D.connect(self.reset25DToDefault)

    def reset25DToDefault(self):
        for name in self.paramNames:
            absInitValue = self.absAxisInitialValues[name]
            stepInitValue = self.stepAxisInitialValues[name]
            self.pars['StepEdit' + name].setText(stepInitValue)
            self.pars['AbsPosEdit' + name].setText(absInitValue)
        self.updateCenterMask.emit('_')

    def resetZernToDefault(self):
        for i in range(len(self.ZernikeCoefficientNames)):
            self.pars['AbsPosEdit' + self.ZernikeCoefficientNames[i]].setText('0.0')
        self.updateMaskZernike.emit('_')

    def checkValidityAbsPos(self, name):
        valid = self.pars['AbsPosEdit'+name].hasAcceptableInput()
        if valid:
            self.pars['AbsPosEdit'+name].setStyleSheet('')
        else:
            self.pars['AbsPosEdit'+name].setStyleSheet("border: 1px solid red;")
         
    def checkValidityStep(self, name):
        valid = self.pars['StepEdit'+name].hasAcceptableInput()
        if valid:
            self.pars['StepEdit'+name].setStyleSheet('')
        else:
            self.pars['StepEdit'+name].setStyleSheet("border: 1px solid red;")
         
    def disableAll(self):
        self.slmPreview.setEnabled(False)
        self.valLabel.setEnabled(False)
        self.valLabel2.setEnabled(False)
        self.slmFrame.setEnabled(False)
        self.zernLabel.setEnabled(False)
        self.label25D.setEnabled(False)
        self.projectZernike.setEnabled(False)
        self.project25D.setEnabled(False)
        self.label25DStep.setEnabled(False)
        self.resetZern.setEnabled(False)
        self.reset25D.setEnabled(False)
        # self.slmFrameCenter.setEnabled(False)
        # self.slmFrame25d.setEnabled(False)
        for i in range(len(self.ZernikeCoefficientNames)):
            name = self.ZernikeCoefficientNames[i]
            self.pars['Label' + name].setEnabled(False)
            self.pars['UpButton' + name].setEnabled(False)
            self.pars['DownButton' + name].setEnabled(False)
            self.pars['AbsPosEdit' + name].setEnabled(False)

        for i in range(len(self.paramNames)):
            name = self.paramNames[i]
            self.pars['Label' + name].setEnabled(False)
            self.pars['UpButton' + name].setEnabled(False)
            self.pars['DownButton' + name].setEnabled(False)
            self.pars['StepEdit' + name].setEnabled(False)
            self.pars['StepUnit' + name].setEnabled(False)
            self.pars['AbsPosEdit' + name].setEnabled(False)
            self.pars['AbsPosUnit' + name].setEnabled(False)

    def enableAll(self):
        self.slmPreview.setEnabled(True)
        self.valLabel.setEnabled(True)
        self.valLabel2.setEnabled(True)
        self.slmFrame.setEnabled(True)
        self.zernLabel.setEnabled(True)
        self.label25D.setEnabled(True)
        self.projectZernike.setEnabled(True)
        self.project25D.setEnabled(True)
        self.label25DStep.setEnabled(True)
        self.resetZern.setEnabled(True)
        self.reset25D.setEnabled(True)
        # self.slmFrameCenter.setEnabled(True)
        # self.slmFrame25d.setEnabled(True)
        for i in range(len(self.ZernikeCoefficientNames)):
            name = self.ZernikeCoefficientNames[i]
            self.pars['Label' + name].setEnabled(True)
            self.pars['UpButton' + name].setEnabled(True)
            self.pars['DownButton' + name].setEnabled(True)
            self.pars['AbsPosEdit' + name].setEnabled(True)

        for i in range(len(self.paramNames)):
            name = self.paramNames[i]
            self.pars['Label' + name].setEnabled(True)
            self.pars['UpButton' + name].setEnabled(True)
            self.pars['DownButton' + name].setEnabled(True)
            self.pars['StepEdit' + name].setEnabled(True)
            self.pars['StepUnit' + name].setEnabled(True)
            self.pars['AbsPosEdit' + name].setEnabled(True)
            self.pars['AbsPosUnit' + name].setEnabled(True)

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
