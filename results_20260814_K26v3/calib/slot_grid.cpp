// Wyznacza SIATKĘ SLOTÓW planu — czyli to, co realnie budzi pętlę wykonania.
//
// Po co to istnieje
// -----------------
// Kryterium kalibracji (PREDEKLARACJA §8.1) brzmi „p99 <= 50% LOGICZNEGO SLOTU",
// a warunek zatrzymania (§8.3) „komórka przekracza 80% slotu". Dla rodziny F9-R2
// slot jest jednorodny (oba źródła 1/100), ale F9-R1 i F9-X mają na osi czasu
// dwa niewspółmierne takty — 1/100 źródła i 1/150 strumienia przeplecionego —
// więc odstępy między kolejnymi slotami NIE SĄ równe. Budżetem jest odstęp
// NAJKRÓTSZY: w tym slocie silnik ma najmniej czasu, a obliczenie wykonuje się
// w każdym.
//
// Dlaczego to nie jest trzecie przepisanie specyfikacji
// -----------------------------------------------------
// Program NIE liczy siatki sam — kompiluje i woła `CRSMath.cpp` SILNIKA, tę samą
// klasę `TimeLine`, którą `executorsm.cpp` tworzy w pętli wykonania. Zbiór
// interwałów wejściowych też nie jest przepisany: pochodzi z wydruku planu
// (`xretractor -c`), czyli z silnika. Reguła łuku „oracle ma czytać czytnikiem
// silnika" (mapa NULL przez `xtrdb` w P6) obowiązuje tu tak samo.
//
// Compile-only jest tu użyte legalnie: twierdzenie dotyczy KSZTAŁTU PLANU
// (jakie takty w nim występują), a nie jego wykonywalności.
//
// Użycie:  ./slot_grid 1/100 1/150
// Wynik:   wiersze `min_slot_ms`, `max_slot_ms`, `n_slots_w_okresie` na stdout.

#include <cstdio>
#include <cstdlib>
#include <set>
#include <string>
#include <vector>

#include <boost/rational.hpp>

#include "CRSMath.hpp"

using boost::rational;

static rational<int> parseRational(const std::string &text) {
  const auto slash = text.find('/');
  if (slash == std::string::npos) return rational<int>(std::atoi(text.c_str()), 1);
  return rational<int>(std::atoi(text.substr(0, slash).c_str()), std::atoi(text.substr(slash + 1).c_str()));
}

int main(int argc, char **argv) {
  if (argc < 2) {
    std::fprintf(stderr, "uzycie: slot_grid <interwal> [<interwal> ...]   np. slot_grid 1/100 1/150\n");
    return 2;
  }
  std::set<rational<int>> intervals;
  for (int i = 1; i < argc; ++i) intervals.insert(parseRational(argv[i]));

  // Ta sama klasa, którą tworzy executorsm.cpp:662.
  CRationalStreamMath::TimeLine tl(intervals);

  // Okres siatki powtarza się po NWW mianowników; 20000 slotów z zapasem
  // pokrywa każdy układ używany w kampanii, a minimum i tak jest osiągane
  // wielokrotnie w każdym okresie.
  const int probes = 20000;
  rational<int> previous(0);
  rational<int> minDelta(0), maxDelta(0);
  for (int i = 0; i < probes; ++i) {
    const rational<int> now   = tl.getNextTimeSlot();
    const rational<int> delta = now - previous;
    previous                  = now;
    if (i == 0 || delta < minDelta) minDelta = delta;
    if (i == 0 || delta > maxDelta) maxDelta = delta;
  }

  const double minMs = 1000.0 * minDelta.numerator() / minDelta.denominator();
  const double maxMs = 1000.0 * maxDelta.numerator() / maxDelta.denominator();
  std::printf("min_slot_ms\t%.6f\n", minMs);
  std::printf("max_slot_ms\t%.6f\n", maxMs);
  std::printf("jednorodna\t%s\n", minDelta == maxDelta ? "tak" : "nie");
  return 0;
}
