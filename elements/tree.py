from . import printing


def map(fn, *trees, isleaf=None):
  assert trees, 'Provide one or more nested Python structures'
  kw = dict(isleaf=isleaf)
  first = trees[0]
  try:
    assert all(isinstance(x, type(first)) for x in trees)
    if isleaf and isleaf(trees[0]):
      return fn(*trees)
    if isinstance(first, list):
      assert all(len(x) == len(first) for x in trees)
      return [map(
          fn, *[t[i] for t in trees], **kw) for i in range(len(first))]
    if isinstance(first, tuple):
      assert all(len(x) == len(first) for x in trees)
      return tuple([map(
          fn, *[t[i] for t in trees], **kw) for i in range(len(first))])
    if isinstance(first, dict):
      assert all(set(x.keys()) == set(first.keys()) for x in trees)
      return {k: map(fn, *[t[k] for t in trees], **kw) for k in first}
    if hasattr(first, 'keys') and hasattr(first, 'get'):
      assert all(set(x.keys()) == set(first.keys()) for x in trees)
      return type(first)(
          {k: map(fn, *[t[k] for t in trees], **kw) for k in first})
  except AssertionError:
    raise TypeError(printing.format_(trees))
  return fn(*trees)


def flatten(tree, isleaf=None):
  leaves = []
  map(lambda x: leaves.append(x), tree, isleaf=isleaf)
  structure = map(lambda x: None, tree, isleaf=isleaf)
  return tuple(leaves), structure


def unflatten(leaves, structure):
  leaves = iter(tuple(leaves))
  return map(lambda x: next(leaves), structure)


def flatdict(structure, sep='/'):
  assert isinstance(structure, dict)
  mapping = {}
  for key, value in structure.items():
    if isinstance(value, dict):
      inner = {f'{key}{sep}{k}': v for k, v in flatdict(value).items()}
      mapping.update(inner)
    else:
      mapping[key] = value
  return mapping


def nestdict(mapping, sep='/'):
  assert isinstance(mapping, dict)
  tree = {}
  for path, value in mapping.items():
    node = tree
    parts = path.split(sep)
    for part in parts[:-1]:
      node = node.setdefault(part, {})
    node[parts[-1]] = value
  return tree
