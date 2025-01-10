from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
import napari
from PyQt5.QtGui import QIntValidator, QDoubleValidator

class ZStackWidget(NapariHybridWidget):

    sigZStackInfoChanged = QtCore.Signal(str, str, str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        zStackLayout = QtWidgets.QGridLayout()
        self.setLayout(zStackLayout)



        self.zStepDistance_label = QLabel("Step Size (/um)")
        self.zStepDistance_textedit = QLineEdit("")
        self.validator = QDoubleValidator()
        self.zStepDistance_textedit.setValidator(self.validator)
        self.zStepDistance_textedit.setToolTip('Size between steps in microns.')  
        # self.zSteps_textedit.setPlaceholderText('Blank or 0 is max frame rate')
        self.zStepDistance_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Step Distance", value))


        self.totalZ_label = QLabel("Total Z (/um)")
        self.totalZ_textedit = QLineEdit("")
        self.validator = QDoubleValidator()
        self.totalZ_textedit.setValidator(self.validator)
        self.totalZ_textedit.setToolTip('Total distance covered in Z')  
        self.totalZ_textedit.textChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Total Z (/um)", value))


        self.checkbox_zStack = QCheckBox('Run Z Stack')
        self.checkbox_zStack.stateChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Checkbox", str(value)))

        self.zStackStart = QtWidgets.QComboBox()
        self.zStackStart.currentTextChanged.connect(lambda value: self.sigZStackInfoChanged.emit('Z-Stack Settings','Scan Start Position', value))


        row = 0
        
        zStackLayout.addWidget(self.zStepDistance_label, row, 0)
        zStackLayout.addWidget(self.zStepDistance_textedit, row, 1)
        zStackLayout.addWidget(self.totalZ_label, row+1, 0)
        zStackLayout.addWidget(self.totalZ_textedit, row+1, 1)
        zStackLayout.addWidget(self.checkbox_zStack, row+2, 0)
        zStackLayout.addWidget(self.zStackStart, row+2, 2)



    def initZStackInfo(self):
        self.zStepDistance_textedit.setText("1")
        self.totalZ_textedit.setText("0")
        self.sigZStackInfoChanged.emit('Z-Stack Settings',"Z-Stack Checkbox", '0')
        self.zStackStart.addItems(['Center', 'Bottom','Top'])
        self.zStackStart.setCurrentIndex(0)

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
