import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).parent.parent.parent))

import elements
import pytest


class TestBasics:

  def test_counter(self):
    counter = elements.Counter()
    assert int(counter) == 0
    counter.increment()
    assert int(counter) == 1
    counter.increment(3)
    assert int(counter) == 4

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

  def test_parser(self):
    parser = elements.FlagParser(foo=12, bar={'baz': True})
    assert parser.parse(['--bar.baz', 'False']).foo == 12
    assert parser.parse(['--bar.baz', 'False']).bar.baz is False
    assert parser.parse(['--bar.*', 'False']).bar.baz is False
    with pytest.raises(TypeError):
      parser.parse(['--bar.baz', '12'])
    with pytest.raises(KeyError):
      parser.parse(['--.*unknown.*', '12'])
    _, remaining = parser.parse_known(['one=two', '--foo', '42', '--three'])
    assert remaining == ['one=two', '--three']
    parser = elements.FlagParser({'foo': 12})
    _, remaining = parser.parse_known(['--help'], exit_on_help=False)
    assert remaining == ['--help']

  def test_logger(self, capsys):
    step = elements.Counter()
    outputs = [elements.TerminalOutput()]
    logger = elements.Logger(step, outputs)
    logger.scalar('name', 15)
    logger.write()
    output = capsys.readouterr()
    print(output)

  def test_every(self):
    should = elements.Every(5)
    result = []
    for i in range(16):
      if should(i):
        result.append(i)
    assert result == [0, 5, 10, 15]

  def test_once(self):
    should = elements.Once()
    result = []
    for i in range(16):
      if should():
        result.append(i)
    assert result == [0]

  def test_until(self):
    should = elements.Until(6)
    result = []
    for i in range(16):
      if should(i):
        result.append(i)
    assert result == [0, 1, 2, 3, 4, 5]
