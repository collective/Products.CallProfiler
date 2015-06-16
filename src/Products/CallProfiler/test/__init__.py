import test_profiler
import unittest


def go():
    suite = unittest.TestSuite((
        test_profiler.suite(),
    ))
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    return result.wasSuccessful()
