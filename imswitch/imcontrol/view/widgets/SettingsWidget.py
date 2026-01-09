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
        
        
    def openFOVWindow(self, blue, green, red, scatter=None, showScatter=False):
        self.openCorrectionWindow = FOVCorrectionWindow(
            blue, green, red,
            scatterImg=scatter,
            showScatter=showScatter,
            parent=self
        )
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

        self._drawCross = False
        self.parentLabel = None
        self.fullPoint = None
        self.displayW = 450     # 600x600
        self.displayH = 450
        self.setFixedSize(self.displayW, self.displayH)
        self.setScaledContents(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.clickPoints = []

        self._localShiftX = 0
        self._localShiftY = 0

        self.baseImage = None
        self.npImage = None
        self._view = None

        self.viewX0 = 0.0
        self.viewY0 = 0.0
        self.viewW = 0.0
        self.viewH = 0.0

        self.factor = (1.0, 1.0)

        self.setBaseImage(npImage, doCenterCrop=True)


    def setBaseImage(self, npImage, doCenterCrop=False):
        self.fullPoint = None

        h, w = npImage.shape[:2]

        if doCenterCrop:
            if w > 4600:
                sx = (w - 4600) // 2
                self._localShiftX = sx
                self._localShiftY = 0
                if npImage.ndim == 2:
                    npImage = npImage[:, sx:sx + 4600]
                else:
                    npImage = npImage[:, sx:sx + 4600, :]
            else:
                self._localShiftX = 0
                self._localShiftY = 0

        self.baseImage = npImage
        H, W = self.baseImage.shape[:2]

        self.viewX0 = 0.0
        self.viewY0 = 0.0
        self.viewW = float(W)
        self.viewH = float(H)

        self.render()


    def getExtOffset(self):
        if self.parentLabel is not None and hasattr(self.parent(), "offsets"):
            return self.parent().offsets[self.parentLabel]
        return (0, 0)

    def render(self):
        if self.baseImage.ndim == 2:
            H, W = self.baseImage.shape
        else:
            H, W, _ = self.baseImage.shape


        vw = int(round(self.viewW))
        vh = int(round(self.viewH))
        vw = max(1, min(W, vw))
        vh = max(1, min(H, vh))

        x0 = int(round(self.viewX0))
        y0 = int(round(self.viewY0))

        x0 = max(0, min(W - vw, x0))
        y0 = max(0, min(H - vh, y0))

        x1 = x0 + vw
        y1 = y0 + vh

        view = self.baseImage[y0:y1, x0:x1].copy()
        self._view = view
        self.npImage = view

        h, w = view.shape[:2]

        if view.ndim == 2:
            qimg = QtGui.QImage(
                view.data,
                w, h,
                view.strides[0],
                QtGui.QImage.Format_Grayscale8
            )
        else:
            qimg = QtGui.QImage(
                view.data,
                w, h,
                view.strides[0],
                QtGui.QImage.Format_RGB888
            )


        pix = QtGui.QPixmap.fromImage(qimg)
        scaled = pix.scaled(self.displayW, self.displayH, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(scaled)

        self.factor = (w / self.displayW, h / self.displayH)

        self.viewX0 = float(x0)
        self.viewY0 = float(y0)
        self.viewW = float(w)
        self.viewH = float(h)

        self.update()


    def setViewCenteredOnFullPoint(self, fullPoint, half=400):
        if fullPoint is None:
            return

        ox, oy = fullPoint
        offx, offy = self.getExtOffset()

        lx = ox - offx - self._localShiftX
        ly = oy - offy - self._localShiftY

        H, W = self.baseImage.shape[:2]

        viewW = min(float(W), float(2 * half))
        viewH = min(float(H), float(2 * half))

        x0 = lx - viewW / 2.0
        y0 = ly - viewH / 2.0

        x0 = max(0.0, min(float(W) - viewW, x0))
        y0 = max(0.0, min(float(H) - viewH, y0))

        self.viewX0 = x0
        self.viewY0 = y0
        self.viewW = viewW
        self.viewH = viewH

        self.render()


    def displayToFull(self, dx, dy):
        offx, offy = self.getExtOffset()
        fx, fy = self.factor

        lx = self.viewX0 + dx * fx
        ly = self.viewY0 + dy * fy

        ox = offx + self._localShiftX + lx
        oy = offy + self._localShiftY + ly
        return (ox, oy)
    

    def fullToDisplay(self, ox, oy):
        offx, offy = self.getExtOffset()
        fx, fy = self.factor

        lx = (ox - offx - self._localShiftX) - self.viewX0
        ly = (oy - offy - self._localShiftY) - self.viewY0

        dx = int(round(lx / fx))
        dy = int(round(ly / fy))

        dx = max(0, min(self.displayW - 1, dx))
        dy = max(0, min(self.displayH - 1, dy))
        return (dx, dy)

    def projectFullPointToClick(self):
        if self.fullPoint is None:
            self.clickPoints = []
            return
        dx, dy = self.fullToDisplay(*self.fullPoint)
        self.clickPoints = [(dx, dy)]

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)

        pen = QtGui.QPen(QtGui.QColor("red"))
        pen.setWidth(2)
        painter.setPen(pen)

        if self._drawCross and self.fullPoint is not None:
            dx, dy = self.fullToDisplay(*self.fullPoint)
            size = 5
            painter.drawLine(dx - size, dy - size, dx + size, dy + size)
            painter.drawLine(dx - size, dy + size, dx + size, dy - size)

        painter.end()

    def setPoint(self, x, y):
        self._drawCross = True
        x = max(0, min(self.displayW - 1, x))
        y = max(0, min(self.displayH - 1, y))

        self.fullPoint = self.displayToFull(x, y)
        self.update()


    def zoomAt(self, mx, my, delta):
        if delta == 0:
            return

        H, W = self.baseImage.shape[:2]


        step = 1.25
        zoomIn = delta > 0

        mx = max(0, min(self.displayW - 1, mx))
        my = max(0, min(self.displayH - 1, my))

        vx0, vy0, vw, vh = self.viewX0, self.viewY0, self.viewW, self.viewH

        ix = vx0 + mx * (vw / self.displayW)
        iy = vy0 + my * (vh / self.displayH)

        if zoomIn:
            newW = vw / step
            newH = vh / step
        else:
            newW = vw * step
            newH = vh * step

        minSize = 30
        newW = max(minSize, min(float(W), newW))
        newH = max(minSize, min(float(H), newH))

        newX0 = ix - mx * (newW / self.displayW)
        newY0 = iy - my * (newH / self.displayH)

        newX0 = max(0.0, min(float(W) - newW, newX0))
        newY0 = max(0.0, min(float(H) - newH, newY0))

        self.viewX0 = newX0
        self.viewY0 = newY0
        self.viewW = newW
        self.viewH = newH

        self.render()

    def wheelEvent(self, event):
        p = event.pos()
        self.zoomAt(p.x(), p.y(), event.angleDelta().y())
        event.accept()

    def setImage(self, npImage, keepFullPoint=None):
        self._localShiftX = 0
        self._localShiftY = 0

        self.baseImage = npImage
        self.baseImage = np.ascontiguousarray(npImage)

        
        if self.baseImage.ndim == 2:
            H, W = self.baseImage.shape
        else:
            H, W, _ = self.baseImage.shape

        self.viewX0 = 0.0
        self.viewY0 = 0.0
        self.viewW = float(W)
        self.viewH = float(H)

        self.fullPoint = keepFullPoint
        self.render()






class FOVCorrectionWindow(QMainWindow):
    def __init__(self, blueImg, greenImg, redImg, scatterImg=None, showScatter=False, parent=SettingsWidget):
        super().__init__(parent)

        self.setWindowTitle("FOV Correction")


        self.fullImages = {"488": blueImg, "561": greenImg, "640": redImg}
        self.offsets = {"488": (0, 0), "561": (0, 0), "640": (0, 0)}
        self.scatterImage = None

        if showScatter and scatterImg is not None:
            self.fullImages["Scatter"] = scatterImg
            self.offsets["Scatter"] = (0, 0)


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

        if showScatter and scatterImg is not None:
            self.col4 = QtWidgets.QVBoxLayout()
            self.scatterLabel = QtWidgets.QLabel(f"<strong>Scatter<strong>")
            self.col4.addWidget(self.scatterLabel)
            self.scatterImage = fovCorrection(scatterImg, parent=self)
            self.col4.addWidget(self.scatterImage)
            self.col4.addStretch()




        self.columnsLayout.addLayout(self.col1)
        self.columnsLayout.addLayout(self.col2)
        self.columnsLayout.addLayout(self.col3)

        self.mainLayout.addLayout(self.columnsLayout)
        if self.scatterImage is not None:
            self.columnsLayout.addLayout(self.col4)
        self.bottomLayout = QtWidgets.QHBoxLayout()

        # points display box
        self.pointsBox = QtWidgets.QWidget()
        self.pointsBox.setFixedSize(170, 90)
        self.pointsLay = QtWidgets.QVBoxLayout(self.pointsBox)
        self.pointsLay.setContentsMargins(0, 0, 0, 0)
        self.pointsLay.setSpacing(2)

        self.pointsLabel = QtWidgets.QLabel(f"<strong>Clicked point coordinates:</<strong>")
        self.pointsLay.addWidget(self.pointsLabel)

        self.pointsDisplay = QtWidgets.QTextEdit()
        self.pointsDisplay.setReadOnly(True)
        self.pointsDisplay.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.pointsLay.addWidget(self.pointsDisplay)


        self.bottomLayout.addWidget(self.pointsBox)

        # roi size box
        self.modeBox = QtWidgets.QWidget()
        self.modeBox.setFixedSize(80, 90)
        self.modeLayout = QtWidgets.QVBoxLayout(self.modeBox)
        self.modeLayout.setContentsMargins(0, 0, 0, 0)
        self.modeLayout.setSpacing(4)


        self.roiSizeLabel = QtWidgets.QLabel(f"<strong>ROI (px):<strong>")
        self.roiSizeLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.modeLayout.addWidget(self.roiSizeLabel)

        
        self.roiSizeBox = QtWidgets.QComboBox()
        self.roiSizeBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        sizes = [128, 256, 512, 1024, 2048, 3072, 4096, 4600]
        for s in sizes:
            self.roiSizeBox.addItem(str(s), s)
            
        self.roiSizeBox.setEditable(True)
        le = self.roiSizeBox.lineEdit()
        le.setReadOnly(True)
        le.setAlignment(QtCore.Qt.AlignCenter)
        le.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        self.roiSizeBox.setCurrentIndex(self.roiSizeBox.findData(512))
        self.roiSizeBox.currentIndexChanged.connect(self.applyRoiSize)
        self.modeLayout.addWidget(self.roiSizeBox, 1)
        self.bottomLayout.addWidget(self.modeBox)
        
        
        # align box
        self.alignBox = QtWidgets.QWidget()
        self.alignBox.setFixedSize(80, 90)
        self.alignLayout = QtWidgets.QVBoxLayout(self.alignBox)
        self.alignLayout.setContentsMargins(0, 0, 0, 0)
        self.alignLayout.setSpacing(4)

        self.alignLabel = QtWidgets.QLabel(f"<strong>Align to:</strong>")
        self.alignLayout.addWidget(self.alignLabel)

        self.alignRefBox = QtWidgets.QComboBox()
        self.alignRefBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        for k in ["488", "561", "640"]:
            self.alignRefBox.addItem(k, k)

        if self.scatterImage is not None:
            self.alignRefBox.addItem("Scatter", "Scatter")
            
        self.alignRefBox.setEditable(True)
        le = self.alignRefBox.lineEdit()
        le.setReadOnly(True)
        le.setAlignment(QtCore.Qt.AlignCenter)
        le.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        self.alignRefBox.setCurrentIndex(self.alignRefBox.findData("561"))
        self.alignLayout.addWidget(self.alignRefBox, 1)

        self.bottomLayout.addWidget(self.alignBox)




        # crop detectors box
        self.cropBox = QtWidgets.QWidget()
        self.cropBox.setFixedSize(200, 90)
        self.cropLay = QtWidgets.QVBoxLayout(self.cropBox)
        self.cropLay.setContentsMargins(0, 0, 0, 0)
        self.cropLay.setSpacing(4)

        self.cropLabel = QtWidgets.QLabel(" ")
        self.cropLay.addWidget(self.cropLabel)

        self.cropButton = QtWidgets.QPushButton("Crop detectors")
        self.cropButton.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.cropLay.addWidget(self.cropButton, 1)

        self.bottomLayout.addWidget(self.cropBox)



        self.bottomLayout.addStretch()
        self.mainLayout.addLayout(self.bottomLayout)


        self.central_widget = QWidget()
        self.central_widget.setLayout(self.mainLayout)
        self.setCentralWidget(self.central_widget)


        # clicking events
        self.blueImage.mousePressEvent = self.handleBlueClick
        self.greenImage.mousePressEvent = self.handleGreenClick
        self.redImage.mousePressEvent = self.handleRedClick
        if self.scatterImage is not None:
            self.scatterImage.mousePressEvent = self.handleScatterClick
            self.scatterImage.parentLabel = "Scatter"



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

    def handleScatterClick(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            self.scatterImage.setPoint(pos.x(), pos.y())
            self.updatePointsDisplay()
    
    def getRefKey(self):
        return str(self.alignRefBox.currentData())


    def getRoiSize(self):
        return int(self.roiSizeBox.currentData())


    def _fallbackCenter(self, key):
        img = self.fullImages[key]
        H, W = img.shape[:2]
        return (W / 2.0, H / 2.0)

    def applyRoiSize(self):
        half = self.getRoiSize() // 2

        c488 = None
        c561 = None
        c640 = None
        cSca = None

        if hasattr(self, "roiCenters"):
            c488 = self.roiCenters.get("488")
            c561 = self.roiCenters.get("561")
            c640 = self.roiCenters.get("640")
            cSca = self.roiCenters.get("Scatter")

        if c488 is None: c488 = self._fallbackCenter("488")
        if c561 is None: c561 = self._fallbackCenter("561")
        if c640 is None: c640 = self._fallbackCenter("640")
        if self.scatterImage is not None and cSca is None: cSca = self._fallbackCenter("Scatter")

        p = self.blueImage.fullPoint if self.blueImage.fullPoint is not None else c488
        self.blueImage.setViewCenteredOnFullPoint(p, half=half)

        p = self.greenImage.fullPoint if self.greenImage.fullPoint is not None else c561
        self.greenImage.setViewCenteredOnFullPoint(p, half=half)

        p = self.redImage.fullPoint if self.redImage.fullPoint is not None else c640
        self.redImage.setViewCenteredOnFullPoint(p, half=half)

        if self.scatterImage is not None:
            p = self.scatterImage.fullPoint if self.scatterImage.fullPoint is not None else cSca
            self.scatterImage.setViewCenteredOnFullPoint(p, half=half)


    


    def updatePointsDisplay(self):
        lines = []

        if self.blueImage.fullPoint is not None:
            lines.append(self.formatPoint("488", self.blueImage))

        if self.greenImage.fullPoint is not None:
            lines.append(self.formatPoint("561", self.greenImage))

        if self.redImage.fullPoint is not None:
            lines.append(self.formatPoint("640", self.redImage))

        if self.scatterImage is not None and self.scatterImage.fullPoint is not None:
            lines.append(self.formatPoint("Scatter", self.scatterImage))

        self.pointsDisplay.setPlainText("\n".join(lines))



    def formatPoint(self, label, img):
        ox, oy = img.fullPoint
        return f"{label}: ({int(round(ox))}, {int(round(oy))})"








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
