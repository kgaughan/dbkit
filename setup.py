#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
	name='dbkit',
	version='0.1.0',
	description='DB-API made easier',
	packages=find_packages(exclude='tests'),
	zip_safe=True,
	install_requires=[],

	author='Keith Gaughan',
	author_email='k@stereochro.me')
