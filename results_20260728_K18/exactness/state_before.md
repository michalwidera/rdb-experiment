# Stan maszyny — przed badaniem

- data: 2026-07-28T14:53:31+02:00
- kod: `master@bc37186ac87cb944d76cf74c7be92706a4a3a87f`
- branch wynikow: `experiment/20260728_K18`
- samples: 20000

## Binarka

```
[warning: probe benchmark build]

/home/michal/retractordb/build/Release-Probe/src/retractor/xretractor - compiler & data processing tool.

Usage: /home/michal/retractordb/build/Release-Probe/src/retractor/xretractor queryfile [option]

Available options:
  -h [ --help ]               Show program options
  -b [ --build-info ]         show optimizer build configuration
  -c [ --onlycompile ]        compile only mode
  -q [ --queryfile ] arg      query set file
  -r [ --quiet ]              no output on screen, skip presenter
  -s [ --status ]             check service status
  -v [ --verbose ]            verbose mode (show stream params)
  -x [ --xqrywait ]           wait with processing for first query
  -k [ --noanykey ]           do not wait for any key to terminate
  -j [ --service ]            service mode: log to stderr (journald), no log 
                              file
  -t [ --realtime ]           enable real-time scheduling (SCHED_FIFO, 
                              mlockall, absolute wakeup)
  -g [ --config ] arg         config file (TOML); overrides search
  -m [ --llimitqry ] arg (=0) loop iteration limit, 0 - no limit
Branch: master:bc37186, Code compiler: GNU Ver. 14.2.0, Build time: 2607281432, Type: Release
Log: /tmp/xretractor.log
This software is licensed under the MIT License and is provided ‘as is’,
without warranty of any kind. For more information, see the LICENSE file.
```

## Build info

```
RDB_OPT_DEDUP_SUBSTRATES=ON
RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON
RDB_OPT_COMMUTATIVE_ADD=ON
RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON
RDB_BENCH_PROBE=ON
```

## System

```
Linux pi400 6.8.0-2049-raspi-realtime #50-Ubuntu SMP PREEMPT_RT Mon Jun 29 16:03:02 UTC 2026 aarch64 aarch64 aarch64 GNU/Linux

coherent_pool=1M 8250.nr_uarts=1 snd_bcm2835.enable_headphones=0 snd_bcm2835.enable_hdmi=1 snd_bcm2835.enable_hdmi=0  smsc95xx.macaddr=E4:5F:01:2D:A9:EB vc_mem.mem_base=0x3ec00000 vc_mem.mem_size=0x40000000  console=ttyS0,115200 multipath=off dwc_otg.lpm_enable=0 console=tty1 root=LABEL=writable rootfstype=ext4 rootwait fixrtc cfg80211.ieee80211_regdom=PL ds=nocloud;i=rpi-imager-1784124660514 isolcpus=3 nohz_full=3 rcu_nocbs=3
```
