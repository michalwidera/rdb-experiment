# Stan maszyny — po badaniu

- data: 2026-11-11T12:18:02+01:00
- kod: `dev/muro@16c516f9eb76c473d5ff8510a2a812b8c23a893d`
- branch wynikow: `experiment/20261111_R618`
- samples: 20000

## Binarka

```
[warning: probe benchmark build]

/home/michal/R618/build/Release-Probe/src/retractor/xretractor - compiler & data processing tool.

Usage: /home/michal/R618/build/Release-Probe/src/retractor/xretractor queryfile [option]

Available options:
  -h [ --help ]               Show program options
  -b [ --build-info ]         show optimizer build configuration
  -c [ --onlycompile ]        compile only mode
  -q [ --queryfile ] arg      query set file
  -r [ --quiet ]              no output on screen, skip presenter
  -s [ --status ]             check service status
  -o [ --cleanup ]            remove leftovers of dead instances and exit
  -v [ --verbose ]            verbose mode (show stream params)
  -x [ --xqrywait ]           wait with processing for first query
  -n [ --name ] arg           instance name; own IPC area and lock
  -a [ --autoname ]           generate a docker-style instance name
  -k [ --noanykey ]           do not wait for any key to terminate
  -j [ --service ]            service mode: log to stderr (journald)
  -t [ --realtime ]           enable real-time scheduling
  -f [ --no-clock ]           offline mode: compute slots without waiting
  -u [ --until-eof ]          forces one-shot all sources
  -g [ --config ] arg         config file (TOML); overrides search
  -m [ --llimitqry ] arg (=0) loop iteration limit, 0 - no limit
Branch: dev/muro:16c516f9, Code compiler: GNU Ver. 14.2.0, Build time: 2611111041, Type: Release
Log: /tmp/xretractor.log
Config: Defaults
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
RDB_OPT_SIMPLIFY_EXPRESSIONS=ON
```

## System

```
Linux pi400 6.8.0-2049-raspi-realtime #50-Ubuntu SMP PREEMPT_RT Mon Jun 29 16:03:02 UTC 2026 aarch64 aarch64 aarch64 GNU/Linux

coherent_pool=1M 8250.nr_uarts=1 snd_bcm2835.enable_headphones=0 snd_bcm2835.enable_hdmi=1 snd_bcm2835.enable_hdmi=0  smsc95xx.macaddr=E4:5F:01:2D:A9:EB vc_mem.mem_base=0x3ec00000 vc_mem.mem_size=0x40000000  console=ttyS0,115200 multipath=off dwc_otg.lpm_enable=0 console=tty1 root=LABEL=writable rootfstype=ext4 rootwait fixrtc cfg80211.ieee80211_regdom=PL ds=nocloud;i=rpi-imager-1784124660514 isolcpus=3 nohz_full=3 rcu_nocbs=3
```
