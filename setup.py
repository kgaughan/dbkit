#!/usr/bin/env python

from __future__ import with_statement

from distutils.core import setup
from buildkit import *


META = get_metadata('dbkit.py')


setup(
    name='dbkit',
    version=META['version'],
    description='DB-API made easier',
    long_description=read('README'),
    url='https://github.com/kgaughan/dbkit/',
    license='MIT',
    py_modules=['dbkit'],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database',
    ],

    author=META['author'],
    author_email=META['email']
)
