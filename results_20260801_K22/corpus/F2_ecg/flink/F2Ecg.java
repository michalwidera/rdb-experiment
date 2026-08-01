// F2 -- niekliniczny potok cech EKG. Rdzen Flink DataStream (stanowy dataflow).
//
// TO NIE JEST DETEKTOR KLINICZNY. Potok cech, bez twierdzen diagnostycznych.
//
// Piec etapow jako osobne operatory (jak w prowenienecji PanTompkinsFlinkJob):
// band-pass 25 -> roznica 5 -> kwadrat/1000 + MWI 30 -> prog 180 -> zlozenie.
//
// Uwaga metodyczna: naiwny dataflow "policz wszystko na biezacych oknach
// i zlacz od razu" NIE jest rownowazny silnikowi. Silnik laczy `mlii[L]`,
// `mwi[L]` i `mwi_thr[L]`, a te powstaja w roznych slotach (L, L-3, L-4).
// Dlatego operator Assemble musi BUFOROWAC po indeksie. W RQL robi to
// `FROM mlii+mwi+mwi_thr`.
//
// Arytmetyka calkowita wg PREDECLARATION.md §4: dzielenie obcina do zera,
// `.avg` to dokladne dzielenie sumy przez liczbe pol, potem obciecie.
// Orientacja okna: win[0] = probka najnowsza (§11.1 E3). Roznica [-1,-2,0,2,1]
// jest ASYMETRYCZNA, wiec zla orientacja rozjedzie sie wlasnie tutaj.
//
// Krotka Tuple5: (n, mliiRaw, stageVal, mwi, thr).
import org.apache.flink.api.common.functions.OpenContext;
import org.apache.flink.api.common.functions.RichFlatMapFunction;
import org.apache.flink.api.java.tuple.Tuple4;
import org.apache.flink.api.java.tuple.Tuple5;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.sink.legacy.RichSinkFunction;
import org.apache.flink.streaming.api.functions.source.legacy.RichSourceFunction;
import org.apache.flink.util.Collector;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class F2Ecg {

  static int truncDiv(long a, long b) {
    long q = a / b; // Java dzieli z obcieciem do zera -- zgodnie z silnikiem
    if (q > Integer.MAX_VALUE || q < Integer.MIN_VALUE) {
      throw new ArithmeticException("wynik " + q + " poza int32");
    }
    return (int) q;
  }

  // CORE_BEGIN
  static class PacedSource extends RichSourceFunction<Tuple5<Long, Integer, Integer, Integer, Integer>> {
    private static final long INTERVAL_NS = 2_777_778L;
    private final int[] mlii;
    private final long slots;
    private volatile boolean running = true;

    PacedSource(int[] mlii, long slots) {
      this.mlii = mlii;
      this.slots = slots;
    }

    @Override
    public void run(SourceContext<Tuple5<Long, Integer, Integer, Integer, Integer>> ctx) throws Exception {
      long t0 = System.nanoTime();
      for (long n = 0; n < slots && running; n++) {
        long deadline = t0 + n * INTERVAL_NS;
        long now = System.nanoTime();
        if (now < deadline) {
          long sleepNs = deadline - now;
          Thread.sleep(sleepNs / 1_000_000L, (int) (sleepNs % 1_000_000L));
        }
        int x = mlii[(int) n];
        ctx.collect(Tuple5.of(n, x, x, 0, 0));
      }
    }

    @Override
    public void cancel() {
      running = false;
    }
  }

  /** Band-pass 25: okno na mliiRaw, splot, /1000. */
  static class BandPass extends RichFlatMapFunction<Tuple5<Long, Integer, Integer, Integer, Integer>,
      Tuple5<Long, Integer, Integer, Integer, Integer>> {
    private static final int WIN = 25;
    private final int[] coef;
    private int[] win;
    private int filled;

    BandPass(int[] coef) {
      this.coef = coef;
    }

    @Override
    public void open(OpenContext ctx) {
      win = new int[WIN];
      filled = 0;
    }

    @Override
    public void flatMap(Tuple5<Long, Integer, Integer, Integer, Integer> in,
        Collector<Tuple5<Long, Integer, Integer, Integer, Integer>> out) {
      for (int k = WIN - 1; k > 0; k--) {
        win[k] = win[k - 1];
      }
      win[0] = in.f1;
      filled = filled + 1;
      if (filled < WIN) {
        return;
      }
      long acc = 0;
      for (int k = 0; k < WIN; k++) {
        acc += (long) win[k] * coef[k];
      }
      out.collect(Tuple5.of(in.f0, in.f1, truncDiv(acc, 1000), 0, 0));
    }
  }

  /** Roznica 5: okno na wyjsciu band-passu, splot bez dzielenia. */
  static class Derivative extends RichFlatMapFunction<Tuple5<Long, Integer, Integer, Integer, Integer>,
      Tuple5<Long, Integer, Integer, Integer, Integer>> {
    private static final int WIN = 5;
    private final int[] coef;
    private int[] win;
    private int filled;

    Derivative(int[] coef) {
      this.coef = coef;
    }

    @Override
    public void open(OpenContext ctx) {
      win = new int[WIN];
      filled = 0;
    }

    @Override
    public void flatMap(Tuple5<Long, Integer, Integer, Integer, Integer> in,
        Collector<Tuple5<Long, Integer, Integer, Integer, Integer>> out) {
      for (int k = WIN - 1; k > 0; k--) {
        win[k] = win[k - 1];
      }
      win[0] = in.f2;
      filled = filled + 1;
      if (filled < WIN) {
        return;
      }
      long acc = 0;
      for (int k = 0; k < WIN; k++) {
        acc += (long) win[k] * coef[k];
      }
      out.collect(Tuple5.of(in.f0, in.f1, truncDiv(acc, 1), 0, 0));
    }
  }

  /** Kwadrat/1000 + MWI 30 (srednia po oknie). */
  static class SquareMwi extends RichFlatMapFunction<Tuple5<Long, Integer, Integer, Integer, Integer>,
      Tuple5<Long, Integer, Integer, Integer, Integer>> {
    private static final int WIN = 30;
    private int[] win;
    private int filled;

    @Override
    public void open(OpenContext ctx) {
      win = new int[WIN];
      filled = 0;
    }

    @Override
    public void flatMap(Tuple5<Long, Integer, Integer, Integer, Integer> in,
        Collector<Tuple5<Long, Integer, Integer, Integer, Integer>> out) {
      long d = in.f2;
      int sq = truncDiv(d * d, 1000);
      for (int k = WIN - 1; k > 0; k--) {
        win[k] = win[k - 1];
      }
      win[0] = sq;
      filled = filled + 1;
      if (filled < WIN) {
        return;
      }
      long sum = 0;
      for (int k = 0; k < WIN; k++) {
        sum += win[k];
      }
      out.collect(Tuple5.of(in.f0, in.f1, sq, truncDiv(sum, WIN), 0));
    }
  }

  /** Prog 180: srednia ruchoma po MWI. */
  static class Threshold extends RichFlatMapFunction<Tuple5<Long, Integer, Integer, Integer, Integer>,
      Tuple5<Long, Integer, Integer, Integer, Integer>> {
    private static final int WIN = 180;
    private int[] win;
    private int filled;

    @Override
    public void open(OpenContext ctx) {
      win = new int[WIN];
      filled = 0;
    }

    @Override
    public void flatMap(Tuple5<Long, Integer, Integer, Integer, Integer> in,
        Collector<Tuple5<Long, Integer, Integer, Integer, Integer>> out) {
      for (int k = WIN - 1; k > 0; k--) {
        win[k] = win[k - 1];
      }
      win[0] = in.f3;
      filled = filled + 1;
      if (filled < WIN) {
        return;
      }
      long sum = 0;
      for (int k = 0; k < WIN; k++) {
        sum += win[k];
      }
      out.collect(Tuple5.of(in.f0, in.f1, in.f2, in.f3, truncDiv(sum, WIN)));
    }
  }

  /**
   * Zlozenie trzech strumieni o ROZNYCH opoznieniach. `mlii[L]` przychodzi
   * w slocie L, `mwi[L]` powstal w slocie L-3, `mwi_thr[L]` w slocie L-4,
   * wiec trzeba je zapamietac po indeksie. To jest obowiazek, ktory w RQL
   * znika w `FROM mlii+mwi+mwi_thr`.
   */
  static class Assemble extends RichFlatMapFunction<Tuple5<Long, Integer, Integer, Integer, Integer>,
      Tuple4<Long, Integer, Integer, Integer>> {
    private Map<Long, Integer> mliiAt;
    private Map<Long, Integer> mwiAt;
    private Map<Long, Integer> thrAt;

    @Override
    public void open(OpenContext ctx) {
      mliiAt = new HashMap<>();
      mwiAt = new HashMap<>();
      thrAt = new HashMap<>();
    }

    @Override
    public void flatMap(Tuple5<Long, Integer, Integer, Integer, Integer> in,
        Collector<Tuple4<Long, Integer, Integer, Integer>> out) {
      long n = in.f0;
      mliiAt.put(n, in.f1);
      mwiAt.put(n + 3, in.f3);
      thrAt.put(n + 4, in.f4);
      Integer raw = mliiAt.get(n);
      Integer mwi = mwiAt.get(n);
      Integer thr = thrAt.get(n);
      if (raw == null || mwi == null || thr == null) {
        return;
      }
      out.collect(Tuple4.of(n, raw - 900, mwi * 5, (mwi - thr * 2) * 5));
      mliiAt.remove(n);
      mwiAt.remove(n);
      thrAt.remove(n);
    }
  }
  // CORE_END

  /** Harness: zapis strumienia kanonicznego K22. Poza rdzeniem, nieliczony. */
  static class CanonicalSink extends RichSinkFunction<Tuple4<Long, Integer, Integer, Integer>> {
    private final String path;
    private final String family;
    private final String variant;
    private transient BufferedWriter writer;

    CanonicalSink(String path, String family, String variant) {
      this.path = path;
      this.family = family;
      this.variant = variant;
    }

    @Override
    public void open(OpenContext ctx) throws Exception {
      writer = new BufferedWriter(new FileWriter(path));
    }

    @Override
    public void invoke(Tuple4<Long, Integer, Integer, Integer> r) throws Exception {
      String p = family + "," + variant + "," + r.f0 + ",qrs_out_";
      writer.write(p + "0," + r.f1 + ",0,0");
      writer.newLine();
      writer.write(p + "1," + r.f2 + ",0,0");
      writer.newLine();
      writer.write(p + "2," + r.f3 + ",0,0");
      writer.newLine();
    }

    @Override
    public void close() throws Exception {
      if (writer != null) {
        writer.close();
      }
    }
  }

  static int[] loadInts(String path) throws Exception {
    List<Integer> vals = new ArrayList<>();
    for (String line : Files.readAllLines(Paths.get(path))) {
      for (String tok : line.trim().split("\\s+")) {
        if (!tok.isEmpty()) {
          vals.add(Integer.parseInt(tok));
        }
      }
    }
    int[] out = new int[vals.size()];
    for (int i = 0; i < out.length; i++) {
      out[i] = vals.get(i);
    }
    return out;
  }

  /** rec205: pary int32 LE (MLII, V1) -- ten sam format co harness Pythona. */
  static int[] loadMlii(String path) throws Exception {
    byte[] raw = Files.readAllBytes(Paths.get(path));
    ByteBuffer buf = ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);
    int n = raw.length / 8;
    int[] mlii = new int[n];
    for (int i = 0; i < n; i++) {
      mlii[i] = buf.getInt(i * 8);
    }
    return mlii;
  }

  public static void main(String[] args) throws Exception {
    String rec = argVal(args, "--rec", null);
    String bpPath = argVal(args, "--bp", null);
    String dPath = argVal(args, "--d", null);
    long slots = Long.parseLong(argVal(args, "--slots", "2240"));
    String out = argVal(args, "--out", "flink.csv");
    String family = argVal(args, "--family", "F2");
    String variant = argVal(args, "--variant", "base");
    if (rec == null || bpPath == null || dPath == null) {
      throw new IllegalArgumentException("Wymagane: --rec --bp --d");
    }

    int[] mlii = loadMlii(rec);
    int[] bpCoef = loadInts(bpPath);
    int[] dCoef = loadInts(dPath);
    if (mlii.length < slots) {
      throw new IllegalArgumentException("za malo probek: " + mlii.length + " < " + slots);
    }

    StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
    env.setParallelism(1);

    // CORE_BEGIN
    DataStream<Tuple5<Long, Integer, Integer, Integer, Integer>> src =
        env.addSource(new PacedSource(mlii, slots));
    src.flatMap(new BandPass(bpCoef))
        .flatMap(new Derivative(dCoef))
        .flatMap(new SquareMwi())
        .flatMap(new Threshold())
        .flatMap(new Assemble())
        .addSink(new CanonicalSink(out, family, variant));
    // CORE_END

    env.execute("k22-f2-ecg");
    System.out.println("OUT " + out);
  }

  static String argVal(String[] args, String key, String def) {
    for (int i = 0; i < args.length - 1; i++) {
      if (args[i].equals(key)) {
        return args[i + 1];
      }
    }
    return def;
  }
}
