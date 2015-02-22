import tsm
import unittest
import unittest.mock as mock


class TestLoadData(unittest.TestCase):
    """
    Test the tsm.load_data function, which has two behaviors:
     * given anything but a string, return a deep copy of it
     * given a string, return a list of lists from CV
    """

    def test_deep_copy_happens(self):
        original = [1, 2, [3, 4]]
        loaded = tsm.load_data(original)
        # Test copy is effective:
        self.assertEqual(original, loaded)
        # Test copy is not by reference:
        self.assertIsNot(original, loaded)
        # Test copy is deep:
        self.assertIsNot(original[2], loaded[2])


if __name__ == '__main__':
    unittest.main()
