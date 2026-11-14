"""Series held in one file: reconstructed SPECT and Enhanced CT/MR/PET.

A multi-frame image puts a whole volume in a single instance, so the series is
not one file per slice. These tests cover splitting such a file into slices,
referencing those slices from a structure set, and refusing files whose frames
are not slices of a volume at all.
"""

import numpy as np
import pydicom
import pytest

from rt_utils import RTStructBuilder, image_helper, multiframe

from .conftest import build_enhanced_multiframe, build_multiframe_nm, save_dataset


def test_nm_volume_is_split_into_slices():
    series = image_helper.load_sorted_image_series([build_multiframe_nm(frames=8)])

    assert len(series) == 8
    assert [series_slice.frame_number for series_slice in series] == list(range(1, 9))
    assert [float(s.ImagePositionPatient[2]) for s in series] == [
        0.0,
        5.0,
        10.0,
        15.0,
        20.0,
        25.0,
        30.0,
        35.0,
    ]
    assert all(list(s.ImageOrientationPatient) == [1, 0, 0, 0, 1, 0] for s in series)
    assert all(list(s.PixelSpacing) == [2, 2] for s in series)


def test_nm_slices_keep_the_file_identity():
    """Frames share the SOPInstanceUID of the file: it names the instance."""
    ds = build_multiframe_nm(frames=4)
    series = image_helper.load_sorted_image_series([ds])

    assert {s.SOPInstanceUID for s in series} == {ds.SOPInstanceUID}
    assert len(series) == 4


def test_frames_are_not_mistaken_for_repeated_instances():
    """The duplicate check keys on the frame as well as the instance.

    Dropping repeated SOPInstanceUIDs is what keeps a series copied into two
    folders from being read twice. Every frame of one file carries the same
    identifier, so without the frame number a whole SPECT volume collapsed to
    one slice.
    """
    series = image_helper.load_sorted_image_series([build_multiframe_nm(frames=6)])

    assert len(image_helper.drop_repeated_instances(series)) == 6


def test_nm_frame_pixels_come_from_the_parent_file():
    ds = build_multiframe_nm(frames=5, rows=8, columns=8)
    volume = ds.pixel_array

    series = image_helper.load_sorted_image_series([ds])

    for index, series_slice in enumerate(series):
        assert np.array_equal(series_slice.pixel_array, volume[index])


def test_slice_vector_orders_the_frames():
    """Slice Vector says which slice each frame is, whatever order they are in."""
    ds = build_multiframe_nm(frames=4, slice_vector=[4, 3, 2, 1])
    series = image_helper.load_sorted_image_series([ds])

    # Sorted by position, so the frame stored last is the first slice.
    assert [s.frame_number for s in series] == [4, 3, 2, 1]
    assert [float(s.ImagePositionPatient[2]) for s in series] == [0.0, 5.0, 10.0, 15.0]


def test_slice_spacing_falls_back_to_slice_thickness():
    ds = build_multiframe_nm(frames=3)
    del ds.SpacingBetweenSlices
    ds.SliceThickness = 4.0

    series = image_helper.load_sorted_image_series([ds])

    assert [float(s.ImagePositionPatient[2]) for s in series] == [0.0, 4.0, 8.0]


def test_frames_stack_along_the_slice_normal():
    """A coronal volume advances along its own normal, not along z."""
    ds = build_multiframe_nm(
        frames=3,
        orientation=(1.0, 0.0, 0.0, 0.0, 0.0, -1.0),
        spacing_between_slices=2.0,
    )

    series = image_helper.load_sorted_image_series([ds])

    positions = [[float(value) for value in s.ImagePositionPatient] for s in series]
    assert positions == [[0.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 4.0, 0.0]]


