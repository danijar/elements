import time

import elements


class TestCheckpoint:

  def test_basic(self, tmpdir):
    filename = elements.Path(tmpdir) / 'checkpoint.pkl'
    foo = Foo(42)
    cp = elements.Checkpoint(filename, parallel=False)
    cp.foo = foo
    foo.value = 12
    cp.save()
    del cp
    foo = Foo(42)
    cp = elements.Checkpoint(filename)
    cp.foo = foo
    cp.load()
    assert foo.value == 12

  def test_load_or_save(self, tmpdir):
    for restart in range(3):
      filename = elements.Path(tmpdir) / 'checkpoint.pkl'
      foo = Foo(42)
      cp = elements.Checkpoint(filename, parallel=False)
      cp.foo = foo
      cp.load_or_save()
      assert foo.value == 42 + restart
      foo.value += 1
      cp.save()

  def test_parallel(self, tmpdir):
    filename = elements.Path(tmpdir) / 'checkpoint.pkl'
    foo = Foo(42)
    cp = elements.Checkpoint(filename, parallel=True)
    cp.foo = foo
    cp.save()
    foo.value = 12
    time.sleep(0.1)
    cp.load()
    foo.value == 42

  def test_saveable_inline(self, tmpdir):
    filename = elements.Path(tmpdir) / 'checkpoint.pkl'
    cp = elements.Checkpoint(filename, parallel=False)
    foo = [42]
    cp.foo = elements.Saveable(
        save=lambda: foo[0],
        load=lambda x: [foo.clear(), foo.insert(0, x)])
    cp.save()
    foo = [12]
    cp.load()
    assert foo == [42]

  def test_saveable_inherit(self, tmpdir):
    filename = elements.Path(tmpdir) / 'checkpoint.pkl'
    bar = Bar(42)
    cp = elements.Checkpoint(filename, parallel=False)
    cp.bar = bar
    cp.save()
    bar.value = 12
    cp.load()
    assert bar.value == 42


class Foo:

  def __init__(self, value):
    self.value = value

  def save(self):
    return {'value': self.value}

  def load(self, data):
    self.value = data['value']


class Bar(elements.Saveable):

  def __init__(self, value):
    super().__init__(['value'])
    self.value = value
