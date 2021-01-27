<p align="center">
  <img src="https://raw.githubusercontent.com/qurit/rt-utils/main/src/rt-utils-logo.png" height="300"/>
</p>
<p align="center">
  <em>A minimal Python library for RTStruct manipulation</em>
</p>
<p align="center">
    <img src="https://github.com/qurit/rt-utils/workflows/Python%20application/badge.svg" height="18">
    <img src="https://img.shields.io/pypi/pyversions/rt-utils" alt="Python version" height="18">
    <a href="https://badge.fury.io/py/rt-utils"><img src="https://badge.fury.io/py/rt-utils.svg" alt="PyPI version" height="18"></a>  
    <img alt="PyPI - License" src="https://img.shields.io/pypi/l/rt-utils" height="18" />
</p>
 
---
 
RT-Utils is motivated to allow physicians and other users to view the results of segmentation performed on a series of DICOM images. RT-Utils allows you to create new RTStructs, easily add one or more regions of interest, and save the resulting RTStruct in just a few lines! Through RT-Utils, you will also be able to load 3D masks from existing RTStruct files.

## How it works
RT-Utils provides a builder class to faciliate the creation and loading of an RTStruct. From there, you can add ROIs through binary masks and optionally input the colour of the region along with the region name.

The format for the ROI mask is an nd numpy array of type bool. It is an array of 2d binary masks, one plane for each slice location within the DICOM series. The slices should be sorted in ascending order within the mask. Through these masks, we extract the contours of the regions of interest and place them within the RTStruct file. Note that there is currently only support for the use of one frame of reference UID and structered set ROI sequence. Also note that holes within the ROI may be handled poorly.

## Installation
```
pip install rt_utils
```

## Creating new RTStructs
```Python
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_new(dicom_series_path="./testlocation")
rtstruct.add_roi(
  mask=MASK_FROM_ML_MODEL, 
  color=[255, 0, 255], 
  name="RT-Utils ROI!"
)
rtstruct.save("test-rt-struct.dcm")
```

## Loading existing RTStructs
```Python
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_from(
  dicom_series_path="./testlocation", 
  rt_struct_path="./testlocation/rt-struct.dcm"
)
rtstruct.add_roi(
  mask=MASK_FROM_ML_MODEL, 
  color=[255, 0, 255], 
  name="RT-Utils ROI!"
)
rtstruct.save("updated-rt-struct.dcm")
```

## Creation Results
<p align="center">
  <img src="https://raw.githubusercontent.com/qurit/rt-utils/main/src/contour.png" width="1000"/>
</p>
<p align="center">
  The results of a generated ROI with a dummy mask, as viewed in Slicer.
</p>

## Loading an existing RTStruct contour as a mask
```Python
import matplotlib.pyplot as plt
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_from(
  dicom_series_path="./testlocation", 
  rt_struct_path="./testlocation/rt-struct.dcm"
)

mask_3d = rtstruct.get_roi_mask_by_name("ROI NAME")
first_mask_slice = mask_3d[:, :, 0]
plt.imshow(first_mask_slice) # View one slice within the mask
plt.show()
rtstruct.save("updated-rt-struct.dcm")
```

## Loading Results
<p align="center">
  <img src="https://raw.githubusercontent.com/qurit/rt-utils/main/src/loaded-mask.png" height="300"/>
</p>
<p align="center">
  The results of a loading an exisiting ROI as a mask, as viewed in Python.
</p>
