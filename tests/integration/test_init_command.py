import shutil
import tempfile
import unittest
import os
import subprocess


class TestInitCommand(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        if os.path.exists('docker-compose.yml'):
            subprocess.run(['docker-compose', 'down'], check=True)
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_something(self):
        self.assertEqual(True, False)