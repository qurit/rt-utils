from .rtstruct import RTStruct
from .rtstruct_builder import RTStructBuilder
from . import ds_helper, image_helper

class RTStructMerger:


    @staticmethod
    def merge_rtstructs(dicom_series_path: str, rt_struct_path1: str, 
        rt_struct_path2: str) -> RTStruct:
        """
        Method to merge two existing RTStruct files belonging to same series data, returning them as one RTStruct
        """

        rtstruct1 = RTStructBuilder.create_from(dicom_series_path, rt_struct_path1)
        rtstruct2 = RTStructBuilder.create_from(dicom_series_path, rt_struct_path2)
        
        for roi_contour_seq, struct_set_roi_seq, rt_roi_observation_seq in zip(rtstruct1.ds.ROIContourSequence, rtstruct1.ds.StructureSetROISequence, rtstruct1.ds.RTROIObservationsSequence):
            roi_number = len(rtstruct2.ds.StructureSetROISequence) + 1
            roi_contour_seq.ReferencedROINumber = roi_number
            struct_set_roi_seq.ROINumber = roi_number
            rt_roi_observation_seq.ReferencedROINumber = roi_number

            # check for ROI name duplication
            for struct_set_roi_seq2 in rtstruct2.ds.StructureSetROISequence:
                if struct_set_roi_seq.ROIName == struct_set_roi_seq2.ROIName:
                    struct_set_roi_seq += "_2"

            rtstruct2.ds.ROIContourSequence.append(roi_contour_seq)
            rtstruct2.ds.StructureSetROISequence.append(struct_set_roi_seq)
            rtstruct2.ds.RTROIObservationsSequence.append(rt_roi_observation_seq)

        return rtstruct2