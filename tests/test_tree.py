import elements
import pytest


class TestTree:

  def test_map_identity(self):
    tree = {'a': 12, 'b': ['c', (1, 2, 3)]}
    copy = elements.tree.map(lambda x: x, tree)
    assert copy == tree
    assert copy is not tree

  def test_map_double(self):
    tree = {'a': 12, 'b': ['c', (1, 2, 3)]}
    ref = {'a': 24, 'b': ['cc', (2, 4, 6)]}
    res = elements.tree.map(lambda x: x * 2, tree)
    assert ref == res

  def test_map_multiple(self):
    tree1 = {'a': 1, 'b': ['foo', (1, 2, 3)]}
    tree2 = {'a': 2, 'b': ['bar', (10, 20, 30)]}
    ref = {'a': 3, 'b': ['foobar', (11, 22, 33)]}
    res = elements.tree.map(lambda x, y: x + y, tree1, tree2)
    assert ref == res
    with pytest.raises(TypeError):
      tree1 = {'a': 1, 'b': ['foo', (1, 2, 3)]}
      tree2 = {'b': 2}
      res = elements.tree.map(lambda x, y: x + y, tree1, tree2)

  def test_map_isleaf(self):
    tree = {'a': 1, 'b': ['foo', (1, 2, 3)]}
    isleaf = lambda x: isinstance(x, list)
    leaves = []
    elements.tree.map(lambda x: leaves.append(x), tree, isleaf=isleaf)
    assert leaves == [1, ['foo', (1, 2, 3)]]

  def test_map_degenerate(self):
    assert elements.tree.map(lambda x: 2 * x, ()) == ()
    assert elements.tree.map(lambda x: 2 * x, 12) == 24
    assert elements.tree.map(lambda x: 2 * x, [[{}, ()]]) == [[{}, ()]]

  def test_flatten_basic(self):
    tree = {'a': 12, 'b': ['c', (1, 2, 3)]}
    leaves, structure = elements.tree.flatten(tree)
    assert leaves == (12, 'c', 1, 2, 3)
    assert structure == {'a': None, 'b': [None, (None, None, None)]}

  def test_flatten_isleaf(self):
    tree = {'a': 12, 'b': ['c', (1, 2, 3)]}
    isleaf = lambda x: isinstance(x, list)
    leaves, structure = elements.tree.flatten(tree, isleaf=isleaf)
    assert leaves == (12, ['c', (1, 2, 3)])
    assert structure == {'a': None, 'b': None}

  def test_flatten_degenerate(self):
    assert elements.tree.flatten(()) == ((), ())
    assert elements.tree.flatten(12) == ((12,), None)
    assert elements.tree.flatten([[{}, ()]]) == ((), [[{}, ()]])

  def test_unflatten(self):
    trees = [
        {'a': 12, 'b': ['c', (1, 2, 3)]},
        (),
        12,
        [[{}, ()]],
    ]
    for tree in trees:
      leaves, structure = elements.tree.flatten(tree)
      copy = elements.tree.unflatten(leaves, structure)
      assert copy == tree
