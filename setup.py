"""See README.md for package documentation."""

from setuptools import setup, find_packages

from io import open
from os import path

from oscpy import __version__

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

URL = 'https://github.com/kivy/oscpy'

setup(
    name='oscpy',
    # https://packaging.python.org/en/latest/single_source_version.html
    version=__version__,
    description=(
        'A Python implementation of Open Sound Control (OSC) network protocol'
    ),
    long_description=long_description,
    long_description_content_type='text/markdown',
    url=URL,
    author='Gabriel Pettier',
    author_email='gabriel@kivy.org',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Networking',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    keywords='OSC network udp',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[],
    extras_require={
        'dev': ['pytest>=3.8', 'wheel', 'pytest-cov', 'pycodestyle'],
        'ci': ['coveralls', 'pytest-rerunfailures'],
    },
    package_data={},
    data_files=[],
    entry_points={
        'console_scripts': ['oscli=oscpy.cli:main'],
    },

    project_urls={
        'Bug Reports': URL + '/issues',
        'Source': URL,
    },
)
