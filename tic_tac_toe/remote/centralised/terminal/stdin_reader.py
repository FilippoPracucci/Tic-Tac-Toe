import threading
from queue import Queue

class StdinReader:
    """Single process-wide instance of a stdin reader."""

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self.queue: Queue[str] = Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                line = input()
            except (EOFError, KeyboardInterrupt):
                self.stop()
                return
            self.queue.put(line)

    @classmethod
    def instance(cls) -> "StdinReader":
        """Get the single instance of the stdin reader."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def stop(self) -> None:
        """Stop the stdin reader thread."""
        self._thread.join(timeout=0.2)
