from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame, QListWidget,QListWidgetItem)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt

class ROIWidget(NapariHybridWidget):

    sigROIInfoChanged = QtCore.Signal(str, str, str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)

        overallLayout = QtWidgets.QVBoxLayout()

        self.setLayout(overallLayout)

        ROIList = QListWidget()
        QListWidgetItem("ROI 1", ROIList)
        QListWidgetItem("ROI 2", ROIList)
        QListWidgetItem("ROI 3", ROIList)
        overallLayout.addWidget(ROIList)

        # self.saveSettings = QPushButton("Test")
        # overallLayout.addWidget(self.saveSettings)
        



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
