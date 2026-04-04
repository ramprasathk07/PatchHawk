from setuptools import setup, find_packages

setup(
    name="sentinel_synth",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "gymnasium>=0.29.0",
        "docker>=7.0.0",
        "streamlit>=1.30.0",
        "wandb>=0.16.0",
        "pytest>=8.0.0",
        "synthetic-data-kit>=0.1.0"
    ]
)