def test_roi_round_trips_through_a_spect_volume():
    ds = build_multiframe_nm(frames=8, rows=32, columns=32)
    rtstruct = RTStructBuilder.create_new([ds])

    mask = np.zeros((32, 32, 8), dtype=bool)
    mask[10:20, 12:18, 2:5] = True
    rtstruct.add_roi(mask=mask, name="lesion")

    loaded = RTStructBuilder.create_from([ds], rtstruct.ds)

    assert np.array_equal(loaded.get_roi_mask_by_name("lesion"), mask)


def test_contours_reference_the_frame_they_were_drawn_on():
    """A contour on a multi-frame image names its frame, not just the file.

    Every slice of the volume has the same SOPInstanceUID, so Referenced Frame
    Number is the only thing that says which slice a contour belongs to.
    """
    ds = build_multiframe_nm(frames=6, rows=16, columns=16)
    rtstruct = RTStructBuilder.create_new([ds])

    mask = np.zeros((16, 16, 6), dtype=bool)
    mask[4:8, 4:8, 3] = True
    rtstruct.add_roi(mask=mask, name="single-slice")

    contours = rtstruct.ds.ROIContourSequence[0].ContourSequence
    assert len(contours) == 1
    contour_image = contours[0].ContourImageSequence[0]
    assert contour_image.ReferencedSOPInstanceUID == ds.SOPInstanceUID
    # The mask is set on index 3 of 6, which is the fourth frame.
    assert int(contour_image.ReferencedFrameNumber) == 4

    referenced = (
        rtstruct.ds.ReferencedFrameOfReferenceSequence[0]
        .RTReferencedStudySequence[0]
        .RTReferencedSeriesSequence[0]
        .ContourImageSequence
    )
    assert [int(image.ReferencedFrameNumber) for image in referenced] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]


def test_contours_without_a_frame_number_still_load():
    """Structure sets written before frames were referenced keep working.

    Such a file names the image but no frame. There is nothing to match it
    against, so it is taken to mean the image as a whole rather than being
    discarded, which would silently produce an empty mask.
    """
    ds = build_multiframe_nm(frames=4, rows=16, columns=16)
    rtstruct = RTStructBuilder.create_new([ds])

    mask = np.zeros((16, 16, 4), dtype=bool)
    mask[4:8, 4:8, 1] = True
    rtstruct.add_roi(mask=mask, name="legacy")

    for contour in rtstruct.ds.ROIContourSequence[0].ContourSequence:
        for contour_image in contour.ContourImageSequence:
            del contour_image.ReferencedFrameNumber

    loaded = RTStructBuilder.create_from([ds], rtstruct.ds)
    restored = loaded.get_roi_mask_by_name("legacy")

    # Without a frame number the contour belongs to every frame of the file,
    # which is the only reading left; it must not come back empty.
    assert restored.any()


def test_a_single_file_path_loads_the_whole_series(tmp_path):
    """A SPECT series is one file, so a file path must work like a folder."""
    ds = build_multiframe_nm(frames=5)
    path = tmp_path / "spect.dcm"
    save_dataset(ds, path)

    assert len(image_helper.load_sorted_image_series(str(path))) == 5


def test_a_folder_holding_one_multiframe_file_loads(tmp_path):
    ds = build_multiframe_nm(frames=5)
    save_dataset(ds, tmp_path / "spect.dcm")

    rtstruct = RTStructBuilder.create_new(str(tmp_path))

    assert len(rtstruct.series_data) == 5


def test_projection_data_is_refused():
    """SPECT projections are frames, but they are not slices of anything."""
    ds = build_multiframe_nm(
        frames=8, image_type=("ORIGINAL", "PRIMARY", "TOMO", "EMISSION")
    )
    ds.AngularViewVector = [index % 4 + 1 for index in range(8)]

    with pytest.raises(Exception, match="projection data"):
        image_helper.load_sorted_image_series([ds])


