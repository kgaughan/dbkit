#!/usr/bin/env python

from __future__ import with_statement

from os import path
from distutils.core import setup
import dbkit

with open(path.join(path.dirname(__file__), 'README.rst')) as fh:
    readme = fh.read()

setup(
    name='dbkit',
    version=dbkit.__version__,
    description='DB-API made easier',
    long_description=readme,
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
