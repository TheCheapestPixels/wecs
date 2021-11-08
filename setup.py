"""A setuptools based setup module.
"""

from setuptools import setup, find_packages
from os import path


here = path.abspath(path.dirname(__file__))
with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name='wecs',
    version='0.2.0a',
    description='An ECS (entity component system)',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/TheCheapestPixels/wecs',
    author='TheCheapestPixels',
    author_email='TheCheapestPixels@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
    ],
    keywords='ecs panda3d',
    packages=find_packages(exclude=['tests', 'examples']),
    python_requires='>=3.7, <4',
    install_requires=[],
    extras_require={
        'panda3d': ['panda3d'],
        'graphviz': ['graphviz'],
        'bobthewizard': ['crayons'],
    },
)
