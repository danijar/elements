import hashlib
import json
import pickle

from . import path as pathlib


def diskcache(*args, **kwargs):
  if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
    return DiskCache(args[0])
  else:
    return lambda fn: DiskCache(fn, *args, **kwargs)


diskcache.root = '/tmp/elements/diskcache'
diskcache.refresh = False
diskcache.verbose = False


class DiskCache:

  def __init__(self, fn, name=None, refresh=None, verbose=None, root=None):
    if name is None:
      name = f'{pathlib.Path(__file__).stem}-{fn.__name__}'
    self.fn = fn
    self.folder = pathlib.Path(diskcache.root if root is None else root) / name
    self.refresh = diskcache.refresh if refresh is None else refresh
    self.verbose = diskcache.verbose if verbose is None else verbose

  def __call__(
      self,
      *args,
      _key=None,
      _refresh=None,
      **kwargs,
  ):
    try:
      inputs = [args, kwargs] if _key is None else _key
      inputs = json.dumps(inputs, sort_keys=True)
    except ValueError as e:
      raise ValueError(
          'Diskcache requires function arguments to be JSON serializable. ' +
          'Alternatively, pass _key=... into the function with a cache key.'
      ) from e
    key = hashlib.sha256(inputs.encode('utf8')).hexdigest()
    filename = self.folder / f'{key}.pkl'
    refresh = self.refresh if _refresh is None else _refresh
    if filename.exists() and not refresh:
      self.verbose and print(f'Loading diskcache: {filename}')
      data = pickle.loads(filename.read_bytes())
      assert data['inputs'] == inputs, ('Hash collision', data, inputs)
      return data['output']
    else:
      self.verbose and print(f'Filling diskcache: {filename}')
      output = self.fn(*args, **kwargs)
      data = {'inputs': inputs, 'output': output}
      filename.parent.mkdir()
      filename.write_bytes(pickle.dumps(data))
    return output

  def clear(self):
    self.verbose and print(f'Clearing diskcache: {self.folder}')
    for file in self.folder.glob('*.pkl'):
      file.remove()
