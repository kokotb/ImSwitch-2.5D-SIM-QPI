import numpy as np
from PIL import Image
from scipy import signal as sg
from scipy.ndimage import gaussian_filter
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
        self.init_guess_x = [0,936,750,70]	# Guesses for fits Background, Centre, Width, Amplitude
        self.init_guess_y = [0,480,380,70]
        self.threshold = 5
         #pixel value threshold for AF image
        self.guess_x = self.init_guess_x[:]	# Guesses for fits Background, Centre, Width, Amplitude
        self.guess_y = self.init_guess_y[:]

    # def getXfromY(self, y):
    #     x = (y-self.y_int)/self.x_slp

    #     return x

    def getYfromX(self, x):
        y = (self.x_slp*x) + self.y_int

        return y

    def scoreOneLive(self, img, left, right):
        score, x_sigma, y_sigma = self.scoreOneImg(img, left, right)
        return score
    
    def removeColumns(self, img, left, right):
        imgMasked = np.delete(img,range(left,right),1)
        return imgMasked
    
    def scoreOneImg(self, im, left, right):
        # Define the model function. In our case, a 1D Gaussian.


        def Gaussian1D(xdata, i0, x0, sX, amp):
            x = xdata
            x0 = float(x0)
            eq = i0+amp*np.exp(-((x-x0)**2/2/sX**2))
            return eq

        try:
            from scipy.optimize import curve_fit
        except ImportError:
            print("Unable to import curve_fit from scipy.optimize.")

        im = im-np.mean(self.removeColumns(im, left, right))/2	# Remove background
        im[im<self.threshold] = 0			# Threshold

        imGaussBlur = gaussian_filter(im.astype(float), sigma=15)
    
        # 1D Gaussian
        h1, w1 = im.shape
        x = np.arange(w1)
        y = np.arange(h1)
        xMasked = np.delete(x, range(left, right))
        imgMaskDel = self.removeColumns(imGaussBlur, left, right)

        # Do x fit
        popt, pcov = curve_fit(Gaussian1D, xMasked, np.mean(imgMaskDel,axis=0), p0=self.guess_x, maxfev = 50000)
        x0 = popt[1]
        sx = popt[2]
        # self.guess_x.clear()
        # self.guess_x.append(popt)
        # Do y fit
        popt, pcov = curve_fit(Gaussian1D, y, np.mean(imgMaskDel,axis=1), p0=self.guess_y, maxfev = 50000)
        y0 = popt[1]
        sy = popt[2]
        
        # Replaces initial guess with final guess
        # self.guess_y.clear()
        # self.guess_y.append(popt)
    
        x_sigma = abs(sx)
        y_sigma = abs(sy)
        score = x_sigma - y_sigma

        # x_c.append(popt[1])
        return score, x_sigma, y_sigma
            

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
