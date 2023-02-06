from mxmake import utils

import os
import unittest


class TestUtils(unittest.TestCase):
    def test_namespace(self):
        self.assertEqual(utils.NAMESPACE, "mxmake-")

    def test_mxenv_path(self):
        self.assertEqual(utils.mxenv_path(), os.path.join("venv", "bin") + os.path.sep)
        os.environ["MXMAKE_MXENV_PATH"] = "other"
        self.assertEqual(utils.mxenv_path(), "other" + os.path.sep)
        del os.environ["MXMAKE_MXENV_PATH"]

    def test_mxmake_files(self):
        self.assertEqual(utils.mxmake_files(), os.path.join(".mxmake", "files"))
        os.environ["MXMAKE_FILES"] = "other"
        self.assertEqual(utils.mxmake_files(), "other")
        del os.environ["MXMAKE_FILES"]

    def test_ns_name(self):
        self.assertEqual(utils.ns_name("foo"), "mxmake-foo")

    def test_list_value(self):
        self.assertEqual(utils.list_value(""), [])
        self.assertEqual(utils.list_value("a\nb c"), ["a", "b", "c"])