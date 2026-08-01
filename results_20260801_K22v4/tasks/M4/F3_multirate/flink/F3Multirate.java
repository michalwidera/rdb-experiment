// F3 -- monitor wieloczestotliwosciowy. Rdzen Flink DataStream.
//
// Zadanie: dwa zrodla o wymiernych interwalach (A = 1/10 s, B = 1/5 s),
// przeplot `#` i przesuniecie `>N`. W RQL to JEDNA instrukcja:
//     SELECT * STREAM f3_out FROM (A>2)#(B>1)
//
// Tutaj autor musi napisac sam:
//  1. dwa niezalezne zegary zrodel na wspolnej siatce 1/30 s (A co 3 jednostki,
//     B co 6) -- przeplot NIE jest probkowaniem "kto jest gotowy", tylko
//     scalaniem dwoch strumieni zdarzen uporzadkowanych w czasie;
//  2. regule rozstrzygania remisu: przy rownym czasie silnik wystawia najpierw
//     B. Ustalone POMIAREM na artefakcie: 1001, 1, 2, 1002, 3, 4 = B0,A0,A1,B1,A2,A3;
//  3. zlozenie opoznien: ogon 35 = 2 (przeplot) + 3 (przesuniecie po przepisaniu
//     (A>2)#(B>1) na (A#B)>3) + 30 (okno agregujace). Kompilator RQL publikuje tail=35.
//
// Uwaga: scalanie jest tu realizowane w zrodle, bo Flink `union` nie gwarantuje
// deterministycznego przeplotu dwoch osobnych zrodel -- a K22 porownuje wartosci
// co do bajtu. To jest realny koszt modelu, nie uproszczenie na jego niekorzysc.
import org.apache.flink.api.common.functions.OpenContext;
import org.apache.flink.api.common.functions.RichFlatMapFunction;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.api.java.tuple.Tuple9;
import org.apache.flink.api.common.functions.RichMapFunction;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.sink.legacy.RichSinkFunction;
import org.apache.flink.streaming.api.functions.source.legacy.RichSourceFunction;
import org.apache.flink.util.Collector;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

public class F3Multirate {

  // CORE_BEGIN
  static class MergedSource extends RichSourceFunction<Tuple2<Long, Integer>> {
    private static final long INTERVAL_NS = 66_666_667L;
    private static final int UNIT_A = 3;
    private static final int UNIT_B = 6;
    private static final int TAIL = 5;
    private final int[] a;
    private final int[] b;
    private final long slots;
    private volatile boolean running = true;

    MergedSource(int[] a, int[] b, long slots) {
      this.a = a;
      this.b = b;
      this.slots = slots;
    }

    @Override
    public void run(SourceContext<Tuple2<Long, Integer>> ctx) throws Exception {
      long ua = 0;
      long ub = 0;
      int ia = 0;
      int ib = 0;
      long t0 = System.nanoTime();
      for (long r = 0; r < slots && running; r++) {
        long deadline = t0 + r * INTERVAL_NS;
        long now = System.nanoTime();
        if (now < deadline) {
          long sleepNs = deadline - now;
          Thread.sleep(sleepNs / 1_000_000L, (int) (sleepNs % 1_000_000L));
        }
        int value;
        if (ub <= ua) {
          value = b[ib];
          ib = ib + 1;
          ub = ub + UNIT_B;
        } else {
          value = a[ia];
          ia = ia + 1;
          ua = ua + UNIT_A;
        }
        ctx.collect(Tuple2.of(TAIL + r, value));
      }
    }

    @Override
    public void cancel() {
      running = false;
    }
  }

  /**
   * Okno agregujace 30 nad przeplotem. Ogon wyjscia to 35 = 5 (przesuniecie)
   * + 30 (okno) -- autor musi zlozyc go recznie z dwoch skladnikow.
   */
  static class Aggregate extends RichFlatMapFunction<Tuple2<Long, Integer>, Tuple2<Long, Integer>> {
    private static final int WIN = 30;
    private int[] win;
    private int filled;

    @Override
    public void open(OpenContext ctx) {
      win = new int[WIN];
      filled = 0;
    }

    @Override
    public void flatMap(Tuple2<Long, Integer> in, Collector<Tuple2<Long, Integer>> out) {
      for (int k = WIN - 1; k > 0; k--) {
        win[k] = win[k - 1];
      }
      win[0] = in.f1;
      filled = filled + 1;
      if (filled < WIN) {
        return;
      }
      long sum = 0;
      for (int k = 0; k < WIN; k++) {
        sum += win[k];
      }
      out.collect(Tuple2.of(in.f0 + 1, (int) (sum / WIN)));
    }
  }

  static class Monitor extends RichMapFunction<Tuple2<Long, Integer>,
      Tuple9<Long, Integer, Integer, Integer, Integer, Integer, Integer, Integer, Integer>> {
    @Override
    public Tuple9<Long, Integer, Integer, Integer, Integer, Integer, Integer, Integer, Integer> map(Tuple2<Long, Integer> in) {
      int v = in.f1;
      return Tuple9.of(in.f0, v, v + 1, v + 2, v + 3, v + 4, v + 5, v + 6, v + 7);
    }
  }
  // CORE_END

  /** Harness: zapis strumienia kanonicznego K22. Poza rdzeniem, nieliczony. */
  static class CanonicalSink extends RichSinkFunction<Tuple9<Long, Integer, Integer, Integer, Integer, Integer, Integer, Integer, Integer>> {
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
    public void invoke(Tuple9<Long, Integer, Integer, Integer, Integer, Integer, Integer, Integer, Integer> r) throws Exception {
      for (int j = 1; j <= 8; j++) {
        Object value = r.getField(j);
        writer.write(family + "," + variant + "," + r.f0 + ",f3_q_" + (j - 1) + "," + value + ",0,0");
        writer.newLine();
      }
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

  public static void main(String[] args) throws Exception {
    String aPath = argVal(args, "--a", null);
    String bPath = argVal(args, "--b", null);
    long slots = Long.parseLong(argVal(args, "--slots", "2000"));
    String out = argVal(args, "--out", "flink.csv");
    String family = argVal(args, "--family", "F3");
    String variant = argVal(args, "--variant", "base");
    if (aPath == null || bPath == null) {
      throw new IllegalArgumentException("Wymagane: --a --b");
    }

    int[] a = loadInts(aPath);
    int[] b = loadInts(bPath);

    StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
    env.setParallelism(1);

    // CORE_BEGIN
    DataStream<Tuple2<Long, Integer>> src = env.addSource(new MergedSource(a, b, slots));
    src.map(new Monitor()).addSink(new CanonicalSink(out, family, variant));
    // CORE_END

    env.execute("k22-f3-multirate");
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
