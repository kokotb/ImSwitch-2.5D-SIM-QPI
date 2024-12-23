import glob
import os
from PIL import Image
import numpy as np
import PIL
import tifffile as tif

images = []
filenames = []
datapath = r'D:\SIM_Data\Evenness\NapariTilingTest'

for imgpath in glob.glob(os.path.join(datapath, "*.tif")):
    filenames.append(imgpath.split("\\")[-1])
    img = Image.open(imgpath)
    img_arr = np.array(img)
    images.append(img_arr)


for k, img in enumerate(images):
    filepath = os.path.join(datapath,'TagEdited') 
    if not os.path.exists(filepath):
            os.makedirs(filepath)
    fullpath = os.path.join(filepath,filenames[k]) 
    try:
        
        tif.imwrite(fullpath, img, metadata ={'data_shape':'512x512'})
    except  Exception as e:
        print('Something happened')