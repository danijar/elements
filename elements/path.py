import contextlib
import fnmatch
import glob as globlib
import os
import re
import shutil


class Path:

  __slots__ = ('_path',)

  filesystems = []

  def __new__(cls, path):
    if cls is not Path:
      return super().__new__(cls)
    path = str(path)
    for impl, pred in cls.filesystems:
      if pred(path):
        obj = super().__new__(impl)
        obj.__init__(path)
        return obj
    raise NotImplementedError(f'No filesystem supports: {path}')

  def __getnewargs__(self):
    return (self._path,)

  def __init__(self, path):
    assert isinstance(path, str)
    path = re.sub(r'^\./*', '', path)  # Remove leading dot or dot slashes.
    path = re.sub(r'(?<=[^/])/$', '', path)  # Remove single trailing slash.
    path = path or '.'  # Empty path is represented by a dot.
    self._path = path

  def __truediv__(self, part):
    sep = '' if self._path.endswith('/') else '/'
    return type(self)(f'{self._path}{sep}{str(part)}')

  def __repr__(self):
    return f'Path({str(self)})'

  def __fspath__(self):
    return str(self)

  def __eq__(self, other):
    return self._path == other._path

  def __lt__(self, other):
    return self._path < other._path

  def __str__(self):
    return self._path

  @property
  def parent(self):
    if '/' not in self._path:
      return type(self)('.')
    parent = self._path.rsplit('/', 1)[0]
    parent = parent or ('/' if self._path.startswith('/') else '.')
    return type(self)(parent)

  @property
  def name(self):
    if '/' not in self._path:
      return self._path
    return self._path.rsplit('/', 1)[1]

  @property
  def stem(self):
    return self.name.split('.', 1)[0] if '.' in self.name else self.name

  @property
  def suffix(self):
    return ('.' + self.name.split('.', 1)[1]) if '.' in self.name else ''

  def read(self, mode='r'):
    assert mode in 'r rb'.split(), mode
    with self.open(mode) as f:
      return f.read()

  def write(self, content, mode='w'):
    assert mode in 'w a wb ab'.split(), mode
    with self.open(mode) as f:
      f.write(content)

  def open(self, mode='r'):
    raise NotImplementedError

  def absolute(self):
    raise NotImplementedError

  def glob(self, pattern):
    raise NotImplementedError

  def exists(self):
    raise NotImplementedError

  def isfile(self):
    raise NotImplementedError

  def isdir(self):
    raise NotImplementedError

  def mkdir(self):
    raise NotImplementedError

  def remove(self, recursive=False):
    if recursive:
      for path in reversed(list(self.glob('**'))):
        path.remove()
    else:
      raise NotImplementedError

  def copy(self, dest, recursive=False):
    _copy_across_filesystems(self, dest, recursive)

  def move(self, dest, recursive=False):
    self.copy(dest, recursive)
    self.remove(recursive)


class LocalPath(Path):

  __slots__ = ('_path',)

  def __init__(self, path):
    super().__init__(os.path.expanduser(str(path)))

  def open(self, mode='r'):
    return open(str(self), mode=mode)

  def absolute(self):
    return type(self)(os.path.absolute(str(self)))

  def glob(self, pattern):
    for path in globlib.glob(f'{str(self)}/{pattern}', recursive=True):
      yield type(self)(path)

  def exists(self):
    return os.path.exists(str(self))

  def isfile(self):
    return os.path.isfile(str(self))

  def isdir(self):
    return os.path.isdir(str(self))

  def mkdir(self):
    os.makedirs(str(self), exist_ok=True)

  def remove(self, recursive=False):
    if recursive:
      shutil.rmtree(self)
    else:
      if self.isdir():
        os.rmdir(str(self))
      else:
        os.remove(str(self))

  def copy(self, dest, recursive=False):
    dest = Path(dest)
    if isinstance(dest, type(self)):
      shutil.copy2(self, type(self)(dest))
    else:
      _copy_across_filesystems(self, dest, recursive)

  def move(self, dest, recursive=False):
    dest = Path(dest)
    if isinstance(dest, type(self)):
      shutil.move(self, dest)
    else:
      _copy_across_filesystems(self, dest, recursive)
      self.remove(recursive)


