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
    sigAddROI = QtCore.Signal()

    def __post_init__(self):
        # super().__init__(*args, **kwargs)

        listLayout = QtWidgets.QVBoxLayout()

        self.ROIList = QListWidget()
        # QListWidgetItem("ROI 1", self.ROIList)
        # QListWidgetItem("ROI 2", self.ROIList)
        # QListWidgetItem("ROI 3", self.ROIList)
        listLayout.addWidget(self.ROIList)


        buttonLayout = QtWidgets.QVBoxLayout()

        self.addButton = QPushButton("Add")
        buttonLayout.addWidget(self.addButton)
        self.delButton = QPushButton("Delete")
        buttonLayout.addWidget(self.delButton)
        self.upButton = QPushButton("Move Up")
        buttonLayout.addWidget(self.upButton)
        self.downButton = QPushButton("Move Down")
        buttonLayout.addWidget(self.downButton)
        self.gotoButton = QPushButton("Go To")
        buttonLayout.addWidget(self.gotoButton)

        overallLayout = QtWidgets.QHBoxLayout()
        self.setLayout(overallLayout)

        overallLayout.addLayout(listLayout)
        overallLayout.addLayout(buttonLayout)


        self.delButton.clicked.connect(self.delItem)
        self.upButton.clicked.connect(self.moveUp)
        self.downButton.clicked.connect(self.moveDown)
        # self.gotoButton.clicked.connect(self.functiontogetintowidget)
        self.addButton.clicked.connect(self.sigAddROI.emit)


    # def functiontogetintowidget(self):
    #     print('made it')

    def addROI(self, name):
        self.ROIList.addItem(name)


    def getCurrentIndex(self):
        currentIndex = self.ROIList.currentRow()
        return currentIndex
    
    def delItem(self):
        currentIndex = self.ROIList.currentRow()
        self.ROIList.takeItem(currentIndex)

    def moveUp(self):
        currentIndex = self.ROIList.currentRow()
        newIndex = currentIndex - 1
        currentName = self.ROIList.currentItem().text()
        if currentIndex != 0:
            self.ROIList.takeItem(currentIndex)
            self.ROIList.insertItem(newIndex, currentName)
            self.ROIList.setCurrentRow(newIndex)

    def moveDown(self):
        currentIndex = self.ROIList.currentRow()
        newIndex = currentIndex + 1
        currentName = self.ROIList.currentItem().text()
        count = self.ROIList.count()
        if (currentIndex + 1) < count:
            self.ROIList.takeItem(currentIndex)
            self.ROIList.insertItem(newIndex, currentName)
            self.ROIList.setCurrentRow(newIndex)

    def getCurrentName(self):
        currentName = self.ROIList.currentItem().text()
        return currentName

    
        



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
