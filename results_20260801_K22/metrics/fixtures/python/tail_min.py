"""Fixture metryk K22 — Python, RECZNE WYPROWADZANIE OGONA I FAZY (C5 > 0).

Kontrola pozytywna dla C5: stala opoznienia grupowego (C5-04), jawna faza
przez modulo (C5-03) i jawny warunek rozgrzewki (C5-01).
"""
src = list(range(64))

# CORE_BEGIN
GROUP_DELAY = 29
for n in range(64):
    idx = n % 8
    if n < GROUP_DELAY:
        continue
    y = src[idx]
# CORE_END
