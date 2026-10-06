import importlib.util

import elements


def load_function(directory, module_name, operation):
  # Real independent Python modules, as in separate dataset preprocessing files.
  path = directory / f'{module_name}.py'
  path.write_text(
      'calls = 0\n'
      'def preprocess(value):\n'
      '  global calls\n'
      '  calls += 1\n'
      f'  return value {operation}\n')
  spec = importlib.util.spec_from_file_location(module_name, path)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def test_same_named_functions_in_different_modules_do_not_share_results(tmp_path):
  first = load_function(tmp_path, 'camera_data', '+ 10')
  second = load_function(tmp_path, 'action_data', '* 3')
  left = elements.diskcache(root=tmp_path / 'cache')(first.preprocess)
  right = elements.diskcache(root=tmp_path / 'cache')(second.preprocess)
  assert left(2) == 12
  assert right(2) == 6
  assert left(2) == 12
  assert right(2) == 6
  assert first.calls == second.calls == 1


def test_distinct_lexical_functions_in_one_module_do_not_share_results(tmp_path):
  def first_function():
    def preprocess(value):
      return value + 10
    return preprocess
  def second_function():
    def preprocess(value):
      return value * 3
    return preprocess
  left = elements.diskcache(root=tmp_path)(first_function())
  right = elements.diskcache(root=tmp_path)(second_function())
  assert left(2) == 12
  assert right(2) == 6


def test_namespace_is_stable_across_module_reload(tmp_path):
  original = load_function(tmp_path, 'stable_preprocessor', '+ 10')
  first = elements.diskcache(root=tmp_path / 'cache')(original.preprocess)
  assert first(2) == 12
  reloaded = load_function(tmp_path, 'stable_preprocessor', '+ 10')
  second = elements.diskcache(root=tmp_path / 'cache')(reloaded.preprocess)
  assert second(2) == 12
  assert reloaded.calls == 0


def test_explicit_namespace_still_allows_intentional_sharing(tmp_path):
  first = load_function(tmp_path, 'first_shared', '+ 10')
  second = load_function(tmp_path, 'second_shared', '+ 10')
  left = elements.diskcache('shared', root=tmp_path / 'cache')(first.preprocess)
  right = elements.diskcache('shared', root=tmp_path / 'cache')(second.preprocess)
  assert left(2) == 12
  assert right(2) == 12
  assert first.calls == 1
  assert second.calls == 0


def test_clear_only_removes_selected_function_results(tmp_path):
  first = load_function(tmp_path, 'first_clear', '+ 10')
  second = load_function(tmp_path, 'second_clear', '* 3')
  left = elements.diskcache(root=tmp_path / 'cache')(first.preprocess)
  right = elements.diskcache(root=tmp_path / 'cache')(second.preprocess)
  left(2)
  right(2)
  left.clear()
  assert right(2) == 6
  assert second.calls == 1
  assert left(2) == 12
  assert first.calls == 2


def test_lambda_namespace_does_not_require_illegal_path_characters(tmp_path):
  cached = elements.diskcache(root=tmp_path)(lambda value: value + 1)
  assert cached(2) == 3
  assert cached(2) == 3
  assert '<' not in cached.folder.name and '>' not in cached.folder.name
