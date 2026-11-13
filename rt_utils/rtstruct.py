import logging
from io import BytesIO
from typing import Dict, List, Union

import numpy as np
from pydicom.dataset import FileDataset
from rt_utils.utils import ROIData
from . import ds_helper, image_helper, smoothing

logger = logging.getLogger(__name__)


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

    def _next_roi_number(self) -> int:
        """Return an ROINumber not already used in this structure set.

        Counting the sequence is not enough. An ROI deleted in another
        application leaves a gap, so len(StructureSetROISequence) + 1 can
        collide with an ROINumber that is still in use. ROINumber is the key
        that ties StructureSetROISequence to ROIContourSequence, so a
        duplicate silently associates two ROIs with the same contours.

        DICOM numbers ROIs from 1, so an empty structure set yields 1.
        """
        used = []
        for structure_roi in self.ds.StructureSetROISequence:
            try:
                used.append(int(structure_roi.ROINumber))
            except (AttributeError, TypeError, ValueError):
                continue

        return max(used, default=0) + 1

    def add_roi(
        self,
        mask: np.ndarray,
        color: Union[str, List[int]] = None,
        name: str = None,
        description: str = "",
        use_pin_hole: bool = False,
        approximate_contours: bool = True,
        roi_generation_algorithm: Union[str, int] = 0,
        roi_interpreted_type: str = "",
        contour_mode: str = "voxel_edge",
        apply_smoothing: Union[str, None] = None,
        smoothing_function=smoothing.pipeline,
        smoothing_parameters: Union[Dict, None] = None,
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
            3D boolean array indicating the ROI, shaped
            ``(Rows, Columns, Slices)``. The in-plane axes are ordered the way
            pydicom reads ``pixel_array``: axis 0 is the row index and axis 1
            the column index, so a mask segmented from the series already has
            the right layout. Slices run along axis 2 in the series' own
            ascending spatial order, matching ``series_data``.

            A mask from another source may need rearranging first. A NIfTI
            volume in particular carries its own axis order and direction in
            its affine, and neither is guaranteed to match the series; passing
            one straight through is what makes an ROI come back rotated or
            flipped.
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
            Only applies to ``contour_mode="voxel_center"``; edge tracing
            already emits one vertex per corner.
        roi_generation_algorithm : str or int, optional
            Identifier for the algorithm used to generate the ROI. Defaults to 0.
        roi_interpreted_type : str, optional
            RTROIInterpretedType: what kind of structure this is, such as
            ``"PTV"``, ``"ORGAN"``, ``"EXTERNAL"`` or ``"BRACHY_CHANNEL"``.
            Planning systems use it to decide how a structure is treated:
            which ones are targets, which are organs at risk, which define
            the patient outline. Defaults to ``""``, meaning unstated, which
            is what earlier versions always wrote.

            PS3.3 C.8.8.8 gives these as Defined Terms, so the list is
            extensible and the value is not validated against it;
            ``rt_utils.utils.ROI_INTERPRETED_TYPES`` holds the standard ones
            for reference.
        contour_mode : {"voxel_edge", "voxel_center"}, optional
            Placement of generated contours. Defaults to ``"voxel_edge"``,
            which traces the outer edges of foreground voxels so the contour
            encloses the area the mask actually occupies.

            ``"voxel_center"`` traces through voxel centres instead, which
            understates the structure by half a voxel on every side. The
            effect is negligible for large structures and severe for small
            ones: a 3x3 voxel region exports at roughly 44% of its true area.
            It remains available for reproducing output from earlier
            releases, where it was the default.

            Both modes round trip exactly through this library.

        Raises
        ------
        ROIException
            - If the mask is not a 3D boolean array.
            - If the mask's shape does not match the loaded DICOM series
              dimensions, in plane or in the number of slices.
            - If the mask is empty (no voxels set to True).

        Returns
        -------
        None
            Modifies the internal RTStruct.
        """
        # TODO: test if name already exists
        self.validate_mask(mask)

        scaling_factor = 1
        if apply_smoothing:
            rows = int(self.series_data[0].Rows)
            mask = smoothing_function(
                mask=mask,
                apply_smoothing=apply_smoothing,
                smoothing_parameters=smoothing_parameters,
            )
            # Smoothing upscales the mask in x and y. Contours are traced at
            # that resolution and divided back down, giving a sub-voxel
            # boundary rather than the original stair steps.
            scaling_factor = int(mask.shape[0] / rows)
            if scaling_factor < 1:
                raise RTStruct.ROIException(
                    "Smoothing must not return a mask smaller than the image; "
                    f"got {mask.shape[0]} rows for an image with {rows}"
                )

        roi_number = self._next_roi_number()
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
            contour_mode=contour_mode,
            scaling_factor=scaling_factor,
            roi_interpreted_type=roi_interpreted_type,
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

    def add_roi_from_coordinates(
        self,
        coordinates: List[List[List[float]]],
        color: Union[str, List[int]] = None,
        name: str = None,
        description: str = "",
        roi_generation_algorithm: Union[str, int] = 0,
        coordinate_space: str = "patient",
    ):
        """
        Add an ROI from contours given directly, rather than from a mask.

        ``coordinate_space`` selects how the points are interpreted:

        ``"patient"`` (the default) takes ``[x, y, z]`` in millimetres::

            rtstruct.add_roi_from_coordinates(
                coordinates=[
                    [[-20.0, -170.0, -559.0], [30.0, -170.0, -559.0],
                     [30.0, -110.0, -559.0], [-20.0, -110.0, -559.0]],
                ],
                name="from-coordinates",
            )

        ``"pixel"`` takes ``[column, row, slice_index]`` on the image grid,
        which is the form an annotation tool working on the images
        produces::

            rtstruct.add_roi_from_coordinates(
                coordinates=[[[60, 50, 0], [120, 50, 0], [120, 100, 0]]],
                name="from-pixels",
                coordinate_space="pixel",
            )

        Pixel coordinates are converted to patient space with the series'
        own transformation, so the polygon is written exactly as given rather
        than being rasterised to a mask and traced back.

        Each contour is attached to the slice nearest its own position, so the
        caller does not need to know the slice ordering. Unlike add_roi this
        takes no mask, so the contours are written as given rather than being
        derived from a rasterised volume.
        """
        if coordinate_space == "pixel":
            coordinates = image_helper.pixel_polygons_to_patient_coordinates(
                coordinates, self.series_data
            )
        elif coordinate_space != "patient":
            raise ValueError(
                f"Invalid coordinate space '{coordinate_space}'. "
                "Expected one of ['patient', 'pixel']."
            )

        roi_number = self._next_roi_number()
        roi_data = ROIData(
            # add_roi_from_coordinates writes the given contours directly, so
            # no mask is rasterised. ROIData still requires the field.
            np.zeros(1),
            color,
            roi_number,
            name,
            self.frame_of_reference_uid,
            description,
            False,
            True,
            roi_generation_algorithm,
        )

        self.ds.ROIContourSequence.append(
            ds_helper.create_roi_contour_from_coordinates(
                coordinates, roi_data, self.series_data
            )
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

        reference_slice = self.series_data[0]
        expected_in_plane = (int(reference_slice.Rows), int(reference_slice.Columns))
        if np.shape(mask)[:2] != expected_in_plane:
            raise RTStruct.ROIException(
                "Mask must have the same in-plane dimensions as the input series. "
                f"Expected {expected_in_plane}, got {np.shape(mask)[:2]}. "
                "Masks are indexed as (Rows, Columns, Slices), the same layout a "
                "DICOM pixel_array is read in, so a mask segmented from the "
                "series already has the right shape. A mask that came from "
                "elsewhere, such as a NIfTI volume, may need transposing first."
            )

        if np.sum(mask) == 0:
            logger.info("ROI mask is empty")

        return True

    CONTOUR_GEOMETRIC_TYPES = (
        "CLOSED_PLANAR",
        "OPEN_PLANAR",
        "OPEN_NONPLANAR",
        "POINT",
    )

    def get_roi_names(self, geometry: str = "ALL") -> List[str]:
        """
        Returns a list of the names of all ROI within the RTStruct.

        ``geometry`` restricts the result to ROIs containing contours of one
        ContourGeometricType: ``"CLOSED_PLANAR"``, ``"OPEN_PLANAR"``,
        ``"OPEN_NONPLANAR"`` or ``"POINT"``. The default, ``"ALL"``, applies
        no filter.

        An ROI matches when **any** of its contours has that type. A single
        ROI can mix types across slices, so classifying it by its first
        contour alone would hide it from a filter it genuinely matches.
        """
        if not self.ds.StructureSetROISequence:
            return []

        if geometry == "ALL":
            return [
                structure_roi.ROIName
                for structure_roi in self.ds.StructureSetROISequence
            ]

        if geometry not in self.CONTOUR_GEOMETRIC_TYPES:
            raise ValueError(
                f"Unrecognised geometric type '{geometry}'. Expected 'ALL' or "
                f"one of {list(self.CONTOUR_GEOMETRIC_TYPES)}."
            )

        matching_roi_numbers = self._roi_numbers_with_geometry(geometry)

        return [
            structure_roi.ROIName
            for structure_roi in self.ds.StructureSetROISequence
            if str(structure_roi.ROINumber) in matching_roi_numbers
        ]

    def _roi_numbers_with_geometry(self, geometry: str) -> set:
        """ROINumbers of ROIs with at least one contour of the given type.

        ROIContourSequence is matched to StructureSetROISequence through
        ReferencedROINumber. The two sequences are not required to be in the
        same order, so pairing them by position would attribute geometry to
        the wrong ROI.
        """
        matching = set()

        for roi_contour in getattr(self.ds, "ROIContourSequence", []):
            contour_sequence = getattr(roi_contour, "ContourSequence", None)
            if not contour_sequence:
                continue

            if any(
                getattr(contour, "ContourGeometricType", None) == geometry
                for contour in contour_sequence
            ):
                matching.add(str(roi_contour.ReferencedROINumber))

        return matching

    def get_roi_mask_by_name(
        self,
        name,
        case_sensitive: bool = True,
        match_by: str = image_helper.MATCH_BY_SOP_INSTANCE_UID,
    ) -> np.ndarray:
        """
        Returns the 3D binary mask of the ROI with the given input name.

        The name must match exactly by default. Pass case_sensitive=False to
        match while ignoring case, which helps when ROI naming conventions
        differ between treatment planning systems.

        Matching exactly is the default because a structure set may contain
        several ROIs whose names differ only in case, and those are distinct
        structures. With case_sensitive=False the first one in
        StructureSetROISequence wins and the others become unreachable.

        ``match_by`` decides how each contour is tied to a slice.

        ``"sop_instance_uid"`` (the default) uses the image the contour names
        in its ContourImageSequence. That is what DICOM intends and it is
        unambiguous.

        ``"position"`` instead assigns each contour to the slice nearest its
        own position along the slice normal. Use it when the identifiers no
        longer line up although the geometry is unchanged, which is what
        anonymisation tools cause by regenerating SOPInstanceUIDs. It is not
        the default because it will happily match contours to a series they
        were never drawn on, as long as the positions are close; by
        identifier, that case raises instead.
        """
        structure_roi = self._find_structure_roi(name, case_sensitive)
        if structure_roi is None:
            raise RTStruct.ROIException(
                f"ROI of name `{name}` does not exist in RTStruct"
            )

        contour_sequence = ds_helper.get_contour_sequence_by_roi_number(
            self.ds, structure_roi.ROINumber
        )
        return image_helper.create_series_mask_from_contour_sequence(
            self.series_data, contour_sequence, match_by=match_by
        )

    def _find_structure_roi(self, name, case_sensitive: bool):
        """The StructureSetROISequence entry with this name, or None."""
        target = name
        if not case_sensitive and isinstance(name, str):
            target = name.casefold()

        for structure_roi in self.ds.StructureSetROISequence:
            roi_name = structure_roi.ROIName
            if not case_sensitive and isinstance(roi_name, str):
                roi_name = roi_name.casefold()

            if roi_name == target:
                return structure_roi

        return None

    def delete_roi(self, name, case_sensitive: bool = True) -> None:
        """Remove the ROI with the given name from the structure set.

        An ROI is spread across three sequences, tied together by ROINumber:
        StructureSetROISequence names it, ROIContourSequence holds its
        geometry, and RTROIObservationsSequence its interpretation. All three
        entries are removed, because leaving any behind produces a structure
        set that viewers and planning systems read inconsistently: contours
        belonging to an ROI that no longer has a name, or a name with nothing
        to draw.

        Numbering is deliberately left alone. ROINumber is the key those
        sequences are joined by, so renumbering the survivors to close the
        gap would silently re-point every reference. A later add_roi takes
        the next number above the highest still in use, so the gap is never
        reused.

        Matching follows get_roi_mask_by_name: exact by default, with
        case_sensitive=False to ignore case.
        """
        structure_roi = self._find_structure_roi(name, case_sensitive)
        if structure_roi is None:
            raise RTStruct.ROIException(
                f"ROI of name `{name}` does not exist in RTStruct"
            )

        roi_number = str(structure_roi.ROINumber)

        self.ds.StructureSetROISequence = [
            roi
            for roi in self.ds.StructureSetROISequence
            if str(roi.ROINumber) != roi_number
        ]
        self.ds.ROIContourSequence = [
            roi
            for roi in getattr(self.ds, "ROIContourSequence", [])
            if str(getattr(roi, "ReferencedROINumber", "")) != roi_number
        ]
        self.ds.RTROIObservationsSequence = [
            roi
            for roi in getattr(self.ds, "RTROIObservationsSequence", [])
            if str(getattr(roi, "ReferencedROINumber", "")) != roi_number
        ]

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
                logger.info("Writing RTStruct to %s", file_path)
                self.ds.save_as(file_path)
        except OSError:
            raise Exception(f"Cannot write to file path '{file_path}'")

    def save_to_memory(self) -> BytesIO:
        """
        Write the RTStruct to an in-memory buffer and return it.

        The buffer is rewound, so it can be handed straight to
        ``pydicom.dcmread`` or to anything expecting a readable file object.
        Useful when the result is uploaded or passed on rather than written to
        disk.
        """
        buffer = BytesIO()
        self.ds.save_as(buffer)
        buffer.seek(0)
        return buffer

    class ROIException(Exception):
        """
        Exception class for invalid ROI masks
        """

        pass
