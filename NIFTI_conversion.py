import os
import pydicom
import numpy as np
import SimpleITK as sitk
from rt_utils import RTStructBuilder
import csv
import json
import dateutil

# Define your DICOM root directory here:
IMAGE_FOLDER_PATH = "///data"

ATTRIBUTE_FILE_NAME = "attributes.csv"
HEADERS_FILE_NAME = "headers.json"
SAVE_JSON = False

def winapi_path(dos_path, encoding=None):
    # Simplified for non-Windows usage:
    return os.path.abspath(dos_path)

def bqml_to_suv(dcm_file: pydicom.FileDataset) -> float:
    '''
    Calculates the SUV conversion factor from Bq/mL to g/mL using DICOM header info.
    This simplified version returns only the SUV factor.
    '''
    nuclide_dose = dcm_file[0x054, 0x0016][0][0x0018, 0x1074].value  # Injected dose (Bq)
    weight = dcm_file[0x0010, 0x1030].value  # Patient weight (kg)
    half_life = float(dcm_file[0x054, 0x0016][0][0x0018, 0x1075].value)  # Half life (s)

    series_time = str(dcm_file[0x0008, 0x0031].value)  # Series time (HHMMSS)
    series_date = str(dcm_file[0x0008, 0x0021].value)  # Series date (YYYYMMDD)
    series_dt = dateutil.parser.parse(series_date + ' ' + series_time)

    nuclide_time = str(dcm_file[0x054, 0x0016][0][0x0018, 0x1072].value)  # Injection time
    nuclide_dt = dateutil.parser.parse(series_date + ' ' + nuclide_time)

    delta_time = (series_dt - nuclide_dt).total_seconds()
    decay_correction = 2 ** (-1 * delta_time/half_life)
    suv_factor = (weight * 1000) / (decay_correction * nuclide_dose)
    return suv_factor

def getDicomHeaders(file):
    dicomHeaders = file.to_json_dict()
    # remove pixel data from headers
    dicomHeaders.pop('7FE00010', None)
    return dicomHeaders

def get_patient_nifti_dir(dicom_dir):
    # This function finds the patient's directory and creates a NIFTI folder inside it.
    # Assuming structure: .../data/patientX/DICOM/...
    # We want: .../data/patientX/NIFTI/
    patient_dir = dicom_dir
    # Move up until we exit DICOM directories
    # Typically, dicom_dir might look like: /.../data/patientX/DICOM/studyY
    # One dirname: /.../data/patientX/DICOM
    # Another dirname: /.../data/patientX
    patient_dir = os.path.dirname(os.path.dirname(dicom_dir))  # This should now point to patientX directory
    nifti_dir = os.path.join(patient_dir, "NIFTI")
    if not os.path.exists(nifti_dir):
        os.makedirs(nifti_dir)
    return nifti_dir

def dicomToNifti(file, seriesDir):
    patientID, modality, studyDate = getattr(file, 'PatientID', None), getattr(file, 'Modality', None), getattr(file, 'StudyDate', None)
    reader = sitk.ImageSeriesReader()
    seriesNames = reader.GetGDCMSeriesFileNames(seriesDir)
    reader.SetFileNames(seriesNames)
    image = reader.Execute()

    # Convert PET to SUV if needed
    if modality == 'PT':
        pet = pydicom.dcmread(seriesNames[0])  # read one image
        suv_factor = bqml_to_suv(pet)
        image = sitk.Multiply(image, suv_factor)

    nifti_dir = get_patient_nifti_dir(seriesDir)
    output_filename = os.path.join(nifti_dir, f'{patientID}_{modality}_{studyDate}.nii.gz')
    sitk.WriteImage(image, output_filename, imageIO='NiftiImageIO')

def sortParallelLists(list1, list2):
    if len(list1) > 0 and len(list2) > 0:
        tuples = zip(*sorted(zip(list1, list2)))
        list1, list2 = [list(tuple) for tuple in tuples]
    return list1, list2

