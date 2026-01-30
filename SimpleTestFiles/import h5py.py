import h5py
import numpy as np
import matplotlib.pyplot as plt


with h5py.File(r"C:\Users\SIM\Desktop\David\Holoeye SLM\WavefrontCompensation\U.14-2144-204707-24-07-06_7020-1 6010-1441.h5") as f:
    # f.visit(print)
    wf = f["measurementtgi/data/wavefront"][:]
    stdev = f["measurementtgi/data/stddeviation"][:]

plt.imshow(wf.astype(np.uint8), cmap="Greys")
plt.colorbar(label="Wavefront")
plt.axis("off")
plt.show()
plt.close()


plt.imshow(stdev.astype(np.uint8), cmap="Greys")
plt.colorbar(label="Wavefront")
plt.axis("off")
plt.show()
plt.close()
