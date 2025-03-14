from io import BytesIO
from typing import List, Union
import numpy as np
import pydicom
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
        ].FrameOfReferenceUID  # Use last structured set ROI

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
        Add a Region of Interest (ROI) to the RTStruct given a 3D binary mask for each slice.

        Optionally input a color or name for the ROI. 
        If `use_pin_hole` is set to True, attempts to handle ROIs with holes by creating a single continuous contour.
        If `approximate_contours` is set to False, no approximation is done during contour generation, 
        potentially resulting in a large amount of contour data.

        This method updates the internal DICOM structure (RTStruct) by adding:
        - ROIContourSequence
        - StructureSetROISequence
        - RTROIObservationsSequence

        Parameters
        ----------
        mask : np.ndarray
            3D boolean array indicating the ROI. Its shape must match
            the underlying DICOM series in the third dimension.
        color : str or list of int, optional
            Color representation for the ROI (e.g., "red" or [255, 0, 0]). Defaults to None.
        name : str, optional
            Name/label for the ROI. Defaults to None.
        description : str, optional
            Longer description of the ROI. Defaults to an empty string.
        use_pin_hole : bool, optional
            If True, attempts to create a single continuous contour for ROIs with holes. Defaults to False.
        approximate_contours : bool, optional
            If False, skips approximation during contour generation, leading to larger contour data. Defaults to True.
        roi_generation_algorithm : str or int, optional
            Identifier for the algorithm used to generate the ROI. Defaults to 0.

        Raises
        ------
        ROIException
            - If the mask is not a 3D boolean array.
            - If the mask's shape does not match the loaded DICOM series dimensions.
            - If the mask is empty (no voxels set to True).

        Returns
        -------
        None
            Modifies the internal RTStruct.
        """
        # TODO: test if name already exists
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
                f"Mask data type must be boolean, but got {mask.dtype}. Please ensure the mask is a 3D boolean array."
            )

        if mask.ndim != 3:
            raise RTStruct.ROIException(f"Mask must be 3 dimensional. Got {mask.ndim}")

        if len(self.series_data) != np.shape(mask)[2]:
            raise RTStruct.ROIException(
                "Mask must have the same number of layers (in the 3rd dimension) as the input series. "
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
        Saves the RTStruct with the specified name / location.
        Automatically adds '.dcm' as a suffix if necessary.
        """
        # Add .dcm if needed
        file_path = file_path if file_path.endswith(".dcm") else file_path + ".dcm"

        try:
            # Using 'with' to handle file opening and closing automatically
            with open(file_path, "w") as file:
                print("Writing file to", file_path)
                self.ds.save_as(file_path)
        except OSError:
            raise Exception(f"Cannot write to file path '{file_path}'")
        
    def save_to_memory(self):
        """
        Saves the RTStruct to a BytesIO stream and returns it.
        """
        buffer = BytesIO()
        pydicom.dcmwrite(buffer, self.ds)
        buffer.seek(0)  # Rewind the buffer for reading
        return buffer

    class ROIException(Exception):
        """
        Exception class for invalid ROI masks
        """
        pass
