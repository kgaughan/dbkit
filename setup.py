#!/usr/bin/env python

from __future__ import with_statement

from os import path
from distutils.core import setup
import dbkit

def read_package_file(package_path):
    """Reads a file from within the package. Genius, no?"""
    with open(path.join(path.dirname(__file__), package_path)) as hdl:
        return hdl.read()

setup(
    name='dbkit',
    version=dbkit.__version__,
    description='DB-API made easier',
    long_description=read_package_file('README'),
    url='https://github.com/kgaughan/dbkit/',
    py_modules=['dbkit'],

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database',
    ],

    author='Keith Gaughan',
    author_email='k@stereochro.me')

# vim:set et ai:
