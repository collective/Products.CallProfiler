import unittest

import test_profiler

def go():
    suite = unittest.TestSuite((
        test_profiler.suite(),
    ))
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    return result.wasSuccessful()

