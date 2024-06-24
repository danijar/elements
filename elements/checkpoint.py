import concurrent.futures
import pickle
import time

from . import printing
from . import path
from . import timer


class Saveable:

  """Helper for creating the `save() -> data` and `load(data)` methods that
  make an object saveable."""

  def __init__(self, attrs=None, save=None, load=None):
    assert bool(save) == bool(load)
    assert bool(save) != bool(attrs)
    self._save = save
    self._load = load
    self._attrs = attrs

  def save(self):
    if self._save:
      return self._save()
    if self._attrs:
      return {k: getattr(self, k) for k in self._attrs}

  def load(self, data):
    if self._load:
      return self._load(data)
    if self._attrs:
      for key in self._attrs:
        setattr(self, key, data[key])


class Checkpoint:

  def __init__(self, filename=None, parallel=True):
    self._filename = filename and path.Path(filename)
    self._values = {}
    self._parallel = parallel
    self._promise = None
    if self._parallel:
      self._worker = concurrent.futures.ThreadPoolExecutor(1, 'checkpoint')

  def __setattr__(self, name, value):
    if name in ('exists', 'save', 'load'):
      return super().__setattr__(name, value)
    if name.startswith('_'):
      return super().__setattr__(name, value)
    has_load = hasattr(value, 'load') and callable(value.load)
    has_save = hasattr(value, 'save') and callable(value.save)
    if not (has_load and has_save):
      message = f"Checkpoint entry '{name}' must implement save() and load()."
      raise ValueError(message)
    self._values[name] = value

  def __getattr__(self, name):
    if name.startswith('_'):
      raise AttributeError(name)
    try:
      return self._values[name]
    except AttributeError:
      raise ValueError(name)

  def exists(self, filename=None):
    assert self._filename or filename
    filename = path.Path(filename or self._filename)
    exists = self._filename.exists()
    if exists:
      print('Found existing checkpoint.')
    else:
      print('Did not find any checkpoint.')
    return exists

  def save(self, filename=None, keys=None):
    assert self._filename or filename
    filename = path.Path(filename or self._filename)
    printing.print_(f'Writing checkpoint: {filename}')
    keys = tuple(self._values.keys() if keys is None else keys)
    assert all([not k.startswith('_') for k in keys]), keys
    data = {k: self._values[k].save() for k in keys}
    if self._parallel:
      self._promise and self._promise.result()
      self._promise = self._worker.submit(self._save, filename, data)
    else:
      self._save(filename, data)

  @timer.section('checkpoint_save')
  def _save(self, filename, data):
    data['_timestamp'] = time.time()
    filename.parent.mkdir()
    content = pickle.dumps(data)
    if str(filename).startswith('gs://'):
      filename.write(content, mode='wb')
    else:
      # Write to a temporary file and then atomically rename, so that the file
      # either contains a complete write or not update at all if writing was
      # interrupted.
      tmp = filename.parent / (filename.name + '.tmp')
      tmp.write(content, mode='wb')
      tmp.move(filename)
    print('Wrote checkpoint.')

  @timer.section('checkpoint_load')
  def load(self, filename=None, keys=None):
    assert self._filename or filename
    self._promise and self._promise.result()  # Wait for last save.
    filename = path.Path(filename or self._filename)
    printing.print_(f'Loading checkpoint: {filename}')
    data = pickle.loads(filename.read('rb'))
    keys = tuple(data.keys() if keys is None else keys)
    for key in keys:
      if key.startswith('_'):
        continue
      try:
        self._values[key].load(data[key])
      except Exception:
        print(f"Error loading '{key}' from checkpoint.")
        raise
    age = time.time() - data['_timestamp']
    printing.print_(f'Loaded checkpoint from {age:.0f} seconds ago.')

  def load_or_save(self):
    if self.exists():
      self.load()
    else:
      self.save()
