from unittest import TestLoader, TextTestRunner

def run_tests():
    loader = TestLoader()
    suite = loader.discover('tests', pattern='*.py')
    runner = TextTestRunner(verbosity=2)
    runner.run(suite)

def run_model_tests():
    loader = TestLoader()
    suite = loader.discover('tests/model', pattern='*.py')
    runner = TextTestRunner(verbosity=2)
    runner.run(suite)
