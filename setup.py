#!/usr/bin/python
# ex:set fileencoding=utf-8:

from setuptools import setup

CLASSIFIERS = []

VERSION = ("0","1")
__version__ = '.'.join(VERSION)
__docformat__ = 'restructuredtext'

setup(
    name='paragliding',
    version=__version__,
    packages=[],
    install_requires = [
        'pytz',
        'numpy',
    ],
    include_package_data=True,
    zip_safe=False,
)
