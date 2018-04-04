from setuptools import setup, find_packages

from io import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

URL = 'https://github.com/tshirtman/oscpy'

setup(
    name='oscpy',
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.1.0',
    description='A modern and efficient OSC Client/Server implementation',
    long_description=long_description,
    url=URL,
    author='Gabriel Pettier',
    author_email='gabriel.pettier@gmail.com',  # Optional
    classifiers=[  # Optional
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Networking',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='OSC network udp',  # Optional

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[],
    extras_require={
        'dev': ['pytest', 'wheel']
    },
    package_data={},
    data_files=[],
    entry_points={},

    project_urls={
        'Bug Reports': URL + '/issues',
        'Source': URL,
    },
)
