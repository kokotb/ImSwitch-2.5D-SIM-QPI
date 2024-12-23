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




# Setup tiling parameters
tiler = Tiler(data_shape=(1, 512,512),
              tile_shape=(0, 64,64),
              overlap = 0.1)

## Access tiles:
# # 1. with an iterator
for tile_id, tile in tiler.iterate(images):
   print(f'Tile {tile_id} out of {len(tiler)} tiles.')
# # 1b. the iterator can also be accessed through __call__
# for tile_id, tile in tiler(images):
#    print(f'Tile {tile_id} out of {len(tiler)} tiles.')
# # 2. individually
# tile_3 = tiler.get_tile(images, 3)
# # 3. in batches
# tiles_in_batches = [batch for _, batch in tiler(images, batch_size=9)]

# Setup merging parameters
merger = Merger(tiler)

## Merge tiles:
# 1. one by one
# for tile_id, tile in tiler(img_arr):
#    merger.add(tile_id)
# 2. in batches
merger.reset()
for batch_id, batch in tiler(images, batch_size=9):
   merger.add_batch(batch_id, 9, batch)

# Final merging: applies tapering and optional unpadding
final_image = merger.merge(unpad=True)  # (3, 1920, 1080)