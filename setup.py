from setuptools import setup, find_packages

setup(
    name="rerereric",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        "console_scripts": [
            "rerereric = rerereric.__main__:main",
        ],
    },
    author="Eric Morphis",
    author_email="meorphis@gmail.com",
    description="A fuzzy git rerere implementation with approximate context matching",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/meorphis/rerereric",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
