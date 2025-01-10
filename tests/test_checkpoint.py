import elements
import pytest


class TestCheckpoint:

  def test_basic(self, tmpdir):
    path = elements.Path(tmpdir)
    foo = SaveableMock(42)
    cp = elements.Checkpoint(path)
    cp.foo = foo
    foo.value = 12
    cp.save()
    assert cp.latest() == path / (path / 'latest').read_text()
    filenames = set(x.name for x in cp.latest().glob('*'))
    assert filenames == {'foo.pkl', 'done'}
    del cp
    foo = SaveableMock(42)
    cp = elements.Checkpoint(tmpdir)
    cp.foo = foo
    cp.load()
    assert foo.value == 12

  def test_load_or_save(self, tmpdir):
    path = elements.Path(tmpdir)
    for restart in range(3):
      foo = SaveableMock(42)
      cp = elements.Checkpoint(path, keep=3)
      cp.foo = foo
      cp.load_or_save()
      assert foo.value == 42 + restart
      foo.value += 1
      cp.save()

  def test_keep(self, tmpdir, keep=3):
    path = elements.Path(tmpdir)
    cp = elements.Checkpoint(path, keep=keep)
    cp.foo = SaveableMock(0)
    for i in range(1, 6):
      cp.foo.value = i
      cp.save()
      filenames = set(x.name for x in path.glob('*'))
      filenames.remove('latest')
      assert len(filenames) == min(i, keep)
    cp.load()
    assert cp.foo.value == 5

  def test_step(self, tmpdir):
    path = elements.Path(tmpdir)
    step = elements.Counter(0)
    cp = elements.Checkpoint(path, step=step, keep=3)
    cp.foo = SaveableMock(0)
    for _ in range(5):
      cp.foo.value = int(step)
      cp.save()
      step.increment()
    filenames = set(x.name for x in path.glob('*'))
    filenames.remove('latest')
    steps = set(int(x.split('-')[1]) for x in filenames)
    assert steps == {2, 3, 4}

  def test_generator(self, tmpdir):
    path = elements.Path(tmpdir)
    cp = elements.Checkpoint(path)
    cp.foo = GeneratorMock([42, 12, 26])
    cp.save()
    filenames = set(x.name for x in cp.latest().glob('*'))
    assert filenames == {
        'foo-0000.pkl',
        'foo-0001.pkl',
        'foo-0002.pkl',
        'done',
    }
    del cp
    cp = elements.Checkpoint(path)
    cp.foo = GeneratorMock([0, 0, 0])
    cp.load()
    assert cp.foo.values == [42, 12, 26]

  def test_saveable_inline(self, tmpdir):
    path = elements.Path(tmpdir)
    cp = elements.Checkpoint(path)
    foo = [42]
    cp.foo = elements.Saveable(
        save=lambda: foo[0],
        load=lambda x: [foo.clear(), foo.insert(0, x)])
    cp.save()
    foo = [12]
    cp.load()
    assert foo == [42]

  def test_saveable_inherit(self, tmpdir):
    path = elements.Path(tmpdir)
    foo = SubclassMock(42)
    cp = elements.Checkpoint(path)
    cp.foo = foo
    cp.save()
    foo.value = 12
    cp.load()
    assert foo.value == 42

  def test_write(self, tmpdir):
    path = elements.Path(tmpdir)
    cp = elements.Checkpoint(path, write=False)
    cp.foo = SaveableMock(42)
    cp.bar = GeneratorMock([1, 2, 3])
    cp.save()
    assert list(path.glob('*')) == []

  def test_path(self, tmpdir):
    path = elements.Path(tmpdir)
    cp = elements.Checkpoint()
    cp.foo = SaveableMock(42)
    cp.save(path / 'inner')
    assert set(path.glob('*')) == {path / 'inner'}
    cp.foo.value = 12
    cp.load(path / 'inner')
    assert cp.foo.value == 42

  def test_keys(self, tmpdir):
    path = elements.Path(tmpdir)
    cp = elements.Checkpoint(path)
    cp.foo = SaveableMock(42)
    cp.bar = SaveableMock(12)
    cp.save(keys=['bar'])
    filenames = set(x.name for x in cp.latest().glob('*'))
    assert filenames == {'bar.pkl', 'done'}
    cp.foo.value = 0
    cp.bar.value = 0
    cp.load(keys=['bar'])
    assert cp.foo.value == 0
    assert cp.bar.value == 12
    with pytest.raises(KeyError):
      cp.load()


class SaveableMock:

  def __init__(self, value):
    self.value = value

  def save(self):
    return {'value': self.value}

  def load(self, data):
    self.value = data['value']


class SubclassMock(elements.Saveable):

  def __init__(self, value):
    super().__init__(['value'])
    self.value = value


class GeneratorMock:

  def __init__(self, values):
    self.values = values

  def save(self):
    for value in self.values:
      shard = {'value': value}
      yield shard

  def load(self, data):
    for i, shard in enumerate(data):
      self.values[i] = shard['value']
