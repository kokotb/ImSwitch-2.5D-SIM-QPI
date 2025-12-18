import numpy as np
from math import floor
from qtpy import QtGui
from pyqtgraph.parametertree import ParameterTree, Parameter
from qtpy import QtCore, QtWidgets
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QCheckBox, QMainWindow, QWidget, QLineEdit, QPushButton, QLabel
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush, QPainter, QFont
from imswitch.imcommon.model import shortcut
from imswitch.imcommon.view.guitools import naparitools
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
import cv2

class CamParamTree(ParameterTree):
    """ Making the ParameterTree for configuration of the detector during imaging
    """

    def __init__(self, detectorParameters, detectorActions, supportedBinnings, roiInfos,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        BinTip = ("Sets binning mode. Binning mode specifies if and how \n"
                  "many pixels are to be read out and interpreted as a \n"
                  "single pixel value.")

        # Parameter tree for the detector configuration
        params = [{'name': 'Model', 'type': 'str', 'readonly': True},
                  {'name': 'Image frame', 'type': 'group', 'children': [
                      {'name': 'Binning', 'type': 'list', 'value': 1,
                       'values': supportedBinnings, 'tip': BinTip},
                      {'name': 'Mode', 'type': 'list', 'value': 'Custom',
                       'values': ['Custom']  + list(roiInfos.keys())},
                      {'name': 'X0', 'type': 'int', 'value': 0, 'limits': (0, 5312)},
                      {'name': 'Y0', 'type': 'int', 'value': 0, 'limits': (0, 4598)},
                      {'name': 'Width', 'type': 'int', 'value': 1, 'limits': (1, 5320)},
                      {'name': 'Height', 'type': 'int', 'value': 1, 'limits': (1, 4600)},
                      {'name': 'Apply', 'type': 'action', 'title': 'Apply'},
                      {'name': 'New ROI', 'type': 'action', 'title': 'New ROI'},
                      {'name': 'Abort ROI', 'type': 'action', 'title': 'Abort ROI'},
                      {'name': 'Save mode', 'type': 'action',
                       'title': 'Save current parameters as mode'},
                      {'name': 'Delete mode', 'type': 'action',
                       'title': 'Remove current mode from list'},
                      {'name': 'Update all detectors', 'type': 'bool', 'value': False}
                  ]}]

        detectorParamGroups = {}
        for detectorParameterName, detectorParameter in detectorParameters.items():
            if detectorParameter.group not in detectorParamGroups:
                # Create group
                detectorParamGroups[detectorParameter.group] = {
                    'name': detectorParameter.group, 'type': 'group', 'children': []
                }

            detectorParameterType = type(detectorParameter).__name__
            if detectorParameterType == 'DetectorNumberParameter':
                pyqtParam = {
                    'name': detectorParameterName,
                    'type': 'float',
                    'value': detectorParameter.value,
                    'readonly': not detectorParameter.editable,
                    'siPrefix': detectorParameter.valueUnits in ['s'],
                    'suffix': detectorParameter.valueUnits,
                    'decimals': 5
                }
            elif detectorParameterType == 'DetectorListParameter':
                pyqtParam = {
                    'name': detectorParameterName,
                    'type': 'list',
                    'value': detectorParameter.value,
                    'readonly': not detectorParameter.editable,
                    'values': detectorParameter.options
                }
            else:
                raise TypeError(f'Unsupported detector parameter type "{detectorParameterType}"')

            detectorParamGroups[detectorParameter.group]['children'].append(pyqtParam)

        for detectorActionName, detectorAction in detectorActions.items():
            if detectorAction.group not in detectorParamGroups:
                # Create group
                detectorParamGroups[detectorAction.group] = {
                    'name': detectorAction.group, 'type': 'group', 'children': []
                }

            detectorParamGroups[detectorAction.group]['children'].append(
                {'name': detectorActionName, 'type': 'action', 'title': detectorActionName}
            )

        params += list(detectorParamGroups.values())

        self.p = Parameter.create(name='params', type='group', children=params)
        self.setParameters(self.p, showTop=False)
        self._writable = True

    def setImageFrameVisible(self, visible):
        """ Sets whetehr the image frame settings are visible. """
        framePar = self.p.param('Image frame')
        framePar.setOpts(visible=visible)

    @property
    def writable(self):
        return self._writable

    @writable.setter
    def writable(self, value):
        """
        property to set basically the whole parameters tree as writable
        (value=True) or not writable (value=False)
        useful to set it as not writable during recording
        """
        self._writable = value
        framePar = self.p.param('Image frame')
        framePar.param('Binning').setWritable(value)
        framePar.param('Mode').setWritable(value)
        framePar.param('X0').setWritable(value)
        framePar.param('Y0').setWritable(value)
        framePar.param('Width').setWritable(value)
        framePar.param('Height').setWritable(value)

        # WARNING: If Apply and New ROI button are included here they will
        # emit status changed signal and their respective functions will be
        # called... -> problems.
        timingPar = self.p.param('Timings')
        timingPar.param('Set exposure time').setWritable(value)

    def attrs(self):
        attrs = []
        for ParName in self.p.getValues():
            Par = self.p.param(str(ParName))
            if not (Par.hasChildren()):
                attrs.append((str(ParName), Par.value()))
            else:
                for sParName in Par.getValues():
                    sPar = Par.param(str(sParName))
                    if sPar.type() != 'action':
                        if not (sPar.hasChildren()):
                            attrs.append((str(sParName), sPar.value()))
                        else:
                            for ssParName in sPar.getValues():
                                ssPar = sPar.param(str(ssParName))
                                attrs.append((str(ssParName), ssPar.value()))
        return attrs


class SettingsWidget(Widget):
    """ Detector settings and ROI parameters. """

    sigROIChanged = QtCore.Signal()
    sigDetectorChanged = QtCore.Signal(str)  # (detectorName)
    sigNextDetectorClicked = QtCore.Signal()
    sigScatterCamToggle = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Graphical elements
        detectorTitle = QtWidgets.QLabel('<h2><strong>Detector settings</strong></h2>')
        detectorTitle.setTextFormat(QtCore.Qt.RichText)
        self.ROI = naparitools.VispyROIVisual(rect_color='yellow', handle_color='orange')
        self.stack = QtWidgets.QStackedWidget()
        self.trees = {}

        self.detectorListBox = QtWidgets.QHBoxLayout()
        self.detectorListLabel = QtWidgets.QLabel('Current detector:')
        self.detectorList = QtWidgets.QComboBox()
        self.nextDetectorButton = guitools.BetterPushButton('Next')
        self.nextDetectorButton.hide()
        self.detectorListBox.addWidget(self.detectorListLabel)
        self.detectorListBox.addWidget(self.detectorList, 1)
        self.detectorListBox.addWidget(self.nextDetectorButton)

        self.scatterCamActive = QCheckBox('Activate Scatter Cam')
        self.scatterCamActive.setEnabled(False)
        
        
        # initialize FOV correction window
        self.correctionButton = QtWidgets.QPushButton('FOV Correction')
        self.detectorListBox.addWidget(self.correctionButton)
        
        


        # Add elements to GridLayout
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(detectorTitle)
        self.layout.addWidget(self.stack)
        self.layout.addLayout(self.detectorListBox)
        self.layout.addWidget(self.scatterCamActive)

        # Connect signals
        self.ROI.sigROIChanged.connect(self.sigROIChanged)
        self.detectorList.currentIndexChanged.connect(
            lambda index: self.sigDetectorChanged.emit(self.detectorList.itemData(index))
        )
        self.nextDetectorButton.clicked.connect(self.sigNextDetectorClicked)
        # FOVCorrectionWindow = FOVCorrectionWindow(QMainWindow)
        
        
    def openFOVWindow(self, blue, green, red):
        self.openCorrectionWindow = FOVCorrectionWindow(blue, green, red, parent=self)
        self.openCorrectionWindow.show()

    def toggleCheckboxes(self, state):
        self.scatterCamActive.setEnabled(not state)


    def addDetector(self, detectorName, detectorModel, detectorParameters, detectorActions,
                    supportedBinnings, roiInfos):
        self.trees[detectorName] = CamParamTree(detectorParameters, detectorActions,
                                                supportedBinnings, roiInfos)
        self.stack.addWidget(self.trees[detectorName])

        self.detectorList.addItem(f'{detectorModel} ({detectorName})', detectorName)
        self.nextDetectorButton.setVisible(True)

    def setDisplayedDetector(self, detectorName):
        # Remember previously displayed detector settings widget scroll position
        prevDetectorWidget = self.stack.currentWidget()
        scrollX = prevDetectorWidget.horizontalScrollBar().value()
        scrollY = prevDetectorWidget.verticalScrollBar().value()

        # Switch to new detector settings widget and set scroll position to same as previous widget
        newDetectorWidget = self.trees[detectorName]
        self.stack.setCurrentWidget(newDetectorWidget)
        newDetectorWidget.horizontalScrollBar().setValue(scrollX)
        newDetectorWidget.verticalScrollBar().setValue(scrollY)

    def selectNextDetector(self):
        self.detectorList.setCurrentIndex(
            (self.detectorList.currentIndex() + 1) % self.detectorList.count()
        )

    def setImageFrameVisible(self, visible):
        """ Sets whetehr the image frame settings are visible. """
        self.stack.currentWidget().setImageFrameVisible(visible)

    def getROIGraphicsItem(self):
        return self.ROI

    def showROI(self, position=None, size=None):
        if position is not None:
            self.ROI.position = position
        if size is not None:
            self.ROI.size = size
        self.ROI.show()

    def hideROI(self):
        self.ROI.hide()

    # FIXME: Remove if not in use
    # def populateWidget(self, detector, parameters):
    #     # To check values
    #     # self.trees['65Camera'].p.param('Image frame').param('Y0').opts['value']
    #     detctorName = '65Camera'
    #     self.trees[detctorName].p.param('Image frame').param('Y0').set[128]
    #     self.trees[detctorName].p.param('Image frame').param('X0').set[520]
    #     self.trees[detctorName].p.param('Image frame').param('Width').set[256]
    #     self.trees[detctorName].p.param('Image frame').param('Height').set[1024]

    @shortcut("Ctrl+N", "Next detector")
    def toggleNextButton(self):
        self.nextDetectorButton.click()

class fovCorrection(QtWidgets.QLabel):
    def __init__(self, npImage, parent=None):
        super().__init__(parent)

        self.parentLabel = None
        self.fullPoint = None
        # convert numpy to pixmap
        self.npImage = npImage
        
        self.npImage = self.npImage[:, (self.npImage.shape[1]-4600)//2 : (self.npImage.shape[1]+4600)//2]
        h, w = self.npImage.shape
        
        self.displayW = 300
        self.displayH = 300
        qimg = QtGui.QImage(self.npImage.tobytes(), w, h, w, QtGui.QImage.Format_Grayscale8)
        self.pixmapOriginal = QtGui.QPixmap.fromImage(qimg)

        scaled = self.pixmapOriginal.scaled(self.displayW, self.displayH, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(scaled)
        self.setFixedSize(self.displayW, self.displayH)
        self.setScaledContents(False)
        self.clickPoints = []
        self.factor = (w / self.displayW, h / self.displayH)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)

        # dot style
        pen = QtGui.QPen(QtGui.QColor("red"))
        pen.setWidth(2)
        painter.setPen(pen)

        if self.clickPoints:
            x, y = self.clickPoints[0]
            size = 5
            # draw cross
            painter.drawLine(x - size, y - size, x + size, y + size)
            painter.drawLine(x - size, y + size, x + size, y - size)
        painter.end()

    def setPoint(self, x, y):
        self.clickPoints = [(x, y)]

        if self.parentLabel is not None and hasattr(self.parent(), "offsets"):
            fx, fy = self.factor
            offx, offy = self.parent().offsets[self.parentLabel]
            ox = floor(offx + x * fx)
            oy = floor(offy + y * fy)
            self.fullPoint = (ox, oy)

        self.update()

    def setImage(self, npImage):
        self.npImage = npImage
        h, w = npImage.shape
        qimg = QtGui.QImage(npImage.tobytes(), w, h, w, QtGui.QImage.Format_Grayscale8)
        pix = QtGui.QPixmap.fromImage(qimg)

        scaled = pix.scaled(self.displayW, self.displayH, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(scaled)

        self.factor = (w / self.displayW, h / self.displayH)

        # keep the same full point after changing image, by projecting it back to display coords
        if self.fullPoint is not None and self.parentLabel is not None and hasattr(self.parent(), "offsets"):
            offx, offy = self.parent().offsets[self.parentLabel]
            fx, fy = self.factor
            ox, oy = self.fullPoint

            dx = int(round((ox - offx) / fx))
            dy = int(round((oy - offy) / fy))

            self.clickPoints = [(dx, dy)]
        else:
            self.clickPoints = []

        self.update()



class FOVCorrectionWindow(QMainWindow):
    def __init__(self, blueImg, greenImg, redImg, parent=SettingsWidget):
        super().__init__(parent)
        self.setWindowTitle("FOV Correction")
        self.setMinimumSize(1230, 400)

        dummy = np.zeros((4600, 4600), dtype=np.uint8)
        self.fullImages = {"488": blueImg, "561": greenImg, "640": redImg}
        self.offsets = {"488": (0, 0), "561": (0, 0), "640": (0, 0)}

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.columnsLayout = QtWidgets.QHBoxLayout()

        self.col1 = QtWidgets.QVBoxLayout()
        self.blueLabel = QtWidgets.QLabel(f"<strong>488<strong>")
        self.col1.addWidget(self.blueLabel)
        self.blueImage = fovCorrection(blueImg, parent=self)
        self.col1.addWidget(self.blueImage)
        self.col1.addStretch()

        self.col2 = QtWidgets.QVBoxLayout()
        self.greenLabel = QtWidgets.QLabel(f"<strong>561<strong>")
        self.col2.addWidget(self.greenLabel)
        self.greenImage = fovCorrection(greenImg, parent=self)
        self.col2.addWidget(self.greenImage)
        self.col2.addStretch()

        self.col3 = QtWidgets.QVBoxLayout()
        self.redLabel = QtWidgets.QLabel(f"<strong>640<strong>")
        self.col3.addWidget(self.redLabel)
        self.redImage = fovCorrection(redImg, parent=self)
        self.col3.addWidget(self.redImage)
        self.col3.addStretch()

        self.col4 = QtWidgets.QVBoxLayout()
        self.compositeLabel = QtWidgets.QLabel("Composite")
        self.col4.addWidget(self.compositeLabel)
        self.compositeImage = fovCorrection(dummy, parent=self)
        self.col4.addWidget(self.compositeImage)
        self.compositeImage.mousePressEvent = self.ignoreClick
        self.col4.addStretch()

        self.columnsLayout.addLayout(self.col1)
        self.columnsLayout.addLayout(self.col2)
        self.columnsLayout.addLayout(self.col3)
        self.columnsLayout.addLayout(self.col4)
        self.mainLayout.addLayout(self.columnsLayout)

        bottomLayout = QtWidgets.QHBoxLayout()

        self.pointsDisplay = QtWidgets.QTextEdit()
        self.pointsDisplay.setReadOnly(True)
        self.pointsDisplay.setFixedHeight(54)
        self.pointsDisplay.setFixedWidth(110)
        bottomLayout.addWidget(self.pointsDisplay)

        self.alignButton = QtWidgets.QPushButton("Align detectors")
        self.alignButton.setFixedHeight(54)
        self.alignButton.setFixedWidth(150)
        bottomLayout.addWidget(self.alignButton)

        self.cropButton = QtWidgets.QPushButton("Crop detectors")
        self.cropButton.setFixedHeight(54)
        self.cropButton.setFixedWidth(150)
        bottomLayout.addWidget(self.cropButton)

        bottomLayout.addStretch()
        self.mainLayout.addLayout(bottomLayout)

        central_widget = QWidget()
        central_widget.setLayout(self.mainLayout)
        self.setCentralWidget(central_widget)

        # clicking events
        self.blueImage.mousePressEvent = self.handleBlueClick
        self.greenImage.mousePressEvent = self.handleGreenClick
        self.redImage.mousePressEvent = self.handleRedClick


    def handleBlueClick(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            self.blueImage.setPoint(pos.x(), pos.y())
            self.updatePointsDisplay()


    def handleGreenClick(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            self.greenImage.setPoint(pos.x(), pos.y())
            self.updatePointsDisplay()


    def handleRedClick(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            self.redImage.setPoint(pos.x(), pos.y())
            self.updatePointsDisplay()


    def ignoreClick(self, event):
        pass

    
    def updatePointsDisplay(self):
        lines = []

        if self.blueImage.clickPoints:
            lines.append(self.formatPoint("488", self.blueImage))

        if self.greenImage.clickPoints:
            lines.append(self.formatPoint("561", self.greenImage))

        if self.redImage.clickPoints:
            lines.append(self.formatPoint("640", self.redImage))

        self.pointsDisplay.setPlainText("\n".join(lines))

    def formatPoint(self, label, img):
        x, y = img.clickPoints[0]

        fx, fy = img.factor
        offx, offy = self.offsets[label]

        ox = floor(offx + x * fx)
        oy = floor(offy + y * fy)

        return f"{label}: ({ox}, {oy})"








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
