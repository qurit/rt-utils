from random import randrange
from pydicom.uid import PYDICOM_ROOT_UID
from dataclasses import dataclass

COLOR_PALLET = [
    [255, 0, 0],        # Red
    [0, 255, 0],        # Lime
    [0, 0, 255],        # Blue
    [255, 255, 0],      # Yellow
    [0, 255, 255],      # Cyan
    [255, 0, 255],      # Magenta
    [192, 192, 192],    # Silver
    [128, 128, 128],    # Gray
    [128, 0, 0],        # Maroon
    [128, 128, 0],      # Olive
    [0, 128, 0],        # Green
    [128, 0, 128],      # Purple
    [0, 128, 128],      # Teal
    [0, 0, 128]         # Navy
]


class SOPClassUID:
    RTSTRUCT_IMPLEMENTATION_CLASS = PYDICOM_ROOT_UID  # TODO find out if this is ok
    CT_IMAGE_STORAGE = '1.2.840.10008.5.1.4.1.1.2'
    DETACHED_STUDY_MANAGEMENT = '1.2.840.10008.3.1.2.3.1'
    RTSTRUCT = '1.2.840.10008.5.1.4.1.1.481.3'


@dataclass
class ROIData:
    """Data class to easily pass ROI data to helper methods."""
    mask: str
    color: list
    number: int
    name: str
    frame_of_reference_uid: int
    description: str = ''
    use_pin_hole: bool = False

    def __post_init__(self):
        self.add_default_values()

    def add_default_values(self):
        if self.color is None:
            self.color = COLOR_PALLET[(self.number - 1) % len(COLOR_PALLET)]

        if self.name is None:
            self.name = f"ROI-{self.number}"
