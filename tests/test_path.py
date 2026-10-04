import os
from pathlib import PureWindowsPath

import pytest

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

    def test_parent(self):
        empty = elements.Path('.')
        root = elements.Path('/')
        assert (root / 'foo' / 'bar.txt').parent.parent == root
        assert (empty / 'foo' / 'bar.txt').parent.parent == empty
        assert root.parent == root
        assert empty.parent == empty

    def test_with_suffix(self):
        examples = [
            ('foo.a', '.b', 'foo.b'),
            ('foo/bar.a.b', '.c', 'foo/bar.a.c'),
            ('foo', '.abc', 'foo.abc'),
            ('foo.xyz', '', 'foo'),
            ('foo', '', 'foo'),
        ]
        for path, suffix, output in examples:
            assert str(elements.Path(path).with_suffix(suffix)) == output

    def test_relative_to(self):
        examples = [
            ('/', '/foo/bar', 'foo/bar'),
            ('/foo/a/b/', '/foo/a/b/c/d', 'c/d'),
            ('foo/a/b/', 'foo/a/b/c/d', 'c/d'),
            ('foo/a/b', 'foo/a/b/c/d', 'c/d'),
            ('foo/a', 'foo/a', '.'),
        ]
        for parent, path, output in examples:
            parent = elements.Path(parent)
            path = elements.Path(path)
            assert str(path.relative_to(parent)) == output

    @pytest.mark.parametrize('relative', [True, False])
    def test_absolute_keeps_file_access(self, tmp_path, monkeypatch, relative):
        file = tmp_path / 'weights.npz'
        file.write_bytes(b'checkpoint')
        monkeypatch.chdir(tmp_path)
        path = elements.Path('weights.npz' if relative else file)
        absolute = path.absolute()
        assert os.path.isabs(os.fspath(absolute))
        assert os.path.normpath(os.fspath(absolute)) == str(file.absolute())
        assert absolute.read_bytes() == b'checkpoint'
        assert absolute.absolute() == absolute

    def test_hidden_file_path_retains_leading_dot(self, tmp_path, monkeypatch):
        (tmp_path / '.checkpoint').write_bytes(b'hidden checkpoint')
        (tmp_path / 'checkpoint').write_bytes(b'different checkpoint')
        monkeypatch.chdir(tmp_path)
        path = elements.Path('.checkpoint')
        assert path.read_bytes() == b'hidden checkpoint'
        assert str(path) == '.checkpoint'

    def test_parent_relative_path_does_not_read_current_directory(
        self, tmp_path, monkeypatch
    ):
        (tmp_path / 'checkpoint.npz').write_bytes(b'parent checkpoint')
        child = tmp_path / 'child'
        child.mkdir()
        (child / 'checkpoint.npz').write_bytes(b'wrong child checkpoint')
        monkeypatch.chdir(child)
        path = elements.Path('../checkpoint.npz')
        assert path.read_bytes() == b'parent checkpoint'
        assert str(elements.Path('..')) == '..'

    def test_glob_native_filesystem_paths(self, tmp_path):
        filename = tmp_path / 'chunk.npz'
        filename.write_bytes(b'replay archive')
        directory = elements.Path(tmp_path)
        matches = list(directory.glob('*.npz'))
        assert len(matches) == 1
        assert matches[0].name == filename.name
        assert matches[0].stem == filename.stem
        assert matches[0].parent == directory
        assert (directory / matches[0].name).read_bytes() == b'replay archive'

    def test_glob_current_directory_paths(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        filename = elements.Path('chunk.npz')
        filename.write_bytes(b'relative archive')
        matches = list(elements.Path('.').glob('*.npz'))
        assert len(matches) == 1
        assert matches[0].name == 'chunk.npz'
        assert matches[0].read_bytes() == b'relative archive'

    @pytest.mark.skipif(os.sep != '\\', reason='Windows native paths')
    @pytest.mark.parametrize(
        'native',
        [
            r'C:\data\replay\chunk.npz',
            r'\\server\share\replay\chunk.npz',
        ],
    )
    def test_windows_drive_and_unc_metadata(self, native):
        expected = PureWindowsPath(native)
        actual = elements.Path(native)
        assert actual.name == expected.name
        assert str(actual.parent) == expected.parent.as_posix()
        assert actual.stem == expected.stem

    @pytest.mark.skipif(
        os.sep == '\\', reason='Backslashes are separators on Windows'
    )
    def test_posix_backslash_filename_is_preserved(self, tmp_path):
        filename = tmp_path / r'chunk\backup.npz'
        filename.write_bytes(b'literal backslash')
        actual = elements.Path(filename)
        assert actual.name == filename.name
        assert actual.read_bytes() == b'literal backslash'
