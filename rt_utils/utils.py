from random import randrange
from pydicom.uid import PYDICOM_ROOT_UID
from dataclasses import dataclass

class SOPClassUID():
    RTSTRUCT_IMPLEMENTATION_CLASS = PYDICOM_ROOT_UID # TODO find out if this is ok
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
        if self.color == None:
            self.color = self.get_random_colour()

        if self.name == None:
            self.name = f"ROI-{self.number}"
    
    def get_random_colour(self):
        max = 256
        return [randrange(max), randrange(max), randrange(max)]