from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)

class TilingWidget(Widget):
    """ Widget that watch for new script files (.py) in a specific folder, for running them sequentially."""

    # sigSaveFocus = QtCore.Signal(bool)
    sigTilingInfoChanged = QtCore.Signal(str, str, str)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.skipTileButton = guitools.BetterPushButton("Skip tile")
        # self.registerFocusButton = guitools.BetterPushButton("Register focus")
        # self.tileNumberEdit = QtWidgets.QLabel("Tile Number: 0/0")

        # layout = QtWidgets.QGridLayout()
        # self.setLayout(layout)

        # layout.addWidget(self.tileNumberEdit, 0, 0)
        # layout.addWidget(self.registerFocusButton, 0, 1)
        # layout.addWidget(self.skipTileButton, 0, 2)

        # Grid scan settings
        gridScanLayout = QtWidgets.QGridLayout()
        self.setLayout(gridScanLayout)

        self.numGridX_label = QLabel("Steps - X")
        self.numGridX_textedit = QLineEdit("")
        self.numGridX_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings','Steps - X', value))

        self.numGridY_label = QLabel("Steps - Y")
        self.numGridY_textedit = QLineEdit("")
        self.numGridY_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings','Steps - Y', value))

        self.overlap_label = QLabel("Overlap [%]")
        self.overlap_textedit = QLineEdit("")
        self.overlap_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Overlap [%]", value))

        self.reconFrameSkip_label = QLabel("Recon Frames to Skips")
        self.reconFrameSkip_textedit = QLineEdit("")
        self.reconFrameSkip_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Recon Frames to Skips", value))

        
        row = 0
        # gridScanLayout.addWidget(self.gridScanBoxLabel,row,0)
        # gridScanLayout.addWidget(QtWidgets.QLabel(""),row,1)
        gridScanLayout.addWidget(self.numGridX_label, row, 0)
        gridScanLayout.addWidget(self.numGridX_textedit, row, 1)
        gridScanLayout.addWidget(self.numGridY_label, row+1, 0)
        gridScanLayout.addWidget(self.numGridY_textedit, row+1, 1)
        gridScanLayout.addWidget(self.overlap_label, row+2, 0)
        gridScanLayout.addWidget(self.overlap_textedit, row+2, 1)
        gridScanLayout.addWidget(self.reconFrameSkip_label, row+3, 0)
        gridScanLayout.addWidget(self.reconFrameSkip_textedit, row+3, 1)
        
        # tabBottomVertLayout1.addLayout(gridScanLayout)




        # self.registerFocusButton.clicked.connect(lambda: self.sigSaveFocus.emit(True))
        # self.skipTileButton.clicked.connect(lambda: self.sigSaveFocus.emit(False))





    def initTilingInfo(self):
        self.numGridX_textedit.setText("1")
        self.numGridY_textedit.setText("1")
        self.overlap_textedit.setText("0")
        self.reconFrameSkip_textedit.setText("0")

    def setLabel(self, label):
        self.tileNumberEdit.setText(label)

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
