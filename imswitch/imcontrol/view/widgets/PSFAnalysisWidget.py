import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtWidgets
from pyqtgraph.parametertree import ParameterTree
from imswitch.imcontrol.view import guitools
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from imswitch.imcommon.model import initLogger
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,QFileDialog,
                             QCheckBox, QLabel, QLineEdit, QDialog)
import json
import os
import threading
from PIL import Image


class PSFAnalysisWidget(NapariHybridWidget):
    """ Widget containing InfoGathering interface. """
    # sigSaveSettings = QtCore.Signal()
    # sigSettingsDialog = QtCore.Signal()

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        self.loadingPopup = PSFWindow(self)

        # Main widget 
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.loadSettings = QPushButton("PSF Analysis Popup window")
        self.layout.addWidget(self.loadSettings, 1, 0)


        self.loadSettings.clicked.connect(self.openLoadWindowThread)
        # self.saveSettings.clicked.connect(self.saveFileDialog)

    def toggleLoadButton(self, state):
        state = not state
        self.loadSettings.setEnabled(state)

   
    def openLoadWindowThread(self):
        threading.Thread(target=self.openLoadWindow(), args=(), daemon=True).start()

    def openLoadWindow(self):
        self.loadingPopup.show()

class PSFWindow(QMainWindow):
    def __init__(self, parent = None): 
        super().__init__(parent) 
        self.init_gui() 
  
    def init_gui(self): 
        self.window = QtWidgets.QWidget() 
        self.layout = QtWidgets.QGridLayout() 
        self.setCentralWidget(self.window) 
        self.window.setLayout(self.layout) 
  
        self.setWindowTitle("PSF analysis window")
  
        self.slmFrame = pg.GraphicsLayoutWidget()
        self.slmFrame.setEnabled(False)
        self.slmFrame.addLabel('Z-Stack of images', angle=-90, row=0, col=0)
        self.vbZernike = self.slmFrame.addViewBox(row=0, col=1, enableMouse=False, border='w', lockAspect=True)

        self.imgZernike = pg.ImageItem()
        self.matrixZernike = np.zeros((1920, 1080))
        self.imgZernike.setImage(self.matrixZernike, levels=(0, 255))
        self.vbZernike.addItem(self.imgZernike)

        self.layout.addWidget(self.slmFrame, 1, 0, 2, 6)

        


        self.folderPath = QtWidgets.QLineEdit()
        self.openDialog = QPushButton("Select folder")
        self.displayImages = QPushButton("Show images")
        

        self.layout.addWidget(self.folderPath, 3, 0)
        self.layout.addWidget(self.openDialog, 3, 1)
        self.layout.addWidget(self.displayImages, 3, 2)
        

        self.openDialog.clicked.connect(self.loadPath)
        self.displayImages.clicked.connect(self.displayStackOfImages)

        self.stackOfImages = np.zeros((512,512,10))
        self.current_index_Z = 0
    #     self.vbZernike.scene().sigWheelEvent.connect(self.on_scroll_XY)

    # def on_scroll_XY(self, event):
    #     global current_index_Z

    #     if event.step > 0 and (current_index_Z + 1) < self.stackOfImages.shape[0]:  # Scroll up
    #         current_index_Z = (current_index_Z + 1)
    #     elif event.step < 0 and (current_index_Z - 1) >= 0:  # Scroll down
    #         current_index_Z = (current_index_Z - 1)
    #     else:
    #         pass
    #     self.imgZernike.setImage(self.stackOfImages[current_index_Z,:,:], levels=(0,255))
    #     #figPSFxy.canvas.draw_idle()

    #     #self.imgZernike.canvas.mpl_connect('scroll_event', on_scroll_XY)
        


    def loadPath(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        self.folderPath.setText(folderpath)

    def displayStackOfImages(self):
        liststackOfImages = []

        for file in os.listdir(self.folderPath.text()):
            im = Image.open(os.path.join(self.folderPath.text(), file))
            imarray = np.array(im)
            liststackOfImages.append(imarray)

        self.stackOfImages = np.array(liststackOfImages)
        self.imgZernike.setImage(self.stackOfImages[0,:,:], levels=(0,255))

    

    

    # def toggleLoadButton(self, state):
    #     state = not state
    #     self.loadSettings.setEnabled(state)


    
        

# Copyright (C) 2020-2023 ImSwitch developers
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
