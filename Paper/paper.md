---
title: 'RT-utils: A Minimal Python Library for RT-struct Manipulation'
tags:
  - RT-struct
  - Radiotherapy structures
  - mask
  - DICOM
  - image segmentation 
authors:
  - name: Asim Shrestha
    affiliation: "1" # (Multiple affiliations must be quoted)
  - name: Adam Watkins
    affiliation: "1"
  - name: Fereshteh Yousefirizi
    orcid: 0000-0001-5261-6163
    corresponding: true # (This is how to denote the corresponding author)
    affiliation: "1"
  - name: Arman Rahmim
  - orcid: 0000-0002-9980-2403
    corresponding: true # (This is how to denote the corresponding author)
    affiliation: "1, 2, 3, 4"
  - name: Carlos Uribe
    orcid: 0000-0003-3127-7478
    corresponding: true # (This is how to denote the corresponding author)
    affiliation: "1, 2, 5"

affiliations:
 - name: Department of Integrative Oncology, BC Cancer Research Institute, Vancouver, British Columbia, Canada
   index: 1
 - name: Department of Radiology, University of British Columbia, Vancouver, BC, Canada
   index: 2
 - name: Departments of Physics and Biomedical Engineering, University of British Columbia, Vancouver, BC, Canada
   index: 3
 - name: Department of Biomedical Engineering, University of British Columbia, Vancouver, Canada
   index: 4
 - name: BC Cancer, Vancouver, Canada
   index: 5
date: 24 July 2024
bibliography: paper.bib

# Optional fields if submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
aas-doi: 10.3847/xxxxx <- update this with the DOI from AAS once you know it.
aas-journal: Astrophysical Journal <- The name of the AAS journal.
---

# Summary

Towards the need for automated and precise AI-based analysis of medical images, we present RT-utils, a specialized Python library tuned for the manipulation of radiotherapy (RT) structures stored in DICOM format. RT-utils excels in converting the polygon contours into binary masks, ensuring accuracy and efficiency. By converting DICOM RT structures into standardized formats such as NumPy arrays and SimpleITK Images, RT-utils optimizes inputs for computational solutions such as AI-based automated segmentation techniques or radiomics analysis. Since its inception in 2020, RT-utils has been used extensively with a focus on simplifying complex data processing tasks. RT-utils offers researchers a powerful solution to enhance workflows and drive significant advancements in medical imaging. 

# Statement of need

The growing need for automated and robust analysis of medical images has driven the adoption of AI-based methods that often use DICOM images and RT structures as masks. However, the effectiveness of these AI approaches can vary due to differences in data sources and conversion techniques [@Whybra2023-en][@Yousefirizi2023-ax][@Rufenacht2023-as]. The DICOM standard includes the "radiotherapy structure set (RT-Struct)" object to facilitate the transfer of patient structures and related information, focusing on regions of interest and dose reference points.

Despite the availability of tools for converting DICOM images and RT-Structures into other formats [@Rufenacht2023-as][@Anderson2021-fp], integrating auto-segmentation solutions using deep learning in clinical environments is rare due to the lack of open-source frameworks that handle DICOM RT-Structure sets effectively. Software packages like dcmrtstruct2nii, DicomRTTool [@Anderson2021-fp], and PyRaDiSe [@Rufenacht2023-as] provide necessary functionalities, while frameworks like TorchIO [@Perez-Garcia2021-jf] and MONAI [@Creators_The_MONAI_Consortium_undated-or] face limitations in processing DICOM RT-structure data. Research has shown that variations in mask generation methods affect patient clustering and radiomic-based modeling in multi-center studies [@Whybra2023-en][@Yousefirizi2023-ax].

To address these challenges, we developed RT-utils, a specialized Python library designed to enhance the efficiency of manipulating RT-Structures. This tool aims to optimize workflows, simplify the handling of medical imaging data, and provide a comprehensive solution for researchers. RT-utils offers advanced techniques to convert expert-provided contours and AI tool output masks to RT-struct format, making them suitable for clinical workflows.

# Overview of RT-utils

Our module introduces intuitive techniques for efficient data curation of RT-Structure files, facilitating the identification of distinct region of interest (ROI) names and their corresponding locations within the structures. It adeptly handles scenarios where multiple ROI names correspond to the same structure, ensuring a comprehensive and accurate representation. Additionally, the module offers the conversion of DICOM images and RT-Struct into widely used formats such as NumPy arrays and SimpleITK Images. These standardized formats serve as optimal inputs for various applications, including deep learning models, image analysis, and radiomic feature calculations (extraction). Moreover, the toolkit simplifies the process of creating DICOM RT-Struct from predicted NumPy arrays, commonly the outputs of semantic segmentation deep learning models, providing a versatile solution for researchers and practitioners in medical imaging.
In the realm of data science, discretized image formats such as NIfTI, NRRD, and MHA are commonly employed, while radiotherapy workflows heavily rely on the DICOM format, specifically the DICOM RT-Struct. Unlike data science architectures like U-Net, which operate on grid-based data, handling the continuously spaced contour points present in RT-Struct poses a unique challenge. To bridge this gap, accurate data conversion between discrete and continuous spaces becomes crucial when working with clinical DICOM RT-Struct data.

## Technical Overview 

