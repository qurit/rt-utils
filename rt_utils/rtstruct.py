from typing import List, Union

import numpy as np
from pydicom.dataset import FileDataset

from rt_utils.utils import ROIData
from . import ds_helper, image_helper


class RTStruct:
    """
    Wrapper class to facilitate appending and extracting ROI's within an RTStruct
    """

    def __init__(self, series_data, ds: FileDataset, ROIGenerationAlgorithm=0):
        self.series_data = series_data
        self.ds = ds
        self.frame_of_reference_uid = ds.ReferencedFrameOfReferenceSequence[
            -1
        ].FrameOfReferenceUID  # Use last strucitured set ROI

    def set_series_description(self, description: str):
        """
        Set the series description for the RTStruct dataset
        """

        self.ds.SeriesDescription = description

    def add_roi(
        self,
        mask: np.ndarray,
        color: Union[str, List[int]] = None,
        name: str = None,
        description: str = "",
        use_pin_hole: bool = False,
        approximate_contours: bool = True,
        roi_generation_algorithm: Union[str, int] = 0,
    ):
        """
        Add a ROI to the rtstruct given a 3D binary mask for the ROI's at each slice
        Optionally input a color or name for the ROI
        If use_pin_hole is set to true, will cut a pinhole through ROI's with holes in them so that they are represented with one contour
        If approximate_contours is set to False, no approximation will be done when generating contour data, leading to much larger amount of contour data
        This method updates the internal DICOM structure (RTStruct) by adding
        a new ROIContourSequence, StructureSetROISequence, and
        RTROIObservationsSequence entry corresponding to the provided mask.
    
        Parameters
        ----------
        mask : np.ndarray
            3D boolean array indicating the ROI. Its shape must match
            the underlying DICOM series in the third dimension.
        color : str or list of int, optional
            The color representation for the ROI. This can be a string (e.g., "red")
            or a list of RGB values (e.g., [255, 0, 0]). Defaults to None.
        name : str, optional
            A name/label for this ROI. Defaults to None.
        description : str, optional
            Longer text describing this ROI. Defaults to an empty string.
        use_pin_hole : bool, optional
            If True, attempts to handle ROIs with holes by creating a pinhole
            (a single continuous contour). Defaults to False.
        approximate_contours : bool, optional
            If False, no approximation is done during contour generation,
            potentially resulting in very large amounts of contour data.
            Defaults to True.
        roi_generation_algorithm : str or int, optional
            Identifier for the algorithm used to generate this ROI. This can be
            a string describing the algorithm or an integer code. Defaults to 0.
    
        Raises
        ------
        ROIException
            - If the mask is not a 3D boolean array.
            - If the mask's shape does not match the loaded DICOM series dimensions.
            - If the mask is empty (no voxels set to True).
    
        Returns
        -------
        None
            This method does not return anything, but modifies the internal RTStruct.
        """
        """

        # TODO test if name already exists
        self.validate_mask(mask)
        roi_number = len(self.ds.StructureSetROISequence) + 1
        roi_data = ROIData(
            mask,
            color,
            roi_number,
            name,
            self.frame_of_reference_uid,
            description,
            use_pin_hole,
            approximate_contours,
            roi_generation_algorithm,
        )

        self.ds.ROIContourSequence.append(
            ds_helper.create_roi_contour(roi_data, self.series_data)
        )
        self.ds.StructureSetROISequence.append(
            ds_helper.create_structure_set_roi(roi_data)
        )
        self.ds.RTROIObservationsSequence.append(
            ds_helper.create_rtroi_observation(roi_data)
        )

    def validate_mask(self, mask: np.ndarray) -> bool:
        if mask.dtype != bool:
            raise RTStruct.ROIException(
                f"Mask data type must be boolean. Got {mask.dtype}"
            )

        if mask.ndim != 3:
            raise RTStruct.ROIException(f"Mask must be 3 dimensional. Got {mask.ndim}")

        if len(self.series_data) != np.shape(mask)[2]:
            raise RTStruct.ROIException(
                "Mask must have the save number of layers (In the 3rd dimension) as input series. "
                + f"Expected {len(self.series_data)}, got {np.shape(mask)[2]}"
            )

        if np.sum(mask) == 0:
            print("[INFO]: ROI mask is empty")

        return True

    def get_roi_names(self) -> List[str]:
        """
        Returns a list of the names of all ROI within the RTStruct
        """

        if not self.ds.StructureSetROISequence:
            return []

        return [
            structure_roi.ROIName for structure_roi in self.ds.StructureSetROISequence
        ]

    def get_roi_mask_by_name(self, name) -> np.ndarray:
        """
        Returns the 3D binary mask of the ROI with the given input name
        """

        for structure_roi in self.ds.StructureSetROISequence:
            if structure_roi.ROIName == name:
                contour_sequence = ds_helper.get_contour_sequence_by_roi_number(
                    self.ds, structure_roi.ROINumber
                )
                return image_helper.create_series_mask_from_contour_sequence(
                    self.series_data, contour_sequence
                )

        raise RTStruct.ROIException(f"ROI of name `{name}` does not exist in RTStruct")

    def save(self, file_path: str):
        """
        Saves the RTStruct with the specified name / location
        Automatically adds '.dcm' as a suffix
        """

        # Add .dcm if needed
        file_path = file_path if file_path.endswith(".dcm") else file_path + ".dcm"

        try:
            file = open(file_path, "w")
            # Opening worked, we should have a valid file_path
            print("Writing file to", file_path)
            self.ds.save_as(file_path)
            file.close()
        except OSError:
            raise Exception(f"Cannot write to file path '{file_path}'")

    class ROIException(Exception):
        """
        Exception class for invalid ROI masks
        """

        pass
