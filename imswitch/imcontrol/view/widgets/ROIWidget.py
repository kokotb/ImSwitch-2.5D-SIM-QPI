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

    sigROIInfoChanged = QtCore.Signal(str, str, list)
    sigAddROI = QtCore.Signal()
    sigReplaceROI = QtCore.Signal()

    def __post_init__(self):
        # super().__init__(*args, **kwargs)

        listLayout = QtWidgets.QVBoxLayout()

        self.ROIList = QListWidget()
        # self.ROIList.setMaximumWidth(100)

        listLayout.addWidget(self.ROIList)


        buttonLayout = QtWidgets.QVBoxLayout()

        self.addButton = QPushButton("Add")
        self.addButton.setMinimumHeight(50)
        buttonLayout.addWidget(self.addButton)
        self.replaceButton = QPushButton("Replace")
        self.replaceButton.setMinimumHeight(50)
        buttonLayout.addWidget(self.replaceButton)
        self.delButton = QPushButton("Delete")
        self.delButton.setMinimumHeight(50)
        buttonLayout.addWidget(self.delButton)
        self.upButton = QPushButton("Move Up")
        self.upButton.setMinimumHeight(50)
        buttonLayout.addWidget(self.upButton)
        self.downButton = QPushButton("Move Down")
        self.downButton.setMinimumHeight(50)
        buttonLayout.addWidget(self.downButton)
        self.gotoButton = QPushButton("Go To")
        self.gotoButton.setMinimumHeight(50)
        buttonLayout.addWidget(self.gotoButton)
        # self.replaceButton = QPushButton("Replace")
        # buttonLayout.addWidget(self.replaceButton)

        # self.scanROIList = QCheckBox('Scan ROIs')
        # buttonLayout.addWidget(self.scanROIList)

        overallLayout = QtWidgets.QVBoxLayout()
        self.setLayout(overallLayout)

        overallLayout.addLayout(listLayout)
        overallLayout.addLayout(buttonLayout)


        self.delButton.clicked.connect(self.delItem)
        self.upButton.clicked.connect(self.moveUp)
        self.downButton.clicked.connect(self.moveDown)
        self.addButton.clicked.connect(self.sigAddROI.emit)
        self.replaceButton.clicked.connect(self.sigReplaceROI.emit)

        self.delButton.clicked.connect(self.getListAllROIs)
        self.upButton.clicked.connect(self.getListAllROIs)
        self.downButton.clicked.connect(self.getListAllROIs)
        self.addButton.clicked.connect(self.getListAllROIs)



    # def functiontogetintowidget(self):
    #     print('made it')

    # def initSharedAttributes(self):
    #      self.scanROIList.setChecked(False)

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
        if currentIndex > 0:
            currentName = self.ROIList.currentItem().text()
            self.ROIList.takeItem(currentIndex)
            self.ROIList.insertItem(newIndex, currentName)
            self.ROIList.setCurrentRow(newIndex)

    def moveDown(self):
        currentIndex = self.ROIList.currentRow()
        newIndex = currentIndex + 1
        count = self.ROIList.count()
        if (currentIndex + 1) < count:
            currentName = self.ROIList.currentItem().text()
            self.ROIList.takeItem(currentIndex)
            self.ROIList.insertItem(newIndex, currentName)
            self.ROIList.setCurrentRow(newIndex)

    def getCurrentName(self):
        try:
            currentName = self.ROIList.currentItem().text()
        except AttributeError:
            currentName = None
        return currentName
    
    def getListAllROIs(self):
        roiCount = self.ROIList.count()
        roiList = []
        for i in range(roiCount):
            currentName = self.ROIList.item(i).text()
            roiList.append([i,currentName])
        self.sigROIInfoChanged.emit('ROI List', 'List', roiList)

        return roiList

    
        



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
