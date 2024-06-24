[![PyPI](https://img.shields.io/pypi/v/elements.svg)](https://pypi.python.org/pypi/elements/#history)

# 🔥 Elements

Building blocks for productive research.

## Installation

```sh
pip install elements
```

## Features

Elements aims to provide well thought out solutions to common problems in
research code. It is also hackable. If you need to change some of the code, we
encourage you to fork the corresponding file into your project directory and
make edits.

### `elements.Logger`

A logger for array types that is extensible through backends. Metrics are
written in a background thread to not block program execution, which is
especially important on cloud services where bucket access is slow.

Provided backends:
- `TerminalOutput(pattern)`: Print scalars to the terminal. Can filter to
  fewer metrics via regex.
- `JSONLOutput(logdir, filename, pattern)`: Write scalars to JSONL files.
  For example, can be read directly with pandas.
- `TensorBoardOutput(logdir)`: Scalars, histograms, images, GIFs.
  Automatically starts new event files when the current one exceeds a size
  limit to support cloud storage where appding to files requires a full
  download and reupload.
- `WandBOutput(pattern, **init_kwargs)`: Strings, histograms, images, videos.
- `MLFlowOutput(run_name, resume_id)`: Logs all types of metrics to MLFlow.

```python
step = elements.Counter()
logger = elements.Logger(step, [
    elements.logger.TerminalOutput(),
    elements.logger.JSONLOutput(logdir, 'metrics.jsonl'),
    elements.logger.TensorBoardOutput(logdir),
    elements.logger.WandBOutput(name='name', project='project'),
])

step.increment()
logger.scalar('foo', 42)
logger.scalar('foo', 43)
logger.scalar('foo', 44)
logger.vector('vector', np.zeros(100))
logger.image('image', np.zeros((800, 600, 3, np.uint8)))
logger.video('video', np.zeros((100, 64, 64, 3, np.uint8)))

logger.add({'foo': 42, 'vector': np.zeros(100)}, prefix='scope')

logger.write()
```

### `elements.Config`

An immutable nested directory to hold configurations. Keys can be accessed via
attribute syntax. Values are restricted to primitive types that are supported
by JSON. Types are checked when replacing values in the config.

```python
config = elements.Config(
    logdir='path/to/dir',
    foo=dict(bar=42),
)

print(config)                      # Pretty printing
print(config.foo.bar)              # Attribute syntax
print(config['foo']['bar'])        # Dictionary syntax
config.logdir = 'path/to/new/dir'  # Not allowed

# Access a copy of the flattened dictionary underlying the config.
config.flat == {'logdir': 'path/to/dir', 'foo.bar': 42}

# Configs are immutable, so updating them returns a new object.
new_config = config.update({'foo.bar': 43})

# Types are enforced when updating configs, but values of other types are
# allowed as long as they can be converted without loss of information.
new_config = config.update({'foo.bar': float(1e5)})  # Allowed
new_config = config.update({'foo.bar': float(1.5)})  # Not allowed

# Configs can be saved and loaded in JSON and YAML formats.
config.save('config.json')
config = elements.Config.load('config.json')
```

### `elements.Flags`

A parser for command line flags similar to `argparse` but faster to use and
more flexible. Enforces types and supports nested dictionaries and overwriting
multiple flags at once via regex.

A mapping of valid keys and their default values must be provided to infer
types. Because there are defaults for all values, there are no required
arguments that the user must specify on the command line.

```python
# Create flags parser from default values.
flags = elements.Flags(logdir='path/to/dir', bar=42)

# Create flags parser from config.
flags = elements.Flags(elements.Config({
    'logdir': 'path/to/dir',
    'foo.bar': 42,
    'list': [1, 2, 3],
}))

# Load a config from YAML and overwrite it from it from the command line.
config = elements.Config.load('defaults.yaml')
config = elements.Flags(config).parse()

# Overwrite some of the keys.
config = flags.parse(['--logdir', 'path/to/new/dir', '--foo.bar', '43'])

# Supports syntax with space or equals.
config = flags.parse(['--logdir=path/to/new/dir'])

# Overwrite lists.
config = flags.parse(['--list', '10', '20', '30'])
config = flags.parse(['--list', '10,20,30'])
config = flags.parse(['--list=10,20,30'])

# Set all nested keys that end in 'bar'.
config = flags.parse(['--.*\.bar$', '43'])

# Parse only known flags.
config, remaining = flags.parse_known(['--logdir', 'dir', '--other', '123'])
remaining == ['--other', '123']

# Print a help page and terminate the program.
flags.parse(['--help'])

# Print a help page without terminating the program.
flags = elements.Flags(logdir='path/to/dir', bar=42, help_exits=False)
parsed, remaining = flags.parse_known(['--help', '--other=value'])
remaining == ['--help', '--other=value']
second_parser.parse(remaining)  # Now we exit.
```

### `elements.Path`

A filesystem abstraction similar to `pathlib` that is extensible to new
filesystems. Comes with support for local filesystems and GCS buckets.

```python
path = elements.Path('gs://bucket/path/to/file.txt')

# String operations
path.parent                           # gs://bucket/path/to
path.name                             # file.txt
path.stem                             # file
path.suffix                           # .txt

# File operations
path.read(mode='r')                   # Content of the file as string
path.read(mode='rb')                  # Content of the file as bytes
path.write(content, mode='w')         # Write string to the file
path.write(content, mode='wb')        # Write bytes to the file
with path.open(mode='r') as f:        # Create a file pointer
  pass

# File system checks
path.parent.glob('*')                 # Get all sibling paths
path.exists()                         # True
path.isdir()                          # False
path.isfile()                         # True

# File system changes
(path.parent / 'foo').mkdir()         # Creates directory including parents
path.remove()                         # Deletes a file or empty directory
path.parent.rmtree()                  # Deletes directory and its content
path.copy(path.parent / 'copy.txt')   # Makes a copy
path.move(path.parent / 'moved.txt')  # Moves the file
```

### `elements.Checkpoint`

Holds a collection of objects that can be saved to and loaded from disk.

Each object attached to the checkpoint needs to implement `save() -> data` and
`load(data)` methods, where `data` is pickleable.

Checkpoints are written in a background thread to not block program execution.
New checkpoints are writing to a temporary path first and renamed to the actual
path once they are fully written, so that the path always points to a valid
name even if the program gets terminated while writing.

```python
step = elements.Counter()

cp = elements.Checkpoint(directory)
# Attach objects to the checkpoint.
cp.step = step
cp.model = model
# After attaching the objects we load the checkpoint from disk if it exists
# and otherwise save an initial checkpoint.
cp.load_or_save()

# Later on, we can change the objects and then save the checkpoint again.
should_save = elements.when.Every(10)
for _ in range(100):
  step.increment()
  if should_save(step):
    cp.save()

# We can also load checkpoints or parts of a checkpoint from a different directory.
cp.load(pretraining_directory, keys=['model'])
print(cp.model)
```

### `elements.Timer`

Collect timing statistics about the run time of different parts of a program.
Measures code inside sections and can wrap methods into sections. Returns
execution count, execution time, fraction of overall program time, and more.
The resulting statisticse can be added to the logger.

```python
timer = Timer()

timer.section('foo'):
  time.sleep(10)

timer.wrap('name', obj, ['method1', 'method2'])
obj.method1()
obj.method1()
obj.method1()
obj.method2()

stats = timer.stats(reset=True, log=True)
stats == {
    'foo_count': 1,
    'foo_total': 10.0,
    'foo_avg': 10.0,
    'foo_min': 10.0,
    'foo_max': 10.0,
    'foo_frac': 0.92,
    'name.method1_count': 3,
    'name.method1_frac': 0.07,
    # ...
    'name.method2_frac': 0.01,
    # ...
}
```

### `elements.when`

Helpers for running code at defined times, such as every fixed number of steps
or seconds or a certain fraction of the time. The counting is robust, so when
you skip a step it will run the code the next time to catch up.

```python
should = elements.when.Every(100)
for step in range(1000):
  if should(step):
    print(step)  # 0, 100, 200, ...

should = elements.when.Ratio(0.3333)
for step in range(100):
  if should(step):
    print(step)  # 0, 4, 7, 10, 13, 16, ...

should = elements.when.Once()
for step in range(100):
  if should(step):
    print(step)  # 0

should = elements.when.Until(5)
for step in range(10):
  if should(step):
    print(step)  # 0, 1, 2, 3, 4

should = elements.when.Clock(1)
for step in range(100):
  if should(step):
    print(step)  # 0, 10, 20, 30, ...
  time.sleep(0.1)
```

### `elements.plotting`

Tools for storing, loading, and plotting data with sensible defaults.

Data is stored in the `run` format in gzipped JSON files. Each file contains a
list of one or more run. A run is a dictionary with the keys `task`, `method`,
`seed`, `xs`, `ys`. The task, method, and seed are string fields, whereas xs
and ys are lists of equal length containing numbers for the data to plot.

Take a look at `plotting.py` in the repository to see the list of all available
functions, beyond what is used in this snippet.

```python
from elements import plotting

runs = plotting.load('filename.json.gz')
plotting.dump(runs, 'filename.json.gz')

bins = np.linspace(0, 1e6, 100)
tensor, tasks, methods, seeds = plotting.tensor(runs, bins)
tensor.shape == (len(tasks), len(methods), len(seeds), len(bins))

fig, axes = plotting.plots(len(tasks))

for i, task in enumerate(tasks):
  ax = axes[i]
  for j, method in enumerate(methods):
    # Aggregate over seeds.
    mean = np.nanmean(tensor[i, j, :, :], 2)
    std = np.nanstd(tensor[i, j, :, :], 2)
    plotting.curve(ax, bins[1:], mean, std, label=method, order=j)

plotting.legend(fig, adjust=True)

# Saves the figure in both PNG and PDF formats and attempts to crop margins off
# the PDF.
plotting.save(fig, 'path/to/name')
```

## Questions

Please file an [issue on Github](https://github.com/danijar/elements/issues).
