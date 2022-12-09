#!/usr/bin/python3

import os
import tempfile
import unittest
from freespacer_app import make_free_space, argument_parser


class apptest(unittest.TestCase):

    @staticmethod
    def test_arg_parser():
        argument_parser()

    def test_tar_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'test.raw')
            with open(test_file, 'w') as f:
                f.write(test_file)
            self.assertEquals([test_file], make_free_space(tmpdir, 0))
            self.assertFalse(os.path.exists(test_file))
            with open(test_file, 'w') as f:
                f.write(test_file)
            self.assertEquals([], make_free_space(tmpdir, 100))
            self.assertTrue(os.path.exists(test_file))


if __name__ == '__main__':
    unittest.main()
