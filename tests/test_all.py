import os
import sys
import tempfile
import errno

from helpful import Tempfile, touch, import_recursive

class TestTempFile(object):
    def test_with_context(self):
        """Tempfile() context wrapper"""
        t = Tempfile()
        paths = [t.mkstemp()[1], t.mkstemp()[1], t.mkdtemp(), t.mkdtemp()]
        for path in paths:
            assert os.path.exists(path)
        t.cleanup()
        for path in paths:
            assert not os.path.exists(path)

    def test_without_context(self):
        """Tempfile() without context wrapper"""
        with Tempfile() as t:
            paths = [t.mkstemp()[1], t.mkstemp()[1], t.mkdtemp(), t.mkdtemp()]
            for path in paths:
                assert os.path.exists(path)
        for path in paths:
            assert not os.path.exists(path)


class TestUtils(object):
    def test_touch(self):
        """touch()"""
        path = tempfile.mkstemp()[1] + "_test"
        touch(path)
        assert os.path.exists(path)

    def test_import_recursive(self):
        """import_recursive()"""

        with Tempfile() as tmp:
            root_dir = tmp.mkdtemp()

            paths = [
                "package1/__init__.py",
                "package1/module1.py",
                "package1/package2/__init__.py",
                "package1/package2/module2.py",
                "package1/package2/package3/__init__.py",
                "package1/package2/package3/module3.py"]

            for path in paths:
                path = os.path.join(root_dir, *path.split("/"))
                try: 
                    os.makedirs(os.path.dirname(path))
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                touch(path)

            sys.path.append(root_dir)

            try:
                # recursive import of package
                modules = sorted(import_recursive('package1').keys())
                expected = [
                    'package1', 
                    'package1.module1', 
                    'package1.package2', 
                    'package1.package2.module2',
                    'package1.package2.package3',
                    'package1.package2.package3.module3']
                assert modules == expected

                # recursive import of module
                modules = sorted(import_recursive('package1.module1').keys())
                expected = ['package1.module1']
                assert modules == expected
            finally:
                sys.path.remove(root_dir)
