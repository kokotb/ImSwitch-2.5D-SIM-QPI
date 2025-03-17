import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtWidgets
from pyqtgraph.parametertree import ParameterTree
from imswitch.imcontrol.view import guitools
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from imswitch.imcommon.model import initLogger
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,QFileDialog,
                             QCheckBox, QLabel, QLineEdit, QDialog)
import json
import os



class PSFAnalysisWidget(NapariHybridWidget):
    """ Widget containing InfoGathering interface. """
    # sigSaveSettings = QtCore.Signal()
    # sigSettingsDialog = QtCore.Signal()

    def __post_init__(self):
        #super().__init__(*args, **kwargs)
        self.loadingPopup = PSFWindow(self)

        # Main widget 
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.loadSettings = QPushButton("Load Settings")
        self.layout.addWidget(self.loadSettings, 1, 0)


        self.loadSettings.clicked.connect(self.openLoadWindow)
        # self.saveSettings.clicked.connect(self.saveFileDialog)

    def toggleLoadButton(self, state):
        state = not state
        self.loadSettings.setEnabled(state)

   
    def openLoadWindow(self):
        
        self.loadingPopup.exec_()
    

class PSFWindow(QDialog):
    def __init__(self, parent: NapariHybridWidget):

        super().__init__(parent)
        self._logger = initLogger(self)
        self.setWindowTitle("Load Settings")

        self.filePath = QtWidgets.QLineEdit()
        self.openDialog = QPushButton("Open")
        self.okButton = QPushButton("OK")
        self.cancelButton = QPushButton("Cancel")



        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.filePath, 0, 0)
        layout.addWidget(self.openDialog, 0, 1)
        layout.addWidget(self.okButton, 1, 1)
        layout.addWidget(self.cancelButton, 1, 0)

        self.setLayout(layout)

        self.openDialog.clicked.connect(self.loadPath)
        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)





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
        if jsonPath == '':
            self._logger.warning('No file path selected')
            jsonObject = dict()
        else:
            with open(jsonPath, 'r') as openfile:    
                # Reading from json file
                jsonObject = json.load(openfile)


        return jsonObject
  




    
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
