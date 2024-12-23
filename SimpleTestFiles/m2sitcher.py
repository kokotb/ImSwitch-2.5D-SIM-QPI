# coding: utf-8
from os import path
import os
import numpy as np
import pandas as pd
import glob
from PIL import Image
import m2stitch
import matplotlib.pyplot as plt
import tifffile as tif

script_path = path.dirname(path.realpath(__file__))

images = []
filenames = []
datapath = r'D:\Cody Folder\Personal\Poster\241111_153020_CT_PosterImages_5x5O10\Tiling\WF'

for imgpath in glob.glob(os.path.join(datapath, "*.tif")):
    filenames.append(imgpath.split("\\")[-1])
    img = tif.imread(imgpath)
    img_arr = np.array(img)
    images.append(img_arr)
images = np.stack(images, axis=0)


ch1 = []
ch2 = []
ch3 = []
for k, img in enumerate(images):
    currentFile = filenames[k].split('_')[2]
    if currentFile == '488':
        ch1.append(np.array(img))
    elif currentFile == '561':
        ch2.append(np.array(img))
        print(filenames[k])
    elif currentFile == '640':
        ch3.append(np.array(img))
ch2 = np.stack(ch2, axis=0)

    


# props_file_path = path.join(script_path, "../tests/data/testimages_props.csv")
# props = pd.read_csv(props_file_path, index_col=0)

cols = [1,1,1,1,1,2,2,2,2,2,3,3,3,3,3,4,4,4,4,4,5,5,5,5,5]
rows = [1,2,3,4,5,5,4,3,2,1,1,2,3,4,5,5,4,3,2,1,1,2,3,4,5]

# print(ch2.shape)
# # must be 3-dim, with each dimension meaning (tile_index,x,y)
# print(rows)
# # the row (second-last dim.) indices for each tile index. for example, [1,1,2,2,2,...]
# print(cols)
# the column (last dim.) indices for each tile index. for example, [2,3,1,2,3,...]

# Note : the row_col_transpose=True is kept only for the sake of version compatibility.
# In the mejor version, the row_col_transpose=False will be the default.
result_df, _ = m2stitch.stitch_images(ch2, rows, cols, row_col_transpose=False)

print(result_df["y_pos"])
# the absolute y (second last dim.) positions of the tiles
print(result_df["x_pos"])
# the absolute x (last dim.) positions of the tiles

# stitching example
result_df["y_pos2"] = result_df["y_pos"] - result_df["y_pos"].min()
result_df["x_pos2"] = result_df["x_pos"] - result_df["x_pos"].min()

size_y = images.shape[1]
size_x = images.shape[2]

stitched_image_size = (
    result_df["y_pos2"].max() + size_y,
    result_df["x_pos2"].max() + size_x,
)
stitched_image = np.zeros_like(images, shape=stitched_image_size)
for i, row in result_df.iterrows():
    stitched_image[
        row["y_pos2"] : row["y_pos2"] + size_y,
        row["x_pos2"] : row["x_pos2"] + size_x,
    ] = images[i]
plt.imshow(stitched_image, cmap="gray")
# im = Image.open(stitched_image)
# im.show()

# result_image_file_path = path.join(datapath, "stitched_image.npy")
# np.save(result_image_file_path, stitched_image)