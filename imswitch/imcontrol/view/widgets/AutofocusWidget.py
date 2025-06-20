from qtpy import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QLineEdit, QLabel, QMainWindow, QWidget, QApplication)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen
import threading
import numpy as np


class AutofocusWidget(NapariHybridWidget):

    sigAutofocusInfoChanged = QtCore.Signal(str, str, str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        blankImage = np.zeros((1280,1024))
        self.AFWindow = SetAFWindow()
        self.clickableImage = ClickableImage(blankImage)
        autofocusLayout = QtWidgets.QGridLayout()
        self.setLayout(autofocusLayout)

        self.openPreview = QtWidgets.QPushButton('Open AF Preview')

        row = 0
        autofocusLayout.addWidget(self.openPreview, row, 0)
        self.AFWindow.clearAnnotations.clicked.connect(self.clearAnnot)


    def initValues(self):
        pass

    def openSetAFWindow(self):
        self.AFWindow.show()

    def clearAnnot(self):
        self.clickableImage.clearAnnot()


class SetAFWindow(QMainWindow):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("Open AF Preview")
        self.setGeometry(100, 100, 1280, 1024)

        afWindowLayout = QtWidgets.QVBoxLayout()
        buttonLayout = QtWidgets.QHBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(afWindowLayout)
        self.setCentralWidget(central_widget)

        blankImage = np.zeros((1280,1024))

        self.acqImgButton = QtWidgets.QPushButton('Refresh Image')
        buttonLayout.addWidget(self.acqImgButton)
        self.clearAnnotations = QtWidgets.QPushButton('Clear Annotations')
        buttonLayout.addWidget(self.clearAnnotations)

        self.label = ClickableImage(blankImage)

        afWindowLayout.addLayout(buttonLayout)
        afWindowLayout.addWidget(self.label)



    def convert_ndarray_to_qpixmap(self, image: np.ndarray) -> QPixmap:
        h, w = image.shape
        q_image = QImage(image.data, w, h, w, QImage.Format_Grayscale8)

        return QPixmap.fromImage(q_image)

class ClickableImage(QLabel):
    def __init__(self, image_np):
        super().__init__()
        self.painted = False
        # Convert NumPy image to QImage and then to QPixmap
        self.image_np = image_np
        self.pixelmap = self.convert_ndarray_to_qpixmap(self.image_np)

        self.setPixmap(self.pixelmap)
        self.setScaledContents(True)  # Ensure image scales with widget
        self.annotation_points = []
        self.lastClick = (0,0,100,100) #Left,Top,width,height of last image click.

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.repaintAnnot()
            x = event.pos().x()
            y = event.pos().y()

            # Account for scaling
            scaled_w = self.width()
            scaled_h = self.height()
            img_h, img_w = self.image_np.shape

            # Map widget coordinates to image coordinates
            img_x = int(x * img_w / scaled_w)
            img_y = int(y * img_h / scaled_h)

            # Clip to image bounds
            img_x = min(max(img_x, 0), img_w - 1)
            img_y = min(max(img_y, 0), img_h - 1)

            windowSize = 100
            top = img_y - windowSize/2
            left = img_x - windowSize/2
            width = windowSize
            height = windowSize

            if not self.painted:
                self.annotation_points.append(event.pos())
                self.update()  # Trigger repaint
                self.lastClick = (left,top,width,height)
                self.painted = True
      

            print(f"Click data: {self.lastClick}")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(Qt.red, 3)
        painter.setPen(pen)
        for point in self.annotation_points:
            painter.drawRect(point.x() - 50, point.y() - 50, 100, 100)


    def repaintAnnot(self):
        self.annotation_points = []
        self.update()
        self.painted = False

    def convert_ndarray_to_qpixmap(self, image: np.ndarray) -> QPixmap:
        h, w = image.shape
        q_image = QImage(image.data, w, h, w, QImage.Format_Grayscale8)

        return QPixmap.fromImage(q_image)


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
