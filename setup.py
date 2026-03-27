"""Setuptools configuration for the KHIS toolkit package."""

from setuptools import find_packages, setup


setup(
    name="khis-toolkit",
    version="0.1.0",
    author="John Andrew",
    author_email="andyombogo@gmail.com",
    url="https://github.com/andyombogo/khis-toolkit",
    license="MIT",
    description="Python analytics toolkit for Kenya DHIS2/KHIS health data",
    packages=find_packages(),
    python_requires=">=3.9",
    include_package_data=True,
)
