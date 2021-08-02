from typing import List, Union
from random import randrange
from pydicom.uid import PYDICOM_IMPLEMENTATION_UID 
from dataclasses import dataclass

COLOR_PALETTE = [
    [255, 0, 255],
    [0, 235, 235],
    [255, 255, 0],
    [255, 0, 0],
    [0, 132, 255],
    [0, 240, 0],
    [255, 175, 0],
    [0, 208, 255],
    [180, 255, 105],
    [255, 20, 147],
    [160, 32, 240],
    [0, 255, 127],
    [255, 114, 0],
    [64, 224, 208],
    [0, 178, 47],
    [220, 20, 60],
    [238, 130, 238],
    [218, 165, 32],
    [255, 140, 190],
    [0, 0, 255],
    [255, 225, 0]
]

ROI_GENERATION_ALGORITHMS = ['AUTOMATIC',
                             'SEMIAUTOMATIC',
                             'MANUAL']

class SOPClassUID:
    RTSTRUCT_IMPLEMENTATION_CLASS = PYDICOM_IMPLEMENTATION_UID  # TODO find out if this is ok
    DETACHED_STUDY_MANAGEMENT = '1.2.840.10008.3.1.2.3.1'
    RTSTRUCT = '1.2.840.10008.5.1.4.1.1.481.3'


@dataclass
class ROIData:
    """Data class to easily pass ROI data to helper methods."""
    mask: str
    color: Union[str, List[int]]
    number: int
    name: str
    frame_of_reference_uid: int
    description: str = ''
    use_pin_hole: bool = False
    approximate_contours: bool = True
    roi_generation_algorithm: Union[str, int] = 0

    def __post_init__(self):
        self.validate_color()
        self.add_default_values()
        self.validate_roi_generation_algoirthm()

    def add_default_values(self):
        if self.color is None:
            self.color = COLOR_PALETTE[(self.number - 1) % len(COLOR_PALETTE)]

        if self.name is None:
            self.name = f"ROI-{self.number}"

    def validate_color(self):
        if self.color is None:
            return

        # Validating list eg: [0, 0, 0]
        if type(self.color) is list:
            if len(self.color) != 3:
                raise ValueError(f'{self.color} is an invalid color for an ROI')
            for c in self.color:
                try:
                    assert 0 <= c <= 255
                except:
                    raise ValueError(f'{self.color} is an invalid color for an ROI')

        else:
            self.color: str = str(self.color)
            self.color = self.color.strip('#')

            # fff -> ffffff
            if len(self.color) == 3:
                self.color = ''.join([x*2 for x in self.color])

            if not len(self.color) == 6:
                raise ValueError(f'{self.color} is an invalid color for an ROI')

            try:
                self.color = [int(self.color[i:i+2], 16) for i in (0, 2, 4)]
            except Exception as e:
                raise ValueError(f'{self.color} is an invalid color for an ROI')

    def validate_roi_generation_algoirthm(self):

        if isinstance(self.roi_generation_algorithm, int):
            # for ints we use the predefined values in ROI_GENERATION_ALGORITHMS
            if self.roi_generation_algorithm > 2 or self.roi_generation_algorithm < 0:
                raise ValueError('roi_generation_algorithm must be either an int (0=\'AUTOMATIC\', 1=\'SEMIAUTOMATIC\', 2=\'MANUAL\') '
                                 'or a str (not recomended).')
            else:
                self.roi_generation_algorithm = ROI_GENERATION_ALGORITHMS[self.roi_generation_algorithm]
    
        elif isinstance(self.roi_generation_algorithm, str):
            # users can pick a str if they want to use a value other than the three default values
            if self.roi_generation_algorithm not in ROI_GENERATION_ALGORITHMS:
                print('Got self.roi_generation_algorithm {}. Some viewers might complain about this option. '
                      'Better options might be 0=\'AUTOMATIC\', 1=\'SEMIAUTOMATIC\', or 2=\'MANUAL\'.'.format(self.roi_generation_algorithm))
        
        else:
            raise TypeError('Expected int (0=\'AUTOMATIC\', 1=\'SEMIAUTOMATIC\', 2=\'MANUAL\') '
                            'or a str (not recomended) for self.roi_generation_algorithm. Got {}.'.format(type(self.roi_generation_algorithm)))

