import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtWidgets
from pyqtgraph.parametertree import ParameterTree
from imswitch.imcontrol.view import guitools
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,QFileDialog,
                             QCheckBox, QLabel, QLineEdit, QDialog)
import json



class InfoGatheringWidget(NapariHybridWidget):
    """ Widget containing InfoGathering interface. """
    # sigSaveSettings = QtCore.Signal()
    # sigSettingsDialog = QtCore.Signal()

    def __post_init__(self):
        #super().__init__(*args, **kwargs)
        self.loadingPopup = MyInputDialog(self)

        # Main widget 
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.saveSettings = QPushButton("Save Settings")
        self.loadSettings = QPushButton("Load Settings")
        self.layout.addWidget(self.saveSettings, 0, 0)
        self.layout.addWidget(self.loadSettings, 1, 0)


        self.loadSettings.clicked.connect(self.openLoadWindow)

    
    def openLoadWindow(self):
        
        self.loadingPopup.exec_()
    

class MyInputDialog(QDialog):
    def __init__(self, parent: NapariHybridWidget):

        super().__init__(parent)

        self.setWindowTitle("Load Settings")
        self.elementList = []


        self.filePath = QtWidgets.QLineEdit()
        self.openDialog = QPushButton("Open")
        self.allCheckbox = QtWidgets.QCheckBox("All")
        self.lasersCheckbox = QtWidgets.QCheckBox('Lasers')
        self.positionersCheckbox = QtWidgets.QCheckBox("Positioners")
        self.tilingCheckbox = QtWidgets.QCheckBox("Tiling")
        self.timingCheckbox = QtWidgets.QCheckBox("Timing")
        self.zstackCheckbox = QtWidgets.QCheckBox("Z-Stack")
        self.detectorsCheckbox = QtWidgets.QCheckBox("Detectors")
        self.parameters25DCheckbox = QtWidgets.QCheckBox("2.5D Parameters")
        self.zernikeParametersCheckbox = QtWidgets.QCheckBox('Zernike Parameters')
        self.SIMParametersCheckbox = QtWidgets.QCheckBox('SIM Parameters')
        self.ROIListCheckbox = QtWidgets.QCheckBox('ROI List')
        self.userDirCheckbox = QtWidgets.QCheckBox("User Directory")
        self.okButton = QPushButton("OK")
        self.cancelButton = QPushButton("Cancel")

        self.allCheckbox._name = 'all'
        self.lasersCheckbox._name = 'lasers'


        self.positionersCheckbox._name = 'positioners'
        self.tilingCheckbox._name = 'tiling'
        self.timingCheckbox._name = 'timing'
        self.zstackCheckbox._name = 'zstack'
        self.detectorsCheckbox._name = 'detectors'
        self.parameters25DCheckbox._name = 'parameters25D'
        self.zernikeParametersCheckbox._name = 'zernike'
        self.SIMParametersCheckbox._name = 'SIM Parameters'
        self.ROIListCheckbox._name = 'roilist'
        self.userDirCheckbox._name = 'userDir'

        self.elementList.append(self.allCheckbox)
        self.elementList.append(self.lasersCheckbox)
        self.elementList.append(self.positionersCheckbox)
        self.elementList.append(self.tilingCheckbox)
        self.elementList.append(self.timingCheckbox)
        self.elementList.append(self.zstackCheckbox)
        self.elementList.append(self.detectorsCheckbox)
        self.elementList.append(self.parameters25DCheckbox)
        self.elementList.append(self.zernikeParametersCheckbox)
        self.elementList.append(self.SIMParametersCheckbox)
        self.elementList.append(self.ROIListCheckbox)
        self.elementList.append(self.userDirCheckbox)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.filePath, 0, 0)
        layout.addWidget(self.openDialog, 0, 1)
        layout.addWidget(self.allCheckbox, 1, 0)
        layout.addWidget(self.lasersCheckbox, 2, 0)
        layout.addWidget(self.positionersCheckbox, 3, 0)
        layout.addWidget(self.tilingCheckbox, 4, 0)
        layout.addWidget(self.timingCheckbox, 5, 0)
        layout.addWidget(self.zstackCheckbox, 6, 0)
        layout.addWidget(self.detectorsCheckbox, 7, 0)
        layout.addWidget(self.parameters25DCheckbox, 8, 0)
        layout.addWidget(self.zernikeParametersCheckbox, 9, 0)
        layout.addWidget(self.SIMParametersCheckbox, 10, 0)
        layout.addWidget(self.ROIListCheckbox, 11, 0)
        layout.addWidget(self.userDirCheckbox, 12, 0)
        layout.addWidget(self.okButton, 13, 1)
        layout.addWidget(self.cancelButton, 13, 0)

        self.setLayout(layout)

        self.openDialog.clicked.connect(self.loadPath)
        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        self.allCheckbox.clicked.connect(self.toggleAllBoxes)

    def openFileDialog(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("JSON (*.json)")
        dialog.setDirectory(r'C:\VSCode\ImSwitch-2.5D-SIM-QPI')
        if dialog.exec():
            filename = dialog.selectedFiles()
        return filename
    
    def loadPath(self):
        jsonPath = self.openFileDialog()[0]
        self.filePath.setText(jsonPath)

    def loadJSON(self):
        jsonPath = self.filePath.text()
        with open(jsonPath, 'r') as openfile:    
            # Reading from json file
            jsonObject = json.load(openfile)


        return jsonObject
    
    def toggleAllBoxes(self):
        allChecked = self.allCheckbox.checkState()
        if allChecked == 2:
            for button in self.elementList:
                button.setCheckState(2)
        if allChecked == 0:
            for button in self.elementList:
                button.setCheckState(0)     




    
# class InfoGatheringWidget(NapariHybridWidget):
#     def __post_init__(self):
#         self.openSelectionDialog()
#     def openSelectionDialog(self):
#         window = QWidget()
#         # layout = QtWidgets.QGridLayout()
#         # window.setLayout(self.layout)
#         # self.testSettings = QPushButton("Test Settings")
#         # layout.addWidget(self.testSettings, 0, 0)
#         window.show()

    


        

# Copyright (C) 2020-2023 ImSwitch developers
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
