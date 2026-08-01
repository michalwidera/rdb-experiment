// Fixture metryk K22 — Flink/Java, JAWNE WARUNKI ROZGRZEWKI (C5 > 0).
// Kontrola pozytywna dla JAVA-C5-01 po poprawce: pierwsza wersja wzorca lapala
// wylacznie `< x.length`, wiec oba warunki nizej byly gubione.
// Ostatni `if` to kontrola ZAKRESU, nie ogon — NIE moze byc policzony jako C5.
// CORE_BEGIN
  static class Warmup {
    private static final int WIN = 30;
    private int filled;

    public void flatMap(long n, long acc) {
      filled = filled + 1;
      if (filled < WIN) {
        return;
      }
      if (n < WIN - 1) {
        return;
      }
      if (acc > Integer.MAX_VALUE || acc < Integer.MIN_VALUE) {
        throw new ArithmeticException("poza int32");
      }
    }
  }
// CORE_END