def test_projections_beside_a_usable_series_are_skipped(tmp_path, series_datasets):
    """A study folder may hold the acquisition as well as something usable.

    Raising there would make an unrelated series unloadable because a file
    beside it cannot be contoured, so the file is skipped and said to be
    skipped.
    """
    for index, ds in enumerate(series_datasets):
        save_dataset(ds, tmp_path / f"slice_{index}.dcm")

    projections = build_multiframe_nm(
        frames=8, image_type=("ORIGINAL", "PRIMARY", "TOMO", "EMISSION")
    )
    projections.AngularViewVector = [index % 4 + 1 for index in range(8)]
    save_dataset(projections, tmp_path / "projections.dcm")

    with pytest.warns(UserWarning, match="Skipped a multi-frame image"):
        series = image_helper.load_sorted_image_series(str(tmp_path))

    assert len(series) == len(series_datasets)


def test_projections_alone_raise_rather_than_look_empty(tmp_path):
    """With nothing else in the path, say why the file cannot be used."""
    projections = build_multiframe_nm(
        frames=8, image_type=("ORIGINAL", "PRIMARY", "TOMO", "EMISSION")
    )
    projections.AngularViewVector = [index % 4 + 1 for index in range(8)]
    save_dataset(projections, tmp_path / "projections.dcm")

    with pytest.raises(Exception, match="projection data"):
        image_helper.load_sorted_image_series(str(tmp_path))


def test_several_energy_windows_are_refused():
    ds = build_multiframe_nm(frames=8)
    ds.NumberOfEnergyWindows = 2
    ds.EnergyWindowVector = [1, 1, 1, 1, 2, 2, 2, 2]

    with pytest.raises(Exception, match="energy window"):
        image_helper.load_sorted_image_series([ds])


def test_a_gated_study_is_refused():
    """Frames outnumbering slices means more than one volume in the file."""
    ds = build_multiframe_nm(frames=8)
    ds.NumberOfSlices = 4

    with pytest.raises(Exception, match="more than one volume"):
        image_helper.load_sorted_image_series([ds])


def test_a_slice_vector_that_repeats_a_slice_is_refused():
    ds = build_multiframe_nm(frames=4, slice_vector=[1, 1, 2, 2])
    del ds.NumberOfSlices

    with pytest.raises(Exception, match="not one volume"):
        image_helper.load_sorted_image_series([ds])


def test_nm_without_detector_geometry_is_refused():
    ds = build_multiframe_nm(frames=4)
    del ds.DetectorInformationSequence

    with pytest.raises(Exception, match="Detector Information Sequence"):
        image_helper.load_sorted_image_series([ds])


def test_a_volume_without_spacing_is_refused():
    ds = build_multiframe_nm(frames=4)
    del ds.SpacingBetweenSlices

    with pytest.raises(Exception, match="Spacing Between Slices"):
        image_helper.load_sorted_image_series([ds])


def test_enhanced_image_uses_its_per_frame_geometry():
    ds = build_enhanced_multiframe(frames=4, z_positions=[0.0, 2.5, 5.0, 7.5])

    series = image_helper.load_sorted_image_series([ds])

    assert [float(s.ImagePositionPatient[2]) for s in series] == [0.0, 2.5, 5.0, 7.5]
    assert all(list(s.PixelSpacing) == [1, 1] for s in series)


def test_enhanced_image_with_unshared_groups():
    ds = build_enhanced_multiframe(frames=3, shared_orientation=False)

    series = image_helper.load_sorted_image_series([ds])

    assert len(series) == 3
    assert all(list(s.ImageOrientationPatient) == [1, 0, 0, 0, 1, 0] for s in series)


def test_enhanced_image_keeps_uneven_spacing():
    """Positions come from each frame, so an uneven stack stays uneven."""
    ds = build_enhanced_multiframe(frames=4, z_positions=[0.0, 3.0, 10.0, 13.0])

    series = image_helper.load_sorted_image_series([ds])

    assert [float(s.ImagePositionPatient[2]) for s in series] == [0.0, 3.0, 10.0, 13.0]


