import inspect
import pickle

from . import path as pathlib
from . import printing
from . import timer
from . import utils


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

  """
  Checkpoints are stored in this file structure:

  directory/
    latest  # Contains folder name of latest complete save.
    <timestamp>-<step>/
      foo.pkl
      bar.pkl
      baz-0.pkl
      baz-1.pkl
      baz-2.pkl
      done  # Empty file marking the save as complete.
    ...
  """

  def __init__(self, directory=None, keep=1, step=None, write=True):
    assert keep is None or keep >= 1
    self._directory = directory and pathlib.Path(directory)
    self._keep = keep
    self._step = step
    self._write = write
    self._saveables = {}

  def __setattr__(self, name, value):
    if name.startswith('_'):
      return super().__setattr__(name, value)
    has_load = hasattr(value, 'load') and callable(value.load)
    has_save = hasattr(value, 'save') and callable(value.save)
    if not (has_load and has_save):
      raise ValueError(
          f"Checkpointed object '{name}' must implement save() and load().")
    self._saveables[name] = value

  def __getattr__(self, name):
    if name.startswith('_'):
      raise AttributeError(name)
    try:
      return self._saveables[name]
    except AttributeError:
      raise ValueError(name)

  def exists(self, path=None):
    assert self._directory or path
    if path:
      result = exists(path)
    else:
      result = bool(self.latest())
    if result:
      print('Found existing checkpoint.')
    else:
      print('Did not find any checkpoint.')
    return result

  @timer.section('checkpoint_save')
  def save(self, path=None, keys=None):
    assert self._directory or path
    if keys is None:
      savefns = {k: v.save for k, v in self._saveables.items()}
    else:
      assert all([not k.startswith('_') for k in keys]), keys
      savefns = {k: self._saveables[k].save for k in keys}
    if path:
      folder = None
    else:
      folder = utils.timestamp(millis=True)
      if self._step is not None:
        folder += f'-{int(self._step):012d}'
      path = self._directory / folder
    printing.print_(f'Saving checkpoint: {path}')
    save(path, savefns, self._write)
    if folder and self._write:
      (self._directory / 'latest').write_text(folder)
      self._cleanup()
    print('Saved checkpoint.')

  @timer.section('checkpoint_load')
  def load(self, path=None, keys=None):
    assert self._directory or path
    if keys is None:
      loadfns = {k: v.load for k, v in self._saveables.items()}
    else:
      assert all([not k.startswith('_') for k in keys]), keys
      loadfns = {k: self._saveables[k].load for k in keys}
    if not path:
      path = self.latest()
      assert path
    printing.print_(f'Loading checkpoint: {path}')
    load(path, loadfns)
    print('Loaded checkpoint.')

  def load_or_save(self):
    if self.exists():
      self.load()
    else:
      self.save()

  def latest(self):
    filename = (self._directory / 'latest')
    if not filename.exists():
      return None
    return self._directory / filename.read_text().strip('\n')

  def _cleanup(self):
    if not self._keep:
      return
    folders = self._directory.glob('*')
    folders = [x for x in folders if x.name != 'latest']
    old = sorted(folders)[:-self._keep]
    for folder in old:
      folder.remove(recursive=True)


def exists(path):
  path = pathlib.Path(path)
  return (path / 'done').exists()


def save(path, savefns, write=True):
  path = pathlib.Path(path)
  assert not exists(path), path
  write and path.mkdir(parents=True)
  for name, savefn in savefns.items():
    try:
      data = savefn()
      if inspect.isgenerator(data):
        for i, shard in enumerate(data):
          assert i < 1e5, i
          if write:  # Iterate even if we're not writing.
            with timer.section('checkpoint_pickle'):
              buffer = pickle.dumps(shard)
            with timer.section('checkpoint_write'):
              (path / f'{name}-{i:04d}.pkl').write_bytes(buffer)
      else:
        if write:
          with timer.section('checkpoint_pickle'):
            buffer = pickle.dumps(data)
          with timer.section('checkpoint_write'):
            (path / f'{name}.pkl').write_bytes(buffer)
    except Exception:
      print(f"Error save '{name}' to checkpoint.")
      raise
  write and (path / 'done').write_bytes(b'')


def load(path, loadfns):
  path = pathlib.Path(path)
  assert exists(path), path
  filenames = set(path.glob('*'))
  for name, loadfn in loadfns.items():
    try:
      if (path / f'{name}.pkl') in filenames:
        buffer = (path / f'{name}.pkl').read_bytes()
        data = pickle.loads(buffer)
        loadfn(data)
      elif (path / f'{name}-0000.pkl') in filenames:
        shards = [x for x in filenames if x.name.startswith(f'{name}-')]
        shards = sorted(shards)
        def generator():
          for filename in shards:
            buffer = filename.read_bytes()
            data = pickle.loads(buffer)
            yield data
        loadfn(generator())
      else:
        raise KeyError(name)
    except Exception:
      print(f"Error loading '{name}' from checkpoint.")
      raise
