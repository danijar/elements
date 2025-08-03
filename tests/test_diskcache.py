import elements
import elements.diskcache


class TestDiskcache:

  def test_basic(self, tmpdir):
    elements.diskcache.root = tmpdir
    elements.diskcache.verbose = True

    counter = elements.Counter()

    @elements.diskcache
    def fn(foo, bar):
      counter.increment()
      return foo + bar

    fn.clear()

    assert counter == 0
    assert fn(1, 2) == 3
    assert counter == 1
    assert fn('a', 'b') == 'ab'
    assert counter == 2

    assert fn(1, 2) == 3
    assert fn('a', 'b') == 'ab'
    assert counter == 2

    fn.clear()
    assert fn(1, 2) == 3
    assert fn('a', 'b') == 'ab'
    assert counter == 4

    assert fn(1, 2, _refresh=True) == 3
    assert counter == 5

    assert fn(1, 2) == 3
    assert fn('a', 'b') == 'ab'
    assert counter == 5


  def test_names(self, tmpdir):

    def make():
      @elements.diskcache('fn1')
      def fn(foo, bar):
        return foo + bar
      return fn
    fn1 = make()

    def make():
      @elements.diskcache('fn2')
      def fn(foo, bar):
        return foo - bar
      return fn
    fn2 = make()

    assert fn1(2, 1) == 3
    assert fn2(2, 1) == 1
