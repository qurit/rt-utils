import numpy as np
from pydicom import dcmread
from rtutils import RTStruct

rtstruct = RTStruct('D:\Projects\Mask-to-RTStruct\sample')
ConstPixelDims = (int(rtstruct.series_data[0].Columns), int(rtstruct.series_data[0].Rows), len(rtstruct.series_data))

# Create image with ROI in two slices
img = np.zeros(ConstPixelDims)
img[150:180,160:170,0] = img[150:180,160:170,0] + 1
img[150:180,150:180,1] = img[150:180,150:180,1] + 1
img[150:180,150:180,2] = img[150:180,150:180,2] + 1
img[150:180,160:170,4] = img[150:180,160:170,3] + 1

mask = img.astype(bool)
rtstruct.add_roi(mask, color=[255, 255, 255], name="Test ROI")
# rtstruct.add_roi(mask)
# rtstruct.add_roi(mask)
# rtstruct.add_roi(mask)

# Save and load
rtstruct.save()
ds = dcmread('./test.dcm')
print(ds)
print(rtstruct.get_roi_names())