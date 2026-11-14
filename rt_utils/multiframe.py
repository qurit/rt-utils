"""Multi-frame images, presented to the rest of the library as single slices.

Most image series store one slice per file, and everything else in rt-utils is
written against that: a series is a list of datasets, one per slice, each with
its own ImagePositionPatient. Several modalities do not store themselves that
way. A reconstructed SPECT study is a single NM file whose Number of Frames is
the whole volume, and Enhanced CT, MR and PET put a volume in one file too.
Such a file used to be read as one slice, or skipped altogether for having no
Image Orientation (Patient) at the top level, so no structure set could be
built on it.

This module turns one multi-frame dataset into a list of per-frame datasets.
Each frame carries the geometry of that frame alone, so every existing code
path, sorting, contour generation and mask rasterisation, sees the series it
expects. The frame remembers which file and which frame number it came from,
which is what lets a contour reference it: DICOM identifies a frame of a
multi-frame image by Referenced SOP Instance UID together with Referenced
Frame Number (PS3.3 C.8.8.6, Contour Image Sequence).
"""

import copy
from typing import List, Optional, Sequence as TypingSequence

import numpy as np
from pydicom.dataset import Dataset
from pydicom.tag import Tag

# Pixel data stays with the file it was read from. Copying it into every frame
# would multiply a volume by its own number of slices, and the frame can read
# its own plane from the parent on demand; see MultiFrameSlice.pixel_array.
_PIXEL_DATA_TAGS = (
    Tag(0x7FE0, 0x0010),  # PixelData
    Tag(0x7FE0, 0x0008),  # FloatPixelData
    Tag(0x7FE0, 0x0009),  # DoubleFloatPixelData
    Tag(0x0028, 0x0008),  # NumberOfFrames, no longer true of a single frame
)


class MultiFrameSlice(Dataset):
    """One frame of a multi-frame image, shaped like a single-frame slice.

    The frame holds the parent's attributes with the geometry of this frame
    substituted, so it can be used anywhere a slice dataset is used. Elements
    are shared with the parent rather than deep copied, since a series can run
    to hundreds of frames; treat a frame as a view, not as an independent
    dataset to edit.

    ``frame_number`` is the DICOM frame number, counted from one, and
    ``source_dataset`` is the dataset it was taken from.
    """

    def __init__(self, source_dataset: Dataset, frame_number: int):
        super().__init__()
        self.source_dataset = source_dataset
        self.frame_number = frame_number

    @property
    def pixel_array(self) -> np.ndarray:
        """This frame's pixels, read from the parent dataset.

        pydicom caches the decoded array on the parent, so reading every
        frame of a series decodes the file once.
        """
        return self.source_dataset.pixel_array[self.frame_number - 1]


def is_multiframe(ds: Dataset) -> bool:
    """Whether a dataset holds more than one frame."""
    return get_number_of_frames(ds) > 1


def get_number_of_frames(ds: Dataset) -> int:
    """Number of Frames, defaulting to one where it is absent or empty."""
    frames = getattr(ds, "NumberOfFrames", None)
    if frames in (None, ""):
        return 1

    try:
        return int(frames)
    except (TypeError, ValueError):
        return 1


def get_frame_number(series_slice: Dataset) -> Optional[int]:
    """The frame a slice came from, or None if it is a single-frame image."""
    return getattr(series_slice, "frame_number", None)


def expand_datasets(datasets: TypingSequence[Dataset]) -> List[Dataset]:
    """Replace every multi-frame dataset in a series with its frames."""
    expanded = []
    for ds in datasets:
        if is_multiframe(ds):
            expanded.extend(expand(ds))
        else:
            expanded.append(ds)

    return expanded


