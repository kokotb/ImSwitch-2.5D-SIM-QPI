from typing import Dict, List

from imswitch.imcommon.model import APIExport
from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import initLogger


class PositionerController(ImConWidgetController):
    """ Linked to PositionerWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.settingAttr = False
        self.__logger = initLogger(self, tryInheritParent=True)
        self.skewState = 1
        # Set up positioners
        for pName, pManager in self._master.positionersManager:
            if not pManager.forPositioning:
                continue

            speed = hasattr(pManager, 'speed')

            if pName == 'Z':
                self._widget.addPositionerZ(pName, pManager.axes, speed)
            elif pName == 'XY':
                self._widget.addPositionerXY(pName, pManager.axes, speed)
            else:
                self._widget.addPositioner(pName, pManager.axes, speed)
            for axis in pManager.axes:
                self.updatePosition(pName, axis)
                self.setSharedAttr(pName, axis, _positionAttr, pManager.position[axis])
                if speed:
                    self.setSharedAttr(pName, axis, _positionAttr, pManager.speed)
        self.setSharedAttr('Z', 'Z', 'Drift', 0.0) #Drift is savable, but not loadable.
  
        # Connect CommunicationChannel signals
        self._commChannel.sharedAttrs.sigAttributeSet.connect(self.attrChanged)
        self._commChannel.sigUpdateZPosition.connect(self.updatePosition)
        self._commChannel.sigUpdateZPositionConfirmed.connect(self.updatePositionConfirmedVal)
        self._commChannel.sigUpdateXYPosition.connect(self.updatePosition)
        self._commChannel.sigSendZDrift.connect(self.updateZDrift)

        

        # self._commChannel.sigSetSpeed.connect(lambda absPos: self.setAbsPosGUI(speed)) #commented when changing speed function to AbsPos

        # Connect PositionerWidget signals
        self._widget.sigStepUpClicked.connect(self.stepUp)
        self._widget.sigStepDownClicked.connect(self.stepDown)
        self._widget.sigStepUpCoarseClicked.connect(self.stepUpCoarse)
        self._widget.sigStepDownCoarseClicked.connect(self.stepDownCoarse)
        self._widget.sigsetAbsPosClicked.connect(self.setAbsPosGUI)
        # self._widget.sigsetPositionerSpeedClicked.connect(self.setSpeed)
        self._widget.sigWheelEvent.connect(self.focusWheelDelta)
        self._commChannel.sigModuleSettings.connect(self.loadSettings)


        

        
        #Settings window initialization
        try: #this is put in a try because was throwing errors on piezo only. Please think of better way.
            # Positioner settings signals connect
            self._widget.settingsWindow.skew2ptButton.clicked.connect(self.handle2ptSkew)
            self._widget.settingsWindow.skewButton.clicked.connect(self.setSkewOnStage)
            self._widget.settingsWindow.maxSpeedButton.clicked.connect(self.setMaxSpeedOnStage)
            self._widget.settingsWindow.maxAccButton.clicked.connect(self.setMaxAccOnStage)
            self._widget.settingsWindow.jerkButton.clicked.connect(self.setJerkOnStage)
            self._widget.settingsWindow.backlashCheck.stateChanged.connect(self.handleBacklash)
            self._widget.settingsWindow.backlashButton.clicked.connect(self.handleBacklash)
            
            self.stageManager = self._master.positionersManager['XY']
            
            currentSkewRaw = self.stageManager.query("controller.stage.skew.enabled.get")[1]
            currentMaxSpeedRaw = self.stageManager.query("controller.stage.speed.get")[1]
            currentMaxAccRaw = self.stageManager.query("controller.stage.acc.get")[1]
            currentJerkRaw = self.stageManager.query("controller.stage.jerk.get")[1]
            currentBacklashRaw = self.stageManager.query("controller.stage.backlash.get")[1]
            
            
            # displaying values in the correct format
            currentSkew = float(currentSkewRaw)
            
            def convertToInt(i):
                if isinstance(i, str) and i.isdigit():
                    return int(i)
                else:
                    return int(float(i))
            getFromStage = [convertToInt(i) for i in [currentMaxSpeedRaw, currentMaxAccRaw, currentJerkRaw, currentBacklashRaw]]
            currentMaxSpeed, currentMaxAcc, currentJerk, currentBacklash = getFromStage

                      
            self._widget.settingsWindow.skewEntry.setText(f"<strong>{currentSkew:.2f}</strong>")
            self._widget.settingsWindow.maxSpeedLabel.setText(f"<strong>{currentMaxSpeed}</strong>")
            self._widget.settingsWindow.maxAccLabel.setText(f"<strong>{currentMaxAcc}</strong>")
            self._widget.settingsWindow.jerkLabel.setText(f"<strong>{currentJerk}</strong>")
            self._widget.settingsWindow.backlashLabel.setText(f"<strong>{currentBacklash}</strong>")

            # set the values to the entry box at the start
            self._widget.settingsWindow.skewEntry.setText(currentSkew)
            self._widget.settingsWindow.maxSpeedEntry.setText(currentMaxSpeed)
            self._widget.settingsWindow.maxAccEntry.setText(currentMaxAcc)
            self._widget.settingsWindow.jerkEntry.setText(currentJerk)
            self._widget.settingsWindow.backlashEntry.setText(currentBacklash)  

        except:
            pass
        
    
    def handle2ptSkew(self):
        if self.skewState == 1:
            self._widget.settingsWindow.skew2ptButton.setText('Set Point B')
            self.stageManager.query("controller.stage.skrew.about.a")
            self.skewState *= -1
        else:
            self._widget.settingsWindow.skew2ptButton.setText('Set Point A')
            self.stageManager.query("controller.stage.skrew.about.b")
            self.skewState *= -1
            value = self.stageManager.query("controller.stage.skew.enabled.get")[1]
            self._widget.settingsWindow.skewEntry.setText(str(value))
            self._widget.settingsWindow.skewLabel.setText(str(value))
            
        
            
        
        
        
        #self._widget.settingsWindow.skewLabel.setText(f"<strong>{value}</strong>")
             
       
    def setSkewOnStage(self):
        value = float(self._widget.settingsWindow.skewEntry.text())
        if 0 <= value <= 44.9:
            r, _ = self.stageManager.query(f"controller.stage.skew.enabled.set {value}")
            if r == 0:
                self._widget.settingsWindow.skewLabel.setText(f"<strong>{value}</strong>")
                self._widget.settingsWindow.skewEntry.setText(str(value))
            else:
                self.__logger.warning("Skew not set.")
        else:
            self.__logger.warning("Skew value out of range 0-44.90 degrees.")
    
    def setMaxSpeedOnStage(self):
        value = int(self._widget.settingsWindow.maxSpeedEntry.text())
        if 1000 <= value <= 10000:   # input the right ceiling value
            r, _ = self.stageManager.query(f"controller.stage.speed.set {value}")
            if r == 0:
                self._widget.settingsWindow.maxSpeedLabel.setText(f"<strong>{value}</strong>")
                self._widget.settingsWindow.maxSpeedEntry.setText(str(value))
            else:
                self.__logger.warning("Max Speed not set.")
        else:
            self.__logger.warning("Max speed value out of range 1000 to 10000.") #fill in range
            
    def setMaxAccOnStage(self):
        value = int(self._widget.settingsWindow.maxAccEntry.text())
        if 1000 <= value < 100000:   # again
            r, _ = self.stageManager.query(f"controller.stage.acc.set {value}")
            if r == 0:
                self._widget.settingsWindow.maxAccLabel.setText(f"<strong>{value}</strong>")
                self._widget.settingsWindow.maxAccEntry.setText(str(value))
            else:
                self.__logger.warning("Max Acceleration not set.")
        else:
            self.__logger.warning("Max acceleration value out of range 1000 to 100000.") # same here
            
    def setJerkOnStage(self):
        value = int(self._widget.settingsWindow.jerkEntry.text())
        if 0 <= value <= 1000:   # again
            r, _ = self.stageManager.query(f"controller.stage.jerk.set {value}")
            if r == 0:
                self._widget.settingsWindow.jerkLabel.setText(f"<strong>{value}</strong>")
                self._widget.settingsWindow.jerkEntry.setText(str(value))
            else:
                self.__logger.warning("Jerk not set.")
        else:
            self.__logger.warning("Jerk value out of range 0 to 1000.") # same here
           
    def handleBacklash(self):
        isChecked = self._widget.settingsWindow.backlashCheck.isChecked()
        for widget in self._widget.settingsWindow.backlashWidgets:
            widget.setEnabled(isChecked)
        if not isChecked:
            self.stageManager.query("controller.stage.backlash.set 0 {}")
        value = int(self._widget.settingsWindow.backlashEntry.text())
        if 0 <= value <= 100:
            r, _ = self.stageManager.query(f"controller.stage.backlash.set 1 {value}")
            if r == 0:
                self._widget.settingsWindow.backlashLabel.setText(f"<strong>{value}</strong>")
                self._widget.settingsWindow.backlashEntry.setText(str(value))
            else:
                self.__logger.warning("Backlash not set.")
        else:
            self.__logger.warning("Backlash value must be 0–100 μm.")

          
    def updateZDrift(self, drift):
        self.setSharedAttr('Z', 'Z', 'Drift', drift)
        self._widget.pars['DriftZ--Z'].setText(f'({drift:.2f} µm)')


    def loadSettings(self, moduleDict):
        try:
            loadBool = moduleDict['positioners']
        except KeyError:
            loadBool = 0
        if loadBool:
            params = self._commChannel.loadedSettings['Positioner']
            for i in range(len(self._widget.elementList)):
                combinedName = self._widget.elementList[i]._name
                category, axis = combinedName.split('--')
                value = self._commChannel.loadedSettings['Positioner'][category][axis]['Position']
                self.setPos(category, axis, value)

    def closeEvent(self):
        self._master.positionersManager.execOnAll(
            lambda p: [p.setPosition(0, axis) for axis in p.axes],
            condition = lambda p: p.resetOnClose
        )

    def getPos(self):
        return self._master.positionersManager.execOnAll(lambda p: p.position)
    
    def focusWheelDelta(self, focusDelta):
        self._master.positionersManager['Z'].move(focusDelta, 'Z')
        self.updatePosition('Z', 'Z')

    def getSpeed(self):
        return self._master.positionersManager.execOnAll(lambda p: p.speed)

    def move(self, positionerName, axis, dist):
        """ Moves positioner by dist micrometers in the specified axis. """
        self._master.positionersManager[positionerName].move(dist, axis)
        self.updatePosition(positionerName, axis)

    def setPos(self, positionerName, axis, position):
        """ Moves the positioner to the specified position in the specified axis. """
        self._master.positionersManager[positionerName].setPosition(position, axis)
        self.updatePosition(positionerName, axis)

    def stepUp(self, positionerName, axis):
        self.move(positionerName, axis, self._widget.getStepSize(positionerName, axis))

    def stepUpCoarse(self, positionerName, axis):
        self.move(positionerName, axis, self._widget.getStepSizeCoarse(positionerName, axis))

    def stepDown(self, positionerName, axis):
        self.move(positionerName, axis, -self._widget.getStepSize(positionerName, axis))
    
    def stepDownCoarse(self, positionerName, axis):
        self.move(positionerName, axis, -self._widget.getStepSizeCoarse(positionerName, axis))

    def setAbsPosGUI(self, positionerName, axis):
        absPos = self._widget.getAbsPos(positionerName, axis) # pulls value from text box
        self.setAbsPos(positionerName=positionerName, absPos=absPos, axis=axis)
        # Updates all positioners with current value in memory
        # for axis1 in self._master.positionersManager[positionerName].axes: 
        self.updatePosition(positionerName, axis=axis)
        # self.updatePosition(positionerName, axis=axis)

    def setAbsPos(self, positionerName, absPos, axis):
        axes = self._master.positionersManager[positionerName].axes
        if positionerName == 'XY' and len(axes)==2:
            axis_x = axes[0]
            axis_y = axes[1]
            x = self._widget.getAbsPos(positionerName, axis_x)
            y = self._widget.getAbsPos(positionerName, axis_y)
            self._master.positionersManager[positionerName].setPositionXY(x, y)
        else:
            self._master.positionersManager[positionerName].setPosition(absPos, axis)

    
    def setSpeed(self, positionerName):
        axes = self._master.positionersManager[positionerName].axes
        speed = self._widget.getSpeedSize(positionerName, axes[0]) # pulls value from text box
        
        if positionerName == 'XY' and len(axes)==2:
            axis_x = axes[0]
            axis_y = axes[1]
            speed_x = self._widget.getSpeedSize(positionerName, axis_x)
            speed_y = self._widget.getSpeedSize(positionerName, axis_y)
            speed = max([speed_x, speed_y])
            self._master.positionersManager[positionerName].setSpeedLow(speed)

            speed_set = self._master.positionersManager[positionerName].getSpeedLow()
            # self._widget.updateSpeedSize(positionerName, axis_x, speed_set)
            # self._widget.updateSpeedSize(positionerName, axis_y, speed_set)
        else:
            self._master.positionersManager[positionerName].setSpeedLow(speed)
            speed_set = self._master.positionersManager[positionerName].getSpeedLow()
            # self._widget.updateSpeedSize(positionerName, axes[0], speed_set)
            
    
    def updatePosition(self, positionerName, axis):
        newPos = self._master.positionersManager[positionerName].position[axis] #Actually queries device for position.
        # newPositions = self.getPos()
        self._widget.updatePosition(positionerName, axis, float(newPos))
        self.setSharedAttr(positionerName, axis, _positionAttr, newPos)

    def updatePositionConfirmedVal(self, positionerName, axis, newPos):

        self._widget.updatePosition(positionerName, axis, float(newPos))
        self.setSharedAttr(positionerName, axis, _positionAttr, newPos)

    def attrChanged(self, key, value):
        if self.settingAttr or len(key) != 4 or key[0] != _attrCategory:
            return

        positionerName = key[1]
        axis = key[2]
        if key[3] == _positionAttr:
            self.setPositioner(positionerName, axis, value)

    def setSharedAttr(self, positionerName, axis, attr, value):
        self.settingAttr = True
        try:
            self._commChannel.sharedAttrs[(_attrCategory, positionerName, axis, attr)] = str(value)
        finally:
            self.settingAttr = False

    def setXYPosition(self, positionerName, x, y):
        # positionerX = self.getPositionerNames()[0]
        # positionerY = self.getPositionerNames()[1]
        # self.__logger.debug(f"Move {positionerX}, axis X, dist {str(x)}")
        # self.__logger.debug(f"Move {positionerY}, axis Y, dist {str(y)}")
        if positionerName == 'XY':
            self.__logger.debug(f"Move {positionerName}, axis X, dist {str(x)}, axis Y, dist {str(y)}")
            self._master.positionersManager[positionerName].setPositionXY(x, y)
        else:
            print(f"{positionerName} cannot perform this operation!")
        #self.move(positionerX, 'X', x)
        #self.move(positionerY, 'Y', y)

    def setZPosition(self, z):
        positionerZ = self.getPositionerNames()[2]
        self.__logger.debug(f"Move {positionerZ}, axis Z, dist {str(z)}")
        #self.move(self.getPositionerNames[2], 'Z', z)


    @APIExport()
    def getPositionerNames(self) -> List[str]:
        """ Returns the device names of all positioners. These device names can
        be passed to other positioner-related functions. """
        return self._master.positionersManager.getAllDeviceNames()

    @APIExport()
    def getPositionerPositions(self) -> Dict[str, Dict[str, float]]:
        """ Returns the positions of all positioners. """
        return self.getPos()

    @APIExport(runOnUIThread=True)
    def setPositionerStepSize(self, positionerName: str, stepSize: float) -> None:
        """ Sets the step size of the specified positioner to the specified
        number of micrometers. """
        self._widget.setStepSize(positionerName, stepSize)

    @APIExport(runOnUIThread=True)
    def movePositioner(self, positionerName: str, axis: str, dist: float) -> None:
        """ Moves the specified positioner axis by the specified number of
        micrometers. """
        self.move(positionerName, axis, dist)
    

    @APIExport(runOnUIThread=True)
    def movePositionerXY(self, positionerName: str, position_x: float, position_y:float):
        """ Moves the specified positioner on both axes in XY at the same time. """
        self.setXYPosition(positionerName, position_x, position_y)

    @APIExport(runOnUIThread=True)
    def setPositioner(self, positionerName: str, axis: str, position: float) -> None:
        """ Moves the specified positioner axis to the specified position. """
        self.setPos(positionerName, axis, position)

    @APIExport(runOnUIThread=True)
    def setPositionerSpeed(self, positionerName: str, speed: float) -> None:
        """ Moves the specified positioner axis to the specified position. """
        self.setSpeed(positionerName, speed)

    @APIExport(runOnUIThread=True)
    def setMotorsEnabled(self, positionerName: str, is_enabled: int) -> None:
        """ Moves the specified positioner axis to the specified position. """
        self._master.positionersManager[positionerName].setEnabled(is_enabled)

    @APIExport(runOnUIThread=True)
    def stepPositionerUp(self, positionerName: str, axis: str) -> None:
        """ Moves the specified positioner axis in positive direction by its
        set step size. """
        self.stepUp(positionerName, axis)

    @APIExport(runOnUIThread=True)
    def stepPositionerDown(self, positionerName: str, axis: str) -> None:
        """ Moves the specified positioner axis in negative direction by its
        set step size. """
        self.stepDown(positionerName, axis)



_attrCategory = 'Positioner'
_positionAttr = 'Position'


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
