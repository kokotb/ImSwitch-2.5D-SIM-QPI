from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
import napari

class TilingWidget(NapariHybridWidget):

    sigTilingInfoChanged = QtCore.Signal(str, str, str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        self.tilingViewBool = False
        # Grid scan settings
        gridScanLayout = QtWidgets.QGridLayout()
        self.setLayout(gridScanLayout)

        self.numGridX_label = QLabel("Steps - X")
        self.numGridX_textedit = QLineEdit("")
        self.numGridX_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings','Steps - X', value))

        self.numGridY_label = QLabel("Steps - Y")
        self.numGridY_textedit = QLineEdit("")
        self.numGridY_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings','Steps - Y', value))

        self.overlap_label = QLabel("Overlap")
        self.overlap_textedit = QLineEdit("")
        self.overlap_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Overlap", value))

        self.tilingReps_label = QLabel("Tiling Repetitions")
        self.tilingReps_textedit = QLineEdit("")
        self.tilingReps_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Tiling Repetitions", value))
        self.checkbox_tiling =  QCheckBox("Run Tiling")
        self.checkbox_tilepreview =  QCheckBox("Tile Preview")
        self.checkbox_tiling.stateChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Tiling Checkbox", str(value)))


        row = 0

        gridScanLayout.addWidget(self.numGridX_label, row, 0)
        gridScanLayout.addWidget(self.numGridX_textedit, row, 1)
        gridScanLayout.addWidget(self.numGridY_label, row+1, 0)
        gridScanLayout.addWidget(self.numGridY_textedit, row+1, 1)
        gridScanLayout.addWidget(self.overlap_label, row+2, 0)
        gridScanLayout.addWidget(self.overlap_textedit, row+2, 1)
        gridScanLayout.addWidget(self.tilingReps_label, row+3, 0)
        gridScanLayout.addWidget(self.tilingReps_textedit, row+3, 1)
        gridScanLayout.addWidget(self.checkbox_tiling, row+4, 0)
        gridScanLayout.addWidget(self.checkbox_tilepreview, row+4, 1)

        
    def initTilingInfo(self):
        self.numGridX_textedit.setText("1")
        self.numGridY_textedit.setText("1")
        self.overlap_textedit.setText("0")
        self.tilingReps_textedit.setText("1")
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
