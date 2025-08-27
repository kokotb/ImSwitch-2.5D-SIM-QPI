from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt, QLocale


import napari

class TilingWidget(NapariHybridWidget):

    sigTilingInfoChanged = QtCore.Signal(str, str, str)
    sigRunTilingActive = QtCore.Signal()
    sigCheckValidity = QtCore.Signal(str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        self.elementList = []
        self.tilingViewBool = False
        self.runTilingActiveBool = False
        # Grid scan settings bn
        overallLayout = QtWidgets.QGridLayout()
        # gridScanLayout = QtWidgets.QGridLayout()
        self.setLayout(overallLayout)

        self.numGridX_label = QLabel("Steps - X")
        # self.numGridX_label.setMaximumWidth(100)
        # self.numGridX_label.setAlignment(Qt.AlignLeft)
        self.numGridX_textedit = QLineEdit("")
        self.numGridX_textedit._name = 'Steps - X'
        self.numGridX_textedit._type = 'str'
        self.validator = QIntValidator(0,500,self)
        self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.numGridX_textedit.setValidator(self.validator)
        self.numGridX_textedit.setFixedWidth(50)
        self.numGridX_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings','Steps - X', value))

        self.numGridY_label = QLabel("Steps - Y")
        self.numGridY_textedit = QLineEdit("")
        self.numGridY_textedit._name = 'Steps - Y'
        self.numGridY_textedit._type = 'str'
        self.validator = QIntValidator(0,500,self)
        self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.numGridY_textedit.setValidator(self.validator)
        self.numGridY_textedit.setFixedWidth(50)
        self.numGridY_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings','Steps - Y', value))

        self.overlap_label = QLabel("Overlap")
        self.overlap_textedit = QLineEdit("")
        self.overlap_textedit._name = 'Overlap'
        self.overlap_textedit._type = 'str'

        self.validator = QDoubleValidator(0.00,1.00,2)
        self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.overlap_textedit.setValidator(self.validator)

        self.overlap_textedit.setFixedWidth(50)
        self.overlap_textedit.setToolTip('Enter a value >= 0.0 and < 1. Entry validation not working on this box.')  
        self.overlap_textedit.textChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Overlap", value))
        

        self.checkbox_tiling =  QCheckBox("Run Tiling")
        self.checkbox_tiling._name = 'Tiling Checkbox'
        self.checkbox_tiling._type = 'int'
        self.checkbox_tiling.stateChanged.connect(self.toggleRunTilingActive)
        self.checkbox_tiling.stateChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Tiling Checkbox", str(value)))
        
        self.checkbox_tilepreview =  QCheckBox("Tile Preview")
        self.checkbox_tilepreview._name = 'Tiling Preview'
        self.checkbox_tilepreview._type = 'int'
        self.checkbox_tilepreview.setEnabled(False)
        self.checkbox_tilepreview.stateChanged.connect(lambda value: self.sigTilingInfoChanged.emit('Tiling Settings',"Tiling Preview", str(value)))

        self.elementList.append(self.numGridX_textedit)
        self.elementList.append(self.numGridY_textedit)
        self.elementList.append(self.overlap_textedit)
        self.elementList.append(self.checkbox_tiling)
        # self.elementList.append(self.checkbox_tilepreview) #CTNOTE: Not working very well, removing for now 27/8/25






        overallLayout.addWidget(self.numGridX_label, 0, 0)
        overallLayout.addWidget(self.numGridX_textedit, 0 ,2)
        # stepsXLayout.setContentsMargins(0, 0, 400, 0)

        overallLayout.addWidget(self.numGridY_label, 1, 0)
        overallLayout.addWidget(self.numGridY_textedit, 1, 2)


        overallLayout.addWidget(self.overlap_label, 2, 0)
        overallLayout.addWidget(self.overlap_textedit, 2, 2)

        overallLayout.addWidget(self.checkbox_tiling, 3, 0)
        # overallLayout.addWidget(self.checkbox_tilepreview, 3, 1)


        self.numGridY_textedit.textChanged.connect(lambda *args, name='numGridY': self.sigCheckValidity.emit(name))
        self.numGridX_textedit.textChanged.connect(lambda *args, name='numGridX': self.sigCheckValidity.emit(name))
        self.overlap_textedit.textChanged.connect(lambda *args, name='overlap': self.sigCheckValidity.emit(name))
        self.sigCheckValidity.connect(self.checkValidity)
        

    def checkValidity(self, name):
        if name == 'numGridY':
            signalOrigin = self.numGridY_textedit
        elif name == 'numGridX':
            signalOrigin = self.numGridX_textedit
        elif name == 'overlap':
            signalOrigin = self.overlap_textedit
        valid = signalOrigin.hasAcceptableInput()
        if valid:
            signalOrigin.setStyleSheet('')
        else:
            signalOrigin.setStyleSheet("border: 1px solid red;")

        
    def toggleRunTilingActive(self):
        self.runTilingActiveBool = not self.runTilingActiveBool
        if self.runTilingActiveBool == False:
             self.checkbox_tilepreview.setEnabled(False)
        else: self.checkbox_tilepreview.setEnabled(True)

    def toggleEnabled(self, state):
        state = not state
        if not state:
            self.numGridX_label.setEnabled(state)
            self.numGridX_textedit.setEnabled(state)
            self.numGridY_label.setEnabled(state)
            self.numGridY_textedit.setEnabled(state)
            self.overlap_label.setEnabled(state)
            self.overlap_textedit.setEnabled(state)
            self.checkbox_tiling.setEnabled(state)
            self.checkbox_tilepreview.setEnabled(state)

        if state:
            self.numGridX_label.setEnabled(state)
            self.numGridX_textedit.setEnabled(state)
            self.numGridY_label.setEnabled(state)
            self.numGridY_textedit.setEnabled(state)
            self.overlap_label.setEnabled(state)
            self.overlap_textedit.setEnabled(state)
            self.checkbox_tiling.setEnabled(state)

            if self.checkbox_tiling.checkState()==2:
                self.checkbox_tilepreview.setEnabled(True)
            if self.checkbox_tiling.checkState()==0:
                self.checkbox_tilepreview.setEnabled(False)

    def initTilingInfo(self):
        self.numGridX_textedit.setText("1")
        self.numGridY_textedit.setText("1")
        self.overlap_textedit.setText("0.1")
        self.sigTilingInfoChanged.emit('Tiling Settings',"Tiling Checkbox", '0') # Checkboxes initialize a little different from QLineEdit. This sends a signal to register value with sharedAttrs
        self.sigTilingInfoChanged.emit('Tiling Settings',"Tiling Preview", '0')

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
