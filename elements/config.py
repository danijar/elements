import json
import re


class Config(dict):

  SEP = '.'
  IS_PATTERN = re.compile(r'.*[^A-Za-z0-9_.-].*')

  def __init__(self, *args, **kwargs):
    mapping = dict(*args, **kwargs)
    mapping = self._ensure_nesting(mapping)
    mapping = self._ensure_types(mapping)
    super().__init__(mapping)
    flat = []
    for key, value in self.items():
      if isinstance(value, type(self)):
        flat += [(f'{key}{self.SEP}{k}', v) for k, v in value.flat.items()]
      else:
        flat.append((key, value))
    self.__dict__['_flat'] = tuple(flat)

  @property
  def flat(self):
    return dict(self._flat)

  def __contains__(self, name):
    try:
      self[name]
      return True
    except KeyError:
      return False

  def __getattr__(self, name):
    return self[name]

  def __getitem__(self, name):
    result = self
    for part in name.split(self.SEP):
      result = dict.__getitem__(result, part)
    return result

  def __setattr__(self, key, value):
    raise TypeError('Config objects are immutable. Use update().')

  def __setitem__(self, key, value):
    raise TypeError('Config objects are immutable. Use update().')

  def update(self, *args, **kwargs):
    result = self.flat.copy()
    inputs = Config(*args, **kwargs)
    for key, new in inputs.flat.items():
      if self.IS_PATTERN.match(key):
        pattern = re.compile(key)
        keys = {k for k in result if pattern.match(k)}
      else:
        keys = [key]
      if not keys:
        raise KeyError(f'Unknown key or pattern {key}.')
      for key in keys:
        old = result[key]
        try:
          if isinstance(old, int) and isinstance(new, float):
            if float(int(new)) != new:
              raise ValueError
          result[key] = type(old)(new)
        except (ValueError, TypeError):
          raise TypeError(
              f"Cannot convert '{new}' to type '{type(old).__name__}' " +
              f"of value '{old}' for key '{key}'.")
    return type(self)(result)

  def __str__(self):
    lines = ['\nConfig:']
    keys, vals, typs = [], [], []
    for key, val in self.flat.items():
      keys.append(key + ':')
      vals.append(self._format_value(val))
      typs.append(self._format_type(val))
    max_key = max(len(k) for k in keys)
    max_val = max(len(v) for v in vals)
    for key, val, typ in zip(keys, vals, typs):
      key = key.ljust(max_key)
      val = val.ljust(max_val)
      lines.append(f'{key}  {val}  ({typ})')
    return '\n'.join(lines)

  def _ensure_nesting(self, inputs):
    result = {}
    for key, value in inputs.items():
      parts = key.split(self.SEP)
      node = result
      for part in parts[:-1]:
        if part not in node:
          node[part] = dict()
        node = node[part]
      node[parts[-1]] = value
    return result

  def _ensure_types(self, inputs):
    result = json.loads(json.dumps(inputs))
    for key, value in result.items():
      if isinstance(value, dict):
        value = type(self)(value)
      if isinstance(value, list):
        value = tuple(value)
      if isinstance(value, tuple):
        if len(value) == 0:
          message = 'Empty lists are disallowed because their type is unclear.'
          raise TypeError(message)
        if not isinstance(value[0], (str, float, int, bool)):
          message = 'Lists can only contain strings, floats, ints, or bools.'
          raise TypeError(message)
        if not all(isinstance(x, type(value[0])) for x in value[1:]):
          message = 'Elements of a list must all be of the same type.'
          raise TypeError(message)
      result[key] = value
    return result

  def _format_value(self, value):
    if isinstance(value, (list, tuple)):
      return '[' + ', '.join(self._format_value(x) for x in value) + ']'
    return str(value)

  def _format_type(self, value):
    if isinstance(value, (list, tuple)):
      assert len(value) > 0, value
      return self._format_type(value[0]) + 's'
    return str(type(value).__name__)
