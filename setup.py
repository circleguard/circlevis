from distutils.core import setup
from setuptools import find_packages
import re

with open("README.md", "r") as readme:
    long_description = readme.read()

# https://stackoverflow.com/a/7071358
VERSION = "Unknown"
VERSION_RE = r"^__version__ = ['\"]([^'\"]*)['\"]"

with open("circlevis/version.py") as f:
    match = re.search(VERSION_RE, f.read())
    if match:
        VERSION = match.group(1)
    else:
        raise RuntimeError("Unable to find version string in circlevis/version.py")

setup(
    name="circlevis",
    version=VERSION,
    description="A Qt Widget that displays a beatmap, and an arbitrary amount "
                "of replays.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
    ],
    keywords = ["osu!", "python", "Qt"],
    author="Liam DeVoe",
    author_email="orionldevoe@gmail.com",
    url="https://github.com/circleguard/circlevis",
    download_url = "https://github.com/circleguard/circlevis/tarball/v" + VERSION,
    packages=find_packages(),
    install_requires=[
        "circleguard ~= 4.0.2",
        "slider ~= 0.2.1"
    ]
)
