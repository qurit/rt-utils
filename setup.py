import setuptools

VERSION = '1.1.2'
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open('requirements.txt') as f:
    required = f.read().splitlines()

setuptools.setup(
    name="rt-utils", 
    version=VERSION,
    author="Asim Shrestha",
    author_email="asim.shrestha@hotmail.com",
    description="A small library for handling masks and RT-Structs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/qurit/rtutils",
    packages=setuptools.find_packages(exclude="tests"),
    keywords=["RTStruct", "Dicom", "Pydicom"],
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Typing :: Typed",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Image Processing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Physics",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
    ],
    python_requires='>=3.6',
    install_requires=required,
)