def buildMaskArray(file, seriesPath, labelPath) -> np.ndarray:
    rtstruct = RTStructBuilder.create_from(dicom_series_path=seriesPath, rt_struct_path=labelPath)
    rois = rtstruct.get_roi_names()
    masks = [rtstruct.get_roi_mask_by_name(roi).astype(int) for roi in rois]

    final_mask = sum(masks)
    final_mask = np.where(final_mask>=1, 1, 0)
    # Reorient mask
    final_mask = np.moveaxis(final_mask, [0, 1, 2], [1, 2, 0])
    return final_mask

def buildMasks(file, seriesPath, labelPath):
    final_mask = buildMaskArray(file, seriesPath, labelPath)
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(seriesPath)
    reader.SetFileNames(dicom_names)
    ref_img = reader.Execute()

    mask_img = sitk.GetImageFromArray(final_mask)
    mask_img.CopyInformation(ref_img)

    nifti_dir = get_patient_nifti_dir(seriesPath)
    patientID, modality, studyDate = getattr(file, 'PatientID', None), getattr(file, 'Modality', None), getattr(file, 'StudyDate', None)
    output_filename = os.path.join(nifti_dir, f'{patientID}_{modality}_{studyDate}_mask.nii.gz')
    sitk.WriteImage(mask_img, output_filename, imageIO="NiftiImageIO")

