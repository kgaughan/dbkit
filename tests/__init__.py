import fnmatch
import glob
import os
import os.path
import unittest


def suite():
    """
    Discover the tests in a manner that works on Python pre-2.7.
    """
    here = os.path.dirname(__file__)
    modules = [
        'tests.' + os.path.splitext(fn)[0]
        for fn in fnmatch.filter(os.listdir(here), 'test_*.py')
    ]
    return unittest.defaultTestLoader.loadTestsFromNames(modules)
