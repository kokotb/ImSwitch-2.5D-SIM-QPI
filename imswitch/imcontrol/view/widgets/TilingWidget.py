from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QIntValidator, QDoubleValidator

import napari

class TilingWidget(NapariHybridWidget):

    sigTilingInfoChanged = QtCore.Signal(str, str, str)
    sigRunTilingActive = QtCore.Signal()

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        self.tilingViewBool = False
        self.runTilingActiveBool = False
        # Grid scan settings bn
        gridScanLayout = QtWidgets.QGridLayout()
        self.setLayout(gridScanLayout)

        self.numGridX_label = QLabel("Steps - X")
        self.numGridX_textedit = QLineEdit("")
        self.validator = QIntValidator(0,1000,self)
        self.numGridX_textedit.setValidator(self.validator)
        self.numGridX_textedit.setFixedWidth(100)
        self.numGridX_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings','Steps - X', value))

        self.numGridY_label = QLabel("Steps - Y")
        self.numGridY_textedit = QLineEdit("")
        self.validator = QIntValidator(0,1000,self)
        self.numGridY_textedit.setValidator(self.validator)
        self.numGridY_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings','Steps - Y', value))

        # self.overlap_label = QLabel("Overlap")
        # self.overlap_textedit = QLineEdit("")
        # pattern = r"^[0-1]{1}.[0-9]{1}"
        # regexp = QRegExp(pattern)
        # self.validator = QRegExpValidator(regexp, self.overlap_textedit)
        # self.overlap_textedit.setValidator(self.validator)

        self.overlap_label = QLabel("Overlap")
        self.overlap_textedit = QLineEdit("")
        # self.validator = QIntValidator(0,100,self)
        # self.overlap_textedit.setValidator(self.validator)
        self.overlap_textedit.setToolTip('Enter a value >= 0.0 and < 1. Entry validation not working on this box.')  
        self.overlap_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Overlap", value))

        # self.tilingReps_label = QLabel("Tiling Repetitions")
        # self.tilingReps_textedit = QLineEdit("")
        # self.validator = QIntValidator(0,10000,self)
        # self.tilingReps_textedit.setValidator(self.validator)
        # self.tilingReps_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Tiling Repetitions", value))

        self.checkbox_tiling =  QCheckBox("Run Tiling")
        self.checkbox_tiling.stateChanged.connect(self.toggleRunTilingActive)
        self.checkbox_tiling.stateChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Tiling Checkbox", str(value)))
        self.checkbox_tilepreview =  QCheckBox("Tile Preview")
        self.checkbox_tilepreview.setEnabled(False)



        row = 0

        gridScanLayout.addWidget(self.numGridX_label, row, 0)
        gridScanLayout.addWidget(self.numGridX_textedit, row, 1)
        gridScanLayout.addWidget(self.numGridY_label, row+1, 0)
        gridScanLayout.addWidget(self.numGridY_textedit, row+1, 1)
        gridScanLayout.addWidget(self.overlap_label, row+2, 0)
        gridScanLayout.addWidget(self.overlap_textedit, row+2, 1)
        # gridScanLayout.addWidget(self.tilingReps_label, row+3, 0)
        # gridScanLayout.addWidget(self.tilingReps_textedit, row+3, 1)
        # gridScanLayout.addWidget(self.checkbox_tiling, row+4, 0)
        # gridScanLayout.addWidget(self.checkbox_tilepreview, row+4, 1)
        gridScanLayout.addWidget(self.checkbox_tiling, row+3, 0)
        gridScanLayout.addWidget(self.checkbox_tilepreview, row+3, 1)

        
    def toggleRunTilingActive(self):
        self.runTilingActiveBool = not self.runTilingActiveBool
        if self.runTilingActiveBool == False:
             self.checkbox_tilepreview.setEnabled(False)
        else: self.checkbox_tilepreview.setEnabled(True)

    def toggleRunTilingButton(self, state):
        state = not state
        self.checkbox_tiling.setEnabled(state)
        if state == False and self.checkbox_tiling.checkState()==2:
            self.checkbox_tilepreview.setEnabled(False)
        if state == True and self.checkbox_tiling.checkState()==2:
            self.checkbox_tilepreview.setEnabled(True)

    def initTilingInfo(self):
        self.numGridX_textedit.setText("1")
        self.numGridY_textedit.setText("1")
        self.overlap_textedit.setText("0.1")
        # self.validator = QDoubleValidator(0.0, 1.0, 1)
        # self.validator.setRange(0,1,1)
        # self.overlap_textedit.setValidator(self.validator)
        # self.tilingReps_textedit.setText("1")
        self.sigTilingInfoChanged.emit('Tiling Settings',"Tiling Checkbox", '0') # Checkboxes initialize a little different from QLineEdit. This sends a signal to register value with sharedAttrs

    def createTilingWindow(self):
        self.tilingView = napari.Viewer(title='Tiling Preview')



        



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