def convertFiles():
    dicomFilePaths = []
    dicomFileDirs = []
    dicomFileTraits = []
    dicomFileHeaders = []
    dicomFileHeaderKeys = []
    labelInstanceUIDs = []
    seriesInstanceUIDs = []
    labelPaths = []
    seriesPaths = []

    # Rename directories with overly long names
    for _ in range(3):
        for root, dirs, files in os.walk(IMAGE_FOLDER_PATH):
            for dir in dirs:
                if len(dir) > 20:
                    i = 5
                    while os.path.exists(os.path.join(root, dir[:i])):
                        i += 1
                    newDir = dir[:i]
                    os.rename(os.path.join(root, dir), os.path.join(root, newDir))

    # Collect DICOM file paths
    for root, dirs, files in os.walk(IMAGE_FOLDER_PATH):
        for file in files:
            if file.endswith('.dcm'):
                filePath = winapi_path(os.path.join(root, file))
                fileDirname = os.path.dirname(filePath)
                if len(dicomFilePaths) > 0 and fileDirname == dicomFileDirs[-1]:
                    dicomFilePaths[-1].append(filePath)
                else:
                    dicomFilePaths.append([filePath])
                    dicomFileDirs.append(fileDirname)

    # Analyze DICOM files
    for i in range(len(dicomFilePaths)):
        if i % 10 == 0 or i == len(dicomFilePaths)-1:
            print(f'Processing {round((i + 1) / len(dicomFilePaths) * 100, 2)}% of files')
        file = pydicom.dcmread(dicomFilePaths[i][0], force=True)
        headers = getDicomHeaders(file)
        traits = {
            "Patient ID": getattr(file, 'PatientID', None),
            "Patient's Sex": getattr(file, 'PatientSex', None),
            "Patient's Age": getattr(file, 'PatientAge', None),
            "Patient's Birth Date": getattr(file, 'PatientBirthDate', None),
            "Patient's Weight": getattr(file, 'PatientWeight', None),
            "Institution Name": getattr(file, 'InstitutionName', None),
            "Referring Physician's Name": getattr(file, 'ReferringPhysicianName', None),
            "Operator's Name": getattr(file, 'OperatorsName', None),
            "Study Date": getattr(file, 'StudyDate', None),
            "Study Time": getattr(file, 'StudyTime', None),
            "Modality": getattr(file, 'Modality', None),
            "Series Description": getattr(file, 'SeriesDescription', None),
            "Dimensions": np.array(getattr(file, 'pixel_array', np.array([]))).shape,
        }
        for key in headers.keys():
            if key not in dicomFileHeaderKeys:
                dicomFileHeaderKeys.append(key)
        dicomFileTraits.append(traits)
        dicomFileHeaders.append(headers)

        fileModality = getattr(file, 'Modality', None)

        # If it's an RTSTRUCT, track the referenced SeriesInstanceUID
        if fileModality == 'RTSTRUCT':
            seriesInstanceUID = headers['30060010']['Value'][0]['30060012']['Value'][0]['30060014']['Value'][0]['0020000E']['Value'][0]
            labelInstanceUIDs.append(seriesInstanceUID)
            labelPaths.append(dicomFilePaths[i][0])

    # Identify which series correspond to RTSTRUCT
    for i in range(len(dicomFileDirs)):
        if i % 10 == 0 or i == len(dicomFileDirs)-1:
            print(f'Scanning series directories {round((i+1)/len(dicomFileDirs)*100, 2)}%')
        file = pydicom.dcmread(dicomFilePaths[i][0], force=True)
        fileModality = getattr(file, 'Modality', None)
        seriesInstanceUID = getDicomHeaders(file)['0020000E']['Value'][0]
        if fileModality != 'RTSTRUCT':
            if seriesInstanceUID in labelInstanceUIDs:
                seriesPaths.append(dicomFileDirs[i])
                seriesInstanceUIDs.append(seriesInstanceUID)

    labelInstanceUIDs, labelPaths = sortParallelLists(labelInstanceUIDs, labelPaths)
    seriesInstanceUIDs, seriesPaths = sortParallelLists(seriesInstanceUIDs, seriesPaths)

    # Save attributes
    if len(dicomFilePaths) > 0:
        data_dir = os.path.join(IMAGE_FOLDER_PATH, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        with open(os.path.join(IMAGE_FOLDER_PATH, ATTRIBUTE_FILE_NAME), 'w', encoding='UTF8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=dicomFileTraits[0].keys())
            writer.writeheader()
            writer.writerows(dicomFileTraits)
        
        if SAVE_JSON:
            with open(os.path.join(IMAGE_FOLDER_PATH, HEADERS_FILE_NAME), 'w') as f:
                json.dump(dicomFileHeaders, f)

    # Convert PET series to NIFTI
    for i in range(len(dicomFileDirs)):
        if i % 10 == 0 or i == len(dicomFileDirs)-1:
            print(f'Converting PET series to NIFTI {round((i+1)/len(dicomFileDirs)*100, 2)}%')
        if len(dicomFilePaths[i]) > 1:
            file = pydicom.dcmread(dicomFilePaths[i][0], force=True)
            fileModality = getattr(file, 'Modality', None)
            if fileModality == 'PT':
                dicomToNifti(file, dicomFileDirs[i])

    # Convert RTSTRUCT to NIFTI masks
    for i in range(min([len(labelPaths), len(seriesPaths)])):
        if i % 10 == 0 or i == len(dicomFileDirs)-1:
            print(f'Converting RTSTRUCT to NIFTI masks {round((i+1)/min([len(labelPaths), len(seriesPaths)])*100, 2)}%')
        file_label = pydicom.dcmread(labelPaths[i], force=True)
        if len(labelInstanceUIDs) != len(seriesInstanceUIDs):
            # Need to match label's UID to a series UID
            j = 0
            if len(labelInstanceUIDs) < len(seriesInstanceUIDs):
                while (i + j) < len(seriesInstanceUIDs) and labelInstanceUIDs[i] != seriesInstanceUIDs[i+j]:
                    j += 1
                try:
                    buildMasks(file_label, seriesPaths[i+j], labelPaths[i])
                except:
                    print('Failed to build mask for label: ', labelPaths[i])
            else:
                while (i + j) < len(labelInstanceUIDs) and seriesInstanceUIDs[i] != labelInstanceUIDs[i+j]:
                    j += 1
                try:
                    buildMasks(pydicom.dcmread(labelPaths[i+j], force=True), seriesPaths[i], labelPaths[i+j])
                except:
                    print('Failed to build mask for label: ', labelPaths[i+j])
        else:
            try:
                buildMasks(file_label, seriesPaths[i], labelPaths[i])
            except:
                print('Failed to build mask for label: ', labelPaths[i])

    print('Done! Created NIFTI files in the NIFTI folder inside each patient directory.')

if __name__ == '__main__':
    convertFiles()
