// Fixture metryk K22 — Flink/Java, minimalny operator stanowy z oknem.
// Odpowiedz znana wyliczona recznie w metrics/test_metrics.py.
// CORE_BEGIN
  static class BandPass {
    private double[] win;
    private long counter;

    public void open() {
      win = new double[3];
      counter = 0;
    }

    public double map(double x) {
      System.arraycopy(win, 1, win, 0, win.length - 1);
      win[win.length - 1] = x;
      double acc = 0.0;
      for (int i = 0; i < win.length; i++) {
        acc += win[i];
      }
      counter = counter + 1;
      return acc;
    }
  }
// CORE_END
