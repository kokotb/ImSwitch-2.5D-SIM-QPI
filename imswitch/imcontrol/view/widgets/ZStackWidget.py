from qtpy import QtCore, QtWidgets

from PyQt5.QtWidgets import (QCheckBox, QLabel, QLineEdit)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QDoubleValidator
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
        self.validator = QDoubleValidator(0.1, 20.0, 3)
        self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.zStepDistance_textedit.setValidator(self.validator)
        self.zStepDistance_textedit.setToolTip('Size between steps in microns. Smallest is 0.1 um.') 
        self.zStepDistance_textedit.setEnabled(False)
        self.zStepDistance_textedit.setFixedWidth(50)
        self.zStepDistance_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Step Size", value))
        self.zStepDistance_textedit.editingFinished.connect(self.floorTotalZ)
        self.zStepDistance_textedit.textChanged.connect(self.sigCheckValidityStep.emit)


        self.totalZ_label = QLabel("Total Z (/um)")
        self.totalZ_textedit = QLineEdit("")
        self.totalZ_textedit._name = 'Total Z /um'
        self.totalZ_textedit._type = 'str'
        self.validator = QDoubleValidator(0.2, 450.0, 1)
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
        self.numSteps_textedit = QLineEdit("2")
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
        zStackLayout.addWidget(self.checkbox_zStack, row+4, 0)
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
        self.zStepDistance_textedit.setText("1")
        self.totalZ_textedit.setText("1")
        self.zOffset_textedit.setText("0")
        self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Checkbox", '0')
        self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Center?", '0')
        self.zStackScanDir.addItems(['Up','Down'])
        self.zStackScanDir.setCurrentIndex(0)

    def updateStartOffset(self, totalDist):
        if self.checkbox_zStackCenter.checkState() == 2:
            self.zOffset_textedit.setText(str(totalDist/2))

        elif self.checkbox_zStackCenter.checkState() == 0:
            self.zOffset_textedit.setText(str(0))
    

    def floorTotalZ(self):
        try:
            stepDist = float(self.zStepDistance_textedit.text())
            totalDist = float(self.totalZ_textedit.text())
        except ValueError:
            print("Step or total Z values incorrect.")
            return
        
        assert stepDist != 0 and totalDist != 0, "Step distance or total Z distance cannot be zero."

        floorDiv = math.floor((totalDist / stepDist))

        if self.checkbox_zStackCenter.checkState() == 0:
            newTotalDist = stepDist * floorDiv
            if stepDist > totalDist:
                self.totalZ_textedit.setText(str(round(stepDist, 1)))
                self.numSteps_textedit.setText(str(round(2, 0)))
            else:    
                self.totalZ_textedit.setText(str(round(newTotalDist, 1)))
                self.numSteps_textedit.setText(str(round(floorDiv + 1, 0)))

        elif self.checkbox_zStackCenter.checkState() == 2:

            if floorDiv % 2 == 0:
                newTotalDist = stepDist * floorDiv
            else: 
                floorSteps = floorDiv + 1

                newTotalDist = round(stepDist * floorSteps,1)
                self.numSteps_textedit.setText(str(round(floorSteps + 1, 0)))

            self.totalZ_textedit.setText(str(newTotalDist))

        self.updateStartOffset(newTotalDist)
        
        return newTotalDist
    

    def toggleRunZStackEnabled(self, state):
        state = not state
        if not state:
            self.checkbox_zStack.setEnabled(state)
            self.zStepDistance_label.setEnabled(state)
            self.totalZ_label.setEnabled(state)
            self.zOffset_label.setEnabled(state)
            self.numSteps_label.setEnabled(state)
            self.zStepDistance_textedit.setEnabled(state)
            self.totalZ_textedit.setEnabled(state)
            self.zStackScanDir.setEnabled(state)
            self.checkbox_zStackCenter.setEnabled(state)

        if state:

            self.zStepDistance_label.setEnabled(state)
            self.totalZ_label.setEnabled(state)
            self.zOffset_label.setEnabled(state)
            self.numSteps_label.setEnabled(state)
            self.zStepDistance_textedit.setEnabled(state)
            self.totalZ_textedit.setEnabled(state)
            self.checkbox_zStack.setEnabled(state)

            if self.checkbox_zStack.checkState() == 2:
                self.zStackScanDir.setEnabled(True)
                self.checkbox_zStackCenter.setEnabled(True)

            elif self.checkbox_zStack.checkState() == 0:
                self.zStackScanDir.setEnabled(False)
                self.checkbox_zStackCenter.setEnabled(False)

                
                


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
