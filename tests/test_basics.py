import elements
import pytest


class TestBasics:

  def test_config(self):
    config = elements.Config({'one.two': 12, 'foo': {'bar': True}})
    assert config.one.two == 12
    assert config.foo.bar is True
    assert config['foo'].bar is True
    assert 'foo' in config
    assert 'foo.bar' in config
    assert str(config)
    _ = config.update({'one.two': 42})
    with pytest.raises(KeyError):
      _ = config.update({'new': 1})
    with pytest.raises(TypeError):
      _ = config.update({'one.two': 'string'})
    with pytest.raises(AttributeError):
      config.one.two = 1
    with pytest.raises(TypeError):
      elements.Config({'foo': lambda: None})

  def test_flags(self):
    flags = elements.Flags(foo=12, bar={'baz': True})
    assert flags.parse(['--bar.baz', 'False']).foo == 12
    assert flags.parse(['--bar.baz', 'False']).bar.baz is False
    assert flags.parse(['--bar.*', 'False']).bar.baz is False
    with pytest.raises(TypeError):
      flags.parse(['--bar.baz', '12'])
    with pytest.raises(KeyError):
      flags.parse(['--.*unknown.*', '12'])
    _, remaining = flags.parse_known(['one=two', '--foo', '42', '--three'])
    assert remaining == ['one=two', '--three']
    flags = elements.Flags({'foo': 12})
    _, remaining = flags.parse_known(['--help'], help_exits=False)
    assert remaining == ['--help']

  def test_logger(self, capsys):
    step = elements.Counter()
    logger = elements.Logger(step, [elements.logger.TerminalOutput()])
    logger.scalar('name', 15)
    logger.write()
    output = capsys.readouterr()
    print(output)

  def test_every(self):
    should = elements.when.Every(5)
    result = []
    for i in range(16):
      if should(i):
        result.append(i)
    assert result == [0, 5, 10, 15]

  def test_once(self):
    should = elements.when.Once()
    result = []
    for i in range(16):
      if should():
        result.append(i)
    assert result == [0]

  def test_until(self):
    should = elements.when.Until(6)
    result = []
    for i in range(16):
      if should(i):
        result.append(i)
    assert result == [0, 1, 2, 3, 4, 5]
