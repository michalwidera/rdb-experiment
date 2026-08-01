"""Fixture metryk K22 — Python, minimalna petla slotowa z oknem.

Odpowiedz znana wyliczona recznie w metrics/test_metrics.py.
Importy i definicje pomocnicze sa POZA rdzeniem, wiec nie sa liczone.
"""
import time

import numpy as np

src = list(range(10))
coef = [1, 2, 3]

# CORE_BEGIN
WIN = 3
win = np.zeros(WIN)
total = 0
for n in range(10):
    now = time.monotonic_ns()
    win[:-1] = win[1:]
    win[-1] = src[n]
    y = win[0] + win[1]
    total = total + y
# CORE_END
