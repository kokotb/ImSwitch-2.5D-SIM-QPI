import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtWidgets
from pyqtgraph.parametertree import ParameterTree
from imswitch.imcontrol.view import guitools
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,QFileDialog,
                             QCheckBox, QLabel, QLineEdit)
import json


class InfoGatheringWidget(NapariHybridWidget):
    """ Widget containing InfoGathering interface. """
    sigSaveSettings = QtCore.Signal()
    sigSettingsDialog = QtCore.Signal()
    def __post_init__(self):
        #super().__init__(*args, **kwargs)

        # Main GUI 
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.saveSettings = QPushButton("Save Settings")
        self.loadSettings = QPushButton("Load Settings")
        self.layout.addWidget(self.saveSettings, 0, 0)
        self.layout.addWidget(self.loadSettings, 1, 0)


    def openFileDialog(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("JSON (*.json)")
        dialog.setDirectory(r'C:\VSCode\ImSwitch-2.5D-SIM-QPI')
        if dialog.exec():
            filename = dialog.selectedFiles()
        return filename
    
    def loadJSON(self):
        jsonPath = self.openFileDialog()[0]
        with open(jsonPath, 'r') as openfile:    
            # Reading from json file
            jsonObject = json.load(openfile)

        return jsonObject

        

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