def expand(ds: Dataset) -> List[Dataset]:
    """Split a multi-frame dataset into one dataset per frame.

    Raises an exception, rather than guessing, when the frames are not slices
    of one volume. Frames of a multi-frame image are not necessarily stacked
    in space: they can be time points, energy windows, detectors or gantry
    angles. Laying those out as though they were slices would produce an
    RTStruct that looks valid and places every contour somewhere the image
    never was.
    """
    frames = get_number_of_frames(ds)
    geometries = get_frame_geometries(ds, frames)

    return [
        _build_frame(ds, frame_number, geometry)
        for frame_number, geometry in enumerate(geometries, start=1)
    ]


class FrameGeometry:
    """Where one frame sits in the patient, and how big its pixels are."""

    def __init__(self, position, orientation, pixel_spacing, slice_thickness=None):
        self.position = [float(value) for value in position]
        self.orientation = [float(value) for value in orientation]
        self.pixel_spacing = [float(value) for value in pixel_spacing]
        self.slice_thickness = slice_thickness


def _build_frame(ds: Dataset, frame_number: int, geometry: FrameGeometry) -> Dataset:
    frame = MultiFrameSlice(ds, frame_number)
    file_meta = getattr(ds, "file_meta", None)
    if file_meta is not None:
        frame.file_meta = file_meta

    for element in ds:
        if element.tag in _PIXEL_DATA_TAGS:
            continue
        # Each frame gets its own element object. Sharing one would make
        # writing this frame's position overwrite the position of every other
        # frame, since pydicom assigns into the element already at that tag.
        # The values themselves are still shared, which is what keeps a
        # hundred-slice volume cheap to split.
        frame[element.tag] = copy.copy(element)

    frame.ImagePositionPatient = geometry.position
    frame.ImageOrientationPatient = geometry.orientation
    frame.PixelSpacing = geometry.pixel_spacing
    if geometry.slice_thickness is not None:
        frame.SliceThickness = geometry.slice_thickness

    # An image that holds one frame is numbered by instance, not by frame, and
    # leaving the parent's number on every frame makes the series look like
    # one image repeated.
    frame.InstanceNumber = frame_number

    return frame


def get_frame_geometries(ds: Dataset, frames: int) -> List[FrameGeometry]:
    """Work out where each frame of a multi-frame image lies.

    Three layouts are understood, in the order a file is likely to use them:
    the per-frame functional groups of an Enhanced image, the detector
    information of an NM image, and, failing both, a single stated position
    and orientation with the frames stacked along the slice normal.
    """
    if "PerFrameFunctionalGroupsSequence" in ds:
        return _functional_group_geometries(ds, frames)

    if getattr(ds, "Modality", None) == "NM" or "DetectorInformationSequence" in ds:
        return _nm_geometries(ds, frames)

    return _stacked_geometries(ds, frames)


def _functional_group_geometries(ds: Dataset, frames: int) -> List[FrameGeometry]:
    """Geometry of an Enhanced CT, MR or PET image.

    Each frame's plane position, plane orientation and pixel measures live in
    its own item of the Per-frame Functional Groups Sequence, except where
    they are the same for every frame, in which case they are stated once in
    the Shared Functional Groups Sequence.
    """
    per_frame = ds.PerFrameFunctionalGroupsSequence
    if len(per_frame) != frames:
        raise Exception(
            f"Multi-frame image {_describe(ds)} states {frames} frame(s) but "
            f"its Per-frame Functional Groups Sequence has {len(per_frame)} "
            "item(s). The two must agree for a frame to be placed in the "
            "patient."
        )

    shared_sequence = getattr(ds, "SharedFunctionalGroupsSequence", None)
    shared = shared_sequence[0] if shared_sequence else None

    geometries = []
    for index, frame_groups in enumerate(per_frame, start=1):
        position = _functional_group_value(
            frame_groups, shared, "PlanePositionSequence", "ImagePositionPatient"
        )
        orientation = _functional_group_value(
            frame_groups, shared, "PlaneOrientationSequence", "ImageOrientationPatient"
        )
        pixel_spacing = _functional_group_value(
            frame_groups, shared, "PixelMeasuresSequence", "PixelSpacing"
        )
        thickness = _functional_group_value(
            frame_groups, shared, "PixelMeasuresSequence", "SliceThickness"
        )

        if position is None or orientation is None:
            raise Exception(
                f"Frame {index} of multi-frame image {_describe(ds)} has no "
                "Image Position (Patient) or no Image Orientation (Patient), "
                "in its own functional groups or in the shared ones, so it "
                "cannot be placed in the patient."
            )

        if pixel_spacing is None:
            pixel_spacing = getattr(ds, "PixelSpacing", None)
        if pixel_spacing is None:
            raise Exception(
                f"Frame {index} of multi-frame image {_describe(ds)} states no "
                "Pixel Spacing, so contour coordinates cannot be scaled."
            )

        _require_placeable_geometry(ds, position, orientation)

        geometries.append(
            FrameGeometry(position, orientation, pixel_spacing, thickness)
        )

    return geometries


