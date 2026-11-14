from collections import defaultdict, deque
from typing import Dict, Iterable, Optional


class FaultInjector:
    def __init__(self, faults: Optional[Dict[str, Iterable[str]]] = None) -> None:
        self._faults = defaultdict(deque)
        for module, values in (faults or {}).items():
            self._faults[module].extend(values)

    def next(self, module: str) -> Optional[str]:
        queue = self._faults[module]
        return queue.popleft() if queue else None
