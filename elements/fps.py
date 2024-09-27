import threading
import time


class FPS:

  def __init__(self):
    self.start = time.time()
    self.total = 0
    self.lock = threading.Lock()

  def step(self, amount=1):
    with self.lock:
      self.total += amount

  def result(self, reset=True):
    with self.lock:
      now = time.time()
      fps = self.total / (now - self.start)
      if reset:
        self.start = now
        self.total = 0
      return fps
