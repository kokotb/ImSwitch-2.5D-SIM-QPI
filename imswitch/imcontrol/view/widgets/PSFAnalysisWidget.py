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
from PIL import Image, ImageDraw


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

class MovableScatterPlotItem(pg.ScatterPlotItem):
    def __init__(self, *args, imageSizeXy, **kargs):
        super().__init__(*args, **kargs)
        self.target = pg.TargetItem()
        self.target.setParentItem(self)
        self.target.sigPositionChanged.connect(self.targetMoved)
        self.target.hide()
        self.selectedPoint = None
        self.coordinateLabel = pg.TextItem()
        self.coordinateLabel.setParentItem(self.target)
        self.coordinateLabel.setAnchor((0, 1))
        self.imageSizeXy = imageSizeXy

    def boundingRect(self):
        return QtCore.QRectF(0, 0, *self.imageSizeXy)

    def targetMoved(self, target):
        if self.target.isVisible() and self.selectedPoint is not None:
            self.data[["x", "y"]][self.selectedPoint.index()] = tuple(target.pos())
            self.updateSpots()
            self.invalidate()
            label = f"{tuple(map(lambda el: round(el, 2), target.pos()))}"
            self.coordinateLabel.setHtml("<div style='color: red; background: black;'>%s</div>" % label)

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            points = self.pointsAt(ev.pos())
            if len(points):
                self.target.setPos(ev.pos())
                self.selectedPoint = points[-1]
                self.target.show()
                ev.accept()
        elif ev.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.target.isVisible():
                self.target.hide()
            else:
                newData = np.r_[np.c_[self.getData()], np.atleast_2d(ev.pos())]
                self.setData(*newData.T)
            ev.accept()
        else:
            super().mouseClickEvent(ev)

