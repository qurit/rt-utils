from .rtstruct import RTStruct
from .rtstruct_builder import RTStructBuilder
from . import ds_helper, image_helper


class RTStructMerger:

    @staticmethod
    def merge_rtstructs(
        dicom_series_path: str, rt_struct_path1: str, rt_struct_path2: str
    ) -> RTStruct:
        """
        Method to merge two existing RTStruct files belonging to same series data, returning them as one RTStruct
        """

        rtstruct1 = RTStructBuilder.create_from(dicom_series_path, rt_struct_path1)
        rtstruct2 = RTStructBuilder.create_from(dicom_series_path, rt_struct_path2)

        for roi_contour_seq, struct_set_roi_seq, rt_roi_observation_seq in zip(
            rtstruct1.ds.ROIContourSequence,
            rtstruct1.ds.StructureSetROISequence,
            rtstruct1.ds.RTROIObservationsSequence,
        ):
            # Renumber onto the end of the destination. Taking the highest
            # number in use rather than counting the sequence matters when
            # the destination has gaps, from an ROI deleted elsewhere: a
            # count would hand out a number another ROI still holds, and
            # ROINumber is what joins the three sequences together.
            roi_number = RTStructMerger._next_roi_number(rtstruct2)
            roi_contour_seq.ReferencedROINumber = roi_number
            struct_set_roi_seq.ROINumber = roi_number
            rt_roi_observation_seq.ReferencedROINumber = roi_number

            struct_set_roi_seq.ROIName = RTStructMerger._unique_roi_name(
                struct_set_roi_seq.ROIName, rtstruct2
            )

            rtstruct2.ds.ROIContourSequence.append(roi_contour_seq)
            rtstruct2.ds.StructureSetROISequence.append(struct_set_roi_seq)
            rtstruct2.ds.RTROIObservationsSequence.append(rt_roi_observation_seq)

        return rtstruct2

    @staticmethod
    def _next_roi_number(rtstruct: RTStruct) -> int:
        """An ROINumber not already used in this structure set."""
        used = []
        for structure_roi in rtstruct.ds.StructureSetROISequence:
            try:
                used.append(int(structure_roi.ROINumber))
            except (AttributeError, TypeError, ValueError):
                continue

        return max(used, default=0) + 1

    @staticmethod
    def _unique_roi_name(name: str, rtstruct: RTStruct) -> str:
        """A name not already taken in this structure set.

        Two structure sets for one series routinely name the same organ the
        same way, so a merge has to rename one of them. ROIName is how a
        human tells structures apart, and two called "Liver" are
        indistinguishable once merged.

        Suffixes count upward until one is free, so merging a third set does
        not produce a second "Liver_2".
        """
        taken = {
            structure_roi.ROIName
            for structure_roi in rtstruct.ds.StructureSetROISequence
        }
        if name not in taken:
            return name

        suffix = 2
        while f"{name}_{suffix}" in taken:
            suffix += 1

        return f"{name}_{suffix}"
