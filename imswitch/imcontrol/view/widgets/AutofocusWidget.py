from qtpy import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (QLabel, QMainWindow, QWidget, QMessageBox, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush
import numpy as np
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import QPointF, QRect, QPoint



class AutofocusWidget(NapariHybridWidget):

    sigAutofocusInfoChanged = QtCore.Signal(str, str, str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        self.AFWindow = SetAFWindow()
        autofocusLayout = QtWidgets.QGridLayout()
        self.setLayout(autofocusLayout)
        self.led = LedIndicator(self)
        self.openPreview = QtWidgets.QPushButton('AF Preview')
        self.openPreview.setEnabled(False)
        self.registerPlane = QtWidgets.QPushButton('Reg. Plane')
        self.registerPlane.setEnabled(False)
        self.clearRegPlane = QtWidgets.QPushButton('Clear Plane')
        self.clearRegPlane.setEnabled(False)

        row = 0
        autofocusLayout.addWidget(self.openPreview, row, 0)
        autofocusLayout.addWidget(self.registerPlane, row, 1)
        autofocusLayout.addWidget(self.clearRegPlane, row , 2)
        autofocusLayout.addWidget(self.led, row + 1, 2)

    def toggleEnabled(self, state):
        self.openPreview.setEnabled(state)
        self.registerPlane.setEnabled(state)
        self.clearRegPlane.setEnabled(state)
        # self.calCurveRange.setEnabled(state)

    def initValues(self):
        pass

class SetAFWindow(QMainWindow):
    sigUpdateCalibChart = QtCore.Signal(np.ndarray,list,list,list)
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("Open AF Preview")
        self.setGeometry(100, 100, 1280, 1024)

        self.frame1 = QFrame()
        self.frame1.setFrameShape(QFrame.StyledPanel)
        self.frame1.setFrameShadow(QFrame.Plain)
        self.frame1.setLineWidth(5)

        

        afWindowLayout = QtWidgets.QVBoxLayout()
        imageLayout = QtWidgets.QVBoxLayout()
        buttonAndTextLayout = QtWidgets.QVBoxLayout()
        textLayout = QtWidgets.QGridLayout(self.frame1)
        # textLayout = QtWidgets.QGridLayout()
        buttonLayout = QtWidgets.QHBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(afWindowLayout)
        self.setCentralWidget(central_widget)

        blankImage = np.zeros((1096,1936))

        self.acqImgButton = QtWidgets.QPushButton('Refresh Image')
        self.acqImgButton.setStyleSheet("QPushButton { height: 100px;font-size: 24px; }")
        buttonLayout.addWidget(self.acqImgButton)
        self.calCurve = QtWidgets.QPushButton('Run Cal. Curve')
        self.calCurve.setStyleSheet("QPushButton { height: 100px;font-size: 24px; }")
        buttonLayout.addWidget(self.calCurve)

        self.resetEstimates = QtWidgets.QPushButton('Reset Estimates')
        self.resetEstimates.setStyleSheet("QPushButton { height: 100px;font-size: 24px; }")
        buttonLayout.addWidget(self.resetEstimates)
        self.regReflection  = QtWidgets.QPushButton('Register Reflection Mask')
        self.regReflection.setCheckable(True)
        self.regReflection.setStyleSheet("QPushButton { height: 100px;font-size: 24px; }")
        buttonLayout.addWidget(self.regReflection)
        self.resetMask = QtWidgets.QPushButton('Reset Reflection Mask')
        self.resetMask.setStyleSheet("QPushButton { height: 100px;font-size: 24px; }")
        buttonLayout.addWidget(self.resetMask)

        self.sigUpdateCalibChart.connect(self.displayChart)




        #################
        self.ccSlopeLabel = QLabel(self)
        self.ccSlopeLabel.setText("Slope:")

        self.ccIntLabel = QLabel(self)
        self.ccIntLabel.setText("Intercept:")

        self.ccR2Label = QLabel(self)
        self.ccR2Label.setText("R^2:")

        self.ccSensLabel = QLabel(self)
        self.ccSensLabel.setText("Sensitivity:")

        self.ccSlopeVal = QLabel(self)
        self.ccSlopeVal.setText("-")
        self.ccIntVal = QLabel(self)
        self.ccIntVal.setText("-")
        self.ccIntVal.setFixedWidth(200)
        self.ccR2Val = QLabel(self)
        self.ccR2Val.setText("-")
        self.ccSensVal = QLabel(self)
        self.ccSensVal.setText("-")

        self.rangeLabel = QLabel(self)
        self.rangeLabel.setText("Scan Range:")

        self.calCurveRange = QtWidgets.QSpinBox()
        self.calCurveRange.setMinimum(1)
        self.calCurveRange.setMaximum(100)
        self.calCurveRange.setValue(20)

        

        row = 0
        textLayout.addWidget(self.rangeLabel, row , 0)
        textLayout.addWidget(self.calCurveRange, row , 1)
        textLayout.addWidget(self.ccSlopeLabel, row + 1, 0)
        textLayout.addWidget(self.ccSlopeVal, row + 1, 1, alignment=Qt.AlignLeft)
        textLayout.addWidget(self.ccIntLabel, row + 2, 0)
        textLayout.addWidget(self.ccIntVal, row + 2, 1, alignment=Qt.AlignLeft)
        textLayout.addWidget(self.ccR2Label, row + 3, 0)
        textLayout.addWidget(self.ccR2Val, row + 3, 1, alignment=Qt.AlignLeft)
        textLayout.addWidget(self.ccSensLabel, row + 4, 0)
        textLayout.addWidget(self.ccSensVal, row + 4, 1, alignment=Qt.AlignLeft)
        textLayoutBoxed = QtWidgets.QVBoxLayout()
        textLayoutBoxed.addWidget(self.frame1)
        
        # textLayout.addStretch()
        textHorizLayout = QtWidgets.QHBoxLayout()
        textHorizLayout.addLayout(textLayoutBoxed)
        ################
        #Chart

        self.chart = QChart()
        self.chart.setTitle("Calibration Data")
        chart_view = QChartView(self.chart)
        chart_view.setMinimumSize(1000, 600)
        chart_view.setRenderHint(QPainter.Antialiasing)
        
        textHorizLayout.addWidget(chart_view)


        self.coordsRegistered = False

        textHorizLayout.addStretch()

        self.embeddedImage = ClickableImage(blankImage, self)
        # self.resizableBox = ResizableBox(self.embeddedImage)
        # textLabel = QtWidgets.QLabel('Find sample focus. Refresh to display focus beam image. Click the center of the focus beam. Click ''Set ROI''. Close window.')
        buttonAndTextLayout.addLayout(buttonLayout)
        buttonAndTextLayout.addLayout(textHorizLayout)



        afWindowLayout.addLayout(buttonAndTextLayout)
        imageLayout.addWidget(self.embeddedImage, alignment=Qt.AlignCenter)
        afWindowLayout.addLayout(imageLayout)
        self.regReflection.clicked.connect(self.regCoordsFunc)

        # self.msgMask = QMessageBox()
        # self.msgMask.setWindowTitle("Please set reflection mask.")
        # self.msgMask.setText("Please set the reflection mask by using the 'Register Reflection Coordinates' button.")
        # self.msgMask.setIcon(QMessageBox.Information)
        # self.msgMask.setStandardButtons(QMessageBox.Ok)

        self.msg = QMessageBox()
        self.msg.setWindowTitle("Set Coordinates")
        self.msg.setText("Please click and drag horizontally to cover all of the back reflection.")
        self.msg.setIcon(QMessageBox.Information)
        self.msg.setStandardButtons(QMessageBox.Ok)
        # afWindowLayout.addStretch()

        

        # self.msg_box = QMessageBox()
        # self.msg_box.setWindowTitle("Do Not Exclude Reflection?")
        # self.msg_box.setText("Excluded region not selected. Continue with complete image?")
        # button_yes = self.msg_box.addButton("Yes", QMessageBox.YesRole)
        # button_no = self.msg_box.addButton("Cancel", QMessageBox.NoRole)


    def regCoordsFunc(self):
        self.embeddedImage.coords = True
        self.regReflection.setChecked(True)
        self.regReflection.setEnabled(False)
        self.msg.show()

    # def showMaskMSG(self):
    #     self.msgMask.show()

    def displayChart(self, zValues, xData, yData, comboData):
        # self.series.clear()
        for s in self.chart.series():
            self.chart.removeSeries(s)
        self.seriesX = QLineSeries()
        self.seriesY = QLineSeries()
        self.seriesCombo = QLineSeries()
        self.seriesX.setName("X-Sigma")
        self.seriesY.setName("Y Sigma")
        self.seriesCombo.setName("X-Y")
        for x, y in zip(xData, zValues):
            self.seriesX.append(QPointF(x, y))
        for x, y in zip(yData, zValues):
            self.seriesY.append(QPointF(x, y))
        for x, y in zip(comboData, zValues):
            self.seriesCombo.append(QPointF(x, y))
        self.chart.addSeries(self.seriesX)
        self.chart.addSeries(self.seriesY)
        self.chart.addSeries(self.seriesCombo)

        xMin = int(min([*xData, *yData, *comboData]))
        yMin = int(min(zValues))
        xMax = int(max([*xData, *yData, *comboData]))
        yMax = int(max(zValues))


        axis_x = QValueAxis()
        # axis_x.setTitleText("Score")
        axis_x.setRange(xMin - xMin*0.05, xMax + xMax*0.01)

        axis_y = QValueAxis()
        # axis_y.setTitleText("Z Position / um")
        axis_y.setRange(yMin - yMin*0.01, yMax + yMax*0.01)

        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        self.seriesX.attachAxis(axis_x)
        self.seriesX.attachAxis(axis_y)
        self.seriesY.attachAxis(axis_x)
        self.seriesY.attachAxis(axis_y)
        self.seriesCombo.attachAxis(axis_x)
        self.seriesCombo.attachAxis(axis_y)

        self.chart.createDefaultAxes() 

    def convert_ndarray_to_qpixmap(self, image: np.ndarray) -> QPixmap:
        h, w = image.shape
        q_image = QImage(image.data, w, h, w, QImage.Format_Grayscale8)

        return QPixmap.fromImage(q_image)
    
# class ResizableBox(QRubberBand):
#     def __init__(self, parent=None):
#         super().__init__(QRubberBand.Rectangle, parent)
#         self.setGeometry(100, 100, 150, 100)
#         self.show()
#         self._dragging = False
#         self._resizing = False
#         self._resizeMargin = 10

#     def mousePressEvent(self, event):
#         if self._isInResizeArea(event.pos()):
#             self._resizing = True
#         else:
#             self._dragging = True
#             self._dragOffset = event.pos()

#     def mouseMoveEvent(self, event):
#         if self._resizing:
#             rect = self.geometry()
#             newWidth = max(20, event.x())
#             newHeight = max(20, event.y())
#             self.setGeometry(rect.x(), rect.y(), newWidth, newHeight)
#         elif self._dragging:
#             self.move(self.mapToParent(event.pos() - self._dragOffset))

#     def mouseReleaseEvent(self, event):
#         self._dragging = False
#         self._resizing = False

#     def _isInResizeArea(self, pos):
#         rect = self.rect()
#         return pos.x() > rect.width() - self._resizeMargin and pos.y() > rect.height() - self._resizeMargin
    

class ClickableImage(QLabel):

    sigUpdateWithMask = QtCore.Signal()

    def __init__(self, image_np, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.painted = False
        # Convert NumPy image to QImage and then to QPixmap
        self.image_np = image_np
        self.pixelmap = self.convert_ndarray_to_qpixmap(self.image_np)

        self.start_point = None
        self.end_point = None
        self.selection_rect = None
        self.coords = False
        self.left = None
        self.right = None

        self.setPixmap(self.pixelmap)
        # self.setScaledContents(True)  # Ensure image scales with widget
        self.annotation_points = []
        # self.lastClick = (0,0,1280,1024) #Left,Top,width,height of last image click.

        

    def convert_ndarray_to_qpixmap(self, image: np.ndarray) -> QPixmap:
        h, w = image.shape
        q_image = QImage(image.data, w, h, w, QImage.Format_Grayscale8)

        return QPixmap.fromImage(q_image)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = self.start_point
            self.update()

    def mouseMoveEvent(self, event):
        if self.start_point:
            # self.end_point = event.pos()
            x = event.pos().x()
            y = self.start_point.y()
            self.end_point = QPoint(x, y)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_point:
            # self.end_point = event.pos()
            x = event.pos().x()
            y = self.start_point.y() 
            self.end_point = QPoint(x, y)
            self.selection_rect = QRect(self.start_point, self.end_point).normalized()
            self.start_point = None
            self.end_point = None
            self.update()

        if self.coords:
            self.left = self.selection_rect.left()
            self.right = self.selection_rect.right()
            print(f'Mask registered: (Left:{self.left}, Right:{self.right})')
            self.coords = False
            self.parent.regReflection.setChecked(False)
            self.parent.regReflection.setEnabled(True)
            self.parent.coordsRegistered = True
            self.sigUpdateWithMask.emit()


    def paintEvent(self, event):
        super().paintEvent(event)
        if self.start_point and self.end_point:
            painter = QPainter(self)
            pen = QPen(QColor(0, 120, 215), 2, Qt.DashLine)
            painter.setPen(pen)
            # rect = QRect(self.start_point, self.end_
            painter.drawLine(self.start_point, self.end_point)
    



class LedIndicator(QWidget):
    def __init__(self, parent=None, diameter=30):
        super().__init__(parent)
        self._on = False
        self._diameter = diameter
        self.setFixedSize(QSize(diameter + 10, diameter + 10))

    def turn_on(self):
        self._on = True
        self.update()

    def turn_off(self):
        self._on = False
        self.update()

    def toggle(self):
        self._on = not self._on
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(0, 255, 0) if self._on else QColor(255, 0, 0)
        painter.setBrush(QBrush(color, Qt.SolidPattern))
        painter.setPen(Qt.black)
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.drawEllipse(rect)


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