class TFPath(Path):

  __slots__ = ('_path',)

  gfile = None

  def __init__(self, path):
    path = str(path)
    if not (path.startswith('/') or '://' in path):
      path = os.path.abspath(os.path.expanduser(path))
    super().__init__(path)
    if not type(self).gfile:
      import tensorflow as tf
      tf.config.set_visible_devices([], 'GPU')
      tf.config.set_visible_devices([], 'TPU')
      type(self).gfile = tf.io.gfile

  def open(self, mode='r'):
    path = str(self)
    if 'a' in mode and path.startswith('/cns/'):
      path += '%r=3.2'
    if mode.startswith('x'):
      if self.exists():
        raise FileExistsError(path)
      mode = mode.replace('x', 'w')
    return self.gfile.GFile(path, mode)

  def absolute(self):
    return self

  def glob(self, pattern):
    for path in self.gfile.glob(f'{str(self)}/{pattern}'):
      yield type(self)(path)

  def exists(self):
    return self.gfile.exists(str(self))

  def isfile(self):
    return self.exists() and not self.isdir()

  def isdir(self):
    return self.gfile.isdir(str(self))

  def mkdir(self):
    self.gfile.makedirs(str(self))

  def remove(self, recursive=False):
    if recursive:
      self.gfile.rmtree(str(self))
    else:
      self.gfile.remove(str(self))

  def copy(self, dest, recursive=False):
    dest = Path(dest)
    if isinstance(dest, type(self)) and not recursive:
      self.gfile.copy(str(self), str(dest), overwrite=True)
    else:
      _copy_across_filesystems(self, dest, recursive)

  def move(self, dest, recursive=False):
    dest = Path(dest)
    if isinstance(dest, type(self)) and not recursive:
      self.gfile.rename(self, str(dest), overwrite=True)
    else:
      _copy_across_filesystems(self, dest, recursive)
      self.remove()


