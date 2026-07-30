# Stan maszyny -- PRZED badaniem

- data: 2026-07-31T10:32:29+02:00
- badanie: experiment=results_20260730_K6c campaign=ablation study_id=1 rodzina=W2
- parametry: reps=15 scale=12 f_phi generatora=180 Hz
- budzet slotow per komorka: W2_Q01=1440 slotow@180 Hz; W2_Q08=1440 slotow@180 Hz; W2_Q32=1440 slotow@180 Hz
- commit kodu: e1e5181141f96965da4a092f7e7191f8cb0b2748
- branch wynikow: experiment/20260730_K6

## uname
```
Linux pi400 6.8.0-2049-raspi-realtime #50-Ubuntu SMP PREEMPT_RT Mon Jun 29 16:03:02 UTC 2026 aarch64 aarch64 aarch64 GNU/Linux
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
CPU(s) scaling MHz:                      100%
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
Mem:           3.7Gi       316Mi       2.2Gi        13Mi       1.3Gi       3.4Gi
Swap:             0B          0B          0B
```
## Load average
```
0.52 0.72 0.70 1/243 19048
```
## Temperatura
```
/sys/class/thermal/thermal_zone0/temp: 38459 m°C
throttled: throttled=0x0
```
## Kernel cmdline
```
coherent_pool=1M 8250.nr_uarts=1 snd_bcm2835.enable_headphones=0 snd_bcm2835.enable_hdmi=1 snd_bcm2835.enable_hdmi=0  smsc95xx.macaddr=E4:5F:01:2D:A9:EB vc_mem.mem_base=0x3ec00000 vc_mem.mem_size=0x40000000  console=ttyS0,115200 multipath=off dwc_otg.lpm_enable=0 console=tty1 root=LABEL=writable rootfstype=ext4 rootwait fixrtc cfg80211.ieee80211_regdom=PL ds=nocloud;i=rpi-imager-1784124660514 isolcpus=3 nohz_full=3 rcu_nocbs=3
```
## Governor CPU
```
cpu0: governor=performance cur=1800000 kHz
cpu1: governor=performance cur=1800000 kHz
cpu2: governor=performance cur=1800000 kHz
cpu3: governor=performance cur=1800000 kHz
```
