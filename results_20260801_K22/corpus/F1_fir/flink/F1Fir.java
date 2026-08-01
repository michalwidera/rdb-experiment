// F1 -- FIR z oknem i redukcja. Rdzen Flink DataStream (stanowy dataflow).
//
// Model: topologia ogolnego dataflow ze stanowymi operatorami. Okno i ogon sa
// obowiazkiem autora operatora; pacing jest obowiazkiem zrodla.
//
// Arytmetyka: CALKOWITA wg semantyki silnika (PREDECLARATION.md §4).
// Java `/` na int obcina do zera -- zgodnie z silnikiem. Suma liczona w `long`
// i sprawdzana wzgledem int32: zakres danych wyklucza przepelnienie, wiec
// wyjscie poza niego jest bledem doboru danych, nie wynikiem.
//
// Orientacja okna: win[0] to probka NAJNOWSZA (PREDECLARATION.md §11.1 E3).
//
// Wczytanie plikow i zapis strumienia kanonicznego to harness -- poza
// znacznikami CORE.
import org.apache.flink.api.common.functions.OpenContext;
import org.apache.flink.api.common.functions.RichFlatMapFunction;
import org.apache.flink.api.java.tuple.Tuple2;
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

public class F1Fir {

  // CORE_BEGIN
  static class PacedSource extends RichSourceFunction<Tuple2<Long, Integer>> {
    private static final long INTERVAL_NS = 1_000_000L;
    private final int[] samples;
    private final long slots;
    private volatile boolean running = true;

    PacedSource(int[] samples, long slots) {
      this.samples = samples;
      this.slots = slots;
    }

    @Override
    public void run(SourceContext<Tuple2<Long, Integer>> ctx) throws Exception {
      long t0 = System.nanoTime();
      for (long n = 0; n < slots && running; n++) {
        long deadline = t0 + n * INTERVAL_NS;
        long now = System.nanoTime();
        if (now < deadline) {
          long sleepNs = deadline - now;
          Thread.sleep(sleepNs / 1_000_000L, (int) (sleepNs % 1_000_000L));
        }
        ctx.collect(Tuple2.of(n, samples[(int) n]));
      }
    }

    @Override
    public void cancel() {
      running = false;
    }
  }

  static class Fir extends RichFlatMapFunction<Tuple2<Long, Integer>, Tuple2<Long, Integer>> {
    private static final int WIN = 26;
    private final int[] coef;
    private int[] win;

    Fir(int[] coef) {
      this.coef = coef;
    }

    @Override
    public void open(OpenContext ctx) {
      win = new int[WIN];
    }

    @Override
    public void flatMap(Tuple2<Long, Integer> in, Collector<Tuple2<Long, Integer>> out) {
      for (int k = WIN - 1; k > 0; k--) {
        win[k] = win[k - 1];
      }
      win[0] = in.f1;
      if (in.f0 < WIN - 1) {
        return;
      }
      long acc = 0;
      for (int k = 0; k < WIN; k++) {
        acc += (long) win[k] * coef[k];
      }
      if (acc > Integer.MAX_VALUE || acc < Integer.MIN_VALUE) {
        throw new ArithmeticException("suma " + acc + " poza int32 -- zakres danych nie wyklucza przepelnienia");
      }
      int y = (int) acc / WIN / 1000;
      out.collect(Tuple2.of(in.f0 + 1, y));
    }
  }
  // CORE_END

  /** Harness: zapis strumienia kanonicznego K22. Poza rdzeniem, nieliczony. */
  static class CanonicalSink extends RichSinkFunction<Tuple2<Long, Integer>> {
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
    public void invoke(Tuple2<Long, Integer> rec) throws Exception {
      writer.write(family + "," + variant + "," + rec.f0 + ",f1_out_0," + rec.f1 + ",0,0");
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

  public static void main(String[] args) throws Exception {
    String source = argVal(args, "--source", null);
    String coefPath = argVal(args, "--coef", null);
    long slots = Long.parseLong(argVal(args, "--slots", "2025"));
    String out = argVal(args, "--out", "flink.csv");
    String family = argVal(args, "--family", "F1");
    String variant = argVal(args, "--variant", "base");
    if (source == null || coefPath == null) {
      throw new IllegalArgumentException("Wymagane: --source --coef");
    }

    int[] samples = loadInts(source);
    int[] coef = loadInts(coefPath);
    if (samples.length < slots) {
      throw new IllegalArgumentException("za malo probek: " + samples.length + " < " + slots);
    }

    StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
    env.setParallelism(1);

    // CORE_BEGIN
    DataStream<Tuple2<Long, Integer>> src = env.addSource(new PacedSource(samples, slots));
    src.flatMap(new Fir(coef)).addSink(new CanonicalSink(out, family, variant));
    // CORE_END

    env.execute("k22-f1-fir");
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
