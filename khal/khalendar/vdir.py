'''
Based off https://github.com/pimutils/python-vdir, which is itself based off
vdirsyncer.
'''

import os
import errno
import uuid

from atomicwrites import atomic_write


class cached_property:
    '''A read-only @property that is only evaluated once. Only usable on class
    instances' methods.
    '''
    def __init__(self, fget, doc=None):
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__
        self.__doc__ = doc or fget.__doc__
        self.fget = fget

    def __get__(self, obj, cls):
        if obj is None:  # pragma: no cover
            return self
        obj.__dict__[self.__name__] = result = self.fget(obj)
        return result


def to_unicode(x, encoding='ascii'):
    if not isinstance(x, str):
        return x.decode(encoding)
    return x


def to_bytes(x, encoding='ascii'):
    if not isinstance(x, bytes):
        return x.encode(encoding)
    return x


SAFE_UID_CHARS = ('abcdefghijklmnopqrstuvwxyz'
                  'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                  '0123456789_.-+')


def _href_safe(uid, safe=SAFE_UID_CHARS):
    return not bool(set(uid) - set(safe))


def _generate_href(uid=None, safe=SAFE_UID_CHARS):
    if not uid or not _href_safe(uid, safe):
        return to_unicode(uuid.uuid4().hex)
    else:
        return uid


def get_etag_from_file(f):
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
    return '{:.9f}'.format(mtime)


class VdirError(IOError):
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            if getattr(self, key, object()) is not None:  # pragma: no cover
                raise TypeError('Invalid argument: {}'.format(key))
            setattr(self, key, value)

        super(VdirError, self).__init__(*args)


class NotFoundError(VdirError):
    pass


class CollectionNotFoundError(VdirError):
    pass


class WrongEtagError(VdirError):
    pass


class AlreadyExistingError(VdirError):
    existing_href = None


class Item:
    def __init__(self, raw):
        assert isinstance(raw, str)
        self.raw = raw

    @cached_property
    def uid(self):
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


def _normalize_meta_value(value):
    return to_unicode(value or '').strip()


class VdirBase:
    item_class = Item
    default_mode = 0o750

    def __init__(self, path, fileext, encoding='utf-8'):
        if not os.path.isdir(path):
            raise CollectionNotFoundError(path)
        self.path = path
        self.encoding = encoding
        self.fileext = fileext

    @classmethod
    def discover(cls, path, **kwargs):
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
    def create(cls, collection_name, **kwargs):
        kwargs = dict(kwargs)
        path = kwargs['path']

        path = os.path.join(path, collection_name)
        if not os.path.exists(path):
            os.makedirs(path, mode=cls.default_mode)
        elif not os.path.isdir(path):
            raise IOError('{} is not a directory.'.format(repr(path)))

        kwargs['path'] = path
        return kwargs

    def _get_filepath(self, href):
        return os.path.join(self.path, href)

    def _get_href(self, uid):
        return _generate_href(uid) + self.fileext

    def list(self):
        for fname in os.listdir(self.path):
            fpath = os.path.join(self.path, fname)
            if os.path.isfile(fpath) and fname.endswith(self.fileext):
                yield fname, get_etag_from_file(fpath)

    def get(self, href):
        fpath = self._get_filepath(href)
        try:
            with open(fpath, 'rb') as f:
                return (Item(f.read().decode(self.encoding)),
                        get_etag_from_file(fpath))
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise NotFoundError(href)
            else:
                raise

    def upload(self, item):
        if not isinstance(item.raw, str):
            raise TypeError('item.raw must be a unicode string.')

        try:
            href = self._get_href(item.uid)
            fpath, etag = self._upload_impl(item, href)
        except OSError as e:
            if e.errno in (
                errno.ENAMETOOLONG,  # Unix
                errno.ENOENT  # Windows
            ):
                # random href instead of UID-based
                href = self._get_href(None)
                fpath, etag = self._upload_impl(item, href)
            else:
                raise

        return href, etag

    def _upload_impl(self, item, href):
        fpath = self._get_filepath(href)
        try:
            with atomic_write(fpath, mode='wb', overwrite=False) as f:
                f.write(item.raw.encode(self.encoding))
                return fpath, get_etag_from_file(f)
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise AlreadyExistingError(existing_href=href)
            else:
                raise

    def update(self, href, item, etag):
        fpath = self._get_filepath(href)
        if not os.path.exists(fpath):
            raise NotFoundError(item.uid)
        actual_etag = get_etag_from_file(fpath)
        if etag != actual_etag:
            raise WrongEtagError(etag, actual_etag)

        if not isinstance(item.raw, str):
            raise TypeError('item.raw must be a unicode string.')

        with atomic_write(fpath, mode='wb', overwrite=True) as f:
            f.write(item.raw.encode(self.encoding))
            etag = get_etag_from_file(f)

        return etag

    def delete(self, href, etag):
        fpath = self._get_filepath(href)
        if not os.path.isfile(fpath):
            raise NotFoundError(href)
        actual_etag = get_etag_from_file(fpath)
        if etag != actual_etag:
            raise WrongEtagError(etag, actual_etag)
        os.remove(fpath)

    def get_meta(self, key):
        fpath = os.path.join(self.path, key)
        try:
            with open(fpath, 'rb') as f:
                return f.read().decode(self.encoding) or None
        except IOError as e:
            if e.errno == errno.ENOENT:
                return None
            else:
                raise

    def set_meta(self, key, value):
        value = value or ''
        assert isinstance(value, str)
        fpath = os.path.join(self.path, key)
        with atomic_write(fpath, mode='wb', overwrite=True) as f:
            f.write(value.encode(self.encoding))


class Color:
    def __init__(self, x):
        if not x:
            raise ValueError('Color is false-ish.')
        if not x.startswith('#'):
            raise ValueError('Color must start with a #.')
        if len(x) != 7:
            raise ValueError('Color must not have shortcuts. '
                             '#ffffff instead of #fff')
        self.raw = x.upper()

    @cached_property
    def rgb(self):
        x = self.raw

        r = x[1:3]
        g = x[3:5]
        b = x[5:8]

        if len(r) == len(g) == len(b) == 2:
            return int(r, 16), int(g, 16), int(b, 16)
        else:
            raise ValueError('Unable to parse color value: {}'
                             .format(self.value))


class ColorMixin:
    color_type = Color

    def get_color(self):
        try:
            return self.color_type(self.get_meta('color'))
        except ValueError:
            return None

    def set_color(self, value):
        self.set_meta('color', self.color_type(value).raw)


class DisplayNameMixin:
    def get_displayname(self):
        return self.get_meta('displayname')

    def set_displayname(self, value):
        self.set_meta('displayname', value)


class Vdir(VdirBase, ColorMixin, DisplayNameMixin):
    pass