def _functional_group_value(frame_groups, shared, sequence_keyword, keyword):
    """A functional group value, from the frame's own groups or the shared ones."""
    for groups in (frame_groups, shared):
        if groups is None:
            continue

        sequence = getattr(groups, sequence_keyword, None)
        if not sequence:
            continue

        value = getattr(sequence[0], keyword, None)
        if value is not None:
            return value

    return None


def _nm_geometries(ds: Dataset, frames: int) -> List[FrameGeometry]:
    """Geometry of a reconstructed NM (SPECT) image.

    An NM image states its position and orientation once, inside the Detector
    Information Sequence, rather than at the top level (PS3.3 C.8.4.8). The
    frames of a reconstructed tomographic image are the slices of the volume,
    spaced along the slice normal by Spacing Between Slices, and Slice Vector
    says which slice each frame belongs to.

    Only a reconstruction is a volume. The projections an NM file can also
    hold are frames too, one per gantry angle, detector and energy window, and
    those are not slices of anything; see _require_reconstructed_tomo.
    """
    _require_reconstructed_tomo(ds, frames)

    detectors = getattr(ds, "DetectorInformationSequence", None)
    if not detectors:
        raise Exception(
            f"NM image {_describe(ds)} has no Detector Information Sequence, "
            "which is where an NM image states its Image Position (Patient) "
            "and Image Orientation (Patient), so its frames cannot be placed "
            "in the patient."
        )

    detector = detectors[0]
    position = getattr(detector, "ImagePositionPatient", None)
    orientation = getattr(detector, "ImageOrientationPatient", None)
    if position is None or orientation is None:
        raise Exception(
            f"NM image {_describe(ds)} states no Image Position (Patient) or "
            "no Image Orientation (Patient) in its Detector Information "
            "Sequence, so its frames cannot be placed in the patient."
        )

    _require_placeable_geometry(ds, position, orientation)

    pixel_spacing = getattr(ds, "PixelSpacing", None)
    if pixel_spacing is None:
        raise Exception(
            f"NM image {_describe(ds)} states no Pixel Spacing, so contour "
            "coordinates cannot be scaled."
        )

    spacing = _slice_spacing(ds)
    slice_indices = _nm_slice_indices(ds, frames)

    return _stack_along_normal(
        position, orientation, pixel_spacing, spacing, slice_indices
    )


def _require_placeable_geometry(ds: Dataset, position, orientation) -> None:
    """Refuse a position or orientation that is not a point and a pair of axes.

    Image Position (Patient) is three coordinates and Image Orientation
    (Patient) is six. Equipment that writes neither a volume nor a plane in
    the patient sometimes leaves a single zero in the position instead, which
    is not a point, and the arithmetic that follows would fail obscurely on
    it.
    """
    coordinates = _as_list(position)
    axes = _as_list(orientation)

    if len(coordinates) != 3 or len(axes) != 6:
        raise Exception(
            f"Multi-frame image {_describe(ds)} states an Image Position "
            f"(Patient) of {len(coordinates)} value(s) and an Image "
            f"Orientation (Patient) of {len(axes)} value(s), where three and "
            "six are required. Its frames cannot be placed in the patient."
        )


