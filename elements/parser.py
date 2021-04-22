import re
import sys

from .config import Config


class FlagParser:

  def __init__(self, *args, **kwargs):
    self._config = Config(*args, **kwargs)

  def parse(self, argv=None, exit_on_help=True):
    config, remaining = self.parse_known(argv, exit_on_help)
    for flag in remaining:
      if flag.startswith('--'):
        raise ValueError(f"Flag '{flag}' did not match any config keys.")
    assert not remaining, remaining
    return config

  def parse_known(self, argv=None, exit_on_help=True):
    if argv is None:
      argv = sys.argv[1:]
    if '--help' in argv:
      print('\nHelp:')
      lines = str(self._config).split('\n')[2:]
      print('\n'.join('--' + re.sub(r'[:,\[\]]', '', x) for x in lines))
      exit_on_help and sys.exit()
    parsed = {}
    remaining = []
    key = None
    vals = None
    for arg in argv:
      if arg.startswith('--'):
        if key:
          self._submit_entry(key, vals, parsed, remaining)
        key, vals = arg, []
        vals = []
      else:
        if key:
          vals.append(arg)
        else:
          remaining.append(arg)
    self._submit_entry(key, vals, parsed, remaining)
    return self._config.update(parsed), remaining

  def _submit_entry(self, key, vals, parsed, remaining):
    if not key:
      vals = ', '.join(f"'{x}'" for x in vals)
      raise ValueError(f"Values {vals} were not preceeded by any flag.")
    name = key[len('--'):]
    if '=' in name:
      remaining.extend([key] + vals)
      return
    if self._config.IS_PATTERN.match(name):
      pattern = re.compile(name)
      keys = {k for k in self._config.flat if pattern.match(k)}
    elif name in self._config:
      keys = [name]
    else:
      remaining.extend([key] + vals)
      return
    if not keys:
      raise KeyError(f"Flag '{key}' did not match any keys.")
    if not vals:
      raise ValueError(f"Flag '{key}' was not followed by any values.")
    for key in keys:
      parsed[key] = parse_flag_value(self._config[key], vals, key)


def parse_flag_value(default, value, key):
  value = value if isinstance(value, (tuple, list)) else (value,)
  if isinstance(default, (tuple, list)):
    if len(value) == 1 and ',' in value[0]:
      value = value[0].split(',')
    return tuple(parse_flag_value(default[0], [x], key) for x in value)
  assert len(value) == 1, value
  value = str(value[0])
  if default is None:
    return value
  if isinstance(default, bool):
    try:
      return bool(['False', 'True'].index(value))
    except ValueError:
      raise TypeError(f"Expected bool but got '{value}' for key '{key}'.")
  if isinstance(default, int):
    value = float(value)  # Allow scientific notation for integers.
    if float(int(value)) != value:
      raise TypeError(f"Expected int but got float '{value}' for key '{key}'.")
    return int(value)
  return type(default)(value)
