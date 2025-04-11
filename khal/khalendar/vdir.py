'''
Based off https://github.com/pimutils/python-vdir, which is itself based off
vdirsyncer.
'''

import contextlib
import errno
import os
import tempfile
import uuid
from collections.abc import Iterable
from hashlib import sha1
from typing import IO, Callable, Optional, Protocol

from ..custom_types import PathLike, SupportsRaw


class HasMetaProtocol(Protocol):
    color_type: Callable

    def get_meta(self, key: str) -> str:
        ...

    def set_meta(self, key: str, value: str) -> None:
        ...


class cached_property:
    '''A read-only @property that is only evaluated once. Only usable on class
    instances' methods.
    '''

    def __init__(self, fget, doc=None) -> None:
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__
        self.__doc__ = doc or fget.__doc__
        self.fget = fget

    def __get__(self, obj, cls):
        if obj is None:  # pragma: no cover
            return self
        obj.__dict__[self.__name__] = result = self.fget(obj)
        return result


SAFE_UID_CHARS = ('abcdefghijklmnopqrstuvwxyz'
                  'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                  '0123456789_.-+@')


def _href_safe(uid: str, safe: str=SAFE_UID_CHARS) -> bool:
    return not bool(set(uid) - set(safe))


def _generate_href(uid: Optional[str]=None, safe: str=SAFE_UID_CHARS) -> str:
    if not uid:
        return str(uuid.uuid4().hex)
    elif not _href_safe(uid, safe):
        return sha1(uid.encode()).hexdigest()
    else:
        return uid


def get_etag_from_file(f) -> str:
    '''Get mtime-based etag from a filepath, file-like object or raw file
    descriptor.

    This function will flush/sync the file as much as necessary to obtain a
    correct mtime.
    '''
    close_f = False
    if hasattr(f, 'read'):
        f.flush()
        f = f.fileno()
    elif isinstance(f, str):
        flags = 0
        if os.path.isdir(f):
            flags = os.O_DIRECTORY
        f = os.open(f, flags)
        close_f = True

    # assure that all internal buffers associated with this file are
    # written to disk
    try:
        os.fsync(f)
        stat = os.fstat(f)
    finally:
        if close_f:
            os.close(f)

    mtime = getattr(stat, 'st_mtime_ns', None)
    if mtime is None:
        mtime = stat.st_mtime
    return f'{mtime:.9f}'


class VdirError(IOError):
    def __init__(self, *args, **kwargs) -> None:
        for key, value in kwargs.items():
            if getattr(self, key, object()) not in [None, '']:  # pragma: no cover
                raise TypeError(f'Invalid argument: {key}')
            setattr(self, key, value)

        super().__init__(*args)


class NotFoundError(VdirError):
    pass


class CollectionNotFoundError(VdirError):
    pass


class WrongEtagError(VdirError):
    pass


class AlreadyExistingError(VdirError):
    existing_href: str = ''


class Item:
    def __init__(self, raw: str) -> None:
        assert isinstance(raw, str)
        self.raw = raw

    @cached_property
    def uid(self) -> Optional[str]:
        uid = ''
        lines = iter(self.raw.splitlines())
        for line in lines:
            if line.startswith('UID:'):
                uid += line[4:].strip()
                break

        for line in lines:
            if not line.startswith(' '):
                break
            uid += line[1:]

        return uid or None


@contextlib.contextmanager
def atomic_write(dest, overwrite=False):
    fd, src = tempfile.mkstemp(prefix=os.path.basename(dest), dir=os.path.dirname(dest))
    file = os.fdopen(fd, mode='wb')

    try:
        yield file
    except Exception:
        os.unlink(src)
        raise
    else:
        file.flush()
        file.close()

        if overwrite:
            os.rename(src, dest)
        else:
            os.link(src, dest)
            os.unlink(src)


class VdirBase:
    item_class = Item
    default_mode = 0o750

    def __init__(self, path: str, fileext: str, encoding: str='utf-8') -> None:
        if not os.path.isdir(path):
            raise CollectionNotFoundError(path)
        self.path = path
        self.encoding = encoding
        self.fileext = fileext

    @classmethod
    def discover(cls, path: str, **kwargs) -> Iterable['VdirBase']:
        try:
            collections = os.listdir(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
            return

        for collection in collections:
            collection_path = os.path.join(path, collection)
            if os.path.isdir(collection_path):
                yield cls(path=collection_path, **kwargs)

    @classmethod
    def create(cls, collection_name: PathLike, **kwargs: PathLike) -> dict[str, PathLike]:
        kwargs = dict(kwargs)
        path = kwargs['path']

        pathn = os.path.join(path, collection_name)
        if not os.path.exists(pathn):
            os.makedirs(pathn, mode=cls.default_mode)
        elif not os.path.isdir(pathn):
            raise OSError(f'{repr(pathn)} is not a directory.')

        kwargs['path'] = pathn
        return kwargs

    def _get_filepath(self, href: str) -> str:
        return os.path.join(self.path, href)

    def _get_href(self, uid: Optional[str]) -> str:
        return _generate_href(uid) + self.fileext

    def list(self) -> Iterable[tuple[str, str]]:
        for fname in os.listdir(self.path):
            fpath = os.path.join(self.path, fname)
            if os.path.isfile(fpath) and fname.endswith(self.fileext):
                yield fname, get_etag_from_file(fpath)

    def get(self, href: str) -> tuple[Item, str]:
        fpath = self._get_filepath(href)
        try:
            with open(fpath, 'rb') as f:
                return (
                    Item(f.read().decode(self.encoding)),
                    get_etag_from_file(fpath)
                )
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise NotFoundError(href)
            else:
                raise

    def upload(self, item: SupportsRaw) -> tuple[str, str]:
        if not isinstance(item.raw, str):
            raise TypeError('item.raw must be a unicode string.')

        try:
            href = self._get_href(item.uid)
            _, etag = self._upload_impl(item, href)
        except OSError as e:
            if e.errno in (
                errno.ENAMETOOLONG,  # Unix
                errno.ENOENT  # Windows
            ):
                # random href instead of UID-based
                href = self._get_href(None)
                _, etag = self._upload_impl(item, href)
            else:
                raise
        return href, etag

    def _upload_impl(self, item: SupportsRaw, href: str) -> tuple[str, str]:
        fpath = self._get_filepath(href)
        try:
            f: IO
            with atomic_write(fpath, overwrite=False) as f:
                f.write(item.raw.encode(self.encoding))
                return fpath, get_etag_from_file(f)
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise AlreadyExistingError(existing_href=href)
            else:
                raise

    def update(self, href: str, item: SupportsRaw, etag: str) -> str:
        fpath = self._get_filepath(href)
        if not os.path.exists(fpath):
            raise NotFoundError(item.uid)
        actual_etag = get_etag_from_file(fpath)
        if etag != actual_etag:
            raise WrongEtagError(etag, actual_etag)

        if not isinstance(item.raw, str):
            raise TypeError('item.raw must be a unicode string.')

        with atomic_write(fpath, overwrite=True) as f:
            f.write(item.raw.encode(self.encoding))
            etag = get_etag_from_file(f)

        return etag

    def delete(self, href: str, etag: Optional[str]) -> None:
        fpath = self._get_filepath(href)
        if not os.path.isfile(fpath):
            raise NotFoundError(href)
        actual_etag = get_etag_from_file(fpath)
        if etag != actual_etag:
            raise WrongEtagError(etag, actual_etag)
        os.remove(fpath)

    def get_meta(self, key: str) -> Optional[str]:
        fpath = os.path.join(self.path, key)
        try:
            with open(fpath, 'rb') as f:
                return f.read().decode(self.encoding).strip() or None
        except OSError as e:
            if e.errno == errno.ENOENT:
                return None
            else:
                raise

    def set_meta(self, key: str, value: str) -> None:
        value = value or ''
        assert isinstance(value, str)
        fpath = os.path.join(self.path, key)
        with atomic_write(fpath, overwrite=True) as f:
            f.write(value.encode(self.encoding))


class Color:
    def __init__(self, x: str) -> None:
        if not x:
            raise ValueError('Color is false-ish.')
        if not x.startswith('#'):
            raise ValueError('Color must start with a #.')
        if len(x) != 7:
            raise ValueError('Color must not have shortcuts. '
                             '#ffffff instead of #fff')
        self.raw: str = x.upper()

    @cached_property
    def rgb(self) -> tuple[int, int, int]:
        x = self.raw

        r = x[1:3]
        g = x[3:5]
        b = x[5:8]

        if len(r) == len(g) == len(b) == 2:
            return int(r, 16), int(g, 16), int(b, 16)
        else:
            raise ValueError(f'Unable to parse color value: {self.raw}')


class ColorMixin:
    color_type: type[Color] = Color

    def get_color(self: HasMetaProtocol) -> Optional[str]:
        try:
            return self.color_type(self.get_meta('color'))
        except ValueError:
            return None

    def set_color(self: HasMetaProtocol, value: str) -> None:
        self.set_meta('color', self.color_type(value).raw)


class DisplayNameMixin:
    def get_displayname(self: HasMetaProtocol) -> str:
        return self.get_meta('displayname')

    def set_displayname(self: HasMetaProtocol, value: str) -> None:
        self.set_meta('displayname', value)


class Vdir(VdirBase, ColorMixin, DisplayNameMixin):
    pass