def test_enhanced_roi_round_trips():
    ds = build_enhanced_multiframe(frames=4, rows=16, columns=16)
    rtstruct = RTStructBuilder.create_new([ds])

    mask = np.zeros((16, 16, 4), dtype=bool)
    mask[5:10, 5:10, 1:3] = True
    rtstruct.add_roi(mask=mask, name="enhanced")

    loaded = RTStructBuilder.create_from([ds], rtstruct.ds)

    assert np.array_equal(loaded.get_roi_mask_by_name("enhanced"), mask)


def test_enhanced_frame_count_must_match_its_functional_groups():
    ds = build_enhanced_multiframe(frames=4)
    ds.NumberOfFrames = 5

    with pytest.raises(Exception, match="Per-frame Functional Groups"):
        image_helper.load_sorted_image_series([ds])


def test_a_plain_multiframe_stacks_from_its_own_position():
    """A file with no per-frame groups and no detector stacks from the top level."""
    ds = build_enhanced_multiframe(frames=3)
    del ds.PerFrameFunctionalGroupsSequence
    del ds.SharedFunctionalGroupsSequence
    ds.ImagePositionPatient = [0.0, 0.0, 10.0]
    ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    ds.PixelSpacing = [1.0, 1.0]
    ds.SpacingBetweenSlices = 2.0

    series = image_helper.load_sorted_image_series([ds])

    assert [float(s.ImagePositionPatient[2]) for s in series] == [10.0, 12.0, 14.0]


def test_a_multiframe_with_no_geometry_at_all_is_refused():
    ds = build_enhanced_multiframe(frames=3)
    del ds.PerFrameFunctionalGroupsSequence
    del ds.SharedFunctionalGroupsSequence

    with pytest.raises(Exception, match="cannot be placed in the patient"):
        image_helper.load_sorted_image_series([ds])


def test_single_frame_images_are_untouched(series_datasets):
    """The ordinary file-per-slice series is unaffected by any of this."""
    expanded = multiframe.expand_datasets(series_datasets)

    assert expanded == series_datasets
    assert all(multiframe.get_frame_number(ds) is None for ds in expanded)


def test_number_of_frames_of_one_is_not_multiframe():
    ds = pydicom.Dataset()
    ds.NumberOfFrames = 1

    assert not multiframe.is_multiframe(ds)


def test_a_position_that_is_not_a_point_is_refused():
    """Real whole-body NM files have been seen with a single zero there."""
    ds = build_multiframe_nm(frames=4)
    ds.DetectorInformationSequence[0].ImagePositionPatient = [0.0]

    with pytest.raises(Exception, match="Image Position"):
        image_helper.load_sorted_image_series([ds])


def test_a_whole_body_reconstruction_stacks_toward_the_head():
    """The geometry of a whole-body SPECT reconstruction seen in the wild.

    228 slices at 4.795 mm, with a CT acquired alongside it spanning 831.5 mm
    to 1926.5 mm. Stacking along the slice normal puts the volume at 838.8 mm
    to 1927.3 mm, which is that extent; stacking the other way would put it
    below zero, with the head where the feet are.
    """
    ds = build_multiframe_nm(
        frames=228,
        rows=128,
        columns=128,
        pixel_spacing=(4.7951998710632, 4.7951998710632),
        spacing_between_slices=4.7951998710632,
        origin=(-305.88104356376, -468.52898522651, 838.84250710174),
        orientation=(
            0.99999528489211,
            -0.0030700038998,
            0.00007259203229,
            0.00307051976859,
            0.99995734524369,
            -0.0087108898245,
        ),
    )

    series = image_helper.load_sorted_image_series([ds])

    assert len(series) == 228
    assert float(series[0].ImagePositionPatient[2]) == pytest.approx(838.84, abs=0.01)
    assert float(series[-1].ImagePositionPatient[2]) == pytest.approx(1927.31, abs=0.01)
    assert image_helper.get_spacing_between_slices(series) == pytest.approx(4.7952)
