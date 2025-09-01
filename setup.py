"""
Setup script for the WarMachine package
"""

from setuptools import setup, find_packages

setup(
    name="warmachine",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "streamlit>=1.22.0",
        "plotly>=5.3.0",
        "pandas>=1.3.0",
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "scikit-learn>=0.24.0",
        "tensorflow>=2.8.0",
        "torch>=1.9.0",
        "transformers>=4.5.0",
        "altair>=4.0.0",
        "vega-datasets>=0.9.0"
    ],
    python_requires=">=3.8",
) 