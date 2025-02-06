from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
import napari
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtCore import QLocale
import math

class ZStackWidget(NapariHybridWidget):

    sigZStackInfoChanged = QtCore.Signal(str, str, str)
    runZStackToggle = QtCore.Signal(int)
    sigCheckValidityStep = QtCore.Signal()
    sigCheckValidityTotal = QtCore.Signal()
    # sigZStackCalc = QtCore.Signal()

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        zStackLayout = QtWidgets.QGridLayout()
        self.setLayout(zStackLayout)

        self.elementList = []

        self.zStepDistance_label = QLabel("Step Size (/um)")
        self.zStepDistance_textedit = QLineEdit("")
        self.zStepDistance_textedit._name = 'Step Size'
        self.zStepDistance_textedit._type = 'str'
        self.validator = QDoubleValidator(0.01, 10.00, 2)
        self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.zStepDistance_textedit.setValidator(self.validator)
        self.zStepDistance_textedit.setToolTip('Size between steps in microns.') 
        self.zStepDistance_textedit.setEnabled(False)
        self.zStepDistance_textedit.setFixedWidth(50)
        self.zStepDistance_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Step Size", value))
        self.zStepDistance_textedit.editingFinished.connect(self.floorTotalZ)
        self.zStepDistance_textedit.textChanged.connect(self.sigCheckValidityStep.emit)


        self.totalZ_label = QLabel("Total Z (/um)")
        self.totalZ_textedit = QLineEdit("")
        self.totalZ_textedit._name = 'Total Z /um'
        self.totalZ_textedit._type = 'str'
        self.validator = QDoubleValidator(0.00, 450.00, 2)
        self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.totalZ_textedit.setValidator(self.validator)
        self.totalZ_textedit.setToolTip('Total distance covered in Z. Only complete steps calculated. 10.9 steps = 10 steps.')  
        self.totalZ_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Total Z /um", value))
        self.totalZ_textedit.setText("")
        self.totalZ_textedit.setFixedWidth(50)
        self.totalZ_textedit.setEnabled(False)
        self.totalZ_textedit.editingFinished.connect(self.floorTotalZ)
        self.totalZ_textedit.textChanged.connect(self.sigCheckValidityTotal.emit)


        self.checkbox_zStack = QCheckBox('Run Z Stack')
        self.checkbox_zStack._name = 'Z-Stack Checkbox'
        self.checkbox_zStack._type = 'int'
        self.checkbox_zStack.stateChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Checkbox", str(value)))
        self.checkbox_zStack.stateChanged.connect(lambda value: self.runZStackToggle.emit(value))
        
        self.checkbox_zStackCenter = QCheckBox('Center?')
        self.checkbox_zStackCenter._name = 'Z-Stack Center?'
        self.checkbox_zStackCenter._type = 'int'
        self.checkbox_zStackCenter.stateChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Center?", str(value)))
        self.checkbox_zStackCenter.stateChanged.connect(self.floorTotalZ)
        self.checkbox_zStackCenter.setEnabled(False)

        self.zOffset_label = QLabel("Start Offset (/um)") 
        self.zOffset_textedit = QLineEdit("")
        self.validator = QDoubleValidator()
        self.zOffset_textedit.setValidator(self.validator)
        self.zOffset_textedit.setToolTip('Offset from current position to scan start position')
        self.zOffset_textedit.setFixedWidth(50)
        # self.zOffset_textedit.setReadOnly(True)
        self.zOffset_textedit.setEnabled(False)
        self.zOffset_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings','Scan Start Offset', value))

        self.numSteps_label = QLabel("Steps") 
        self.numSteps_textedit = QLineEdit("1")
        self.numSteps_textedit.setToolTip('Number of steps in the z-stack')
        self.numSteps_textedit.setFixedWidth(50)
        self.numSteps_textedit.setEnabled(False)
        # self.numSteps_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings','Scan Start Offset', value))

        self.zStackScanDir = QtWidgets.QComboBox()
        self.zStackScanDir._name = 'Scan Direction'
        self.zStackScanDir._type = 'combostr'
        self.zStackScanDir.setFixedWidth(75)
        self.zStackScanDir.setEnabled(False)

        self.zStackScanDir.currentTextChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings','Scan Direction', value))

        self.elementList.append(self.zStepDistance_textedit)
        self.elementList.append(self.totalZ_textedit)
        self.elementList.append(self.checkbox_zStack)
        self.elementList.append(self.checkbox_zStackCenter)
        self.elementList.append(self.zStackScanDir)



        row = 0
        
        zStackLayout.addWidget(self.zStepDistance_label, row, 0)
        zStackLayout.addWidget(self.zStepDistance_textedit, row, 1)
        zStackLayout.addWidget(self.totalZ_label, row+1, 0)
        zStackLayout.addWidget(self.totalZ_textedit, row+1, 1)

        zStackLayout.addWidget(self.zOffset_label, row+2, 0)
        zStackLayout.addWidget(self.zOffset_textedit, row+2, 1)

        zStackLayout.addWidget(self.numSteps_label, row+3, 0)
        zStackLayout.addWidget(self.numSteps_textedit, row+3, 1)
        

        zStackLayout.addWidget(self.checkbox_zStackCenter, row+4, 1)
        zStackLayout.addWidget(self.zStackScanDir, row+4, 2)

        zStackLayout.addWidget(self.checkbox_zStack, row+4, 0)

        self.sigCheckValidityStep.connect(self.checkValidityStep)
        self.sigCheckValidityTotal.connect(self.checkValidityTotal)

    def checkValidityStep(self):
        valid = self.zStepDistance_textedit.hasAcceptableInput()
        if valid:
            self.zStepDistance_textedit.setStyleSheet('')
        else:
            self.zStepDistance_textedit.setStyleSheet("border: 1px solid red;")

    def checkValidityTotal(self):
        valid = self.totalZ_textedit.hasAcceptableInput()
        if valid:
            self.totalZ_textedit.setStyleSheet('')
        else:
            self.totalZ_textedit.setStyleSheet("border: 1px solid red;")

    def initZStackInfo(self):
        # self.sigZStackInfoChanged.emit('Z-Stack Settings','Scan Direction', 'Up')
        self.zStepDistance_textedit.setText("1")
        self.totalZ_textedit.setText("1")
        self.zOffset_textedit.setText("0")
        self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Checkbox", '0')
        self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Center?", '0')
        self.zStackScanDir.addItems(['Up','Down'])
        self.zStackScanDir.setCurrentIndex(0)

    # def centerToggled(self):
    #     if self.checkbox_zStackCenter.checkState() == 2:
    #         totalDist = self.floorTotalZ()
        
    #     self.zOffset_textedit.setText(str(totalDist))

    def updateStartOffset(self, totalDist):
        # scanDir = self.zStackScanDir.currentText()
        if self.checkbox_zStackCenter.checkState() == 2:
            self.zOffset_textedit.setText(str(totalDist/2))

        elif self.checkbox_zStackCenter.checkState() == 0:
            self.zOffset_textedit.setText(str(0))
    

    def floorTotalZ(self):
        stepDist = float(self.zStepDistance_textedit.text())
        totalDist = float(self.totalZ_textedit.text())
        try:
            floorSteps = math.floor((totalDist / stepDist))
        except ZeroDivisionError:
            print("Step size is equal to zero.")
            # floorSteps = 0

        if self.checkbox_zStackCenter.checkState() == 0:
            if floorSteps == 0:
                newTotalDist = stepDist
            else:
                newTotalDist = stepDist * floorSteps
            self.totalZ_textedit.setText(str(round(newTotalDist, 2)))

        elif self.checkbox_zStackCenter.checkState() == 2:
            if floorSteps == 0:
                newTotalDist = stepDist * 2
            else:

                if floorSteps % 2 == 0:
                    pass
                else: 
                    floorSteps = floorSteps + 1

                newTotalDist = round(stepDist * floorSteps,2)

            self.totalZ_textedit.setText(str(newTotalDist))

        self.updateStartOffset(newTotalDist)
        
        return newTotalDist
    

    def toggleRunZStackEnabled(self, state):
        state = not state
        self.checkbox_zStack.setEnabled(state)
                
                


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
