import unittest


def suite():
    modules = ['tests.test_dbkit', 'tests.test_pool']
    return unittest.defaultTestLoader.loadTestsFromNames(modules)
