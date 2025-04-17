from qtpy import QtCore, QtWidgets
from PyQt5.QtWidgets import (QCheckBox, QLineEdit)
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtGui import QIntValidator, QDoubleValidator


class TimingWidget(NapariHybridWidget):

    sigTimingInfoChanged = QtCore.Signal(str, str, str)

    def __post_init__(self):
        # super().__init__(*args, **kwargs)
        timingLayout = QtWidgets.QGridLayout()
        self.setLayout(timingLayout)

        self.elementList = []

        self.checkbox_timingPeriod = QCheckBox('Period')
        self.checkbox_timingPeriod._name = 'Period Checkbox'
        self.checkbox_timingPeriod._type = 'int'
        ####
        self.timingPeriod_textedit = QLineEdit("")
        self.timingPeriod_textedit._name = 'Timing Period'
        self.timingPeriod_textedit._type = 'str'
        self.validator = QDoubleValidator()
        self.timingPeriod_textedit.setValidator(self.validator)
        self.timingPeriod_textedit.setToolTip('Time from the start of one set of images to another. If this time is shorter that the image cycle, it will run as fast as possible.')
        self.timingPeriod_textedit.setFixedWidth(50)

        self.timingPeriod_textedit.setEnabled(False)
        ####
        self.timingUnit = QtWidgets.QComboBox()
        self.timingUnit._name = 'Timing Unit'
        self.timingUnit._type = 'combostr'
        self.timingUnit.setFixedWidth(30)
        self.timingUnit.setEnabled(False)
        
        ######################
        self.checkbox_timingDuration = QCheckBox('Duration')
        self.checkbox_timingDuration._name = 'Duration Checkbox'
        self.checkbox_timingDuration._type = 'int'
        ####
        self.timingDuration_textedit = QLineEdit("")
        self.timingDuration_textedit._name = 'Duration'
        self.timingDuration_textedit._type = 'str'
        self.timingDuration_textedit.setEnabled(False)
        self.validator = QDoubleValidator()
        self.timingDuration_textedit.setValidator(self.validator)
        self.timingDuration_textedit.setToolTip('Length of time to execute experiment.')
        self.timingDuration_textedit.setFixedWidth(50)

        ####
        self.timingDurationUnit = QtWidgets.QComboBox()
        self.timingDurationUnit._name = 'Duration Unit'
        self.timingDurationUnit._type = 'combostr'
        self.timingDurationUnit.setFixedWidth(30)
        self.timingDurationUnit.setEnabled(False)
        ##########################################
        self.checkbox_tilingReps = QCheckBox('Reps')
        self.checkbox_tilingReps._name = 'Rep Checkbox'
        self.checkbox_tilingReps._type = 'int'
        self.totalReps_textedit = QLineEdit("")
        self.totalReps_textedit._name = 'Repetitions'
        self.totalReps_textedit._type = 'str'
        self.totalReps_textedit.setEnabled(False)
        self.validator = QIntValidator(0,10000,self)
        self.totalReps_textedit.setFixedWidth(50)
        self.totalReps_textedit.setValidator(self.validator)
        

        ################
        self.elementList.append(self.checkbox_timingPeriod)
        self.elementList.append(self.timingPeriod_textedit)
        self.elementList.append(self.timingUnit)
        self.elementList.append(self.checkbox_timingDuration)
        self.elementList.append(self.timingDuration_textedit)
        self.elementList.append(self.timingDurationUnit)
        self.elementList.append(self.checkbox_tilingReps)
        self.elementList.append(self.totalReps_textedit)
        ################

        #Signals from widget elements
        self.timingPeriod_textedit.textChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Timing Period', value))
        self.timingDuration_textedit.textChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Duration', value))
        self.totalReps_textedit.textChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings',"Repetitions", value))
        ####
        self.timingUnit.currentTextChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Timing Unit', value))
        self.timingDurationUnit.currentTextChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Duration Unit', value))
        ####
        self.checkbox_timingPeriod.stateChanged.connect(self.togglePer)
        self.checkbox_timingPeriod.stateChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Period Checkbox', str(value)))
        self.checkbox_tilingReps.stateChanged.connect(self.toggleReps)
        self.checkbox_tilingReps.stateChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Rep Checkbox', str(value)))
        self.checkbox_timingDuration.stateChanged.connect(self.toggleDuration)
        self.checkbox_timingDuration.stateChanged.connect(lambda value: self.sigTimingInfoChanged.emit('Timing Settings','Duration Checkbox', str(value)))

        row = 0
        timingLayout.addWidget(self.checkbox_timingPeriod, row, 0)
        timingLayout.addWidget(self.timingPeriod_textedit, row, 1)
        timingLayout.addWidget(self.timingUnit, row, 2)
        timingLayout.addWidget(self.checkbox_timingDuration, row+1, 0)
        timingLayout.addWidget(self.timingDuration_textedit, row+1, 1)
        timingLayout.addWidget(self.timingDurationUnit, row+1, 2)
        timingLayout.addWidget(self.checkbox_tilingReps, row+2, 0)
        timingLayout.addWidget(self.totalReps_textedit, row+2, 1)

        self.repCheckState = False
        self.durCheckState = False
        self.perCheckState = False


     



    def toggleCheckboxes(self, state):
        state = not state
        if state == False:
            self.checkbox_timingPeriod.setEnabled(state)
            self.checkbox_tilingReps.setEnabled(state)
            self.checkbox_timingDuration.setEnabled(state)
            self.totalReps_textedit.setEnabled(state)
            self.timingDuration_textedit.setEnabled(state)
            self.timingDurationUnit.setEnabled(state)
            self.timingPeriod_textedit.setEnabled(state)
            self.timingUnit.setEnabled(state)

        if state == True:

            if self.checkbox_timingPeriod.checkState() == 2:
                self.checkbox_timingPeriod.setEnabled(state)
                self.timingPeriod_textedit.setEnabled(state)
                self.timingUnit.setEnabled(state)
            else:
                self.checkbox_timingPeriod.setEnabled(state)
                self.timingPeriod_textedit.setEnabled(not state)
                self.timingUnit.setEnabled(not state)

            if self.checkbox_timingDuration.checkState() == 2:
                self.timingDuration_textedit.setEnabled(state)
                self.timingDurationUnit.setEnabled(state)
                self.checkbox_timingDuration.setEnabled(state)
                self.checkbox_tilingReps.setEnabled(not state)
                self.totalReps_textedit.setEnabled(not state)
            
            elif self.checkbox_tilingReps.checkState() == 2:
                self.checkbox_tilingReps.setEnabled(state)
                self.totalReps_textedit.setEnabled(state)
                self.checkbox_timingDuration.setEnabled(not state)
                self.timingDuration_textedit.setEnabled(not state)
                self.timingDurationUnit.setEnabled(not state)

            elif (self.checkbox_tilingReps.checkState() == 0) and (self.checkbox_timingDuration.checkState() == 0):
                self.checkbox_tilingReps.setEnabled(state)
                self.checkbox_timingDuration.setEnabled(state)
                self.totalReps_textedit.setEnabled(not state)
                self.timingDuration_textedit.setEnabled(not state)
                self.timingDurationUnit.setEnabled(not state)


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
            # self.timingDuration_textedit.setEnabled(False)
            self.checkbox_timingDuration.setEnabled(False)
        else:
            self.totalReps_textedit.setEnabled(False)
            # self.timingDuration_textedit.setEnabled(False)
            self.checkbox_timingDuration.setEnabled(True)

    def togglePer(self):
        self.perCheckState = not self.perCheckState
        if self.perCheckState:
            self.timingPeriod_textedit.setEnabled(True)
            self.timingUnit.setEnabled(True)
        else:
            self.timingPeriod_textedit.setEnabled(False)
            self.timingUnit.setEnabled(False)


    
    def populateUnitsList(self):
        self.timingUnit.addItems(['s', 'm','h'])
        self.timingDurationUnit.addItems(['s', 'm','h'])
        self.timingDurationUnit.setCurrentIndex(1)



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
