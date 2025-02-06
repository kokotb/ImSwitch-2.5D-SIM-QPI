from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QIntValidator, QDoubleValidator
import napari

class TimingWidget(NapariHybridWidget):

    sigTimingInfoChanged = QtCore.Signal(str, str, str)
    # sigTimingCheckChanged = QtCore.Signal(str, str, int)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        timingLayout = QtWidgets.QGridLayout()
        self.setLayout(timingLayout)

        self.elementList = []

        self.timingPeriod_label = QLabel("Period")
        self.timingPeriod_textedit = QLineEdit("")
        self.timingPeriod_textedit._name = 'Timing Period'
        self.timingPeriod_textedit._type = 'str'
        self.validator = QDoubleValidator()  # Range from 0.0 to 2.0 with 2 decimal places
        self.timingPeriod_textedit.setValidator(self.validator)
        self.timingPeriod_textedit.setToolTip('Time from the start of one set of images to another. If this time is shorter that the image cycle, it will just run as fastest speed possible.')  
        self.timingPeriod_textedit.setPlaceholderText('Blank or 0 is max frame rate')
        self.timingPeriod_textedit.setFixedWidth(50)
        self.timingPeriod_textedit.textChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Timing Period', value))
        self.timingUnit = QtWidgets.QComboBox()
        self.timingUnit._name = 'Timing Unit'
        self.timingUnit._type = 'combostr'
        self.timingUnit.setFixedWidth(30)

        self.checkbox_timingDuration = QCheckBox('Duration')
        self.checkbox_timingDuration._name = 'Duration Checkbox'
        self.checkbox_timingDuration._type = 'int'
        # self.timingDuration_label = QLabel("Duration")
        self.timingDuration_textedit = QLineEdit("")
        self.timingDuration_textedit._name = 'Duration'
        self.timingDuration_textedit._type = 'str'
        self.timingDuration_textedit.setEnabled(False)
        self.validator = QDoubleValidator()
        self.timingDuration_textedit.setValidator(self.validator)
        self.timingDuration_textedit.setToolTip('Length of time to execute experiment.')
        self.timingDuration_textedit.setPlaceholderText('Blank or 0 is continuous')
        self.timingDuration_textedit.setFixedWidth(50)
        self.timingDuration_textedit.textChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Duration', value))
        # self.timingDuration_textedit.editingFinished.connect(self.calcReps)
        self.timingDurationUnit = QtWidgets.QComboBox()
        self.timingDurationUnit._name = 'Duration Unit'
        self.timingDurationUnit._type = 'combostr'
        self.timingDurationUnit.setFixedWidth(30)
        self.timingDurationUnit.setEnabled(False)

        self.checkbox_tilingReps = QCheckBox('Reps')
        self.checkbox_tilingReps._name = 'Rep Checkbox'
        self.checkbox_tilingReps._type = 'int'
        # self.tilingReps_label = QLabel("Repetitions")
        self.totalReps_textedit = QLineEdit("")
        self.totalReps_textedit._name = 'Repetitions'
        self.totalReps_textedit._type = 'str'
        self.totalReps_textedit.setEnabled(False)
        self.validator = QIntValidator(0,10000,self)
        self.totalReps_textedit.setFixedWidth(50)
        self.totalReps_textedit.setValidator(self.validator)
        self.totalReps_textedit.textChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings',"Repetitions", value))
        # self.tilingReps_textedit.editingFinished.connect(self.calcDuration)


        ################
        self.elementList.append(self.timingPeriod_textedit)
        self.elementList.append(self.timingUnit)
        self.elementList.append(self.checkbox_timingDuration)
        self.elementList.append(self.timingDuration_textedit)
        self.elementList.append(self.timingDurationUnit)
        self.elementList.append(self.checkbox_tilingReps)
        self.elementList.append(self.totalReps_textedit)
        ######################



        
        self.timingUnit.currentTextChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Timing Unit', value))
        self.timingDurationUnit.currentTextChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Duration Unit', value))


        row = 0
        
        timingLayout.addWidget(self.timingPeriod_label, row, 0)
        timingLayout.addWidget(self.timingPeriod_textedit, row, 1)
        timingLayout.addWidget(self.timingUnit, row, 2)
        timingLayout.addWidget(self.checkbox_timingDuration, row+1, 0)
        # timingLayout.addWidget(self.timingDuration_label, row+1, 1)
        timingLayout.addWidget(self.timingDuration_textedit, row+1, 1)
        timingLayout.addWidget(self.timingDurationUnit, row+1, 2)
        timingLayout.addWidget(self.checkbox_tilingReps, row+2, 0)
        # timingLayout.addWidget(self.tilingReps_label, row+2, 1)
        timingLayout.addWidget(self.totalReps_textedit, row+2, 1)

        self.repCheckState = False
        self.durCheckState = False

        self.checkbox_tilingReps.stateChanged.connect(self.toggleReps)
        self.checkbox_tilingReps.stateChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Rep Checkbox', str(value)))

        self.checkbox_timingDuration.stateChanged.connect(self.toggleDuration)
        self.checkbox_timingDuration.stateChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Duration Checkbox', str(value)))
     



    def toggleCheckboxes(self, state):
        state = not state
        self.checkbox_tilingReps.setEnabled(state)
        self.checkbox_timingDuration.setEnabled(state)

    def toggleDuration(self):
        self.durCheckState = not self.durCheckState
        if self.durCheckState:
            self.timingDuration_textedit.setEnabled(True)
            self.totalReps_textedit.setEnabled(False)
            self.checkbox_tilingReps.setEnabled(False)
            self.timingDurationUnit.setEnabled(True)
        else:
            self.timingDuration_textedit.setEnabled(False)
            self.totalReps_textedit.setEnabled(False)
            self.checkbox_tilingReps.setEnabled(True)
            self.timingDurationUnit.setEnabled(False)

    def toggleReps(self):
        self.repCheckState = not self.repCheckState
        if self.repCheckState:
            self.totalReps_textedit.setEnabled(True)
            self.timingDuration_textedit.setEnabled(False)
            self.checkbox_timingDuration.setEnabled(False)
        else:
            self.totalReps_textedit.setEnabled(False)
            self.timingDuration_textedit.setEnabled(False)
            self.checkbox_timingDuration.setEnabled(True)

    
    def populateUnitsList(self):
        self.timingUnit.addItems(['s', 'm','h'])
        self.timingDurationUnit.addItems(['s', 'm','h'])
        self.timingDurationUnit.setCurrentIndex(1)
        
    # def calcReps(self):
    #     period = self.getPeriodInSec()
    #     duration = self.getDurationInSec()
    #     reps = duration / period
    #     print(reps)

    # def calcDuration(self):
    #     period = self.getPeriodInSec()
    #     reps = self.tilingReps_textedit.text()
    #     duration = period * reps
    #     print(duration)

    # def getPeriodInSec(self):
    #     try:
    #         timingPeriodBox = float(self.timingPeriod_textedit.text())
    #     except ValueError:
    #         timingPeriodBox = 0
    #     except KeyError:
    #         timingPeriodBox = None
    #     if timingPeriodBox is not None:
    #         timingUnit = self.timingUnit.currentText()
    #         if timingUnit == 's':
    #             timingSecs = timingPeriodBox
    #         elif timingUnit == 'm':
    #             timingSecs = timingPeriodBox * 60
    #         elif timingUnit == 'h':

    #             timingSecs = timingPeriodBox * 3600
    #         return timingSecs
    #     return None
    
    # def getDurationInSec(self):
    #     try:
    #         timingDurationBox = float(self.timingDuration_textedit.text())
    #     except ValueError:
    #         timingDurationBox = 0
    #     except KeyError:
    #         timingDurationBox = None
    #     if timingDurationBox is not None:
    #         durationUnit = self.timingDurationUnit.currentText()
    #         if durationUnit == 's':
    #             durationsSecs = timingDurationBox
    #         elif durationUnit == 'm':
    #             durationsSecs = timingDurationBox * 60
    #         elif durationUnit == 'h':

    #             durationsSecs = timingDurationBox * 3600
    #         return durationsSecs
    #     return None

        



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
