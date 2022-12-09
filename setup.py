#!/usr/bin/env python3
from setuptools import setup

setup(
    name='pibackbone',
    setup_requires=['pbr>=1.9', 'setuptools>=17.1'],
    python_requires='>=3.6',
    packages=['pibackbone'],
    package_dir={'pibackbone': 'pibackbone'},
    pbr=True
)
