import SimpleITK as sitk
from SimpleITK import GetArrayFromImage, sitkNearestNeighbor, Image
import numpy as np
from torch import nn
from rt_utils import RTStructBuilder

def debug_output(seg: sitk.Image, seg_path: str, uid:str, dicom_path: str):
    mask_from_sitkImage_zyx = np.transpose(sitk.GetArrayFromImage(seg), (2, 1, 0))
    mask_from_sitkImage_xzy = np.transpose(mask_from_sitkImage_zyx, axes=(2, 0, 1))
    mask_from_sitkImage_xyz = np.transpose(mask_from_sitkImage_xzy, (2, 1, 0))
    mask_from_sitkImage_int64 = mask_from_sitkImage_xyz
    mask_from_sitkImage_bool = mask_from_sitkImage_int64.astype(bool)
    # Create new RT Struct. Requires the DICOM series path for the RT Struct.
    rtstruct = RTStructBuilder.create_new(dicom_series_path = dicom_path)
    # Add the 3D mask as an ROI setting the color, description, and name
    rtstruct.add_roi(
    mask=mask_from_sitkImage_bool, 
    color=[255, 0, 255], 
    name="your ROI!"
    )
 
    rtstruct.save(os.path.join(OUTPUT_DIR, uid+'_tmtv-rt-struct'))
