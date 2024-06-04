import setuptools

VERSION = "1.0.1"
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("requirements.txt") as f:
    required = f.read().splitlines()

setuptools.setup(
    name="rt-utils-raystation",
    version=VERSION,
    author="Lukas Heine, Fabian Hörst",
    author_email="fabian.hoerst@uk-essen.de",
    description="A small library for handling masks and RT-Structs, with fixed for using with RayStation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/code-lukas/rt-utils",
    #package_dir={'':"rt_utils"},
    packages=setuptools.find_packages(exclude="tests"),
    keywords=["RTStruct", "Dicom", "Pydicom"],
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
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
    python_requires=">=3.7",
    install_requires=required,
)
