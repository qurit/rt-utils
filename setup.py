import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open('requirements.txt') as f:
    required = f.read().splitlines()
version = '0.0.4'

setuptools.setup(
    name="rt-utils", 
    version=version,
    author="Asim Shrestha",
    author_email="asim.shrestha@hotmail.com",
    description="A small library for handling masks and RT-Structs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/qurit/rtutils",
    packages=setuptools.find_packages(),
    keywords=["RTStruct", "Dicom", "Pydicom"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=required,
)
