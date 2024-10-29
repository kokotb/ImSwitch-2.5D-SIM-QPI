from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
import napari

class TimingWidget(NapariHybridWidget):

    sigTimingInfoChanged = QtCore.Signal(str, str, str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        timingLayout = QtWidgets.QGridLayout()
        self.setLayout(timingLayout)

        self.timingPeriod_label = QLabel("Timing Period")
        self.timingPeriod_textedit = QLineEdit("")
        self.timingPeriod_textedit.setPlaceholderText('blank is max frame rate')
        self.timingPeriod_textedit.textChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Timing Period', value))
        self.timingUnit = QtWidgets.QComboBox()
        
        self.timingUnit.currentTextChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Timing Unit', value))
        row = 0
        timingLayout.addWidget(self.timingPeriod_label, row, 0)
        timingLayout.addWidget(self.timingPeriod_textedit, row, 1)
        timingLayout.addWidget(self.timingUnit, row, 2)

    # def getPeriodInSec(self):
    #     timingPeriodBox = self.timingPeriod_textedit.text()
    #     timingUnit = self.timingUnit.currentText()
    #     if timingUnit == 's':
    #         timingSecs = timingPeriodBox
    #     elif timingUnit == 'm':
    #         timingSecs = timingPeriodBox * 60
    #     elif timingUnit == 'h':
    #         timingSecs = timingPeriodBox * 3600
    #     return timingSecs
    
    def populateUnitsList(self):
        self.timingUnit.addItems(['s', 'm','h'])
        

        



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
