#!/usr/bin/env python3
"""Niezalezny oracle granicy zdarzeniowej dla znaleziska A (krok 2 planu).

Model buduje sie WYLACZNIE z definicji formalnych artykulu (main-debs.tex):
  * Def. interleave  (eq:interleave) — c_n oraz Delta_c,
  * Def. stream sum  (eq:sum)        — c_n oraz Delta_c = min,
  * Def. time shift  (eq:shift)      — rekord n niesie s_{n-m}.
Nie importuje kodu RetractorDB i nie odtwarza jego postaci zamknietych.

Semantyka brzegu, ta sama co w silniku:
  origin O — liczba poczatkowych indeksow BEZ DEFINICJI (siegaja przed poczatek zrodla),
  ogon   W — OPOZNIENIE EMISJI: rekord n jest wydawany w slocie n+W.
Rekord zrodla deklarowanego o indeksie k jest gotowy w chwili (k+1)*Delta (koniec swojego
przedzialu). Slot n konczy sie w (n+1)*Delta_out. Warunek emisji rekordu n:
      avail(n) <= (n + W + 1) * Delta_out
a W jest NAJMNIEJSZA liczba calkowita >= 0 spelniajaca go dla kazdego n >= O.
"""
from fractions import Fraction as F

HORIZON = 4000


class Decl:
    def __init__(self, delta):
        self.delta = F(delta)

    def defined(self, n):
        return n >= 0

    def avail(self, n):
        return (n + 1) * self.delta


class Shift:
    """tau_m — rekord n niesie s_{n-m}; indeksy < m nie maja definicji."""

    def __init__(self, src, m):
        self.src, self.m, self.delta = src, m, src.delta

    def defined(self, n):
        return n >= self.m and self.src.defined(n - self.m)

    def avail(self, n):
        return self.src.avail(n - self.m)


class Hash:
    """phi — eq:interleave."""

    def __init__(self, a, b):
        self.a, self.b = a, b
        da, db = a.delta, b.delta
        self.z = db / (da + db)
        self.delta = da * db / (da + db)

    def _pick(self, n):
        lo, hi = (n * self.z).__floor__(), ((n + 1) * self.z).__floor__()
        return (self.b, n - lo) if lo == hi else (self.a, lo)

    def defined(self, n):
        s, i = self._pick(n)
        return i >= 0 and s.defined(i)

    def avail(self, n):
        s, i = self._pick(n)
        return s.avail(i)


class Sum:
    """Sigma — eq:sum; szybszy sklada rytm, wolniejszy jest wspolindeksowany."""

    def __init__(self, a, b):
        self.a, self.b = a, b
        self.delta = min(a.delta, b.delta)

    def _deps(self, n):
        a, b = self.a, self.b
        if a.delta <= b.delta:
            return [(a, n), (b, (F(n) * a.delta / b.delta).__floor__())]
        return [(a, (F(n) * b.delta / a.delta).__floor__()), (b, n)]

    def defined(self, n):
        return all(i >= 0 and s.defined(i) for s, i in self._deps(n))

    def avail(self, n):
        return max(s.avail(i) for s, i in self._deps(n))


def boundary(stream):
    """Zwraca (origin, ogon) wyliczone wprost z definicji, bez postaci zamknietej."""
    origin = 0
    while origin < HORIZON and not stream.defined(origin):
        origin += 1
    for n in range(origin, HORIZON):
        if not stream.defined(n):
            raise AssertionError(f"dziura w definicji przy n={n} — model nie opisuje tego ksztaltu")
    need = 0
    for n in range(origin, HORIZON):
        q = stream.avail(n) / stream.delta - n - 1
        need = max(need, -((-q.numerator) // q.denominator))  # ceil
    return origin, max(0, need)


def emits(stream, origin, tail, upto=HORIZON):
    """Czy przy zadanym ogonie KAZDY rekord zdazy? Sluzy bramce mutantow."""
    return all(stream.avail(n) <= (n + tail + 1) * stream.delta for n in range(origin, upto))


A, B = F(1, 100), F(1, 50)
SHAPES = {
    "A#B": lambda: Hash(Decl(A), Decl(B)),
    "A+B": lambda: Sum(Decl(A), Decl(B)),
    "(A>2)#(B>1)": lambda: Hash(Shift(Decl(A), 2), Shift(Decl(B), 1)),
    "(A#B)>3": lambda: Shift(Hash(Decl(A), Decl(B)), 3),
    "(A>4)#(B>2)": lambda: Hash(Shift(Decl(A), 4), Shift(Decl(B), 2)),
    "(A#B)>6": lambda: Shift(Hash(Decl(A), Decl(B)), 6),
    "(A>2)+(B>1)": lambda: Sum(Shift(Decl(A), 2), Shift(Decl(B), 1)),
    "(A+B)>2": lambda: Shift(Sum(Decl(A), Decl(B)), 2),
}
# Wartosci silnika 530c80e z `xretractor -c` (R1 OFF, zeby zobaczyc ksztalt nieprzepisany).
ENGINE = {
    "A#B": (0, 2),
    "A+B": (0, 1),
    "(A>2)#(B>1)": (3, 2),
    "(A#B)>3": (3, 0),
    "(A>4)#(B>2)": (6, 2),
    "(A#B)>6": (6, 0),
    "(A>2)+(B>1)": (2, 1),
    "(A+B)>2": (2, 0),
}

print(f"{'ksztalt':<14} | {'oracle O/W':<11} | {'silnik O/W':<11} | werdykt")
print("-" * 58)
verdicts = {}
for name, make in SHAPES.items():
    o, w = boundary(make())
    eo, ew = ENGINE[name]
    v = "zgodne" if (o, w) == (eo, ew) else ("SILNIK ZAWYZA" if (eo + ew) > (o + w) else "**SILNIK ZANIZA**")
    verdicts[name] = v
    print(f"{name:<14} | {o}/{w:<9} | {eo}/{ew:<9} | {v}")

print("\n=== bramka mutantow: ogon musi byc MINIMALNY i WYSTARCZAJACY ===")
for name, make in SHAPES.items():
    s = make()
    o, w = boundary(s)
    ok_w = emits(s, o, w)
    ok_less = emits(s, o, w - 1) if w > 0 else False
    status = "OK" if (ok_w and not ok_less) else "**BRAMKA NIE ODROZNIA**"
    print(f"{name:<14} W={w} wystarcza={ok_w}  W-1={w-1} wystarcza={ok_less}  -> {status}")

print("\n=== niezmiennik tozsamosci: ksztalty rownowazne ===")
for lhs, rhs in [("(A>2)#(B>1)", "(A#B)>3"), ("(A>4)#(B>2)", "(A#B)>6"), ("(A>2)+(B>1)", "(A+B)>2")]:
    bl, br = boundary(SHAPES[lhs]()), boundary(SHAPES[rhs]())
    print(f"{lhs:<14} {bl}  ~  {rhs:<11} {br}   -> {'ZGODNE' if bl == br else '**ROZJAZD ORACLE**'}")
