import numpy as np
from pydicom import dcmread
from rtutils import RTStruct

rtstruct = RTStruct('D:\Projects\Mask-to-RTStruct\sample')
ConstPixelDims = (int(rtstruct.series_data[0].Columns), int(rtstruct.series_data[0].Rows), len(rtstruct.series_data))

# Create image with ROI in once slice
img = np.zeros(ConstPixelDims)
img[10:20,10:20,1] = img[10:20,10:20,1] + 1
mask = img.astype(bool)
rtstruct.add_roi(mask)

# Save and load
rtstruct.save()
ds = dcmread('./test.dcm')
print(ds)
print(rtstruct.get_roi_names())