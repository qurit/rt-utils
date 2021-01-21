from dataclasses import dataclass
from random import randrange

@dataclass
class ROIData:
    """Data class to easily pass ROI data to helper methods."""
    mask: str
    color: list
    number: int
    name: str
    frame_of_reference_uid: int
    description: str = ''

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