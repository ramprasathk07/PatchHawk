from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="patchhawk",
    version="1.0.0",
    author="PatchHawk Team",
    description="RL-powered supply-chain vulnerability detector & auto-patcher",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ramprasathk07/patchhawk",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "openenv-core>=0.2.0",
        "openai>=1.0.0",
        "numpy>=1.24.0",
        "PyYAML>=6.0",
        "pydantic>=2.0.0",
        "docker>=7.0.0",
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.27.0",
        "streamlit>=1.30.0",
        "wandb>=0.16.0",
        "pytest>=8.0.0",
    ],
    extras_require={
        "training": [
            "unsloth>=2024.0",
            "trl>=0.7.0",
            "transformers>=4.38.0",
            "torch>=2.1.0",
            "peft>=0.8.0",
            "datasets>=2.16.0",
        ],
        "sdk": [
            "synthetic-data-kit>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "patchhawk-train=patchhawk.training.train_grpo:train_agent",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Security",
    ],
)
