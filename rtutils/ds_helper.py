import datetime
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence

def generate_base_dataset(file_name: str) -> FileDataset:
    file_meta = get_file_meta()
    ds = FileDataset(file_name, {}, file_meta=file_meta, preamble=b"\0" * 128)
    add_required_elements_to_ds(ds)
    add_sequence_lists_to_ds(ds)
    return ds

def get_file_meta() -> FileMetaDataset:
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
    file_meta.MediaStorageSOPInstanceUID = "1.2.3"
    file_meta.ImplementationClassUID = "1.2.3.4"
    return file_meta

def add_required_elements_to_ds(ds: FileDataset):
    # Appends data elements required by the DICOM standarad 
    ds.PatientName = "Test^Firstname"
    ds.PatientID = "123456"
    ds.Modality = 'RTSTRUCT'
    ds.Manufacturer = 'Qurit Lab'
    ds.InstitutionName = 'BC Cancer Research Center'
    # Set the transfer syntax
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    # Set creation date/time
    dt = datetime.datetime.now()
    ds.ContentDate = dt.strftime('%Y%m%d')

def add_sequence_lists_to_ds(ds: FileDataset):
    ds.ReferencedFrameOfReferenceSequence = Sequence()
    ds.StructureSetROISequence = Sequence()
    ds.ROIContourSequence = Sequence()
    ds.RTROIObservationsSequence = Sequence()
    
def create_rtroi_observation(observation_number: int) -> Dataset:
    rtroi_observation = Dataset()
    rtroi_observation.ObservationNumber = str(observation_number)
    rtroi_observation.ReferencedROINumber = str(observation_number)
    rtroi_observation.ROIObservationDescription = 'Type:Soft,Range:*/*,Fill:0,Opacity:0.0,Thickness:1,LineThickness:2,read-only:false'
    rtroi_observation.RTROIInterpretedType = ''
    rtroi_observation.ROIInterpreter = ''
    return rtroi_observation