class GCSPath(Path):

  __slots__ = ('_path', '_blob')

  client = None
  buckets = {}

  def __init__(self, path):
    path = str(path)
    super().__init__(path)
    if not type(self).client:
      from google import auth
      from google.cloud import storage
      credentials, project = auth.default()
      type(self).client = storage.Client(project, credentials)
    self._blob = None

  @property
  def blob(self):
    if not self._blob:
      from google.cloud import storage
      path = str(self)[5:]
      name = path.split('/', 1)[1] if '/' in path[5:] else None
      self._blob = name and storage.Blob(name, self.bucket)
    return self._blob

  @property
  def bucket(self):
    import google
    bucket = str(self)[5:].split('/', 1)[0]
    if bucket not in type(self).buckets:
      try:
        type(self).buckets[bucket] = self.client.get_bucket(bucket)
      except google.api_core.exceptions.NotFound:
        return None
    return type(self).buckets[bucket]

  def open(self, mode='r'):
    assert self.blob, 'is a directory'
    if 'w' in mode:
      return self.blob.open(mode, chunk_size=1024 * 1024, ignore_flush=True)
    else:
      return self.blob.open(mode, chunk_size=1024 * 1024)

  def read(self, mode='r'):
    assert self.blob, 'is a directory'
    if mode == 'rb':
      return self.blob.download_as_bytes(self.client)
    elif mode == 'r':
      return self.blob.download_as_text(self.client)
    else:
      raise NotImplementedError(mode)

  def write(self, content, mode='w'):
    assert mode in 'w a wb ab'.split(), mode
    if mode == 'a':
      prefix = self.read('r')
      content = prefix + content
    if mode == 'ab':
      prefix = self.read('rb')
      content = prefix + content
    self.blob.upload_from_string(content)

  def absolute(self):
    return self

  def glob(self, pattern):
    prefix = self.blob.name + '/' if self.blob else ''
    assert prefix == '' or prefix.endswith('/'), prefix
    assert len(pattern) >= 1, pattern
    if '**' in pattern:
      # We have to expand to maximum depth anyways. We have to search one depth
      # deeper to find files which prefixes should be returned as folders.
      pattern2 = prefix + pattern
      pattern2 += '' if pattern2.endswith('*') else '*'
      response = self.bucket.list_blobs(prefix=prefix, match_glob=pattern2)
      filenames = [x.name for x in response]
      folders = [x.rsplit('/', 1)[0] for x in filenames if '/' in x]
      folders = list(set(folders))
    else:
      # Glob for files and iteratively look for folders.
      pattern2 = prefix + pattern
      response = self.bucket.list_blobs(prefix=prefix, match_glob=pattern2)
      filenames = [x.name for x in response]
      parts = pattern.rstrip('/').split('/')
      queue = [(prefix, 0)]
      folders = []
      while queue:
        root, depth = queue.pop(0)
        part = parts[depth]
        if not any(x in part for x in '*[]{}'):  # Workaround for naive glob.
          response = self.bucket.list_blobs(prefix=root + part, delimiter='/')
        else:
          response = self.bucket.list_blobs(
              prefix=root, match_glob=root + part + '/', delimiter='/')
        results = list(response)  # Fetch all pages.
        results = list(response.prefixes)
        for child in results:
          if depth < len(parts) - 1:
            queue.append((child, depth + 1))
          else:
            folders.append(child)
    results = [x.rstrip('/') for x in folders + filenames]
    results = sorted(fnmatch.filter(results, prefix + pattern.rstrip('/')))
    return [type(self)(f'gs://{self.bucket.name}/{x}') for x in results]

  def exists(self):
    if not self.bucket:
      return False
    return self.isfile() or self.isdir()

  def isfile(self):
    if not self.bucket or not self.blob:
      return False
    return self.blob.exists(self.client)

  def isdir(self):
    from google.cloud import storage
    if not self.bucket:
      return False
    if not self.blob:
      return self.bucket.exists()
    if self.isfile():
      return False
    if storage.Blob(self.blob.name + '/', self.bucket).exists():
      return True
    try:
      next(iter(self.glob('*')))
      return True
    except StopIteration:
      return False

  def mkdir(self):
    from google.cloud import storage
    if not self.blob:
      return
    if self.exists():
      return
    folder = storage.Blob(self.blob.name + '/', self.bucket)
    folder.upload_from_string(b'')

  def remove(self, recursive=False):
    if recursive:
      for child in self.glob('**'):
        child.remove()
    else:
      self.blob.delete(self.client)

  def copy(self, dest, recursive=False):
    dest = Path(dest)
    if isinstance(dest, type(self)) and not recursive:
      self.bucket.copy_blob(self.blob, dest.bucket, dest.blob.name)
    else:
      _copy_across_filesystems(self, dest, recursive)

  def move(self, dest, recursive=False):
    dest = Path(dest)
    if isinstance(dest, type(self)) and not recursive:
      if self.bucket.name == dest.bucket.name:
        self.bucket.rename_blob(self.blob, dest.blob.name)
      else:
        self.bucket.copy_blob(self.blob, dest.bucket, dest.blob.name)
    else:
      _copy_across_filesystems(self, dest, recursive)
      self.remove()

  def _bucket(self, path):
    if not str(path).startswith('gs://'):
      return None
    return type(self)(path).bucket.name


def _copy_across_filesystems(source, dest, recursive):
  assert isinstance(source, Path), type(source)
  assert isinstance(dest, Path), type(dest)
  if not recursive:
    assert source.isfile()
    dest.write(source.read('rb'), 'wb')
    return
  if dest.exists():
    dest = dest / source.name
  dest.mkdir()
  prefix = str(source)
  for s in source.glob('**'):
    assert str(s).startswith(prefix), (source, s)
    d = dest / str(s)[len(prefix):].lstrip('/')
    if s.isdir():
      d.mkdir()
    else:
      d.write(s.read('rb'), 'wb')


Path.filesystems = [
    (GCSPath, lambda path: path.startswith('gs://')),
    (TFPath, lambda path: path.startswith('/cns/')),
    (LocalPath, lambda path: True),
]
