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
import threading



class PSFAnalysisWidget(NapariHybridWidget):
    """ Widget containing InfoGathering interface. """
    # sigSaveSettings = QtCore.Signal()
    # sigSettingsDialog = QtCore.Signal()

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        self.loadingPopup = PSFWindow(self)

        # Main widget 
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.loadSettings = QPushButton("Load Settings")
        self.layout.addWidget(self.loadSettings, 1, 0)


        self.loadSettings.clicked.connect(self.openLoadWindowThread)
        # self.saveSettings.clicked.connect(self.saveFileDialog)

    def toggleLoadButton(self, state):
        state = not state
        self.loadSettings.setEnabled(state)

   
    def openLoadWindowThread(self):
        threading.Thread(target=self.openLoadWindow(), args=(), daemon=True).start()

    def openLoadWindow(self):
        self.loadingPopup.show()

class PSFWindow(QMainWindow):
    def __init__(self, parent = None): 
        super().__init__(parent) 
        self.init_gui() 
  
    def init_gui(self): 
        self.window = QtWidgets.QWidget() 
        self.layout = QtWidgets.QGridLayout() 
        self.setCentralWidget(self.window) 
        self.window.setLayout(self.layout) 
  
        self.textbox = QtWidgets.QLineEdit() 
        self.echo_label = QtWidgets.QLabel('') 
  
        self.textbox.textChanged.connect(self.textbox_text_changed) 
  
        self.layout.addWidget(self.textbox, 0, 0) 
        self.layout.addWidget(self.echo_label, 1, 0) 
  
    def textbox_text_changed(self): 
        self.echo_label.setText(self.textbox.text()) 

    
        

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
