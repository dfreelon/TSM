import tsm
import unittest
import unittest.mock as mock
import io


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

    @mock.patch('builtins.open')
    def test_calls_open_with_default_args(self, mock_open):
        result = tsm.load_data('path')
        mock_open.assert_called_once_with('path', 'r',
                                          encoding='utf-8', errors='replace')

    @mock.patch('builtins.open')
    def test_calls_open_with_encoding(self, mock_open):
        result = tsm.load_data('path', enc='other')
        mock_open.assert_called_once_with('path', 'r', encoding='other',
                                          errors='replace')

    def test_returns_list_of_lists_from_csv(self):
        fake_file = io.StringIO('one,two,three\n1,2,3\n')
        with mock.patch('builtins.open', return_value=fake_file):
            result = tsm.load_data('path')
        self.assertEqual(result, [['one', 'two', 'three'], ['1', '2', '3']])

    def test_strips_null_bytes_from_csv(self):
        # This doesn't check for the case when a file ends "blah\n\0"
        fake_file = io.StringIO('\0one,t\0wo,three\n1\0,2,3\0\n')
        with mock.patch('builtins.open', return_value=fake_file):
            result = tsm.load_data('path')
        self.assertEqual(result, [['one', 'two', 'three'], ['1', '2', '3']])


if __name__ == '__main__':
    unittest.main()
