import numpy as np
from pydicom.filereader import dcmread
import matplotlib.pyplot as plt
from matplotlib import pyplot, cm
import numpy as np
import cv2 as cv2

ds = dcmread('./sample/rt.dcm')
contour_sequence_list = ds.ROIContourSequence
contour_sequence_data = contour_sequence_list[0]
contour_sequence = contour_sequence_data.ContourSequence
contour = contour_sequence[0]
contour_data = contour.ContourData
# print(contour_data)
num_points = len(contour_data) // 3 # Points defined as a sequence of (x, y, z) triplets
assert len(contour_data) % 3 == 0  # Invalid sequence of points

print(contour_data)
reshaped_contour_data = np.reshape(contour_data, [num_points, 3]).astype(int)
print(contour.ContourImageSequence[0].ReferencedSOPInstanceUID)
ds = dcmread(f'./sample/{contour.ContourImageSequence[0].ReferencedSOPInstanceUID}.dcm')
num_points = len(ds.PixelData) // 3 # Points defined as a sequence of (x, y, z) triplets
img = np.array(ds.pixel_array)
# reshaped_image = np.reshape(ds.PixelData, [num_points, 2])
# print(len(reshaped_image))
arr = np.zeros(img.shape).astype(bool)
cols = reshaped_contour_data[:,0]
rows = reshaped_contour_data[:,1]
arr[cols, rows] = True

plt.imshow(arr)
plt.imshow(img, cmap='gray')
plt.show()
arr = np.zeros(img.shape)
poly = reshaped_contour_data[:,:2]
print(reshaped_contour_data)
# cv2.fillPoly(img=arr, pts=[poly], color=1)
# mask = img.astype(bool)
# Get discrete points
# cols = pixelCoords[:,0]
# rows = pixelCoords[:,1]
# arr[cols, rows] = True # Note the order of indices (cols before rows)