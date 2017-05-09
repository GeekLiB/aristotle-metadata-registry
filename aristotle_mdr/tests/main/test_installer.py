from django.test import TestCase

from aristotle_mdr.install import easy

class InstallerTest(TestCase):
    def test_methods(self):
        easy.download_example_mdr()
