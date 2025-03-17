# import sample data
from skimage.data import cells3d

import napari



viewer = napari.Viewer()

# # create a `Viewer` and `Image` layer here
# print(type(cells3d()[:,0,:,:]))
# #viewer, image_layer = napari.imshow(cells3d()[:,0,:,:])
# viewer, image_layer = napari.imshow()
# # print shape of image data
# print(image_layer.data.shape)

# # start the event loop and show the viewer
napari.run()