class PSFWindow(QMainWindow):
    def __init__(self, parent = None): 
        super().__init__(parent) 
        self.init_gui() 
  
    def init_gui(self): 
        self.psfLayout = QtWidgets.QHBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(self.psfLayout) # self.psfLayout is main layout
        self.setCentralWidget(central_widget)
        self.setWindowTitle("PSF analysis window")


        # Z Stack Layout - displays whole stack of images at full size (512x512 usually) =====================================
        self.ZstackLayout = QtWidgets.QGridLayout()
  
        self.zStackFrame = pg.GraphicsLayoutWidget()
        self.zStackFrame.setEnabled(False)
        self.zStackFrame.addLabel('Z-Stack of images', angle=-90, row=0, col=0)
        self.zStackFrame.setMinimumSize(500, 500)
        self.vbZStack = self.zStackFrame.addViewBox(row=0, col=1, enableMouse=False, border='w', lockAspect=True)

        self.imgZStack = pg.ImageItem()
        self.vbZStack.addItem(self.imgZStack)

        self.image_stack = np.zeros((512,512,10))
        self.current_index = 0     # scroll through whole Zstack
        # self.imgZStack.setImage(self.image_stack[self.current_index], levels=(0, 255))
        self.vbZStack.addItem(self.imgZStack)
        
        self.labelPSFviewSize = QtWidgets.QLabel(f'<strong>PSF view image size</strong>')
        self.ZstackLayout.addWidget(self.labelPSFviewSize, 4, 0)
        self.PSFViewSize = QtWidgets.QLineEdit("20")
        self.ZstackLayout.addWidget(self.PSFViewSize, 4, 1)

        self.ZstackLayout.addWidget(self.zStackFrame, 1, 0, 2, 16)

        self.folderPath = QtWidgets.QLineEdit()
        self.folderPath.setText("C:/Users/SIM/Desktop/David/PSF_analysis_algorithm/PSFExample/green")
        self.openDialog = QPushButton("Select folder")
        self.displayImages = QPushButton("Show images")

        self.ZstackLayout.addWidget(self.folderPath, 3, 0)
        self.ZstackLayout.addWidget(self.openDialog, 3, 1)
        self.ZstackLayout.addWidget(self.displayImages, 3, 2)

        self.openDialog.clicked.connect(self.loadPath)
        self.displayImages.clicked.connect(self.displayStackOfImages)

        self.psfLayout.addLayout(self.ZstackLayout)
        # ====================================================================================================================





        # PSF view - displays wchosen area of images at custom size (20x20 usually), xy, xz and yz ===========================
        self.PSFViewLayout = QtWidgets.QHBoxLayout()

        # XY PSF projection view
        self.PSFXYFrame = pg.GraphicsLayoutWidget()
        self.PSFXYFrame.setEnabled(False)
        self.PSFXYFrame.addLabel('XY - PSF View', angle=-90, row=0, col=0)
        self.PSFXYFrame.setMinimumSize(400, 400)
        self.vbPSFXY = self.PSFXYFrame.addViewBox(row=0, col=1, enableMouse=False, border='w', lockAspect=True)

        self.imgPSFXY = pg.ImageItem()
        self.imgPSFXY.setImage(np.zeros((512, 512)))
        self.vbPSFXY.addItem(self.imgPSFXY)

        # XZ PSF projection view
        self.PSFXZFrame = pg.GraphicsLayoutWidget()
        self.PSFXZFrame.setEnabled(False)
        self.PSFXZFrame.addLabel('XZ - PSF View', angle=-90, row=0, col=0)
        self.PSFXZFrame.setMinimumSize(400, 200)
        self.vbPSFXZ = self.PSFXZFrame.addViewBox(row=0, col=1, enableMouse=False, border='w', lockAspect=True)

        self.imgPSFXZ = pg.ImageItem()
        self.imgPSFXZ.setImage(np.zeros((512, 512)))
        self.vbPSFXZ.addItem(self.imgPSFXZ)

        # YZ PSF projection view
        self.PSFYZFrame = pg.GraphicsLayoutWidget()
        self.PSFYZFrame.setEnabled(False)
        self.PSFYZFrame.addLabel('YZ - PSF View', angle=-90, row=0, col=0)
        self.PSFYZFrame.setMinimumSize(400, 200)
        self.vbPSFYZ = self.PSFYZFrame.addViewBox(row=0, col=1, enableMouse=False, border='w', lockAspect=True)

        self.imgPSFYZ = pg.ImageItem()
        self.imgPSFYZ.setImage(np.zeros((512, 512)))
        self.vbPSFYZ.addItem(self.imgPSFYZ)


        self.PSFViewLayout.addWidget(self.PSFXYFrame)
        self.PSFViewLayout.addWidget(self.PSFXZFrame)
        self.PSFViewLayout.addWidget(self.PSFYZFrame)

        self.psfLayout.addLayout(self.PSFViewLayout)
        # ====================================================================================================================

        # 3D array for PSF view (cropped zstack)
        self.PSFstack = np.zeros((20,20,10))

        # Center of PSF, selected by clicking on zstack image pixel
        self.selectedX = 0
        self.selectedY = 0
        self.selectedZ = 0

        # Current projection coordinates in PSF view
        self.current_indexX = 0
        self.current_indexY = 0
        self.current_indexZ = 0


        # Lines in psf view to locate position while scrolling thgough a stack ============================
        self.overlayMatrixXY =  np.zeros((512, 512))
        self.overlayImgXY = pg.ImageItem(self.overlayMatrixXY)
        self.vbPSFXY.addItem(self.overlayImgXY)

        self.overlayMatrixXZ =  np.zeros((512, 512))
        self.overlayImgXZ = pg.ImageItem(self.overlayMatrixXZ)
        self.vbPSFXZ.addItem(self.overlayImgXZ)

        self.overlayMatrixYZ =  np.zeros((512, 512))
        self.overlayImgYZ = pg.ImageItem(self.overlayMatrixYZ)
        self.vbPSFYZ.addItem(self.overlayImgYZ)
        


    def updateZstackImage(self):
        self.imgZStack.setImage(self.image_stack[self.current_index], levels=(0, 255))

    def updatePSFXYimage(self):
        self.imgPSFXY.setImage(self.PSFstack[self.current_indexZ, :, :], levels=(0, 255))
        self.updatelines()

    def updatePSFXZimage(self):
        self.imgPSFXZ.setImage(np.rot90(self.PSFstack[:, self.current_indexY, :]), levels=(0, 255))
        self.updatelines()

    def updatePSFYZimage(self):
        self.imgPSFYZ.setImage(np.rot90(self.PSFstack[:, :, self.current_indexX]), levels=(0, 255))
        self.updatelines()



    def updatelines(self):
        shape = np.shape(self.PSFstack)
        linescale = 9
        linewidth = 1
        shapeX, shapeY, shapeZ = (linescale*shape[2], linescale*shape[1], linescale*shape[0])

        currX = linescale*self.current_indexX + linescale // 2
        currY = linescale*self.current_indexY + linescale // 2
        currZ = linescale*self.current_indexZ + linescale // 2

        imXY = Image.new('RGBA', (shapeX, shapeY), (0, 0, 0, 0))
        drawXY = ImageDraw.Draw(imXY)
        drawXY.line([(currX,0), (currX, shapeY)], fill=(255, 255, 0), width=linewidth)
        drawXY.line([(0, currY), (shapeX, currY)], fill=(255, 0, 255), width=linewidth)
        centerArrayXY = np.array(imXY)
        self.overlayImgXY.setImage(centerArrayXY)
        self.overlayImgXY.setRect(0, 0, shape[2], shape[1])

        imXZ = Image.new('RGBA', (shapeZ, shapeX), (0, 0, 0, 0))
        drawXZ = ImageDraw.Draw(imXZ)
        drawXZ.line([(0, shapeX - currX), (shapeZ, shapeX - currX)], fill=(255, 255, 0), width=linewidth)
        drawXZ.line([(currZ, 0), (currZ, shapeX)], fill=(0, 255, 255), width=linewidth)
        centerArrayXZ = np.array(imXZ)
        self.overlayImgXZ.setImage(centerArrayXZ)
        self.overlayImgXZ.setRect(0, 0, shape[2], shape[0])

        imYZ = Image.new('RGBA', (shapeZ, shapeY), (0, 0, 0, 0))
        drawYZ = ImageDraw.Draw(imYZ)
        drawYZ.line([(0, shapeY - currY), (shapeZ, shapeY - currY)], fill=(255, 0, 255), width=linewidth)
        drawYZ.line([(currZ, 0), (currZ, shapeY)], fill=(0, 255, 255), width=linewidth)
        centerArrayYZ = np.array(imYZ)
        self.overlayImgYZ.setImage(centerArrayYZ)
        self.overlayImgYZ.setRect(0, 0, shape[1], shape[0])

    def updateYline(self):
        pass

    def updateXline(self):
        pass

    """def wheelEvent(self, event):
        pos = event.position() # mouse position  

        mappedposZstack = self.vbZStack.mapFromScene(pos)  #positions, bounds of all images
        boundsZstack = self.vbZStack.boundingRect()  
        mappedposPSFXY = self.vbPSFXY.mapFromScene(pos)  
        boundsPSFXY = self.vbPSFXY.sceneBoundingRect()
        mappedposPSFXZ = self.vbPSFXZ.mapFromScene(pos)  
        boundsPSFXZ = self.vbPSFXZ.boundingRect()
        mappedposPSFYZ = self.vbPSFYZ.mapFromScene(pos)  
        boundsPSFYZ = self.vbPSFYZ.boundingRect()

        print(pos, mappedposPSFXY, boundsPSFXY)
        
        if boundsZstack.contains(mappedposZstack):
            num_degrees = event.angleDelta().y() / 120  
            new_index = self.current_index - int(num_degrees)
            self.current_index = max(0, min(len(self.image_stack) - 1, new_index))
            self.updateZstackImage()
        elif boundsPSFXY.contains(mappedposPSFXY):
            num_degrees = event.angleDelta().y() / 120  
            new_index = self.current_indexZ - int(num_degrees)
            self.current_indexZ = max(0, min(len(self.PSFstack.shape[0]) - 1, new_index))
            self.updatePSFXYimage()
        elif boundsPSFXZ.contains(mappedposPSFXZ):
            num_degrees = event.angleDelta().y() / 120  
            new_index = self.current_indexY - int(num_degrees)
            self.current_indexY = max(0, min(len(self.PSFstack.shape[1]) - 1, new_index))
            self.updatePSFXZimage()
        elif boundsPSFYZ.contains(mappedposPSFYZ):
            num_degrees = event.angleDelta().y() / 120  
            new_index = self.current_indexX - int(num_degrees)
            self.current_indexX = max(0, min(len(self.PSFstack.shape[2]) - 1, new_index))
            self.updatePSFYZimage()
        else:
            pass"""
    
    def wheelEvent(self, event):
        global_pos = event.globalPosition()  

        viewbox_global_pos_Zstack = self.vbZStack.scene().views()[0].mapToGlobal(QtCore.QPoint(0, 0))
        viewbox_global_pos_PSFXY = self.vbPSFXY.scene().views()[0].mapToGlobal(QtCore.QPoint(0, 0))
        viewbox_global_pos_PSFXZ = self.vbPSFXZ.scene().views()[0].mapToGlobal(QtCore.QPoint(0, 0))
        viewbox_global_pos_PSFYZ = self.vbPSFYZ.scene().views()[0].mapToGlobal(QtCore.QPoint(0, 0))

        local_pos_Zstack = global_pos - viewbox_global_pos_Zstack
        local_pos_PSFXY = global_pos - viewbox_global_pos_PSFXY
        local_pos_PSFXZ = global_pos - viewbox_global_pos_PSFXZ
        local_pos_PSFYZ = global_pos - viewbox_global_pos_PSFYZ

        if self.vbZStack.boundingRect().contains(local_pos_Zstack):
            num_degrees = event.angleDelta().y() / 120  
            new_index = self.current_index - int(num_degrees)
            self.current_index = max(0, min(len(self.image_stack) - 1, new_index))
            self.updateZstackImage()
        elif self.vbPSFXY.boundingRect().contains(local_pos_PSFXY):
            num_degrees = event.angleDelta().y() / 120  
            new_index = self.current_indexZ - int(num_degrees)
            self.current_indexZ = max(0, min(self.PSFstack.shape[0] - 1, new_index))
            self.updatePSFXYimage()
        elif self.vbPSFXZ.boundingRect().contains(local_pos_PSFXZ):
            num_degrees = event.angleDelta().y() / 120  
            new_index = self.current_indexY - int(num_degrees)
            self.current_indexY = max(0, min(self.PSFstack.shape[1] - 1, new_index))
            self.updatePSFXZimage()
        elif self.vbPSFYZ.boundingRect().contains(local_pos_PSFYZ):
            num_degrees = event.angleDelta().y() / 120  
            new_index = self.current_indexX - int(num_degrees)
            self.current_indexX = max(0, min(self.PSFstack.shape[2] - 1, new_index))
            self.updatePSFYZimage()
        else:
            pass

    

    def loadPath(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        self.folderPath.setText(folderpath)

    def displayStackOfImages(self):
        liststackOfImages = []

        for file in os.listdir(self.folderPath.text()):
            im = Image.open(os.path.join(self.folderPath.text(), file))
            imarray = np.array(im)
            liststackOfImages.append(imarray)

        self.image_stack = np.array(liststackOfImages)
        self.imgZStack.setImage(self.image_stack[0,:,:], levels=(0,255))

    def mouseReleaseEvent(self, event):
        if self.imgZStack.image is None:
            return

        pos = event.pos()
        mapped_pos = self.imgZStack.mapFromScene(pos)

        self.selectedX = int(mapped_pos.y())
        self.selectedY = int(mapped_pos.x())

        #if 0 <= x < self.image_stack.shape[2] and 0 <= y < self.image_stack.shape[1]:
        # print(f"Clicked on coordinates: ({self.selectedX}, {self.selectedY})")

        self.showSelectedPSF()

    def showSelectedPSF(self):
        self.current_indexZ = self.current_index
        # range for PSFstack is shifted manually, does not work if window size is changed

        PSFviewsize = int(self.PSFViewSize.text())
        self.PSFstack = self.image_stack[:, self.selectedY - 12 - PSFviewsize//2: self.selectedY -12 + PSFviewsize//2, self.selectedX - PSFviewsize//2 + 12 : self.selectedX + PSFviewsize//2 + 12]
        self.imgPSFXY.setImage(self.PSFstack[self.current_indexZ, :, :], levels=(0, 255))
        self.imgPSFXZ.setImage(np.rot90(self.PSFstack[:, self.current_indexY, :]), levels=(0, 255))
        self.imgPSFYZ.setImage(np.rot90(self.PSFstack[:, :, self.current_indexX]), levels=(0, 255))
        self.updatelines()
    

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
