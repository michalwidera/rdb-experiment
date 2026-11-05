// R603 - mikrotest mechanizmu H-a bez silnika i bez korpusu (pi400, Cortex-A72, jadro 6.8 PREEMPT_RT).
//
// Pytanie: czy munmap wspoldzielonego segmentu /dev/shm przez watek na rdzeniu 0 kosztuje watek
// tego samego procesu na izolowanym rdzeniu 3, i czy koszt znika, gdy munmap idzie w kawalkach
// ponizej progu 512 stron (__flush_tlb_range -> flush_tlb_mm w arch/arm64/include/asm/tlbflush.h).
//
// Watek S ("slot", SCHED_FIFO, rdzen 3): co --period-us budzi sie clock_nanosleep(TIMER_ABSTIME),
// czyta grupe licznikow PMU (odcinek "pobudka" = od konca poprzedniej iteracji do pobudki),
// dotyka --pages stron prywatnego bufora (odczyt+zapis 1 bajtu na strone, kolejnosc rosnaca),
// czyta liczniki ponownie (odcinek "praca") i zapisuje wiersz do pamieci.
// Watek R ("zwalniajacy", SCHED_OTHER, rdzen 0): --events razy: tworzy segment --seg-mib MiB
// w /dev/shm (ftruncate + posix_fallocate, jak boost 1.91), mapuje MAP_SHARED, zapisuje kazda
// strone (strony brudne, jak kolejka po zapelnieniu), czeka --settle-ms, a potem zwalnia:
// munmap calosci (tryb whole) albo kawalkami po --chunk-kib KiB rosnaco (tryb chunk), i unlink.
// Tryb kolejnych zdarzen: ABBA (whole, chunk, chunk, whole, ...), zeby dryf nie faworyzowal trybu.
// Po zwolnieniu czeka --gap-ms przed nastepnym zdarzeniem.
//
// Wyjscie: <out>_slots.csv i <out>_events.csv (czasy CLOCK_MONOTONIC w ns). Analiza: analyze_microtest.py.
// Wymaga cap_perfmon (perf_event_paranoid=4) i cap_sys_nice (SCHED_FIFO); binarka nie w /dev/shm (nosuid).
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/perf_event.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#define NEV 6
// L1D_TLB_REFILL, L1I_TLB_REFILL, L2D_CACHE, L2D_CACHE_REFILL, L1D_CACHE_REFILL, INST_RETIRED
static const uint64_t kEvents[NEV] = {0x05, 0x02, 0x16, 0x17, 0x03, 0x08};
static const char *kNames[NEV] = {"l1d_tlb_refill", "l1i_tlb_refill", "l2d_cache", "l2d_cache_refill",
                                  "l1d_cache_refill", "inst_retired"};

struct pmu_read {
  uint64_t nr, enabled, running, v[NEV];
};

struct slot_row {
  int64_t deadline, wake, end;
  int64_t wake_cnt[NEV], work_cnt[NEV];
  int valid;  // 0 = grupa multipleksowana albo odczyt nieudany
};

struct event_row {
  int mode;  // 0 whole, 1 chunk
  int64_t t_create, t_begin, t_munmap_end, t_end;
};

static long period_us = 1250, pages = 16, seg_mib = 8, chunk_kib = 1024, settle_ms = 200, gap_ms = 300, events = 80;
static atomic_int stop_flag;
static struct slot_row *slots;
static long nslots, maxslots;

static int64_t now_ns(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static void die(const char *what) {
  perror(what);
  exit(2);
}

static int pmu_open(void) {
  int leader = -1;
  for (int i = 0; i < NEV; i++) {
    struct perf_event_attr a;
    memset(&a, 0, sizeof a);
    a.size = sizeof a;
    a.type = PERF_TYPE_RAW;
    a.config = kEvents[i];
    a.disabled = i == 0;
    a.exclude_hv = 1;
    a.read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
    int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, leader, 0);
    if (fd < 0) die("perf_event_open");
    if (i == 0) leader = fd;
  }
  if (ioctl(leader, PERF_EVENT_IOC_ENABLE, PERF_IOC_FLAG_GROUP)) die("PERF_EVENT_IOC_ENABLE");
  return leader;
}

static int pmu_read(int fd, struct pmu_read *r) {
  return read(fd, r, sizeof *r) == (ssize_t)sizeof *r && r->nr == NEV && r->enabled == r->running;
}

static void pin(int cpu) {
  cpu_set_t set;
  CPU_ZERO(&set);
  CPU_SET(cpu, &set);
  if (pthread_setaffinity_np(pthread_self(), sizeof set, &set)) die("pthread_setaffinity_np");
}

static void *slot_thread(void *arg) {
  (void)arg;
  pin(3);
  struct sched_param sp = {.sched_priority = 80};
  if (pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp)) die("SCHED_FIFO");
  volatile char *buf = mmap(NULL, (size_t)pages * 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_POPULATE, -1, 0);
  if (buf == MAP_FAILED) die("mmap bufora");
  int fd = pmu_open();
  struct pmu_read prev, w, e;
  int ok_prev = pmu_read(fd, &prev);
  struct timespec next;
  clock_gettime(CLOCK_MONOTONIC, &next);
  while (!atomic_load(&stop_flag) && nslots < maxslots) {
    next.tv_nsec += period_us * 1000;
    while (next.tv_nsec >= 1000000000L) {
      next.tv_nsec -= 1000000000L;
      next.tv_sec++;
    }
    while (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL) == EINTR) {
    }
    struct slot_row *row = &slots[nslots];
    row->wake = now_ns();
    row->deadline = (int64_t)next.tv_sec * 1000000000LL + next.tv_nsec;
    int ok_w = pmu_read(fd, &w);
    for (long i = 0; i < pages; i++) buf[i * 4096] += 1;
    row->end = now_ns();
    int ok_e = pmu_read(fd, &e);
    row->valid = ok_prev && ok_w && ok_e;
    for (int k = 0; k < NEV; k++) {
      row->wake_cnt[k] = (int64_t)(w.v[k] - prev.v[k]);
      row->work_cnt[k] = (int64_t)(e.v[k] - w.v[k]);
    }
    prev = e;
    ok_prev = ok_e;
    nslots++;
  }
  return NULL;
}