def _as_list(value) -> list:
    """A DICOM value as a list, whether it holds one element or several."""
    if value is None:
        return []

    if isinstance(value, (str, bytes)):
        return [value]

    try:
        return list(value)
    except TypeError:
        return [value]


def _require_reconstructed_tomo(ds: Dataset, frames: int) -> None:
    """Refuse NM frames that are not slices of a reconstructed volume.

    A tomographic NM acquisition is stored as its projections: one frame per
    gantry angle, per detector head and per energy window. Image Type says
    which it is, "RECON TOMO" for the reconstruction and "TOMO" for the
    projections it was reconstructed from, and the vectors that index the
    frames say the same thing in another way.

    Contours cannot be drawn on projections. They are not slices, they have no
    position along a slice normal, and each is a view of the whole object from
    one angle. The reconstruction is a separate series, and that is what a
    structure set is drawn on.
    """
    image_type = [str(value).upper() for value in getattr(ds, "ImageType", [])]

    if "RECON TOMO" in image_type or "RECON GATED TOMO" in image_type:
        projection_like = False
    elif "TOMO" in image_type or "GATED TOMO" in image_type:
        projection_like = True
    else:
        projection_like = False

    angular_views = _distinct_count(getattr(ds, "AngularViewVector", None))
    detectors = _distinct_count(getattr(ds, "DetectorVector", None))
    energy_windows = _distinct_count(getattr(ds, "EnergyWindowVector", None))

    if projection_like or angular_views > 1:
        raise Exception(
            f"NM image {_describe(ds)} holds projection data, not a "
            f"reconstructed volume: Image Type is {image_type or '<absent>'} "
            f"and its {frames} frames span {angular_views} gantry angle(s), "
            f"{detectors} detector(s) and {energy_windows} energy window(s). "
            "Its frames are views of the object from each angle, not slices "
            "through it, so they have no position along a slice normal and "
            "nothing can be contoured on them. Build the structure set on the "
            "reconstructed SPECT series (Image Type RECON TOMO) instead, or "
            "on the CT of the same study."
        )

    if detectors > 1 or energy_windows > 1:
        raise Exception(
            f"NM image {_describe(ds)} holds {frames} frames spanning "
            f"{detectors} detector(s) and {energy_windows} energy window(s), "
            "so its frames are not a single stack of slices. Select one "
            "detector and one energy window before building a structure set "
            "on it."
        )

    slices = getattr(ds, "NumberOfSlices", None)
    if slices not in (None, "") and int(slices) != frames:
        raise Exception(
            f"NM image {_describe(ds)} states {frames} frames but "
            f"{int(slices)} slices, so its frames hold more than one volume: "
            "a gated or multi-phase study stores every phase in one file. "
            "Select a single volume before building a structure set on it."
        )


def _distinct_count(vector) -> int:
    """How many different values a frame index vector takes."""
    if vector is None:
        return 1

    try:
        values = list(vector)
    except TypeError:
        return 1

    return len({int(value) for value in values}) if values else 1


def _nm_slice_indices(ds: Dataset, frames: int) -> List[int]:
    """Which slice each frame is, counted from zero.

    Slice Vector numbers the slices from one, in the order the frames are
    stored. It is what tells a file whose frames were written in some other
    order where each one belongs. Where it is absent, the frames are taken to
    be in slice order.
    """
    slice_vector = getattr(ds, "SliceVector", None)
    if slice_vector is None:
        return list(range(frames))

    indices = [int(value) - 1 for value in slice_vector]
    if len(indices) != frames:
        raise Exception(
            f"NM image {_describe(ds)} states {frames} frames but its Slice "
            f"Vector has {len(indices)} entries, so which slice each frame "
            "belongs to is unknown."
        )

    if sorted(indices) != list(range(frames)):
        raise Exception(
            f"NM image {_describe(ds)} has a Slice Vector that is not a "
            "permutation of its slices, so its frames are not one volume: "
            f"{frames} frames carry {len(set(indices))} distinct slice "
            "number(s). This is what a gated or multi-energy-window study "
            "looks like; select a single volume before building a structure "
            "set on it."
        )

    return indices


