import glob
import os
from PIL import Image
import numpy as np
import PIL
import tifffile as tif

import numpy as np
from tiler import Tiler, Merger


images = []
filenames = []
datapath = r'D:\SIM_Data\Evenness\NapariTilingTest'
for imgpath in glob.glob(os.path.join(datapath, "*.tif")):
    filenames.append(imgpath.split("\\")[-1])
    img = Image.open(imgpath)
    img_arr = np.array(img)
    images.append(img_arr)
images = np.stack(images, axis=0)



# Loading image
# Photo by Christian Holzinger on Unsplash: https://unsplash.com/photos/CUY_YHhCFl4
# image = np.array(Image.open("example_image.jpg"))  # 1280x1920x3

# Setup Tiler and Merger
tiler = Tiler(data_shape=img_arr.shape, tile_shape=(64, 64))
merger = Merger(tiler)

# Example 1: process all tiles one by one, i.e. batch_size=0
for tile_i, tile in tiler(image, batch_size=0):
    merger.add(tile_i, tile)
result_bs0 = merger.merge(dtype=image.dtype)

# Example 2: process all tiles in batches of 1, i.e. batch_size=1
merger.reset()
for batch_i, batch in tiler(image, batch_size=1):
    merger.add_batch(batch_i, 1, batch)
result_bs1 = merger.merge(dtype=image.dtype)

# Example 3: process all tiles in batches of 10, i.e. batch_size=10
merger.reset()
for batch_i, batch in tiler(image, batch_size=10):
    merger.add_batch(batch_i, 10, batch)
result_bs10 = merger.merge(dtype=image.dtype)

# Example 4: process all tiles in batches of 10, but drop the batch that has <batch_size tiles, drop_last=True
merger.reset()
for batch_i, batch in tiler(image, batch_size=10, drop_last=True):
    merger.add_batch(batch_i, 10, batch)
result_bs10 = merger.merge(dtype=image.dtype)

assert np.all(result_bs0 == result_bs1)
assert np.all(result_bs0 == result_bs10)