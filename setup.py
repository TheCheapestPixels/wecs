"""A setuptools based setup module.
"""

from setuptools import setup, find_packages
from os import path


here = path.abspath(path.dirname(__file__))

setup(
    name='wecs',
    version='0.1.1dev',
    description='An ECS (entity component system)',
    url='https://github.com/TheCheapestPixels/wecs',
    author='TheCheapestPixels',
    author_email='TheCheapestPixels@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='ecs',
    packages=find_packages(exclude=['tests', 'examples']),
    python_requires='>=3.7, <4',
    install_requires=[],
    extras_require={
        'panda3d': ['panda3d'],
        'graphviz': ['graphviz'],
        'bobthewizard': ['crayons'],
    },
)