def _stacked_geometries(ds: Dataset, frames: int) -> List[FrameGeometry]:
    """Geometry of a multi-frame image that states one position and orientation.

    The frames are taken to be slices in storage order, stepping along the
    slice normal by Spacing Between Slices. This is the layout of an old-style
    multi-frame CT or ultrasound volume, which carries Image Position
    (Patient) at the top level and nothing per frame.
    """
    position = getattr(ds, "ImagePositionPatient", None)
    orientation = getattr(ds, "ImageOrientationPatient", None)
    pixel_spacing = getattr(ds, "PixelSpacing", None)

    if position is None or orientation is None:
        raise Exception(
            f"Multi-frame image {_describe(ds)} has {frames} frames but no "
            "per-frame geometry and no Image Position (Patient) or Image "
            "Orientation (Patient) of its own, so its frames cannot be placed "
            "in the patient. An Enhanced image states this in its Per-frame "
            "Functional Groups Sequence and an NM image in its Detector "
            "Information Sequence; this file has neither."
        )

    if pixel_spacing is None:
        raise Exception(
            f"Multi-frame image {_describe(ds)} states no Pixel Spacing, so "
            "contour coordinates cannot be scaled."
        )

    _require_placeable_geometry(ds, position, orientation)

    return _stack_along_normal(
        position,
        orientation,
        pixel_spacing,
        _slice_spacing(ds),
        list(range(frames)),
    )


def _stack_along_normal(
    position, orientation, pixel_spacing, spacing, slice_indices
) -> List[FrameGeometry]:
    """Place frames along the slice normal, one spacing apart.

    The normal is the cross product of the row and column directions, as
    everywhere else in this library, so the stack runs the way DICOM says the
    slices advance.
    """
    origin = np.asarray([float(value) for value in position], dtype=float)
    row_direction = np.asarray([float(value) for value in orientation[:3]])
    column_direction = np.asarray([float(value) for value in orientation[3:]])
    normal = np.cross(row_direction, column_direction)

    # Slice Thickness is left as the file states it. It is the thickness of a
    # slice, which is the step between slices only when they neither overlap
    # nor leave gaps, and nothing here is derived from it: spacing comes from
    # the positions themselves.
    return [
        FrameGeometry(origin + index * spacing * normal, orientation, pixel_spacing)
        for index in slice_indices
    ]


def _slice_spacing(ds: Dataset) -> float:
    """The distance between neighbouring frames, in millimetres.

    Spacing Between Slices is the centre-to-centre distance and is what a
    stack steps by. Slice Thickness is the thickness of one slice, which is
    the same thing only when the slices neither overlap nor leave gaps; it is
    used when nothing better is stated, because a volume with no spacing at
    all cannot be placed.
    """
    for keyword in ("SpacingBetweenSlices", "SliceThickness"):
        value = getattr(ds, keyword, None)
        if value in (None, ""):
            continue

        spacing = float(value)
        if spacing != 0:
            return spacing

    raise Exception(
        f"Multi-frame image {_describe(ds)} states neither Spacing Between "
        "Slices nor Slice Thickness, so the distance between its frames is "
        "unknown and they cannot be placed in the patient."
    )


def _describe(ds: Dataset) -> str:
    """A short identification of a dataset for an error message."""
    return str(getattr(ds, "SOPInstanceUID", "<unknown>"))
