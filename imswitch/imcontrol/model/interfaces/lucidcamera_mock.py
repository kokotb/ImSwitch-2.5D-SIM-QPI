import os
import glob

import numpy as np
from scipy.stats import multivariate_normal

import time
import tifffile as tif


class LucidCamMock:
    def __init__(self):
        self.properties = {
            'Height': 1024,
            'Width': 1024,
            'OffsetX': 0,
            'OffsetY': 0,
            'subarray_vpos': 0,
            'subarray_hpos': 0,
            'ExposureTime': 0.1,
            'subarray_vsize': 1024,
            'subarray_hsize': 1024,
            'HeightMax': 4600,
            'WidthMax': 5320,
            'StreamBufferHandlingMode': "NewestOnly"
        }
        self.exposure = 100
        self.gain = 1
        self.brightness = 1
        self.model = 'mock'
        self.SensorHeight = 512
        self.SensorWidth = 512
        self.shape = (self.SensorHeight,self.SensorWidth)
        self.tl_stream_nodemap = []

    def start_live(self):
        pass
    
    def start_liveSIM(self, num_buffers):
        pass

    def stop_live(self):
        pass

    def suspend_live(self):
        pass

    def prepare_live(self):
        pass

    def setROI(self, hpos, vpos, hsize, vsize):
        pass

    def setBinning(self, binning):
        pass

    def forceValidROI(self, hpos, vpos, hsize, vsize):

        #OffsetX(hpos) and Width(hsize) must be in multiples of 8, with Width minimum >=32.
        #OffsetY(vpos) and Height(hsize) must be even, with Height minimum >=32.
        xmod = 8
        ymod = 2
        integer, decimal = divmod(hpos/xmod,1)
        if decimal < 0.5:
            hpos_new = int(xmod*integer)
        else:
            hpos_new = int(xmod*(integer+1))
        integer, decimal = divmod(vpos/ymod,1)
        if decimal < 0.5:
            vpos_new = int(ymod*integer)
        else:
            vpos_new = int(ymod*(integer+1))

        integer, decimal = divmod(hsize/xmod,1)
        if decimal < 0.5:
            hsize_new = int(xmod*integer)
        else:
            hsize_new = int(xmod*(integer+1))
        integer, decimal = divmod(vsize/ymod,1)
        if decimal < 0.5:
            vsize_new = int(ymod*integer)
        else:
            vsize_new = int(ymod*(integer+1))
        
        hsize_new = max(hsize_new, 32)  # minimum ROI size (32 for Lucid cam)
        vsize_new = max(vsize_new, 32)  # minimum ROI size (32 for Lucid cam)

        return hpos_new, vpos_new, hsize_new, vsize_new

    def grabFrame(self, **kwargs):
        mocktype = "random_peak"
        if mocktype=="focus_lock":
            img = np.zeros((500, 600))
            beamCenter = [int(np.random.randn() * 1 + 250), int(np.random.randn() * 30 + 300)]
            img[beamCenter[0] - 10:beamCenter[0] + 10, beamCenter[1] - 10:beamCenter[1] + 10] = 1
        elif mocktype=="random_peak":
            # imgsize = (800, 800)
            imgsize = self.shape
            peakmax = 60
            noisemean = 10
            # generate image
            img = np.zeros(imgsize)
            # add a random gaussian peak sometimes
            if np.random.rand() > 0.8:
                x, y = np.meshgrid(np.linspace(0,imgsize[1],imgsize[1]), np.linspace(0,imgsize[0],imgsize[0]))
                pos = np.dstack((x, y))
                xc = (np.random.rand()*2-1)*imgsize[0]/2 + imgsize[0]/2
                yc = (np.random.rand()*2-1)*imgsize[1]/2 + imgsize[1]/2
                rv = multivariate_normal([xc, yc], [[50, 0], [0, 50]])
                img = np.random.rand()*peakmax*317*rv.pdf(pos)
                img = img + 0.01*np.random.poisson(img)
            # add Poisson noise
            img = img + np.random.poisson(lam=noisemean, size=imgsize)
        else:
            img = np.zeros((500, 600))
            beamCenter = [int(np.random.randn() * 30 + 250), int(np.random.randn() * 30 + 300)]
            img[beamCenter[0] - 10:beamCenter[0] + 10, beamCenter[1] - 10:beamCenter[1] + 10] = 1
            img = np.random.randn(img.shape[0],img.shape[1])
        return img

    def getLast(self, is_resize=False):
        return self.grabFrame()
    
    def getROIValue(self, property_name):

        try:
            return self.properties[property_name]
        except Exception as e:
            return 0
    
    def getLastChunk(self):
        return np.expand_dims(self.grabFrame(),0)
    
    def setPropertyValue(self, property_name, property_value, toPrint=True):
        return property_value

    def getPropertyValue(self, property_name):
        try:
            return self.properties[property_name]
        except Exception as e:
            return 0

    def openPropertiesGUI(self):
        pass
    
    def close(self):
        pass

    def close(self):
        pass
    
    def flushBuffer(self):
        pass 
    
    def getBufferValue(self):
        value = 9
        return value
    
    def setCamForAcquisition(self, buffer_size):
        pass
    
    def grabFrameSet(self, buffer_size):
        #if False:
        if True:
            allImages = []
            # Hardcoded path
            path_current_py = os.path.dirname(os.path.realpath(__file__))
            # Three parents above to get to imswitch folder
            path_parent = os.path.abspath(os.path.join(os.path.abspath(os.path.join(os.path.abspath(os.path.join(path_current_py, os.pardir)), os.pardir)), os.pardir))
            print(path_parent)
            # Hardcoded folder but same an all machines
            path_child = "_data\\test_data_ImSwitch"
            # Create the path
            path_in = os.path.join(path_parent, path_child)
            # names_import = glob.glob(f'{path_in}\\*{dic_wl[num]}*.tif*')
            names_import = glob.glob(f'{path_in}\\*{488}*.tif*')
            stack_mock_color = []
            for name in names_import:
                stack_mock_color.append(tif.imread(name))
            #allImages.append(stack_mock_color)
            allImages = np.array(np.divide(stack_mock_color,16).astype(np.uint16))
        else:
            # Simulate SIM set 
            # Nx = 1024
            # Ny = 1024
            import NanoImagingPack as nip
            Nx, Ny = self.shape
            Nrot = 3
            Nphi = 3
            Isample = np.zeros((Nx,Ny))
            Isample[np.random.random(Isample.shape)>0.999]=1

            allImages = []
            for iRot in range(Nrot):
                for iPhi in range(Nphi):
                    IGrating = 1+np.sin(((iRot/Nrot)*nip.xx((Nx,Ny))+(Nrot-iRot)/Nrot*nip.yy((Nx,Ny)))*np.pi/2+np.pi*iPhi/Nphi)
                    allImages.append(nip.gaussf(IGrating*Isample,3))

            allImages=np.array(allImages)
            allImages-=np.min(allImages)
            allImages/=np.max(allImages)
        return allImages

    def setCamForLiveView(self, trigBool=False):
        pass
    
    def setCamForAcquisition(self, buffer_size):
        pass
    
    def setCamStopAcquisition(self):
        pass
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


"""path_current_py = os.path.dirname(os.path.realpath(__file__))
path_parent = os.path.abspath(os.path.join(os.path.abspath(os.path.join(os.path.abspath(os.path.join(path_current_py, os.pardir)), os.pardir)), os.pardir))
print(path_parent)
path_child = "_data\\test_data_ImSwitch"
path_in = os.path.join(path_parent, path_child)
print(path_in)"""