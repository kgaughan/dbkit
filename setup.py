#!/usr/bin/env python

import os.path

from setuptools import setup


def read(filename):
    """Read files relative to this file."""
    full_path = os.path.join(os.path.dirname(__file__), filename)
    with open(full_path, "r") as fh:
        return fh.read()


setup(
    name="dbkit",
    version="0.2.5",
    description="DB-API made easier",
    long_description=read("README") + "\n\n" + read("ChangeLog"),
    url="https://github.com/kgaughan/dbkit/",
    license="MIT",
    py_modules=["dbkit"],
    zip_safe=True,
    test_suite="tests.suite",
    classifiers=[
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Database",
    ],
    author="Keith Gaughan",
    author_email="k@stereochro.me",
)
