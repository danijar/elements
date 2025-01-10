from datetime import datetime


def timestamp(time=None, millis=False):
  if time is None:
    time = datetime.now()
  string = time.strftime("%Y%m%dT%H%M%S")
  if millis:
    string += f'F{time.microsecond:06d}'
  return string
