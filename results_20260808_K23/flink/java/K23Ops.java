// Operatory wspolne trzech rodzin K23 po stronie Flinka.
//
// ZAMROZONA GRANULACJA (decyzja tego kroku, do wpisania w predeklaracje):
// job Flinka odwzorowuje plan RQL WEZEL W WEZEL —
//   * kazdy wezel substratu planu RetractorDB  -> jeden operator Flinka, ktorego rekordy
//     wyjsciowe licza sie do LICZNIKA metryki (Canon.onSubstrateWrite),
//   * wlasny szczytowy wezel `FROM` monitora razem z jego programem pol -> JEDEN koncowy
//     operator, ktorego wynik jest rekordem PUBLICZNYM (MIANOWNIK) i idzie na sink.
// Dzieki temu po obu stronach zgadzaja sie: schematy, kanoniczne szerokosci i liczba
// rekordow kazdego wezla — rozni sie wylacznie LICZBA INSTANCJI, czyli dokladnie to,
// o co pyta H9.
//
// Ta granulacja jest KONSERWATYWNA. Idiomatyczny DataStream rozbilby jeszcze operator
// monitora na osobne kroki (np. zestawienie i cecha w F9-R2), co dodaloby FLINK_NATURAL
// materializacji i PODNIOSLO redukcje na korzysc H9. Wybor przeciwny hipotezie jest
// swiadomy; skutek liczbowy podano w PLANY_FLINKA.md §6.
//
// Czego tu NIE MA: zadnego pomiaru czasu. Zrodla nie spia i nie maja zegara sciennego —
// czasem logicznym jest wylacznie indeks slotu. §10 zakazuje porownywania czasu
// RetractorDB z czasem JVM, wiec aparatura nie daje nawet mozliwosci pomylki.
import org.apache.flink.api.common.functions.OpenContext;
import org.apache.flink.api.common.functions.RichMapFunction;
import org.apache.flink.api.java.tuple.Tuple3;
import org.apache.flink.streaming.api.functions.co.CoProcessFunction;
import org.apache.flink.streaming.api.functions.sink.legacy.RichSinkFunction;
import org.apache.flink.streaming.api.functions.source.legacy.RichSourceFunction;
import org.apache.flink.util.Collector;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class K23Ops {

  private K23Ops() {}

  /** Rekord strumienia rodzin K23: jedno pole INTEGER — kanonicznie 9 B (SZKIC_RODZIN.md §3.4). */
  public static final Canon.Descriptor RECORD = Canon.singleInteger("v");

  /** Kanoniczna szerokosc rekordu, ta sama po obu stronach porownania. */
  public static final long W = Canon.recordBytes(RECORD);

  /**
   * Krotka transportowa: (slot, wartosc, tag).
   *
   * <p>`tag` NIE jest polem danych i nie wnosi kanonicznych bajtow: mowi, ktore zadeklarowane
   * zrodlo wnioslo wartosc do rekordu przeplotu. W RetractorDB ta informacja wynika z pozycji
   * na zamrozonej siatce wymiernej, wiec nie zajmuje miejsca w rekordzie. Kanoniczna szerokosc
   * rekordu przeplotu jest szerokoscia jednopolowego zrodla (U-4 w SZKIC_RODZIN.md).
   */
  public static Tuple3<Long, Long, Integer> rec(long slot, long value, int tag) {
    return Tuple3.of(slot, value, tag);
  }

  public static final int TAG_A = 0;
  public static final int TAG_B = 1;
  public static final int TAG_C = 2;
  public static final int TAG_D = 3;

  //
  // ─── Zrodlo: INGRESS, poza metryka (§10: "z mianownika wylaczyc ingress zrodel") ────────
  //

  /** Zrodlo jednego zadeklarowanego strumienia. Slot = indeks rekordu w jego wlasnej siatce. */
  public static class DeclaredSource extends RichSourceFunction<Tuple3<Long, Long, Integer>> {
    private final int[] values;
    private final long records;
    private final int tag;
    private volatile boolean running = true;

    public DeclaredSource(int[] values, long records, int tag) {
      this.values = values;
      this.records = records;
      this.tag = tag;
    }

    @Override
    public void run(SourceContext<Tuple3<Long, Long, Integer>> ctx) {
      for (long slot = 0; slot < records && running; slot++) {
        ctx.collect(rec(slot, values[(int) (slot % values.length)], tag));
      }
    }

    @Override
    public void cancel() {
      running = false;
    }
  }

  //
  // ─── Wezly badanego podplanu i etapy publiczne ──────────────────────────────────────────
  //

  /**
   * Przesuniecie `>n`: jeden rekord wyjscia na rekord wejscia, ta sama szerokosc kanoniczna.
   * `substrate` decyduje, czy wezel nalezy do badanego podplanu (licznik), czy jest czescia
   * etapu publicznego monitora (mianownik). `square` domyka program pola monitora tam, gdzie
   * przesuniecie jest szczytowym wezlem `FROM` (postac P2 w F9-R1).
   */
  public static class Shift extends RichMapFunction<Tuple3<Long, Long, Integer>, Tuple3<Long, Long, Integer>> {
    private final int slots;
    private final boolean substrate;
    private final boolean square;

    public Shift(int slots, boolean substrate, boolean square) {
      this.slots = slots;
      this.substrate = substrate;
      this.square = square;
    }

    @Override
    public Tuple3<Long, Long, Integer> map(Tuple3<Long, Long, Integer> in) {
      if (substrate) {
        Canon.onSubstrateWrite(W);
      }
      long value = square ? in.f1 * in.f1 : in.f1;
      return rec(in.f0 + slots, value, in.f2);
    }
  }

  /**
   * Przeplot `#` dwoch strumieni o wymiernych taktach na wspolnej siatce.
   *
   * <p>Reguly odwzorowane z aparatury K22 (results_20260801_K22/corpus/F3_multirate), gdzie
   * kolejnosc przeplotu byla ustalona POMIAREM na artefakcie silnika: przy rownym czasie
   * pierwszy wychodzi strumien o wolniejszym takcie. Krok siatki podaje wywolujacy
   * (`unitA`, `unitB`), zeby ta klasa nie znala rate'ow rodziny.
   *
   * <p>Deterministyczny niezaleznie od kolejnosci naplywu: wybor strony zalezy wylacznie od
   * licznikow siatki, a nie od tego, ktore wejscie odezwalo sie pierwsze.
   */
  public static class Interleave
      extends CoProcessFunction<Tuple3<Long, Long, Integer>, Tuple3<Long, Long, Integer>, Tuple3<Long, Long, Integer>> {
    private final int unitA;
    private final int unitB;
    private final boolean substrate;
    private final boolean square;
    private transient ArrayDeque<Tuple3<Long, Long, Integer>> queueA;
    private transient ArrayDeque<Tuple3<Long, Long, Integer>> queueB;
    private transient long unitsA;
    private transient long unitsB;
    private transient long outSlot;

    public Interleave(int unitA, int unitB, boolean substrate, boolean square) {
      this.unitA = unitA;
      this.unitB = unitB;
      this.substrate = substrate;
      this.square = square;
    }

    @Override
    public void open(OpenContext ctx) {
      queueA = new ArrayDeque<>();
      queueB = new ArrayDeque<>();
      unitsA = 0;
      unitsB = 0;
      outSlot = 0;
    }

    @Override
    public void processElement1(Tuple3<Long, Long, Integer> in, Context ctx, Collector<Tuple3<Long, Long, Integer>> out) {
      queueA.addLast(in);
      drain(out);
    }

    @Override
    public void processElement2(Tuple3<Long, Long, Integer> in, Context ctx, Collector<Tuple3<Long, Long, Integer>> out) {
      queueB.addLast(in);
      drain(out);
    }

    private void drain(Collector<Tuple3<Long, Long, Integer>> out) {
      while (true) {
        Tuple3<Long, Long, Integer> next;
        if (unitsB <= unitsA) {
          if (queueB.isEmpty()) {
            return;
          }
          next = queueB.pollFirst();
          unitsB += unitB;
        } else {
          if (queueA.isEmpty()) {
            return;
          }
          next = queueA.pollFirst();
          unitsA += unitA;
        }
        if (substrate) {
          Canon.onSubstrateWrite(W);
        }
        long value = square ? next.f1 * next.f1 : next.f1;
        out.collect(rec(outSlot++, value, next.f2));
      }
    }
  }

  /**
   * Suma strumieni `+` zestawiona po slocie, z programem pola nad zadeklarowanymi zrodlami.
   *
   * <p>Uzywana w dwoch rolach:
   * <ul>
   *   <li>F9-R2 — wezel substratu `STREAM_SELECT_*` o programie {PUSH A, PUSH B, STREAM_ADD}
   *       i schemacie jednego INTEGER (wynik `Sqrt`), czyli `substrate = true`;
   *   <li>F9-X — szczytowy wezel `FROM` monitora razem z programem `Sqrt(A*C + B*D)`,
   *       czyli `substrate = false` (rekord publiczny).
   * </ul>
   *
   * <p>Zatrzaski `latch` odwzorowuja rozwiazywanie odwolan `A[0]`…`D[0]` przez zlozony `FROM`:
   * w slocie, w ktorym dana skladowa przeplotu nie wnosi wartosci, obowiazuje jej ostatnia
   * znana wartosc. Rownowaznosc WARTOSCI obu stron nie jest przedmiotem tego kroku — sprawdza
   * ja wspolny oracle w P6 (§10, bramka poprawnosci); tutaj wiaza schematy i liczba rekordow.
   */
  public static class AddFeature
      extends CoProcessFunction<Tuple3<Long, Long, Integer>, Tuple3<Long, Long, Integer>, Tuple3<Long, Long, Integer>> {
    /** Program pola rodziny: F9-R2 liczy Sqrt(A*A + B*B), F9-X liczy Sqrt(A*C + B*D). */
    public enum Program {
      TWO_AXIS,
      TWO_PAIRS
    }

    private final boolean substrate;
    private final Program program;
    private transient Map<Long, Tuple3<Long, Long, Integer>> pendingLeft;
    private transient Map<Long, Tuple3<Long, Long, Integer>> pendingRight;
    private transient long[] latch;

    public AddFeature(boolean substrate, Program program) {
      this.substrate = substrate;
      this.program = program;
    }

    @Override
    public void open(OpenContext ctx) {
      pendingLeft = new HashMap<>();
      pendingRight = new HashMap<>();
      latch = new long[4];
    }

    @Override
    public void processElement1(Tuple3<Long, Long, Integer> in, Context ctx, Collector<Tuple3<Long, Long, Integer>> out) {
      pendingLeft.put(in.f0, in);
      emitIfPaired(in.f0, out);
    }

    @Override
    public void processElement2(Tuple3<Long, Long, Integer> in, Context ctx, Collector<Tuple3<Long, Long, Integer>> out) {
      pendingRight.put(in.f0, in);
      emitIfPaired(in.f0, out);
    }

    private void emitIfPaired(long slot, Collector<Tuple3<Long, Long, Integer>> out) {
      Tuple3<Long, Long, Integer> left = pendingLeft.remove(slot);
      Tuple3<Long, Long, Integer> right = pendingRight.remove(slot);
      if (left == null || right == null) {
        if (left != null) {
          pendingLeft.put(slot, left);
        }
        if (right != null) {
          pendingRight.put(slot, right);
        }
        return;
      }
      latch[left.f2] = left.f1;
      latch[right.f2] = right.f1;

      long a = latch[TAG_A];
      long b = latch[TAG_B];
      long c = latch[TAG_C];
      long d = latch[TAG_D];
      long sum = (program == Program.TWO_AXIS) ? a * a + b * b : a * c + b * d;
      long value = (long) Math.sqrt((double) Math.abs(sum));

      if (substrate) {
        Canon.onSubstrateWrite(W);
      }
      out.collect(rec(slot, value, TAG_A));
    }
  }

  /**
   * Etap publiczny monitora, ktory czyta gotowy substrat: odpowiednik `m_i :- PUSH_STREAM(...)`
   * w planie RetractorDB. Nie wnosi bajtow do licznika — jego wynik jest rekordem publicznym.
   */
  public static class MonitorOutput extends RichMapFunction<Tuple3<Long, Long, Integer>, Tuple3<Long, Long, Integer>> {
    @Override
    public Tuple3<Long, Long, Integer> map(Tuple3<Long, Long, Integer> in) {
      return in;
    }
  }

  /** Per-monitorowy sink: MIANOWNIK metryki. Poza badanym podplanem (§10). */
  public static class MonitorSink extends RichSinkFunction<Tuple3<Long, Long, Integer>> {
    private final String path;
    private final String monitor;
    private transient BufferedWriter writer;

    public MonitorSink(String path, String monitor) {
      this.path = path;
      this.monitor = monitor;
    }

    @Override
    public void open(OpenContext ctx) throws Exception {
      writer = new BufferedWriter(new FileWriter(path));
    }

    @Override
    public void invoke(Tuple3<Long, Long, Integer> r) throws Exception {
      Canon.onPublicAppend();
      writer.write(monitor + "," + r.f0 + "," + r.f1);
      writer.newLine();
    }

    @Override
    public void close() throws Exception {
      if (writer != null) {
        writer.close();
      }
    }
  }

  //
  // ─── Pomoc wspolna dla trzech jobow ─────────────────────────────────────────────────────
  //

  public static int[] loadInts(String path) throws Exception {
    List<Integer> values = new ArrayList<>();
    for (String line : Files.readAllLines(Paths.get(path))) {
      for (String token : line.trim().split("\\s+")) {
        if (!token.isEmpty()) {
          values.add(Integer.parseInt(token));
        }
      }
    }
    int[] out = new int[values.size()];
    for (int i = 0; i < out.length; i++) {
      out[i] = values.get(i);
    }
    return out;
  }

  public static boolean flag(String[] args, String key) {
    for (String a : args) {
      if (a.equals(key)) {
        return true;
      }
    }
    return false;
  }

  /**
   * Wartosci zrodla: plik generatora, jesli podany i istnieje, inaczej deterministyczna rampa.
   * Rampa wystarcza do zbudowania planu (ten krok nie mierzy i nie sprawdza wartosci);
   * kampania P6 podaje pliki jawnie, a liczba rekordow jest zamrozona w predeklaracji.
   */
  public static int[] loadOrRamp(String path) throws Exception {
    if (path != null && Files.exists(Paths.get(path))) {
      return loadInts(path);
    }
    int[] ramp = new int[64];
    for (int i = 0; i < ramp.length; i++) {
      ramp[i] = i + 1;
    }
    return ramp;
  }

  public static String arg(String[] args, String key, String def) {
    for (int i = 0; i < args.length - 1; i++) {
      if (args[i].equals(key)) {
        return args[i + 1];
      }
    }
    return def;
  }

  /**
   * Alokacja monitorow na postacie — regula zamrozona przez czlowieka 2026-08-08
   * (SZKIC_RODZIN.md §3.3): `F(Q) = min(F_max, floor(Q/2))`, monitory rozdzielone rowno
   * miedzy pierwsze `F(Q)` postaci w zamrozonej kolejnosci; przy `F(Q) <= 1` wszystkie
   * monitory dostaja postac pierwsza.
   */
  public static int formsForQ(int q, int fMax) {
    return Math.max(1, Math.min(fMax, q / 2));
  }

  /** Numer postaci (0-based) dla monitora `i` przy `q` monitorach i `fMax` postaciach. */
  public static int formOf(int i, int q, int fMax) {
    int forms = formsForQ(q, fMax);
    return (i * forms) / q;
  }
}
