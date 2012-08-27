#!/usr/bin/env python

from setuptools import setup
import dbkit

setup(
    name='dbkit',
    version=dbkit.__version__,
    description='DB-API made easier',
    long_description=open('README').read(),
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

    author=dbkit.__author__,
    author_email=dbkit.__email__
)
