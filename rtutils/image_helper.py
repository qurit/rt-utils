
from pydicom import dcmread
import os
from skimage.measure import find_contours
import matplotlib
import numpy as np

def load_sorted_image_series(dicom_series_path: str):
        series_data = []
        for root, _, files in os.walk(dicom_series_path):
            for file in files:
                if file.endswith('.dcm'):
                    ds = dcmread(os.path.join(root, file))
                    # Only add CT images
                    if ds.file_meta.MediaStorageSOPClassUID == '1.2.840.10008.5.1.4.1.1.2': # CT Image Storage
                        series_data.append(ds)

        if len(series_data) == 0:
            raise Exception("No DICOM data found in input path")

        # Sort slices ascending
        series_data.sort(key=lambda ds: ds.SliceLocation, reverse=False)

        return series_data

def get_contours_coords(roi_mask_slice: np.ndarray, series_slice):
    # Method will find multiple contours if possible. Ensure only one is found
    contours = find_contours(roi_mask_slice)
    if len(contours) != 1:
        print(
            "ERROR: unexpected number of counters in slice. " +
            f"Expected 1, got {len(contours)}"
            )

    contour = contours[0]
    translated_contour = translate_contour_to_data_coordinants(contour, series_slice)
    formated_contour = format_contour_for_dicom(contour, series_slice)
    # plt.imshow(series_slice.pixel_array)

    # for contour in contours:
    #     plt.plot(contour[:, 1], contour[:, 0], linewidth=2)
    # plt.show()
    return formated_contour # Data is located in first index

def translate_contour_to_data_coordinants(contour, series_slice):
    offset = series_slice.ImagePositionPatient
    spacing = series_slice.PixelSpacing
    contour[:, 0] = (contour[:, 0]) * spacing[0] + offset[0]
    contour[:, 1] = (contour[:, 1]) * spacing[1] + offset[1]
    return contour

def format_contour_for_dicom(contour, series_slice):
    # DICOM uses a 1d array of x, y, z coords
    z_indicies = np.ones((contour.shape[0], 1)) * series_slice.SliceLocation
    contour = np.concatenate((contour, z_indicies), axis = 1)
    contour = np.ravel(contour)
    contour = contour.tolist()
    return contour
# def get_mask(contours, slices):
#     z = [s.ImagePositionPatient[2] for s in slices]
#     pos_r = slices[0].ImagePositionPatient[1]
#     spacing_r = slices[0].PixelSpacing[1]
#     pos_c = slices[0].ImagePositionPatient[0]
#     spacing_c = slices[0].PixelSpacing[0]

#     label = np.zeros_like(image, dtype=np.uint8)
#     for con in contours:
#         num = int(con['number'])
#         for c in con['contours']:
#             nodes = np.array(c).reshape((-1, 3))
#             assert np.amax(np.abs(np.diff(nodes[:, 2]))) == 0
#             z_index = z.index(nodes[0, 2])
#             r = (nodes[:, 1] - pos_r) / spacing_r
#             c = (nodes[:, 0] - pos_c) / spacing_c
#             rr, cc = polygon(r, c)
#             label[rr, cc, z_index] = num

#     colors = tuple(np.array([con['color'] for con in contours]) / 255.0)
#     return label, colors