"""
Tetsing the functionalities of scripting.
"""

# Make functions into a simple functions
# ai = api.imcontrol

# positions_start = ai.getPositionerPositions()

# print(positions_start)

# ai.movePositionerXY('XY', 30.0 , 10.0)

# ai.movePositioner('XY', 'X', -20.0)
# ai.movePositioner('XY', 'Y', -5.0)


# positions_finish = ai.getPositionerPositions()

# print(positions_finish)

# def plot_img_with_rectangles(img_data, coords, save_dir, save_name):
#     """ Dummy image analysis routine to identify regions of interest (ROIs) for further measurements.

#     Args:
#         stack (numpy array): image dataset as provided by im.meas.config.stack
#         coords (list of int): list of coordinates in pixels, each as [x,y,width,height]

#     Returns:
#     """
#     my_dpi = 100.
#     img = Image.fromarray(img_data)
#     fig = plt.figure(figsize=(float(img.size[0]) / my_dpi, float(img.size[1]) / my_dpi), dpi=my_dpi)
#     ax = fig.add_subplot(111)
#     fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
#     ax.imshow(img)

#     for i, [x, y, w, h] in enumerate(coords):
#         rect = patches.Rectangle((x, y), w, h, linewidth=.5, edgecolor='r', facecolor='none')
#         ax.add_patch(rect)
#         ax.text(x, y-3, f'{i}', color='r', ha='center', va='center', fontsize=7)

#     # plt.show()
#     fig.savefig(f'{save_dir}\\{save_name}_objects.png', dpi=800)
#     plt.close(fig)

#     return None


# def plot_scanning_direction(img_data, coords, save_dir, save_name):
    
#     for i in range(0,len(coords)-1,2):
#         x = np.array([coords[i,0], coords[i+1,0]])
#         y = np.array([coords[i,1], coords[i+1,1]])
#         plt.plot(x, y, 'ro-')
#     plt.show()
#     plt.savefig(f'{save_dir}\\{save_name}_objects.png', dpi=800)
#     plt.close()
#     print("Done.")

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt

x, y = np.random.random(size=(2,10))
print(x)

for i in range(0, len(x), 2):
    print(x[i:i+2])
    plt.plot(x[i:i+2], y[i:i+2], 'ro-')
    

plt.show()