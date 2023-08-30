import gzip
import json
import os
import pathlib
import warnings

import numpy as np


COLORS = (
    '#377eb8', '#4daf4a', '#984ea3', '#e41a1c', '#ff7f00', '#a65628',
    '#f781bf', '#888888', '#a6cee3', '#b2df8a', '#cab2d6', '#fb9a99',
)


def load(filename):
  filename = pathlib.Path(filename)
  with gzip.open(filename, 'rb') as f:
    return json.load(f)


def dump(runs, filename):
  filename = pathlib.Path(filename)
  filename.parent.mkdir(exist_ok=True)
  with gzip.open(filename, 'wb') as f:
    f.write(json.dumps(runs).encode('utf-8'))


def save(fig, filename):
  filename = pathlib.Path(filename)
  filename.parent.mkdir(exist_ok=True)
  png = filename.with_suffix('.png')
  pdf = filename.with_suffix('.pdf')
  fig.savefig(png, dpi=300)
  print('Saved', png.name)
  fig.savefig(pdf, dpi=300)
  print('Saved', pdf.name)
  # If pdfcrop from texlive is not available, the below prints a warning.
  os.system(f'pdfcrop {pdf.name} {pdf.name}')


def plots(
    amount, cols=4, size=(2, 2.3), xticks=4, yticks=5, grid=(1, 1), **kwargs):
  import matplotlib.pyplot as plt
  from matplotlib import ticker
  cols = min(amount, cols)
  rows = int(np.ceil(amount / cols))
  size = (cols * size[0], rows * size[1])
  fig, axes = plt.subplots(rows, cols, figsize=size, squeeze=False, **kwargs)
  axes = axes.flatten()
  for ax in axes:
    ax.xaxis.set_major_locator(ticker.MaxNLocator(xticks))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(yticks))
    if grid:
      grid = (grid, grid) if not hasattr(grid, '__len__') else grid
      ax.grid(which='both', color='#eeeeee')
      ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(int(grid[0])))
      ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(int(grid[1])))
      ax.tick_params(which='minor', length=0)
  for ax in axes[amount:]:
    ax.axis('off')
  return fig, axes


def curve(
    ax, domain, values, low=None, high=None, label=None, order=0, **kwargs):
  finite = np.isfinite(values)
  ax.plot(
      domain[finite], values[finite],
      label=label, zorder=1000 - order, **kwargs)
  if low is not None:
    ax.fill_between(
        domain[finite], low[finite], high[finite],
        zorder=100 - order, alpha=0.2, lw=0, **kwargs)


def bars(
    ax, labels, values, lower=None, upper=None, colors=None, reverse=False):
  values = np.array(values)
  domain = np.arange(len(values))
  assert values.shape == domain.shape, (values.shape, domain.shape)
  assert len(labels) == len(values), (labels, values)
  if reverse:
    labels = labels[::-1]
    values = values[::-1]
    lower = lower[::-1]
    upper = upper[::-1]
    colors = colors[::-1]
  yerr = np.stack([-(lower - values), upper - values], 0)
  ax.bar(domain, values, yerr=yerr, color=colors or COLORS[len(labels)])
  ax.set_xticks(domain + 0.3)
  ax.set_xticklabels(labels, ha='right', rotation=30, rotation_mode='anchor')
  ax.set_xlim(-0.6, domain[-1] + 0.4)
  ax.tick_params(axis='x', which='both', length=0)
  ax.tick_params(axis='y', which='major', length=2, labelsize=9, pad=2)
  ax.spines['top'].set_visible(False)
  ax.spines['right'].set_visible(False)


def legend(fig, data=None, adjust=True, plotpad=0.5, legendpad=0, **kwargs):
  options = dict(
      fontsize='medium', numpoints=1, labelspacing=0, columnspacing=1.2,
      handlelength=1.5, handletextpad=0.5, ncol=4, loc='lower center')
  options.update(kwargs)
  # Find all labels and remove duplicates.
  entries = {}
  for ax in fig.axes:
    for handle, label in zip(*ax.get_legend_handles_labels()):
      if data and label in data:
        label = data[label]
      entries[label] = handle
  leg = fig.legend(entries.values(), entries.keys(), **options)
  leg.get_frame().set_edgecolor('white')
  if adjust:
    legextent = leg.get_window_extent(fig.canvas.get_renderer())
    legextent = legextent.transformed(fig.transFigure.inverted())
    yloc, xloc = options['loc'].split()
    legpad = legendpad
    xpad, ypad = legpad if hasattr(legpad, '__len__') else (legpad,) * 2
    x0 = dict(left=legextent.x1 + xpad, center=0, right=0)[xloc]   # left
    y0 = dict(lower=legextent.y1 + ypad, center=0, upper=0)[yloc]  # bottom
    x1 = dict(left=1, center=1, right=legextent.x0 - xpad)[xloc]   # right
    y1 = dict(lower=1, center=1, upper=legextent.y0 - ypad)[yloc]  # top
    rect = [x0, y0, x1, y1]  # left, bottom, right, top
    xpad, ypad = plotpad if hasattr(plotpad, '__len__') else (plotpad,) * 2
    fig.tight_layout(rect=rect, w_pad=xpad, h_pad=ypad)


def binning(xs, ys, borders, reducer=np.nanmean, fill='nan'):
  assert fill in ('nan', 'last', 'zeros')
  xs = xs if isinstance(xs, np.ndarray) else np.asarray(xs)
  ys = ys if isinstance(ys, np.ndarray) else np.asarray(ys)
  order = np.argsort(xs)
  xs, ys = xs[order], ys[order]
  binned = []
  for start, stop in zip(borders[:-1], borders[1:]):
    left = (xs < start).sum()
    right = (xs <= stop).sum()
    value = np.nan
    if left < right:
      value = reduce(ys[left:right], reducer)
    if np.isnan(value):
      if fill == 'zeros':
        value = 0
      if fill == 'last' and binned:
        value = binned[-1]
    binned.append(value)
  return borders[1:], np.array(binned)


def tensor(runs, borders, tasks=None, methods=None, seeds=None, fill='nan'):
  tasks = tasks or sorted(set(run['task'] for run in runs))
  methods = methods or sorted(set(run['method'] for run in runs))
  seeds = seeds or sorted(set(run['seed'] for run in runs))
  tensor = np.empty((len(tasks), len(methods), len(seeds), len(borders) - 1))
  tensor[:] = np.nan
  for run in runs:
    try:
      i = tasks.index(run['task'])
      j = methods.index(run['method'])
      k = seeds.index(run['seed'])
    except ValueError:
      continue
    _, ys = binning(run['xs'], run['ys'], borders, fill=fill)
    tensor[i, j, k, :] = ys
  return tensor, tasks, methods, seeds


def reduce(values, reducer=np.nanmean, *args, **kwargs):
  with warnings.catch_warnings():  # Buckets can be empty.
    warnings.simplefilter('ignore', category=RuntimeWarning)
    return reducer(values, *args, **kwargs)
