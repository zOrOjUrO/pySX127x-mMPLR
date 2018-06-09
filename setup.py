import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyLoRa_pkg",
    version="0.0.5",
    author="Rui Silva",
    author_email="ruisilva.real@sapo.pt",
    description="This is a python interface to the Semtech SX1276/7/8/9 long range, low power transceiver family.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rpsreal/pySX127x",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
