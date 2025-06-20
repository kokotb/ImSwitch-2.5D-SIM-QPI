from qtpy import QtCore, QtWidgets
from PyQt5.QtWidgets import (QCheckBox, QLineEdit, QLabel, QMainWindow, QWidget, QApplication)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QImage, QPixmap
import threading
import numpy as np


class AutofocusWidget(NapariHybridWidget):

    sigAutofocusInfoChanged = QtCore.Signal(str, str, str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        self.AFWindow = SetAFWindow()
        autofocusLayout = QtWidgets.QGridLayout()
        self.setLayout(autofocusLayout)

        self.openPreview = QtWidgets.QPushButton('Set AF ROI')

        row = 0
        autofocusLayout.addWidget(self.openPreview, row, 0)

        

    def initValues(self):
        pass




    def openSetAFWindow(self):
        self.AFWindow.show()

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

        self.displyImage = self.convert_ndarray_to_qpixmap(np.zeros((1280,1024)))

        self.acqImgButton = QtWidgets.QPushButton('Acquire Image')
        buttonLayout.addWidget(self.acqImgButton)

        self.label = QLabel()
        self.label.setPixmap(self.displyImage)
        self.label.setScaledContents(True)

        afWindowLayout.addLayout(buttonLayout)
        afWindowLayout.addWidget(self.label)



    def convert_ndarray_to_qpixmap(self, image: np.ndarray) -> QPixmap:
        """Convert a NumPy RGB or BGR image to QPixmap."""
        if image.ndim == 2:
            # Grayscale
            h, w = image.shape
            q_image = QImage(image.data, w, h, w, QImage.Format_Grayscale8)
        else:
            raise ValueError("Unsupported image format")

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
