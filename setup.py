import setuptools
import pathlib


setuptools.setup(
    name='elements',
    version='1.0.0',
    description='Building blocks for productive research.',
    url='http://github.com/danijar/elements',
    long_description=pathlib.Path('README.md').read_text(),
    long_description_content_type='text/markdown',
    packages=['elements'],
    install_requires=['numpy', 'imageio', 'matplotlib'],
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
