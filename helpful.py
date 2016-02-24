import six
import os
import shutil
import warnings
import tempfile
import importlib
import pkgutil
import inspect
import string
import random
import sys
import itertools
import datetime

from decimal import Decimal
from collections import OrderedDict, Iterable

if six.PY2: # pragma: nocover
    text_type = unicode
    string_types = (str, unicode)
else: # pragma: nocover
    string_types = (str, )
    text_type = str

NoneType = type(None)

###########################################################
# Mixins
###########################################################

class ClassDictMixin():
    """
    Dict which can be accessed via class attributes
    Thanks http://www.goodcode.io/blog/python-dict-object/
    """
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def copy(self):
        # XXX: needs UT
        return self.__class__(**self)

def unique_iter(seq):
    """
    See http://www.peterbe.com/plog/uniqifiers-benchmark
    Originally f8 written by Dave Kirby
    """
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]



def flatteniter(iter_lst):
    """
    >>> flatteniter([[1,2,3], [4,5,6]])
    [1, 2, 3, 4, 5, 6]
    """
    return list(itertools.chain(*iter_lst))


class HashableDictMixin(object):
    def __hash__(self):
        """
        This /should/ allow object to be hashable, for use in a set
        XXX: Needs UT

        Thanks Raymond @ http://stackoverflow.com/a/16162138/1267398
        """
        return hash((frozenset(self), frozenset(self.values())))


###########################################################
# Hashable dict
###########################################################


class ClassDict(ClassDictMixin, dict):
    """
    >>> d = ClassDict(hello="world")
    >>> d.hello
    'world'
    >>> d.get('hello')
    'world'
    >>> d.hello = 'wtf'
    >>> d.hello
    'wtf'
    >>> d['hello']
    'wtf'
    >>> d.world
    Traceback (most recent call last):
    AttributeError:
    >>> del d.hello
    >>> del d.world
    Traceback (most recent call last):
    AttributeError:
    >>> d.hello = 1
    >>> b = d.copy()
    >>> b.hello = 2
    >>> b.hello == d.hello
    False
    """


class HashableDict(HashableDictMixin, dict):
    """
    >>> hash(HashableDict(a=1, b=2)) is not None
    True
    """


class HashableOrderedDict(HashableDictMixin, OrderedDict):
    """
    >>> hash(HashableOrderedDict(a=1, b=2)) is not None
    True
    """

def ensure_class(obj):
    """
    Ensure object is a class

    >>> ensure_class(object)
    >>> ensure_class(object())
    Traceback (most recent call last):
    TypeError:
    >>> ensure_class(1)
    Traceback (most recent call last):
    TypeError:
    """
    if not inspect.isclass(obj):
        raise TypeError("Expected class, got {}".format(obj))


def iter_ensure_class(iterable):
    """
    Ensure every item in iterable is a class

    >>> iter_ensure_class([object, object])
    >>> iter_ensure_class([object, object()])
    Traceback (most recent call last):
    TypeError:
    """
    ensure_instance(iterable, Iterable)
    [ ensure_class(item) for item in iterable ]

def ensure_subclass(value, types):
    """
    Ensure value is a subclass of types

    >>> class Hello(object): pass
    >>> ensure_subclass(Hello, Hello)
    >>> ensure_subclass(object, Hello)
    Traceback (most recent call last):
    TypeError:
    """
    ensure_class(value)
    if not issubclass(value, types):
        raise TypeError(
            "expected subclass of {}, not {}".format(
                types, value))

def ensure_instance(value, types):
    """
    Ensure value is an instance of a certain type

    >>> ensure_instance(1, [str])
    Traceback (most recent call last):
    TypeError:

    >>> ensure_instance(1, str)
    Traceback (most recent call last):
    TypeError:

    >>> ensure_instance(1, int)
    >>> ensure_instance(1, (int, str))

    :attr types: Type of list of types
    """
    if not isinstance(value, types):
        raise TypeError(
            "expected instance of {}, got {}".format(
                types, value))


def iter_ensure_instance(iterable, types):
    """
    Iterate over object and check each item type

    >>> iter_ensure_instance([1,2,3], [str])
    Traceback (most recent call last):
    TypeError:
    >>> iter_ensure_instance([1,2,3], int)
    >>> iter_ensure_instance(1, int)
    Traceback (most recent call last):
    TypeError:
    """
    ensure_instance(iterable, Iterable)
    [ ensure_instance(item, types) for item in iterable ]

def touch(path, times=None):
    """
    Implements unix utility `touch`
    XXX: Needs UT

    :attr fname: File path
    :attr times: See `os.utime()` for args
                 https://docs.python.org/3.4/library/os.html#os.utime
    """
    with open(path, 'a'):
        os.utime(path, times)


def import_recursive(path):
    """
    Recursively import all modules and packages
    Thanks http://stackoverflow.com/a/25562415/1267398
    XXX: Needs UT

    :attr path: Path to package/module
    """
    results = {}
    obj = importlib.import_module(path)
    results[path] = obj
    path = getattr(obj, '__path__', os.path.dirname(obj.__file__))
    for loader, name, is_pkg in pkgutil.walk_packages(path):
        full_name = obj.__name__ + '.' + name
        results[full_name] = importlib.import_module(full_name)
        if is_pkg:
            results.update(import_recursive(full_name))
    return results


