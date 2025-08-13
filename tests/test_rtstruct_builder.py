from rt_utils.rtstruct import RTStruct
import pytest
import os
from rt_utils import RTStructBuilder
from rt_utils.utils import SOPClassUID
from rt_utils import image_helper
from pydicom.dataset import validate_file_meta
import numpy as np
import pydicom

def test_create_from_empty_series_dir():
    empty_dir_path = os.path.join(os.path.dirname(__file__), "empty")
    assert os.path.exists(empty_dir_path)
    with pytest.raises(Exception):
        RTStructBuilder.create_new(empty_dir_path)


def test_only_images_loaded_into_series_data(new_rtstruct: RTStruct):
    assert len(new_rtstruct.series_data) > 0
    for ds in new_rtstruct.series_data:
        assert hasattr(ds, "pixel_array")


def test_valid_filemeta(new_rtstruct: RTStruct):
    try:
        validate_file_meta(new_rtstruct.ds.file_meta)
    except Exception:
        pytest.fail("Invalid file meta in RTStruct dataset")


def test_add_non_binary_roi(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    mask = mask.astype(float)
    with pytest.raises(RTStruct.ROIException):
        new_rtstruct.add_roi(mask)


def test_add_empty_roi(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    new_rtstruct.add_roi(mask)
    assert len(new_rtstruct.ds.ROIContourSequence) == 1
    assert len(new_rtstruct.ds.ROIContourSequence[0].ContourSequence) == 0  # No slices added
    assert len(new_rtstruct.ds.StructureSetROISequence) == 1
    assert len(new_rtstruct.ds.RTROIObservationsSequence) == 1


def test_add_invalid_sized_roi(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    mask = mask[:, :, 1:]  # One less slice than expected
    with pytest.raises(RTStruct.ROIException):
        new_rtstruct.add_roi(mask)


def test_add_valid_roi(new_rtstruct: RTStruct):
    assert new_rtstruct.get_roi_names() == []
    assert len(new_rtstruct.ds.ROIContourSequence) == 0
    assert len(new_rtstruct.ds.StructureSetROISequence) == 0
    assert len(new_rtstruct.ds.RTROIObservationsSequence) == 0

    NAME = "Test ROI"
    COLOR = [123, 123, 232]
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1

    new_rtstruct.add_roi(mask, color=COLOR, name=NAME)

    assert len(new_rtstruct.ds.ROIContourSequence) == 1
    assert (
        len(new_rtstruct.ds.ROIContourSequence[0].ContourSequence) == 1
    )  # Only 1 slice was added
    assert len(new_rtstruct.ds.StructureSetROISequence) == 1
    assert len(new_rtstruct.ds.RTROIObservationsSequence) == 1
    assert new_rtstruct.ds.ROIContourSequence[0].ROIDisplayColor == COLOR
    assert new_rtstruct.get_roi_names() == [NAME]


def test_get_invalid_roi_mask_by_name(new_rtstruct: RTStruct):
    assert new_rtstruct.get_roi_names() == []
    with pytest.raises(RTStruct.ROIException):
        new_rtstruct.get_roi_mask_by_name("FAKE_NAME")


def test_loading_invalid_rt_struct(series_path):
    invalid_rt_struct_path = os.path.join(series_path, "ct_1.dcm")
    assert os.path.exists(invalid_rt_struct_path)
    with pytest.raises(Exception):
        RTStructBuilder.create_from(series_path, invalid_rt_struct_path)


def test_loading_invalid_reference_rt_struct(series_path):
    # This RTStruct references images not found within the series path
    invalid_reference_rt_struct_path = os.path.join(
        series_path, "invalid_reference_rt.dcm"
    )
    assert os.path.exists(invalid_reference_rt_struct_path)
    with pytest.raises(Exception):
        RTStructBuilder.create_from(series_path, invalid_reference_rt_struct_path)


def test_non_existant_referenced_study_sequence(series_path):
    non_existent_reference_study_rt_struct_path = os.path.join(
        series_path, "non_existent_reference_rt.dcm"
    )
    assert os.path.exists(non_existent_reference_study_rt_struct_path)
    rtstruct = RTStructBuilder.create_from(
        series_path, non_existent_reference_study_rt_struct_path
    )

    # Test that the attribute does not exist but RTStruct instantiation was still successful
    assert not hasattr(
        rtstruct.ds.ReferencedFrameOfReferenceSequence[0], "RTReferencedStudySequence"
    )


def test_loading_valid_rt_struct(series_path):
    valid_rt_struct_path = os.path.join(series_path, "rt.dcm")
    assert os.path.exists(valid_rt_struct_path)
    rtstruct = RTStructBuilder.create_from(series_path, valid_rt_struct_path)

    # Tests existing values predefined in the file are found
    assert hasattr(rtstruct.ds, "ROIContourSequence")
    assert hasattr(rtstruct.ds, "StructureSetROISequence")
    assert hasattr(rtstruct.ds, "RTROIObservationsSequence")
    assert len(rtstruct.ds.ROIContourSequence) == 1
    assert len(rtstruct.ds.StructureSetROISequence) == 1
    assert len(rtstruct.ds.RTROIObservationsSequence) == 1

    # Test adding a new ROI
    mask = get_empty_mask(rtstruct)
    mask[50:100, 50:100, 0] = 1
    rtstruct.add_roi(mask)

    assert len(rtstruct.ds.ROIContourSequence) == 2  # 1 should be added
    assert len(rtstruct.ds.StructureSetROISequence) == 2  # 1 should be added
    assert len(rtstruct.ds.RTROIObservationsSequence) == 2  # 1 should be added
    new_roi = rtstruct.ds.StructureSetROISequence[-1]
    assert new_roi.ROIName == "ROI-2"


def test_loaded_mask_iou(new_rtstruct: RTStruct):
    # Put weird shape in mask
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1
    mask[60:150, 40:120, 0] = 1

    IOU_threshold = 1.0  # Expected accuracy
    run_mask_iou_test(new_rtstruct, mask, IOU_threshold)


def test_mask_with_holes_iou(new_rtstruct: RTStruct):
    # Create square mask with holes
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1
    mask[65:85, 65:85, 0] = 0
    # add another structure with hole inside of hole
    mask[120:230, 120:230, 0] = 1
    mask[135:215, 135:215, 0] = 0
    mask[150:200, 150:200, 0] = 1
    mask[165:185, 165:185, 0] = 0

    IOU_threshold = 1
    run_mask_iou_test(new_rtstruct, mask, IOU_threshold)


def test_pin_hole_iou(new_rtstruct: RTStruct):
    # Create square mask with hole
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1
    mask[65:85, 65:85, 0] = 0

    IOU_threshold = 0.95  # Expect lower accuracy holes lose information
    run_mask_iou_test(new_rtstruct, mask, IOU_threshold, use_pin_hole=True)


def test_no_approximation_iou(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1
    mask[60:150, 40:120, 0] = 1

    IOU_threshold = 1.0  # Expected accuracy
    run_mask_iou_test(new_rtstruct, mask, IOU_threshold, approximate_contours=False)


def test_contour_data_sizes(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1
    mask[60:150, 40:120, 0] = 1

    # Given we've added the same mask with and without contour approximation
    new_rtstruct.add_roi(mask)
    new_rtstruct.add_roi(mask, approximate_contours=False)

    # Then using approximation leads to less data within the contour data
    assert get_data_len_by_index(new_rtstruct, 0) < get_data_len_by_index(
        new_rtstruct, 1
    )


def test_nonstandard_image_orientation(oriented_rtstruct: RTStruct):
    mask = get_empty_mask(oriented_rtstruct)
    mask[10:70, 5:15, 1] = 1
    mask[60:70, 5:40, 1] = 1

    IOU_threshold = 1.0  # Expected accuracy
    run_mask_iou_test(oriented_rtstruct, mask, IOU_threshold)


def test_one_slice_image(one_slice_rtstruct: RTStruct):
    mask = get_empty_mask(one_slice_rtstruct)
    mask[10:70, 5:15, 0] = 1
    mask[60:70, 5:40, 0] = 1

    IOU_threshold = 1.0  # Expected accuracy
    run_mask_iou_test(one_slice_rtstruct, mask, IOU_threshold)


def get_data_len_by_index(rt_struct: RTStruct, i: int):
    return len(rt_struct.ds.ROIContourSequence[i].ContourSequence[0].ContourData)


def run_mask_iou_test(
    rtstruct: RTStruct,
    mask,
    IOU_threshold,
    use_pin_hole=False,
    approximate_contours=True,
):
    # Save and load mask
    mask_name = "test"
    rtstruct.add_roi(
        mask,
        name=mask_name,
        use_pin_hole=use_pin_hole,
        approximate_contours=approximate_contours,
    )
    loaded_mask = rtstruct.get_roi_mask_by_name(mask_name)

    # Use IOU to test accuracy of loaded mask
    numerator = np.logical_and(mask, loaded_mask)
    denominator = np.logical_or(mask, loaded_mask)
    IOU = np.sum(numerator) / np.sum(denominator)
    assert IOU >= IOU_threshold


def get_empty_mask(rtstruct) -> np.ndarray:
    ref_dicom_image = rtstruct.series_data[0]
    mask_dims = (
        int(ref_dicom_image.Columns),
        int(ref_dicom_image.Rows),
        len(rtstruct.series_data),
    )
    mask = np.zeros(mask_dims)
    return mask.astype(bool)

def load_dicom_files_in_memory(file_paths):
    dicom_datasets = []
    for path in file_paths:
        with open(path, 'rb') as f:
            ds = pydicom.dcmread(f)
            dicom_datasets.append(ds)
    return dicom_datasets

def test_create_rtstruct_from_memory():
    print(os.getcwd())
    dicom_files = load_dicom_files_in_memory(['tests/mock_data/ct_1.dcm', 'tests/mock_data/ct_2.dcm'])
    rtstruct = RTStructBuilder.create_new_from_memory(dicom_files)
    assert rtstruct is not None
    assert len(rtstruct.series_data) == len(dicom_files)

def test_save_rtstruct_to_memory():
    dicom_files = load_dicom_files_in_memory(['tests/mock_data/ct_1.dcm', 'tests/mock_data/ct_2.dcm'])
    rtstruct = RTStructBuilder.create_new_from_memory(dicom_files)
    buffer = rtstruct.save_to_memory()
    assert buffer is not None
    buffer.seek(0)  # Reset the buffer to the beginning for reading
    loaded_ds = pydicom.dcmread(buffer)
    assert loaded_ds is not None
