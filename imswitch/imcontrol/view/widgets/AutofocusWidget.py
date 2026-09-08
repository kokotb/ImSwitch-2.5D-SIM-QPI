from qtpy import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (QLabel, QMainWindow, QWidget, QFrame, QGroupBox)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush
import numpy as np
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
from PyQt5.QtGui import QPainter, QFont, QIntValidator, QDoubleValidator
from PyQt5.QtCore import QPointF, QRect, QPoint, Qt, QTimer, QLocale



class AutofocusWidget(NapariHybridWidget):

    sigAutofocusInfoChanged = QtCore.Signal(str, str, str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        self.AFWindow = SetAFWindow()
        autofocusButtonLayout = QtWidgets.QVBoxLayout()
        
        overallLayout = QtWidgets.QHBoxLayout()
        self.setLayout(overallLayout)
        self.led = LedIndicator(self)
        self.openPreview = QtWidgets.QPushButton('Autofocus Settings')
        self.openPreview.setEnabled(False)
        self.registerPlane = QtWidgets.QPushButton('Register Plane')
        self.registerPlane.setEnabled(False)
        self.clearRegPlane = QtWidgets.QPushButton('Clear Plane')
        self.clearRegPlane.setEnabled(False)

        # row = 0
        autofocusButtonLayout.addWidget(self.openPreview)
        autofocusButtonLayout.addWidget(self.registerPlane)
        autofocusButtonLayout.addWidget(self.clearRegPlane)
        overallLayout.addLayout(autofocusButtonLayout)
        overallLayout.addWidget(self.led)

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
        self.setWindowTitle("Autofocus")
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
        self.ccR2Label.setText("Linearity (R^2):")

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

        self.maskWidthLabel = QLabel(self)
        self.maskWidthLabel.setText("Mask Width:")

        self.maskWidth = QtWidgets.QSpinBox()
        self.maskWidth.setMinimum(10)
        self.maskWidth.setMaximum(300)
        self.maskWidth.setValue(150)

        self.calCurveRange = QtWidgets.QSpinBox()
        self.calCurveRange.setMinimum(1)
        self.calCurveRange.setMaximum(100)
        self.calCurveRange.setValue(20)

        

        row = 0
        textLayout.addWidget(self.maskWidthLabel, row , 0)
        textLayout.addWidget(self.maskWidth, row , 1)
        textLayout.addWidget(self.rangeLabel, row + 1 , 0)
        textLayout.addWidget(self.calCurveRange, row+1, 1)
        textLayout.addWidget(self.ccSlopeLabel, row + 2, 0)
        textLayout.addWidget(self.ccSlopeVal, row + 2, 1, alignment=Qt.AlignLeft)
        textLayout.addWidget(self.ccIntLabel, row + 3, 0)
        textLayout.addWidget(self.ccIntVal, row + 3, 1, alignment=Qt.AlignLeft)
        textLayout.addWidget(self.ccR2Label, row + 4, 0)
        textLayout.addWidget(self.ccR2Val, row + 4, 1, alignment=Qt.AlignLeft)
        textLayout.addWidget(self.ccSensLabel, row + 5, 0)
        textLayout.addWidget(self.ccSensVal, row + 5, 1, alignment=Qt.AlignLeft)
        textLayoutBoxed = QtWidgets.QVBoxLayout()
        textLayoutBoxed.addWidget(self.frame1)
        
        # textLayout.addStretch()
        textHorizLayout = QtWidgets.QHBoxLayout()
        textHorizLayout.addLayout(textLayoutBoxed)
        ################
        #Chart

        self.chart = QChart()
        self.chart.setTitle("Calibration Curve Data")
        chart_view = QChartView(self.chart)
        chart_view.setMinimumHeight(600)
        chart_view.setMaximumWidth(1000)

        chart_view.setRenderHint(QPainter.Antialiasing)
        
        textHorizLayout.addWidget(chart_view)

        instruction_box = QGroupBox("Instructions")
        instruction_layout = QtWidgets.QVBoxLayout()
        self.instruction_label1 = QLabel("1. Click the 'Register Reflection Mask' button.")
        self.instruction_label1.setWordWrap(True)  # Enable text wrapping 

        self.instruction_label1.setStyleSheet("color: white;")


        self.instruction_label2 = QLabel("2. Click the center of the bright vertical reflection.")
        self.instruction_label2.setWordWrap(True)  # Enable text wrapping 
        self.instruction_label2.setStyleSheet("color: gray;")

        self.instruction_label3 = QLabel("3. Click the 'Run Cal. Curve' button to obtain calibration curve.\n\n-- If successful, calibration curve data will appear in the chart. Acceptable sensitivity is >5 pixels/um.")
        self.instruction_label3.setWordWrap(True)  # Enable text wrapping
        self.instruction_label3.setStyleSheet("color: gray;")

        self.instructionList = [self.instruction_label1,self.instruction_label2,self.instruction_label3]

        for i, name in enumerate(self.instructionList):     
            instruction_layout.addWidget(name)
            name.order = i


        instruction_box.setLayout(instruction_layout)
        instructionsAndSettingsLayout = QtWidgets.QVBoxLayout()
        instructionsAndSettingsLayout.addWidget(instruction_box)
        # textHorizLayout.addWidget(instruction_box)


        
        settings_box = QGroupBox("Autofocus Settings")
        settings_layout = QtWidgets.QGridLayout()

        self.numAvgLabel = QLabel("Avg. Bin")
        self.numAvg = QtWidgets.QSpinBox()
        self.numAvg.setMinimum(1)
        self.numAvg.setMaximum(100)
        self.numAvg.setValue(10)

        self.thresholdLabel = QLabel("Action Threshold (/um)")
        self.AFthreshold = QtWidgets.QDoubleSpinBox()
        self.AFthreshold.setRange(0.0,1.0)
        self.AFthreshold.setValue(0.1)
        self.AFthreshold.setDecimals(2)
        self.AFthreshold.setSingleStep(0.05)

        self.AFPeriodLabel = QLabel("AF Firing Period (/s)")
        self.AFPeriod = QtWidgets.QSpinBox()
        self.AFPeriod.setMinimum(1)
        self.AFPeriod.setMaximum(21600) #6 hours
        self.AFPeriod.setValue(60)

        row = 0
          
        settings_layout.addWidget(self.numAvgLabel, row , 0)
        settings_layout.addWidget(self.numAvg, row , 1)
        settings_layout.addWidget(self.thresholdLabel, row + 1 , 0)
        settings_layout.addWidget(self.AFthreshold, row + 1 , 1)
        settings_layout.addWidget(self.AFPeriodLabel, row + 2 , 0)
        settings_layout.addWidget(self.AFPeriod, row + 2 , 1)

        settings_box.setLayout(settings_layout)

        instructionsAndSettingsLayout.addWidget(settings_box)

        textHorizLayout.addLayout(instructionsAndSettingsLayout)

        self.embeddedImage = ClickableImage(blankImage, self)
        buttonAndTextLayout.addLayout(buttonLayout)
        buttonAndTextLayout.addLayout(textHorizLayout)





        afWindowLayout.addLayout(buttonAndTextLayout)
        imageLayout.addWidget(self.embeddedImage, alignment=Qt.AlignCenter)
        afWindowLayout.addLayout(imageLayout)
        self.regReflection.clicked.connect(self.regCoordsFunc)

        self.coordsRegistered = False



    def regCoordsFunc(self):
        if self.embeddedImage.setCoords:
            self.regReflection.setChecked(False)
            self.embeddedImage.setCoords = False
            self.instruction_label1.setStyleSheet("color: white;")
            self.instruction_label2.setStyleSheet("color: gray;")
            try:
                self.popup.close()
            except AttributeError:
                pass
        else:
            self.embeddedImage.setCoords = True
            self.regReflection.setChecked(True)
            self.popup = PopupMessage("Please click the center of the bright vertical reflection to mask it out of the image.")
            self.instruction_label1.setStyleSheet("color: gray;")
            self.instruction_label2.setStyleSheet("color: white;")
            self.popup.show_message()


    def displayChart(self, zValues, xData, yData, comboData):
        # self.series.clear()
        for s in self.chart.series():
            self.chart.removeSeries(s)
        if self.chart.axisX():
            self.chart.removeAxis(self.chart.axisX())
        if self.chart.axisY():
            self.chart.removeAxis(self.chart.axisY())
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
        axis_x.setTitleText("\nScore")
        axis_x.setTitleFont(QFont("Arial", 12))
        axis_x.setRange(xMin - xMin*0.05, xMax + xMax*0.01)

        axis_y = QValueAxis()
        axis_y.setTitleText("Z Position / um\n")
        axis_y.setTitleFont(QFont("Arial", 12))
        axis_y.setRange(yMin - yMin*0.01, yMax + yMax*0.01)

        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        self.seriesX.attachAxis(axis_x)
        self.seriesX.attachAxis(axis_y)
        self.seriesY.attachAxis(axis_x)
        self.seriesY.attachAxis(axis_y)
        self.seriesCombo.attachAxis(axis_x)
        self.seriesCombo.attachAxis(axis_y)

        # self.chart.createDefaultAxes()

    def convert_ndarray_to_qpixmap(self, image: np.ndarray) -> QPixmap:
        h, w = image.shape
        q_image = QImage(image.data, w, h, w, QImage.Format_Grayscale8)

        return QPixmap.fromImage(q_image)
    
    def closeEvent(self, event):
        if self.regReflection.isChecked():
            self.regReflection.setChecked(False)
            self.embeddedImage.setCoords = False
        for name in self.instructionList:
            if name.order == 0:
                name.setStyleSheet("color: white;")
            else:
                name.setStyleSheet("color: gray;")

        try:
            self.popup.close()
        except AttributeError:
            pass
        event.accept()

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
        self.setCoords = False
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
            # self.start_point = event.pos()
            # self.end_point = self.start_point
            x = event.pos().x()
            self.update()

            if self.setCoords:
                self.parent.popup.close()
                self.parent.instruction_label2.setStyleSheet("color: gray;")
                self.parent.instruction_label3.setStyleSheet("color: white;")
                maskWidth = self.parent.maskWidth.value()
                self.left = x - int(maskWidth/2)
                self.right = x + int(maskWidth/2)
                # self.left = self.selection_rect.left()
                # self.right = self.selection_rect.right()
                print(f'Mask registered: (Left: {self.left}, Right: {self.right})')
                self.setCoords = False
                self.parent.regReflection.setChecked(False)
                # self.parent.regReflection.setEnabled(True)
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
        self.setFixedSize(QSize(diameter + 50, diameter + 50))

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


class PopupMessage(QWidget):
    def __init__(self, message, timeout=None):
        super().__init__()

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget {
                background-color: #333;
                color: white;
                border-radius: 10px;
                padding: 15px;
                font-size: 32px;
            }
        """)

        layout = QtWidgets.QVBoxLayout()
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)
        self.adjustSize()
        # if timeout:
        #     QTimer.singleShot(timeout, self.close)

    def show_message(self, parent=None, pos=None):
        if parent:
            self.setParent(parent)
        if pos:
            self.move(pos)
        self.show()


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
