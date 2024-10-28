from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
import napari

class ZStackWidget(NapariHybridWidget):



    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        timingLayout = QtWidgets.QGridLayout()
        self.setLayout(timingLayout)

        self.timingPeriod_label = QLabel("ZStack")

        row = 0
        timingLayout.addWidget(self.timingPeriod_label, row, 0)



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
