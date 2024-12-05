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
    author="Your Name",
    author_email="your.email@example.com",
    description="A fuzzy git rerere driver that allows for approximate conflict resolution matching",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/git-fuzzy-rerere",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
