from typing import List, Union
from random import randrange
from pydicom.uid import PYDICOM_IMPLEMENTATION_UID
from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageDraw

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
    [255, 225, 0],
]

ROI_GENERATION_ALGORITHMS = ["AUTOMATIC", "SEMIAUTOMATIC", "MANUAL"]


class SOPClassUID:
    RTSTRUCT_IMPLEMENTATION_CLASS = (
        PYDICOM_IMPLEMENTATION_UID  # TODO find out if this is ok
    )
    DETACHED_STUDY_MANAGEMENT = "1.2.840.10008.3.1.2.3.1"
    RTSTRUCT = "1.2.840.10008.5.1.4.1.1.481.3"


@dataclass
class ROIData:
    """Data class to easily pass ROI data to helper methods."""
    def __init__(self,
                data,
                color:str,
                number:int,
                name: str,
                frame_of_reference_uid:int,
                description:str,
                use_pin_hole:bool=False,
                approximate_contours:bool=True,
                roi_generation_algorithm: Union[str, int] = 0) -> None:
        """
        The ROI data can be in two formats.
            1, a [H, W, N] tensor contain N binary masks where N ths number of slices.
            2, a list of contour coordinates representing the vertex of a polygon ROI
        """
        assert isinstance(data, (np.ndarray, list))
        if isinstance(data, np.ndarray):
            self.mask = data
            self.polygon = None
        else:
            self.polygon = self.valaidate_polygon(data)
            self.mask=self.polygon2mask(data)
            self.polygon = data
        # set attributes
        self.color = color
        self.number = number
        self.name = name
        self.frame_of_reference_uid = frame_of_reference_uid
        self.description = description
        self.use_pin_hole = use_pin_hole
        self.approximate_contours = approximate_contours
        self.roi_generation_algorithm = roi_generation_algorithm

        self.__post_init__()

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
                raise ValueError(f"{self.color} is an invalid color for an ROI")
            for c in self.color:
                try:
                    assert 0 <= c <= 255
                except:
                    raise ValueError(f"{self.color} is an invalid color for an ROI")

        else:
            self.color: str = str(self.color)
            self.color = self.color.strip("#")

            # fff -> ffffff
            if len(self.color) == 3:
                self.color = "".join([x * 2 for x in self.color])

            if not len(self.color) == 6:
                raise ValueError(f"{self.color} is an invalid color for an ROI")

            try:
                self.color = [int(self.color[i : i + 2], 16) for i in (0, 2, 4)]
            except Exception as e:
                raise ValueError(f"{self.color} is an invalid color for an ROI")

    def validate_roi_generation_algoirthm(self):

        if isinstance(self.roi_generation_algorithm, int):
            # for ints we use the predefined values in ROI_GENERATION_ALGORITHMS
            if self.roi_generation_algorithm > 2 or self.roi_generation_algorithm < 0:
                raise ValueError(
                    "roi_generation_algorithm must be either an int (0='AUTOMATIC', 1='SEMIAUTOMATIC', 2='MANUAL') "
                    "or a str (not recomended)."
                )
            else:
                self.roi_generation_algorithm = ROI_GENERATION_ALGORITHMS[
                    self.roi_generation_algorithm
                ]

        elif isinstance(self.roi_generation_algorithm, str):
            # users can pick a str if they want to use a value other than the three default values
            if self.roi_generation_algorithm not in ROI_GENERATION_ALGORITHMS:
                print(
                    "Got self.roi_generation_algorithm {}. Some viewers might complain about this option. "
                    "Better options might be 0='AUTOMATIC', 1='SEMIAUTOMATIC', or 2='MANUAL'.".format(
                        self.roi_generation_algorithm
                    )
                )

        else:
            raise TypeError(
                "Expected int (0='AUTOMATIC', 1='SEMIAUTOMATIC', 2='MANUAL') "
                "or a str (not recomended) for self.roi_generation_algorithm. Got {}.".format(
                    type(self.roi_generation_algorithm)
                )
            )

    def valaidate_polygon(self, polygon):
        if len(polygon) == 0:
            raise ValueError('Empty polygon')
        return polygon

    @staticmethod
    def polygon2mask(polygon):
        h, w = polygon[0].h, polygon[0].w
        mask = np.concatenate([p.mask[:, :, None] for p in polygon], axis=-1)
        return mask


class Polygon2D:
    def __init__(self, coords, h, w) -> None:
        """
        coords: coordinates of vertice of a polygon [x1, y1, x2, y2, ..., xn, yn]
        """
        assert len(coords) % 2 == 0, 'invalid size of coords'
        self._coords = np.array(coords).reshape(-1, 2)
        self._h, self._w = h, w
        self._mask = None
        self._area = -1

    @property
    def h(self):
        return self._h

    @property
    def w(self):
        return self._w

    @property
    def coords(self):
        return self._coords

    @property
    def area(self):
        if self._area > 0:
            return self._area
        else:
            return self.mask.sum()

    @property
    def mask(self):
        if self._mask is not None:
            return self._mask
        else:
            if self.coords.shape[0] <= 1:
                self._mask = np.zeros((self.h, self.w), dtype=bool)
            else:
                img = Image.new('L', (self.w, self.h), 0)
                ImageDraw.Draw(img).polygon(self.coords.flatten().tolist(), outline=1, fill=1)
                self._mask = np.array(img, dtype=bool)
            return self._mask
