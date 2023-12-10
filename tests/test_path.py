import elements


class TestPath:

  def test_str_canonical(self):
    examples = ['/', 'foo/bar', 'file.txt', '/bar.tar.gz']
    for example in examples:
      assert str(elements.Path(example)) == example

  def test_parent_and_name(self):
    examples = ['foo/bar', '/bar.tar.gz', 'file.txt', 'foo/bar/baz']
    for example in examples:
      path = elements.Path(example)
      assert path == path.parent / path.name

  def test_stem_and_suffix(self):
    examples = ['foo/bar', '/bar.tar.gz', 'file.txt', 'foo/bar/baz']
    for example in examples:
      path = elements.Path(example)
      assert path.name == path.stem + path.suffix

  def test_leading_dot(self):
    assert str(elements.Path('')) == '.'
    assert str(elements.Path('.')) == '.'
    assert str(elements.Path('./')) == '.'
    assert str(elements.Path('./foo')) == 'foo'

  def test_trailing_slash(self):
    assert str(elements.Path('./')) == '.'
    assert str(elements.Path('a/')) == 'a'
    assert str(elements.Path('foo/bar/')) == 'foo/bar'

  # @pytest.mark.filterwarnings('ignore::DeprecationWarning')
  # def test_protocols(self):
  #   assert str(elements.Path('gs://')) == ('gs://')
  #   assert str(elements.Path('gs://foo/bar')) == 'gs://foo/bar'

  def test_parent(self):
    empty = elements.Path('.')
    root = elements.Path('/')
    assert (root / 'foo' / 'bar.txt').parent.parent == root
    assert (empty / 'foo' / 'bar.txt').parent.parent == empty
    assert root.parent == root
    assert empty.parent == empty
