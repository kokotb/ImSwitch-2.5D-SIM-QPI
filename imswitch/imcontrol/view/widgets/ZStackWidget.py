from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
import napari
from PyQt5.QtGui import QIntValidator, QDoubleValidator
import math

class ZStackWidget(NapariHybridWidget):

    sigZStackInfoChanged = QtCore.Signal(str, str, str)
    runZStackToggle = QtCore.Signal(int)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        zStackLayout = QtWidgets.QGridLayout()
        self.setLayout(zStackLayout)



        self.zStepDistance_label = QLabel("Step Size (/um)")
        self.zStepDistance_textedit = QLineEdit("")
        self.validator = QDoubleValidator()
        self.zStepDistance_textedit.setValidator(self.validator)
        self.zStepDistance_textedit.setToolTip('Size between steps in microns.') 
        self.zStepDistance_textedit.setEnabled(False)
        # self.zSteps_textedit.setPlaceholderText('Blank or 0 is max frame rate')
        self.zStepDistance_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Step Size", value))
        self.zStepDistance_textedit.textChanged.connect(self.floorTotalZ)


        self.totalZ_label = QLabel("Total Z (/um)")
        self.totalZ_textedit = QLineEdit("")
        # self.validator = QDoubleValidator()
        # self.totalZ_textedit.setValidator(self.validator)
        self.totalZ_textedit.setToolTip('Total distance covered in Z. Only complete steps calcualted. 10.9 steps = 10 steps.')  
        self.totalZ_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Total Z (/um)", value))
        self.totalZ_textedit.setText("0")
        self.totalZ_textedit.setEnabled(False)
        self.totalZ_textedit.editingFinished.connect(self.floorTotalZ)


        self.checkbox_zStack = QCheckBox('Run Z Stack')

        self.checkbox_zStack.stateChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Checkbox", str(value)))

        self.checkbox_zStack.stateChanged.connect(lambda value: self.runZStackToggle.emit(value))
        
        self.checkbox_zStackCenter = QCheckBox('Center?')
        self.checkbox_zStackCenter.stateChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Center?", str(value)))
        self.checkbox_zStackCenter.stateChanged.connect(self.floorTotalZ)
        self.checkbox_zStackCenter.setEnabled(False)

        self.zOffset_label = QLabel("Start Offset") 
        self.zOffset_textedit = QLineEdit("")
        self.validator = QDoubleValidator()
        self.zOffset_textedit.setValidator(self.validator)
        self.zOffset_textedit.setToolTip('Offset from current position to scan start position')
        # self.zOffset_textedit.setReadOnly(True)
        self.zOffset_textedit.setEnabled(False)
        self.zOffset_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings','Scan Start Offset', value))

        self.zStackScanDir = QtWidgets.QComboBox()
        self.zStackScanDir.setEnabled(False)
        self.zStackScanDir.currentTextChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings','Scan Direction', value))


        row = 0
        
        zStackLayout.addWidget(self.zStepDistance_label, row, 0)
        zStackLayout.addWidget(self.zStepDistance_textedit, row, 1)
        zStackLayout.addWidget(self.totalZ_label, row+1, 0)
        zStackLayout.addWidget(self.totalZ_textedit, row+1, 1)
        zStackLayout.addWidget(self.checkbox_zStack, row+2, 0)
        zStackLayout.addWidget(self.checkbox_zStackCenter, row+2, 1)
        zStackLayout.addWidget(self.zStackScanDir, row+2, 2)
        zStackLayout.addWidget(self.zOffset_label, row+2, 3)
        zStackLayout.addWidget(self.zOffset_textedit, row+2, 4)



    def initZStackInfo(self):
        self.zStepDistance_textedit.setText("1")
        self.totalZ_textedit.setText("0")
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
        if self.checkbox_zStackCenter.checkState() == 2:
            self.zOffset_textedit.setText(str(totalDist/2))

        elif self.checkbox_zStackCenter.checkState() == 0:
            self.zOffset_textedit.setText(str(0))
    

    def floorTotalZ(self):
        stepDist = float(self.zStepDistance_textedit.text())
        totalDist = float(self.totalZ_textedit.text())
        floorSteps = math.floor((totalDist / stepDist))

        if self.checkbox_zStackCenter.checkState() == 0:

            newTotalDist = stepDist * floorSteps
            self.totalZ_textedit.setText(str(newTotalDist))

        elif self.checkbox_zStackCenter.checkState() == 2:
            # floorSteps = floorSteps + 1
            if floorSteps % 2 == 0:
                pass
            else: 
                floorSteps = floorSteps + 1

            newTotalDist = stepDist * floorSteps
            self.totalZ_textedit.setText(str(newTotalDist))

        self.updateStartOffset(newTotalDist)
        
        return newTotalDist
                
                


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