def extend_instance(instance, *bases, **kwargs):
    """
    Apply subclass (mixin) to a class object or its instance

    By default, the mixin is placed at the start of bases
    to ensure its called first as per MRO. If you wish to
    have it injected last, which is useful for monkeypatching,
    then you can specify 'last=True'. See here:
    http://stackoverflow.com/a/10018792/1267398

    :attr cls: Target object
    :type cls: Class instance

    :attr bases: List of new bases to subclass with

    :attr last: Inject new bases after existing bases
    :type last: bool

    >>> class A(object): pass
    >>> class B(object): pass
    >>> a = A()
    >>> b = B()
    >>> isinstance(b, A)
    False
    >>> extend_instance(b, A)
    >>> isinstance(b, A)
    True
    """
    last = kwargs.get('last', False)
    bases = tuple(bases)
    for base in bases:
        assert inspect.isclass(base), "bases must be classes"
    assert not inspect.isclass(instance)
    base_cls = instance.__class__
    base_cls_name = instance.__class__.__name__
    new_bases = (base_cls,)+bases if last else bases+(base_cls,)
    new_cls = type(base_cls_name, tuple(new_bases), {})
    setattr(instance, '__class__', new_cls)


def add_bases(cls, *bases):
    """
    Add bases to class

    >>> class Base(object): pass
    >>> class A(Base): pass
    >>> class B(Base): pass
    >>> issubclass(A, B)
    False
    >>> add_bases(A, B)
    >>> issubclass(A, B)
    True
    """
    assert inspect.isclass(cls), "Expected class object"
    for mixin in bases:
        assert inspect.isclass(mixin), "Expected class object for bases"
    new_bases = (bases + cls.__bases__)
    cls.__bases__ = new_bases


def subclass(cls, *bases, **kwargs):
    """
    Add bases to class (late subclassing)

    Annoyingly we cannot yet modify __bases__ of an existing
    class, instead we must create another subclass, see here;
    http://bugs.python.org/issue672115

    >>> class A(object): pass
    >>> class B(object): pass
    >>> class C(object): pass
    >>> issubclass(B, A)
    False
    >>> D = subclass(B, A)
    >>> issubclass(D, A)
    True
    >>> issubclass(D, B)
    True
    """
    last = kwargs.get('last', False)
    bases = tuple(bases)
    for base in bases:
        assert inspect.isclass(base), "bases must be classes"
    new_bases = (cls,)+bases if last else bases+(cls,)
    new_cls = type(cls.__name__, tuple(new_bases), {})
    return new_cls


def import_from_path(path):
    """
    Imports a package, module or attribute from path
    Thanks http://stackoverflow.com/a/14050282/1267398

    >>> import_from_path('os.path')
    <module 'posixpath' ...
    >>> import_from_path('os.path.basename')
    <function basename at ...
    >>> import_from_path('os')
    <module 'os' from ...
    >>> import_from_path('getrektcunt')
    Traceback (most recent call last):
    ImportError:
    >>> import_from_path('os.dummyfunc')
    Traceback (most recent call last):
    ImportError:
    >>> import_from_path('os.dummyfunc.dummylol')
    Traceback (most recent call last):
    ImportError:
    """
    try:
        return importlib.import_module(path)
    except ImportError:
        if '.' not in path:
            raise
        module_name, attr_name = path.rsplit('.', 1)
        if not does_module_exist(module_name):
            raise ImportError("No object found at '{}'".format(path))
        mod = importlib.import_module(module_name)

        if not hasattr(mod, attr_name):
            raise ImportError("No object found at '{}'".format(path))
        return getattr(mod, attr_name)


def does_module_exist(path):
    """
    Check if Python module exists at path

    >>> does_module_exist('os.path')
    True
    >>> does_module_exist('dummy.app')
    False
    """
    try:
        importlib.import_module(path)
        return True
    except ImportError:
        return False


def sort_dict_by_key(obj):
    """
    Sort dict by its keys

    >>> sort_dict_by_key(dict(c=1, b=2, a=3, d=4))
    OrderedDict([('a', 3), ('b', 2), ('c', 1), ('d', 4)])
    """
    sort_func = lambda x: x[0]
    return OrderedDict(sorted(obj.items(), key=sort_func))


def generate_random_token(length=32):
    """
    Generate random secure token

    >>> len(generate_random_token())
    32
    >>> len(generate_random_token(6))
    6
    """
    chars = (string.ascii_lowercase + string.ascii_uppercase + string.digits)
    return ''.join(random.choice(chars) for _ in range(length))


def default(*args, **kwargs):
    """
    Return first argument which is "truthy"

    >>> default(None, None, 1)
    1
    >>> default(None, None, 123)
    123
    >>> print(default(None, None))
    None
    """
    default = kwargs.get('default', None)
    for arg in args:
        if arg:
            return arg
    return default


