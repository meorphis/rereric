from setuptools import setup, find_packages

setup(
    name="git-fuzzy-rerere",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'git-fuzzy-rerere=git_fuzzy_rerere.fuzzy_rerere:main',
        ],
    },
    author="Git Fuzzy Rerere Contributors",
    author_email="",
    description="A fuzzy git rerere implementation with approximate conflict resolution matching",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/git-fuzzy-rerere/git-fuzzy-rerere",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
