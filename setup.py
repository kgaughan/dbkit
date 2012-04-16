#!/usr/bin/env python

from __future__ import with_statement

from os import path
from setuptools import setup, find_packages

with open(path.join(path.dirname(__file__), 'README.rst')) as fh:
    readme = fh.read()

setup(
    name='dbkit',
    version='0.1.0',
    description='DB-API made easier',
    long_description=readme,
    url='https://github.com/kgaughan/dbkit/',
    packages=find_packages(exclude='tests'),
    zip_safe=True,
    install_requires=[],

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
