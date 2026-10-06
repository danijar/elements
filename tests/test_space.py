import elements
import numpy as np
import pytest


@pytest.mark.parametrize('dtype,shape,low,high', [
    (np.float32, (3,), -1, 1),
    (np.int32, (), 0, 7),
    (np.uint8, (2, 3), None, None),
    (bool, (2,), None, None),
    (str, (), None, None),
])
def test_equivalent_descriptors_return_python_bool(dtype, shape, low, high):
  left = elements.Space(dtype, shape, low, high)
  right = elements.Space(dtype, shape, low, high)
  assert (left == right) is True
  assert (right == left) is True
  assert (left != right) is False
  assert (left == left) is True


@pytest.mark.parametrize('different', [
    (np.float64, (3,), -1, 1),
    (np.float32, (2,), -1, 1),
    (np.float32, (3,), [-1, -2, -1], 1),
    (np.float32, (3,), -1, [1, 2, 1]),
])
def test_each_descriptor_field_distinguishes_spaces(different):
  original = elements.Space(np.float32, (3,), -1, 1)
  changed = elements.Space(*different)
  assert (original == changed) is False
  assert (changed == original) is False
  assert (original != changed) is True


def test_observation_and_action_schema_comparison_detects_mismatch():
  reference = {
      'image': elements.Space(np.uint8, (64, 64, 3)),
      'action': elements.Space(np.float32, (6,), -1, 1),
  }
  equivalent = {
      name: elements.Space(space.dtype, space.shape, space.low, space.high)
      for name, space in reference.items()
  }
  assert reference == equivalent
  changed_shape = dict(equivalent, action=elements.Space(np.float32, (7,), -1, 1))
  changed_bounds = dict(equivalent, action=elements.Space(np.float32, (6,), -2, 2))
  assert reference != changed_shape
  assert reference != changed_bounds


def test_sequence_membership_uses_descriptor_values():
  selected = elements.Space(np.float32, (3,), -1, 1)
  equivalent = elements.Space(np.float32, (3,), [-1, -1, -1], [1, 1, 1])
  different = elements.Space(np.float32, (3,), -1, 2)
  assert equivalent in [selected]
  assert different not in [selected]
  assert [selected] != [different]


@pytest.mark.parametrize('foreign', [None, 0, 'space', object()])
def test_unrelated_values_follow_python_comparison_protocol(foreign):
  space = elements.Space(np.float32, (3,), -1, 1)
  assert space.__eq__(foreign) is NotImplemented
  assert (space == foreign) is False
  assert (foreign == space) is False


def test_reflected_comparison_can_handle_a_space():
  class Compatible:
    def __eq__(self, other):
      return isinstance(other, elements.Space)
  space = elements.Space(np.float32, (3,), -1, 1)
  assert (space == Compatible()) is True
