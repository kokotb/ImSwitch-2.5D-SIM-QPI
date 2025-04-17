from ..basecontrollers import ImConWidgetController
import numpy as np
from imswitch.imcommon.model import initLogger
import os
import cv2
from tifffile import tifffile

import time

class AutofocusController(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self.sharedAttrs = self._commChannel.sharedAttrs._data
        self._widget.sigAutofocusInfoChanged.connect(self.valueChanged)
        # self._widget.checkbox_Autofocus.stateChanged.connect(self.testFunc)
        self._widget.initValues()

    def load_tif_images_from_folder(folder_path):
        # List all files in the folder
        tif_images = []
        
        # Loop through all files in the folder
        for filename in os.listdir(folder_path):
            if filename.endswith('.tif') or filename.endswith('.tiff'):  # Check for .tif or .tiff extensions
                file_path = os.path.join(folder_path, filename)
                
                # Use tifffile to load the image
                try:
                    image = tifffile.imread(file_path)
                    startTime = time.time()
                    # image = image / ((2**4)-1)
                    # image = image.astype(np.uint8)
                    endTime = time.time()
                    elapsed = endTime - startTime
                    tif_images.append(image)
                    # print(f"Loaded image: {filename}")
                except Exception as e:
                    print(f"Error loading image {filename}: {e}")
        
        return tif_images, elapsed
    
    def getLastZStack(self):
        pass

    # def testFunc(self):


    def calcAFArray(self, origin):

        AFList = []
        startZ = origin - 1
        steps = 10
        stepSize = 0.2
        AFList.append(startZ)
        for i in range(steps):
            AFList.append(startZ+(i+1)*stepSize)

        return AFList

    def computeLaplacianArray(imarray, toPrint = False):
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



    def valueChanged(self, attrCategory, parameterName, value):
        self.setSharedAttr(attrCategory, parameterName, value)

    def setSharedAttr(self, attrCategory, parameterName, value):
        """Sending attribute to shared attributes

        Args:
            parameterName (str): name of a parameter passed from wdiget
            attr (_type_): type of a attribute (value, enabled, ...)
            value (_type_): value of the parameter read from wdiget
        """
        # print(value)
        self.settingAttr = True
        try:
            self._commChannel.sharedAttrs[(attrCategory, parameterName)] = value
        finally:
            self.settingAttr = False

    


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