static void sleep_ms(long ms) {
  struct timespec ts = {ms / 1000, (ms % 1000) * 1000000L};
  nanosleep(&ts, NULL);
}

int main(int argc, char **argv) {
  const char *out = NULL;
  for (int i = 1; i + 1 < argc; i += 2) {
    long v = strtol(argv[i + 1], NULL, 10);
    if (!strcmp(argv[i], "--period-us")) period_us = v;
    else if (!strcmp(argv[i], "--pages")) pages = v;
    else if (!strcmp(argv[i], "--seg-mib")) seg_mib = v;
    else if (!strcmp(argv[i], "--chunk-kib")) chunk_kib = v;
    else if (!strcmp(argv[i], "--settle-ms")) settle_ms = v;
    else if (!strcmp(argv[i], "--gap-ms")) gap_ms = v;
    else if (!strcmp(argv[i], "--events")) events = v;
    else if (!strcmp(argv[i], "--out")) out = argv[i + 1];
    else {
      fprintf(stderr, "nieznana opcja %s\n", argv[i]);
      return 2;
    }
  }
  if (out == NULL) {
    fprintf(stderr, "uzycie: %s --out PREFIKS [--pages N] [--seg-mib M] [--chunk-kib K] [--events E] ...\n", argv[0]);
    return 2;
  }
  if (mlockall(MCL_CURRENT | MCL_FUTURE)) die("mlockall");
  maxslots = (long)((events * (settle_ms + gap_ms + 100) + 3000) * 1000 / period_us) + 1000;
  slots = calloc((size_t)maxslots, sizeof *slots);
  struct event_row *ev = calloc((size_t)events, sizeof *ev);
  if (slots == NULL || ev == NULL) die("calloc");
  pin(0);
  pthread_t st;
  if (pthread_create(&st, NULL, slot_thread, NULL)) die("pthread_create");
  sleep_ms(1000);  // rozbieg watku S
  const size_t seg = (size_t)seg_mib << 20, chunk = (size_t)chunk_kib << 10;
  char name[64];
  snprintf(name, sizeof name, "/r603_microtest_%d", getpid());
  for (long n = 0; n < events; n++) {
    const int mode = ((n % 4) == 0 || (n % 4) == 3) ? 0 : 1;  // ABBA
    ev[n].t_create = now_ns();
    int fd = shm_open(name, O_CREAT | O_EXCL | O_RDWR, 0600);
    if (fd < 0) die("shm_open");
    if (ftruncate(fd, (off_t)seg) || posix_fallocate(fd, 0, (off_t)seg)) die("ftruncate/posix_fallocate");
    char *p = mmap(NULL, seg, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (p == MAP_FAILED) die("mmap segmentu");
    close(fd);
    for (size_t off = 0; off < seg; off += 4096) p[off] = (char)n;
    sleep_ms(settle_ms);
    ev[n].mode = mode;
    ev[n].t_begin = now_ns();
    if (mode == 0) {
      if (munmap(p, seg)) die("munmap");
    } else {
      for (size_t off = 0; off < seg; off += chunk)
        if (munmap(p + off, seg - off < chunk ? seg - off : chunk)) die("munmap kawalka");
    }
    ev[n].t_munmap_end = now_ns();
    if (shm_unlink(name)) die("shm_unlink");
    ev[n].t_end = now_ns();
    sleep_ms(gap_ms);
  }
  atomic_store(&stop_flag, 1);
  pthread_join(st, NULL);

  char path[512];
  snprintf(path, sizeof path, "%s_slots.csv", out);
  FILE *f = fopen(path, "w");
  if (f == NULL) die(path);
  fprintf(f, "deadline_ns,wake_ns,end_ns,valid");
  for (int k = 0; k < NEV; k++) fprintf(f, ",wake_%s", kNames[k]);
  for (int k = 0; k < NEV; k++) fprintf(f, ",work_%s", kNames[k]);
  fprintf(f, "\n");
  for (long i = 0; i < nslots; i++) {
    fprintf(f, "%lld,%lld,%lld,%d", (long long)slots[i].deadline, (long long)slots[i].wake, (long long)slots[i].end, slots[i].valid);
    for (int k = 0; k < NEV; k++) fprintf(f, ",%lld", (long long)slots[i].wake_cnt[k]);
    for (int k = 0; k < NEV; k++) fprintf(f, ",%lld", (long long)slots[i].work_cnt[k]);
    fprintf(f, "\n");
  }
  fclose(f);
  snprintf(path, sizeof path, "%s_events.csv", out);
  f = fopen(path, "w");
  if (f == NULL) die(path);
  fprintf(f, "mode,t_create_ns,t_begin_ns,t_munmap_end_ns,t_end_ns\n");
  for (long n = 0; n < events; n++)
    fprintf(f, "%s,%lld,%lld,%lld,%lld\n", ev[n].mode ? "chunk" : "whole", (long long)ev[n].t_create, (long long)ev[n].t_begin, (long long)ev[n].t_munmap_end,
            (long long)ev[n].t_end);
  fclose(f);
  fprintf(stderr, "slots=%ld events=%ld pages=%ld seg_mib=%ld chunk_kib=%ld\n", nslots, events, pages, seg_mib, chunk_kib);
  return 0;
}
