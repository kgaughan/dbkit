#!/usr/bin/env python

from distutils.core import setup
import dbkit

setup(
    name='dbkit',
    version=dbkit.__version__,
    description='DB-API made easier',
    long_description=open('README').read(),
    license=open('LICENSE').read(),
    url='https://github.com/kgaughan/dbkit/',
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
    author_email=dbkit.__email__,
    maintainer=dbkit.__author__,
    maintainer_email=dbkit.__email__
)