The module stands out in its capability to identify discrete Regions of Interest (ROI) and pinpoint their precise spatial locations within intricate structures. Noteworthy is its adept handling of scenarios where multiple ROI names correspond to the same anatomical structure, ensuring a comprehensive and accurate representation of data.
One of the primary functionalities of the module involves the sophisticated identification of distinct ROI names within RT-Struct files. It also accommodates cases where multiple ROI names map to the same anatomical structure, ensuring precise and comprehensive data organization. The module further facilitates the conversion of DICOM images and RT-Structures into widely adopted formats, specifically NumPy arrays and SimpleITK Images. These standardized formats serve as optimal inputs for various applications, including deep learning models, image analysis pipelines, and radiomic feature calculations. 

Another noteworthy feature is the module ability to simplify the generation of DICOM RT-Struct from predicted NumPy arrays, commonly serving as the output of semantic segmentation deep learning models. This functionality establishes a direct link between predictive modeling and clinical applications, offering a path from automated segmentation to structured RT data. RT-utils employs geometric operations from the Shapely library to convert DICOM ROI Contours into binary masks. This involves creating Shapely polygons from contours and rasterizing these polygons into binary masks. Leveraging geometric principles and libraries, our method accurately represents contours as masks, offering a valuable tool for efficient processing of RT-Struct data in radiotherapy applications.

First released in 2020, RT-utils is openly hosted on GitHub (*Starred >180 times as of July 2024), and on PyPI (https://pypi.org/project/rt-utils/) encouraging collaborative development. The demonstrated utility of RT-utils aligns with the evolving landscape of AI-based approaches in the medical domain. In this section, we elaborate on the practical applications of RT-utils. To install RT-utils, simply execute the command pip install RT-utils. 

## Available Manipulations

Once installed, users can import RTStructBuilder to create a new RT-Struct or load an existing one. Upon accomplishing this, users acquire the capability to execute the following operations:
o	Create a distinctive ROI within the RT-Struct using a binary mask. Optionally, users can specify the color, name, and description of the RT-Struct.
o	Retrieve a list of names for all ROIs contained within the RT-Struct.
o	Load ROI masks from the RT-Struct by specifying their respective names.
o	Safeguard the RT-Struct by providing either a name or a path for storage.

## Handling of DICOM Headers

RT-utils approach to managing DICOM headers is straightforward and it is designed for simplicity and effectiveness. Initially, we include all necessary headers to ensure the RT-Struct file validity. Subsequently, we maximize the transfer of headers from the input DICOM series, encompassing vital patient information. Moreover, the introduction of new ROIs dynamically integrates them into the relevant sequences within the RT-Struct.

## Incorporating an ROI Mask

The add_roi method requires the ROI mask to follow a specific format: it should be a 3D array where each 2D slice constitutes a binary mask. In this context, a pixel value of one within the mask indicates that the pixel belongs to the ROI for a specific slice. It is essential that the number of slices in the array match the number of slices in your DICOM series. The order of slices in the array should align with their corresponding slice locations in the DICOM series, ensuring that the first slice in the array corresponds to the smallest slice location in the DICOM series, the second slice corresponds to the second slice location, and so on.

## Practical Applications

RT-utils spans a diverse range of technical capabilities such as Creating new RT Structs, Adding to existing RT Structs, loading an existing RT Struct contour as a mask and Merging two existing RT Structs. Rt-utils also has the parameter use_pin_hole is a Boolean value that is initially set to false. When enabled (set to true), it erases lines within a mask, allowing each distinct region in an image to be enclosed by a single contour instead of having nested contours. This feature is useful when working with RT-Struct viewers that do not support nested contours or contours with holes. These capabilities extend to various applications, offering accelerated development of deep learning models through standardized inputs. It facilitates the integration of RT-Struct data into computational analyses and image processing pipelines (e.g. radiomics and AI), contributing to the efficiency of medical image analysis. Moreover, the toolkit supports a smooth transition from predictive models to clinical workflows, enhancing the practical utility of automated segmentation. In essence, RT-utils not only simplifies the curation of RT-Struct data but also empowers users with versatile tools for interfacing with standard formats, thereby facilitating advanced medical image analysis and model integration. RT-utils is confined to a straightforward 2D-based conversion algorithm. This limitation might generate a synthetic appearance of RT contour i.e. pixelated contours which could potentially impede the acceptance of generated RT contours within clinical environments and in our future efforts this issue will be addressed.

# Real-world Example
For comparing the effects of different RT-Struct conversion methods, we investigated the RT-utils tool, dcmrtstruct2nii (https://github.com/Sikerdebaard/dcmrtstruct2nii) and the built-in tools from LIFEx[@Nioche2018-ct] and 3D Slicer [@Fedorov2012-ax]. We implemented the conversion technique and conducted a comparison of the NIfTI ground truth files. The level of agreement observed between RT-utils and LIFEx surpasses that of other techniques. The mean absolute errors with respect to RT-utils are shown on sagittal and coronal masks. (Figures 1). The visual inspection of an example of converted masks overlaid on PET scans using different techniques are shown in Figures 1. 

![The visual inspection of an example of converted masks overlaid on PET scans using different techniques](https://github.com/user-attachments/assets/139bfba0-d25c-4373-8cf1-c603eeae1d6f)


# Acknowledgements

The authors wish to acknowledge the Natural Sciences and Engineering Research Council of Canada (NSERC) Discovery Grants RGPIN-2019-06467 and RGPIN-2021-02965.

# References