def urljoin(*args):
    """
    Joins given arguments into a url, removing duplicate slashes
    Thanks http://stackoverflow.com/a/11326230/1267398

    >>> urljoin('/lol', '///lol', '/lol//')
    '/lol/lol/lol'
    """
    value = "/".join(map(lambda x: str(x).strip('/'), args))
    return "/{}".format(value)


def is_hex(value):
    """
    Check if value is hex

    >>> is_hex('abab')
    True
    >>> is_hex('gg')
    False
    """
    try:
        int(value, 16)
    except ValueError:
        return False
    else:
        return True


def is_int(value):
    """
    Check if value is an int

    :type value: int, str, bytes, float, Decimal

    >>> is_int(123), is_int('123'), is_int(Decimal('10'))
    (True, True, True)
    >>> is_int(1.1), is_int('1.1'), is_int(Decimal('10.1'))
    (False, False, False)
    >>> is_int(object)
    Traceback (most recent call last):
    TypeError:
    """
    ensure_instance(value, (int, str, bytes, float, Decimal))
    if isinstance(value, int):
        return True
    elif isinstance(value, float):
        return False
    elif isinstance(value, Decimal):
        return str(value).isdigit()
    elif isinstance(value, (str, bytes)):
        return value.isdigit()
    raise ValueError() # pragma: nocover


def padded_split(value, sep, maxsplit=None, pad=None):
    """
    Modified split() to include padding
    See http://code.activestate.com/lists/python-ideas/3366/

    :attr value: see str.split()
    :attr sep: see str.split()
    :attr maxsplit: see str.split()
    :attr pad: Value to use for padding maxsplit

    >>> padded_split('text/html', ';', 1)
    ['text/html', None]
    >>> padded_split('text/html;q=1', ';', 1)
    ['text/html', 'q=1']
    >>> padded_split('text/html;a=1;b=2', ';', 1)
    ['text/html', 'a=1;b=2']
    >>> padded_split('text/html', ';', 1, True)
    ['text/html', True]
    >>> padded_split('text/html;a=1;b=2', ';', 2)
    ['text/html', 'a=1', 'b=2']
    >>> padded_split('text/html;a=1', ';', 2)
    ['text/html', 'a=1', None]
    """
    result = value.split(sep, maxsplit)
    if maxsplit is not None:
        result.extend(
            [pad] * (1+maxsplit-len(result)))
    return result


def coerce_to_bytes(x, charset=sys.getdefaultencoding(), errors='strict'):
    """
    Coerce value to bytes

    >>> a = coerce_to_bytes('hello')
    >>> assert isinstance(a, bytes)
    >>> a = coerce_to_bytes(b'hello')
    >>> assert isinstance(a, bytes)
    >>> a = coerce_to_bytes(None)
    >>> assert a is None
    >>> coerce_to_bytes(object())
    Traceback (most recent call last):
    ...
    TypeError: Cannot coerce to bytes
    """
    PY2 = sys.version_info[0] == 2
    if PY2: # pragma: nocover
        if x is None:
            return None
        if isinstance(x, (bytes, bytearray, buffer)):
            return bytes(x)
        if isinstance(x, unicode):
            return x.encode(charset, errors)
        raise TypeError('Cannot coerce to bytes')

    else: # pragma: nocover
        if x is None:
            return None
        if isinstance(x, (bytes, bytearray, memoryview)):
            return bytes(x)
        if isinstance(x, str):
            return x.encode(charset, errors)
        raise TypeError('Cannot coerce to bytes')


def get_exception():
    """
    Workaround for the missing "as" keyword in py3k.
    XXX: needs UT
    """
    return sys.exc_info()[1]


def makelist(data):
    """
    Thanks bottle
    XXX: needs UT
    """
    if isinstance(data, (list, set, tuple)):
        return list(data)
    elif data:
        return [data]
    else:
        return []


def random_date_between(start_date, end_date):
    """Return random date between start/end"""
    assert isinstance(start_date, datetime.date)
    delta_secs = int((end_date - start_date).total_seconds())
    delta = datetime.timedelta(seconds=random.randint(0, delta_secs))
    return (start_date + delta)


def datetime_to_epoch(dt):
    return (dt - datetime.datetime(1970, 1, 1)).total_seconds()


class Tempfile(object):
    """
    Tempfile wrapper with cleanup support

    XXX: Needs UT
    """

    def __init__(self):
        self.paths = []

    def mkstemp(self, *args, **kwargs):
        path = tempfile.mkstemp(*args, **kwargs)
        self.paths.append(path)
        return path

    def mkdtemp(self, *args, **kwargs):
        path = tempfile.mkdtemp(*args, **kwargs)
        self.paths.append(path)
        return path

    def cleanup(self):
        """Remove any created temp paths"""
        for path in self.paths:
            if isinstance(path, tuple):
                os.close(path[0])
                os.unlink(path[1])
            else:
                shutil.rmtree(path)
        self.paths = []

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.cleanup()

