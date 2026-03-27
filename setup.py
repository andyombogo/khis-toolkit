"""Setuptools configuration for the KHIS toolkit package."""

from setuptools import find_packages, setup


setup(
    name="khis-toolkit",
    version="0.1.0",
    author="John Andrew",
    license="MIT",
    description=(
        "Python analytics toolkit for Kenya DHIS2/KHIS health data - "
        "county-level cleaning, forecasting, and mapping."
    ),
    packages=find_packages(),
    python_requires=">=3.9",
    include_package_data=True,
)
