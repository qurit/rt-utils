<p align="center">
  <img src="https://raw.githubusercontent.com/qurit/rt-utils/main/src/rt-utils-logo.png" height="300"/>
</p>
<p align="center">
  <em>A minimal Python library for RT Struct manipulation</em>
</p>
<p align="center">
    <img src="https://github.com/qurit/rt-utils/workflows/Python%20application/badge.svg" height="18">
    <img src="https://img.shields.io/pypi/pyversions/rt-utils" alt="Python version" height="18">
    <a href="https://pypi.org/project/rt-utils"><img src="https://badge.fury.io/py/rt-utils.svg" alt="PyPI version" height="18"></a>  
    <img alt="PyPI - License" src="https://img.shields.io/github/license/qurit/rt-utils?color=g" height="18" />
</p>
 
---
 
RT-Utils is motivated to allow physicians and other users to view the results of segmentation performed on a series of DICOM images. RT-Utils allows you to create or load RT Structs, extract 3d masks from RT Struct ROIs, easily add one or more regions of interest, and save the resulting RT Struct in just a few lines!

## How it works
RT-Utils provides a builder class to faciliate the creation and loading of an RT Struct. From there, you can add ROIs through binary masks and optionally input the colour of the region along with the region name.

The format for the ROI mask is an nd numpy array of type bool. It is an array of 2d binary masks, one plane for each slice location within the DICOM series. The slices should be sorted in ascending order within the mask. Through these masks, we extract the contours of the regions of interest and place them within the RT Struct file. Note that there is currently only support for the use of one frame of reference UID and structered set ROI sequence. Also note that holes within the ROI may be handled poorly.

## Installation
```
pip install rt_utils
```

## Creating new RT Structs
```Python
from rt_utils import RTStructBuilder

# Create new RT Struct. Requires the DICOM series path for the RT Struct.
rtstruct = RTStructBuilder.create_new(dicom_series_path="./testlocation")

# ...
# Create mask through means such as ML
# ...

# Add the 3D mask as an ROI.
# The colour, description, and name will be auto generated
rtstruct.add_roi(mask=MASK_FROM_ML_MODEL)

# Add another ROI, this time setting the color, description, and name
rtstruct.add_roi(
  mask=MASK_FROM_ML_MODEL, 
  color=[255, 0, 255], 
  name="RT-Utils ROI!"
)

rtstruct.save('new-rt-struct')
```

## Adding to existing RT Structs
```Python
from rt_utils import RTStructBuilder
import matplotlib.pyplot as plt

# Load existing RT Struct. Requires the series path and existing RT Struct path
rtstruct = RTStructBuilder.create_from(
  dicom_series_path="./testlocation", 
  rt_struct_path="./testlocation/rt-struct.dcm"
)

# Add ROI. This is the same as the above example.
rtstruct.add_roi(
  mask=MASK_FROM_ML_MODEL, 
  color=[255, 0, 255], 
  name="RT-Utils ROI!"
)

rtstruct.save('new-rt-struct')
```

## Creation Results
<p align="center">
  <img src="https://raw.githubusercontent.com/qurit/rt-utils/main/src/contour.png" width="1000"/>
</p>
<p align="center">
  The results of a generated ROI with a dummy mask, as viewed in Slicer.
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/qurit/RT-Utils/main/src/liver-contour.png" width="1000"/>
</p>
<p align="center">
  The results of a generated ROI with a liver segmentation model, as viewed in Slicer. (Note the underlying patient data has been hidden)
</p>

## Loading an existing RT Struct contour as a mask
```Python
from rt_utils import RTStructBuilder
import matplotlib.pyplot as plt

# Load existing RT Struct. Requires the series path and existing RT Struct path
rtstruct = RTStructBuilder.create_from(
  dicom_series_path="./testlocation", 
  rt_struct_path="./testlocation/rt-struct.dcm"
)

# View all of the ROI names from within the image
print(rtstruct.get_roi_names())

# Loading the 3D Mask from within the RT Struct
mask_3d = rtstruct.get_roi_mask_by_name("ROI NAME")

# Display one slice of the region
first_mask_slice = mask_3d[:, :, 0]
plt.imshow(first_mask_slice)
plt.show()
```

## Loading Results
<p align="center">
  <img src="https://raw.githubusercontent.com/qurit/rt-utils/main/src/loaded-mask.png" height="300"/>
</p>
<p align="center">
  The results of a loading an exisiting ROI as a mask, as viewed in Python.
</p>

## Additional Parameters
The add_roi method of our RTStruct class has a multitude of optional parameters available. Below is a comprehensive list of all these parameters and what they do.
- <b>color</b>: This parameter can either be a colour string such as '#ffffff' or a RGB value as a list such as '[255, 255, 255]'. This parameter will dictate the colour of your ROI when viewed in a viewing program. If no colour is provided, RT Utils will pick from our internal colour palette based on the ROI Number of the ROI.
- <b>name</b>: A str value that defaults to none. Used to set the name of the ROI within the RT Struct. If the name is none, RT Utils will set a name of ROI-{ROI Number}.
- <b>description</b>: A str value that sets the description of the ROI within the RT Struct. If no value is provided, the description is just left blank.
- <b>use_pin_hole</b>: A boolean value that defaults to false. If set to true, lines will be erased through your mask such that each separate region within your image can be encapsulated via a single contour instead of contours nested within one another. Use this if your RT Struct viewer of choice does not support nested contours / contours with holes.
- <b>approximate_contours</b>: A boolean value that defaults to True which defines whether or not approximations are made when extracting contours from the input mask. Setting this to false will lead to much larger contour data within your RT Struct so only use this if as much precision as possible is required.