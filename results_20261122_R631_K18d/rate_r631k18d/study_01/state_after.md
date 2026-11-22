# Stan maszyny -- PO badaniu

- data: 2026-11-22T08:36:31+01:00
- badanie: experiment=results_20261122_R631_K18d campaign=rate_r631k18d study_id=1 rate_hz=360 clients=1 samples=20000
- commit kodu: 758be53b3b8339d176dc678f9a75a259b8926925
- branch wynikow: experiment/20261122_R631

## Build xretractor
```
RDB_OPT_DEDUP_SUBSTRATES=ON
RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON
RDB_OPT_COMMUTATIVE_ADD=ON
RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON
RDB_BENCH_PROBE=ON
RDB_OPT_SIMPLIFY_EXPRESSIONS=ON
```
## uname
```
Linux pi400 6.8.0-2049-raspi-realtime #50-Ubuntu SMP PREEMPT_RT Mon Jun 29 16:03:02 UTC 2026 aarch64 aarch64 aarch64 GNU/Linux
```
## dystrybucja
```
PRETTY_NAME="Ubuntu 24.04.4 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.4 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
```
## CPU
```
Architecture:                            aarch64
CPU op-mode(s):                          32-bit, 64-bit
Byte Order:                              Little Endian
CPU(s):                                  4
On-line CPU(s) list:                     0-3
Vendor ID:                               ARM
Model name:                              Cortex-A72
Model:                                   3
Thread(s) per core:                      1
Core(s) per cluster:                     4
Socket(s):                               -
Cluster(s):                              1
Stepping:                                r0p3
CPU(s) scaling MHz:                      89%
CPU max MHz:                             1800.0000
CPU min MHz:                             600.0000
BogoMIPS:                                108.00
Flags:                                   fp asimd evtstrm crc32 cpuid
L1d cache:                               128 KiB (4 instances)
L1i cache:                               192 KiB (4 instances)
L2 cache:                                1 MiB (1 instance)
Vulnerability Gather data sampling:      Not affected
Vulnerability Indirect target selection: Not affected
Vulnerability Itlb multihit:             Not affected
Vulnerability L1tf:                      Not affected
Vulnerability Mds:                       Not affected
Vulnerability Meltdown:                  Not affected
Vulnerability Mmio stale data:           Not affected
Vulnerability Reg file data sampling:    Not affected
Vulnerability Retbleed:                  Not affected
Vulnerability Spec rstack overflow:      Not affected
Vulnerability Spec store bypass:         Vulnerable
Vulnerability Spectre v1:                Mitigation; __user pointer sanitization
Vulnerability Spectre v2:                Vulnerable
Vulnerability Srbds:                     Not affected
Vulnerability Tsa:                       Not affected
Vulnerability Tsx async abort:           Not affected
Vulnerability Vmscape:                   Not affected
```
## Pamiec
```
               total        used        free      shared  buff/cache   available
Mem:           3.7Gi       319Mi       2.5Gi        14Mi       1.0Gi       3.4Gi
Swap:             0B          0B          0B
```
## Fragmentacja pamieci
```
Node 0, zone      DMA   1512    876    685    494    518    405    298    181     63     68     81 
Node 0, zone    DMA32   2967  22582  17410  11651   5987   2762    596    104      1      0      0 
```
## Load average
```
0.72 0.63 1.44 1/238 7145
```
## Temperatura
```
/sys/class/thermal/thermal_zone0/temp: 31154 m°C
throttled: throttled=0x0
```
## Kernel cmdline
```
coherent_pool=1M 8250.nr_uarts=1 snd_bcm2835.enable_headphones=0 snd_bcm2835.enable_hdmi=1 snd_bcm2835.enable_hdmi=0  smsc95xx.macaddr=E4:5F:01:2D:A9:EB vc_mem.mem_base=0x3ec00000 vc_mem.mem_size=0x40000000  console=ttyS0,115200 multipath=off dwc_otg.lpm_enable=0 console=tty1 root=LABEL=writable rootfstype=ext4 rootwait fixrtc cfg80211.ieee80211_regdom=PL ds=nocloud;i=rpi-imager-1784124660514 isolcpus=3 nohz_full=3 rcu_nocbs=3
```
## Governor CPU
```
cpu0: governor=ondemand cur=1500000 kHz min=600000 max=1800000 kHz
cpu1: governor=ondemand cur=1500000 kHz min=600000 max=1800000 kHz
cpu2: governor=ondemand cur=1600000 kHz min=600000 max=1800000 kHz
cpu3: governor=ondemand cur=1600000 kHz min=600000 max=1800000 kHz
```
