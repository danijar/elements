import elements
import pytest


class TestFlags:

  def test_int(self):
    flags = elements.Flags({'foo': 42})
    assert flags.parse(['--foo=1']).foo == 1
    assert flags.parse(['--foo=1.0']).foo == 1
    assert flags.parse(['--foo=1e2']).foo == 100
    with pytest.raises(TypeError):
      flags.parse(['--foo=0.5'])
    with pytest.raises(TypeError):
      flags.parse(['--foo=foo'])
    with pytest.raises(TypeError):
      assert flags.parse(['--foo=1,2,3'])

  def test_float(self):
    flags = elements.Flags({'foo': 1.0})
    assert flags.parse(['--foo=0.5']).foo == 0.5
    assert flags.parse(['--foo=1']).foo == 1.0
    assert flags.parse(['--foo=1e2']).foo == 1e2
    with pytest.raises(TypeError):
      flags.parse(['--foo=True'])
    with pytest.raises(TypeError):
      flags.parse(['--foo=foo'])
    with pytest.raises(TypeError):
      assert flags.parse(['--foo=0.5,1.0'])

  def test_bool(self):
    flags = elements.Flags({'foo': True})
    assert flags.parse(['--foo=True']).foo is True
    assert flags.parse(['--foo=False']).foo is False
    with pytest.raises(TypeError):
      flags.parse(['--foo=true'])
    with pytest.raises(TypeError):
      flags.parse(['--foo=1'])
    with pytest.raises(TypeError):
      flags.parse(['--foo=foo'])
    with pytest.raises(TypeError):
      assert flags.parse(['--foo=True,False'])

  def test_str(self):
    flags = elements.Flags({'foo': 'hello'})
    assert flags.parse(['--foo=hi']).foo == 'hi'
    assert flags.parse(['--foo=1,2,3']).foo == '1,2,3'
    assert flags.parse(['--foo=']).foo == ''
    with pytest.raises(TypeError):
      assert flags.parse(['--foo', '1', '2', '3'])

  def test_sequence(self):
    flags = elements.Flags({'foo': [1, 2]})
    assert flags.parse(['--foo=1']).foo == (1,)
    assert flags.parse(['--foo=1,2,3']).foo == (1, 2, 3)
    assert flags.parse(['--foo', '1,2,3']).foo == (1, 2, 3)
    assert flags.parse(['--foo', '1', '2', '3']).foo == (1, 2, 3)
    with pytest.raises(TypeError):
      assert flags.parse(['--foo', 'False'])
    with pytest.raises(TypeError):
      assert flags.parse(['--foo=1,2,0.5'])

  def test_append(self):
    flags = elements.Flags({'foo': [1, 2]})
    assert flags.parse(['--foo+=3']).foo == (1, 2, 3)
    assert flags.parse(['--foo+', '3']).foo == (1, 2, 3)
    with pytest.raises(TypeError):
      assert flags.parse(['--foo+', '0.5'])
    assert flags.parse(['--foo=1', '--foo+=2', '--foo+=3']).foo == (1, 2, 3)
    assert flags.parse(['--foo+=3', '--foo+=4']).foo == (1, 2, 3, 4)

  def test_nested(self):
    flags = elements.Flags({'foo.bar': 12})
    assert flags.parse(['--foo.bar=42']).foo.bar == 42
    with pytest.raises(KeyError):
      assert flags.parse(['--foo=42'])
    with pytest.raises(KeyError):
      assert flags.parse(['--foo.baz=42'])
    flags = elements.Flags({'foo': {'bar': 12}})
    assert flags.parse(['--foo.bar=42']).foo.bar == 42

  def test_regex(self):
    flags = elements.Flags({'foo.bar': 12, 'baz': 'text'})
    assert flags.parse([r'--.*\.bar=42']).foo.bar == 42
    assert flags.parse([r'--.*z$=hello']).baz == 'hello'
    parsed = flags.parse([r'--.*=42'])
    assert parsed.foo.bar == 42
    assert parsed.baz == '42'
    with pytest.raises(TypeError):
      assert flags.parse([r'--.*\.bar=0.5'])

  def test_kwargs(self):
    assert elements.Flags(foo=42).parse(['--foo=12']).foo == 12
    assert elements.Flags(foo=42, bar='text').parse(['--bar=i']).bar == 'i'

  def test_multiple(self):
    defaults = elements.Config(foo=12, bar=0.5, baz='text')
    flags = elements.Flags(defaults)
    assert flags.parse([]) == defaults
    assert flags.parse(['--bar', '2.5', '--foo=1']) == (
        defaults.update(foo=1, bar=2.5))
    with pytest.raises(ValueError):
      flags.parse(['--bar', '--foo=1'])

  def test_invalid(self):
    flags = elements.Flags(foo=12)
    with pytest.raises(KeyError):
      flags.parse(['--bar=1'])
    with pytest.raises(ValueError):
      flags.parse(['foo=1'])
    with pytest.raises(ValueError):
      flags.parse(['1', '--foo=5'])

  def test_from_yaml(self, tmpdir):
    filename = elements.Path(tmpdir) / 'defaults.yaml'
    filename.write("""
    foo: 42
    parent.child: 12
    seq: [1, 2, 3]
    scope:
      inside: foo
    """)
    defaults = elements.Config.load(filename)
    flags = elements.Flags(defaults)
    assert flags.parse(['--parent.child=42']).parent.child == 42
    assert flags.parse(['--seq=2,4,6']).seq == (2, 4, 6)
