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
        self.buttonList = []


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
        self.userDirCheckbox = QtWidgets.QCheckBox("User Directory")
        self.okButton = QPushButton("OK")
        self.cancelButton = QPushButton("Cancel")

        self.buttonList.append(self.allCheckbox)
        self.buttonList.append(self.lasersCheckbox)
        self.buttonList.append(self.positionersCheckbox)
        self.buttonList.append(self.tilingCheckbox)
        self.buttonList.append(self.timingCheckbox)
        self.buttonList.append(self.zstackCheckbox)
        self.buttonList.append(self.detectorsCheckbox)
        self.buttonList.append(self.parameters25DCheckbox)
        self.buttonList.append(self.zernikeParametersCheckbox)
        self.buttonList.append(self.SIMParametersCheckbox)
        self.buttonList.append(self.userDirCheckbox)

                        
        









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
        layout.addWidget(self.userDirCheckbox, 11, 0)
        layout.addWidget(self.okButton, 11, 1)
        layout.addWidget(self.cancelButton, 11, 0)

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
            for button in self.buttonList:
                button.setCheckState(2)
        if allChecked == 0:
            for button in self.buttonList:
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
