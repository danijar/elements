import setuptools
import pathlib


def parse_requirements(path):
  requirements = pathlib.Path(path)
  requirements = requirements.read_text().split('\n')
  requirements = [x for x in requirements if x.strip()]
  return requirements


setuptools.setup(
    name='elements',
    version='2.0.0',
    description='Building blocks for productive research.',
    url='http://github.com/danijar/elements',
    long_description=pathlib.Path('README.md').read_text(),
    long_description_content_type='text/markdown',
    packages=['elements'],
    install_requires=parse_requirements('requirements.txt'),
    extras_requires=parse_requirements('requirements-optional.txt'),
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
