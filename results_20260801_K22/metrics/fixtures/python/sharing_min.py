"""Fixture metryk K22 — Python, RECZNE WSPOLDZIELENIE obliczenia (C6 > 0).

Kontrola pozytywna dla C6: licznik, ktory nigdy nie trafia, nie dowodzi
niczego. `shared` jest policzone raz i odczytane przez dwa wyjscia.
"""
src = list(range(10))
out_a = []
out_b = []

# CORE_BEGIN
for n in range(10):
    shared = src[n] * 2
    out_a.append(shared + 1)
    out_b.append(shared - 1)
# CORE_END
