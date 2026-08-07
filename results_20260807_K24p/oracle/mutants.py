#!/usr/bin/env python3
"""Zamrożony zestaw mutantów rachunku silnika (predeklarowany).

Mutant psuje replikę w jednym miejscu. Bramka wymaga wykrycia 100% z nich:
mutant jest **wykryty**, gdy w korpusie bramkowym istnieje węzeł, na którym
oracle zgadza się z repliką i nie zgadza się z mutantem. Bez tego warunku
bramka byłaby spełniona przez sam fakt, że oracle różni się od czegokolwiek.

Zestaw dzieli się na dwie rodziny, bo silnik niesie teraz dwie wielkości:

* ``TAIL_MUTANTS`` — cztery mutacje ogona z §10/K24, zachowane bez zmian, plus
  dwie nowe celujące w miejsca, które zmieniło przestemplowanie z 2026-08-06:
  ogon `>N`, który przestał zawierać `N`, i ogon `@`, który przestał zawierać
  człon fazowy. Obie odtwarzają dokładnie stan sprzed zmiany, więc bramka
  odpowiada też na pytanie „czy oracle w ogóle widzi różnicę między starą
  a nową semantyką” — gdyby nie widział, kampania byłaby ślepa;
* ``ORIGIN_MUTANTS`` — mutacje początku logicznego. Wielkość jest nowa i nie
  miała dotąd żadnej bramki; bez nich origin mógłby być cicho błędny, bo suma
  origin+ogon w wielu planach jest niewrażliwa na przesunięcie między członami.
"""

TAIL_MUTANTS = {
    "hash_phase_plus_one": {"hash_phase": 1},
    "hash_phase_minus_one": {"hash_phase": -1},
    "hash_swap_pq": {"hash_swap": True},
    "hash_drop_own": {"hash_drop_own": True},
    "theta_zero_own": {"theta_zero_own": True},
    # Stan sprzed przestemplowania: `N` z powrotem w ogonie przesunięcia.
    "shift_tail_keeps_n": {"shift_tail_keeps_n": True},
    # Stan sprzed przestemplowania: człon fazowy z powrotem w ogonie okna.
    "agse_tail_keeps_phase": {"agse_tail_keeps_phase": True},
}

ORIGIN_MUTANTS = {
    # Okno bez rozpiętości — origin zapomina, że rekord n sięga wstecz o |L|-1.
    "agse_drop_span": {"agse_drop_span": True},
    "agse_origin_plus_one": {"agse_origin_delta": 1},
    "agse_origin_minus_one": {"agse_origin_delta": -1},
    # Przesunięcie bez origin — cały efekt `>N` znika z planu.
    "shift_drop_origin": {"shift_drop_origin": True},
    # Przeplot patrzy tylko na lewą składową; prawa może wtedy być czytana
    # przed swoim początkiem.
    "hash_origin_left_only": {"hash_origin_left_only": True},
}

# Zachowana pod starą nazwą, żeby skrypty odwołujące się do MUTANTS działały
# bez zmian; bramka mutantów rozdziela obie rodziny sama.
MUTANTS = dict(TAIL_MUTANTS)
