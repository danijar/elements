from .config import Config
from .counter import Counter
from .logger import Logger, TerminalOutput, JSONLOutput, TensorBoardOutput
from .parser import FlagParser, parse_flag_value
from .when import Once, Until, Every


class staticproperty:

  def __init__(self, function):
    self.function = function

  def __get__(self, instance, owner=None):
    return self.function()
