#!/usr/bin/env python3
"""Zamrożony zestaw mutantów postaci zamkniętej (predeklarowany).

Cztery mutacje z §10/K24 planu badawczego, każda psująca jedno miejsce
repliki. Bramka wymaga wykrycia 100% z nich: mutant jest **wykryty**, gdy
w korpusie bramkowym istnieje węzeł, na którym oracle zgadza się z repliką
i nie zgadza się z mutantem. Bez tego warunku bramka byłaby spełniona przez
sam fakt, że oracle różni się od czegokolwiek.
"""

MUTANTS = {
    "hash_phase_plus_one": {"hash_phase": 1},
    "hash_phase_minus_one": {"hash_phase": -1},
    "hash_swap_pq": {"hash_swap": True},
    "hash_drop_own": {"hash_drop_own": True},
    "theta_zero_own": {"theta_zero_own": True},
}
