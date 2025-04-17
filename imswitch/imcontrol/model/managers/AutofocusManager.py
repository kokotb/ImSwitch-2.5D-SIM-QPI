import numpy as np
from PIL import Image
from scipy import signal as sg
# from imswitch.imcontrol.view.guitools.ViewSetupInfo import ViewSetupInfo as SetupInfo
from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger
import time
import os
import cv2


class AutofocusManager(SignalInterface):

    def __init__(self):
        super().__init__()
        self._logger = initLogger(self)

    def calcAFArray(self, origin):

        AFList = []
        startZ = origin - 2
        steps = 20
        stepSize = 0.2
        AFList.append(startZ)
        for i in range(steps):
            AFList.append(startZ+(i+1)*stepSize)

        return AFList
            
    def computeLaplacianArray(self, imarray, toPrint = False):
        startTime = time.time()
        scoreArray = []
        for i, image in enumerate(imarray):
            laplacian = cv2.Laplacian(image, cv2.CV_64F)  # Apply Laplacian filter
            score = np.var(laplacian)
            scoreArray.append(score)
            if toPrint:
                print(f'Laplacian {i}: {score}')

        maxVal = max(range(len(scoreArray)), key=scoreArray.__getitem__)
        endTime = time.time()
        elapsed = endTime-startTime
        print(f'Laplacian time: {elapsed}')

            
        return scoreArray, maxVal  # Compute variance of Laplacian
    
    def computeLaplacian(self, img, toPrint = False):

        laplacian = cv2.Laplacian(img, cv2.CV_64F)  # Apply Laplacian filter
        score = np.var(laplacian)
        if toPrint:
            print(f'Laplacian {i}: {score}')           
        return score



# Copyright (C) 2020-2024 ImSwitch developers
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
