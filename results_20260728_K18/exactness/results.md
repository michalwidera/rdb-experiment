# K18 exactness/replay — wynik

- kod: `master@bc37186ac87cb944d76cf74c7be92706a4a3a87f`
- branch wynikow: `experiment/20260728_K18`
- samples: 20000
- replay: 2 przebiegi, 17 strumieni, 67 plikow artefaktow
- round-trip: `a2 == a` i `b2 == b` bez rekordu zastepczego

## Replay

```
IDENTYCZNY          STREAM_ADD_STREAM_ADD_mlii_v1_mwi
IDENTYCZNY          STREAM_ADD_STREAM_ADD_mlii_v1_mwi.desc
IDENT-PO-TIMESTAMP  STREAM_ADD_STREAM_ADD_mlii_v1_mwi.meta
IDENTYCZNY          STREAM_ADD_STREAM_ADD_mlii_v1_mwi.shadow
IDENTYCZNY          STREAM_ADD_mlii_v1
IDENTYCZNY          STREAM_ADD_mlii_v1.desc
IDENT-PO-TIMESTAMP  STREAM_ADD_mlii_v1.meta
IDENTYCZNY          STREAM_ADD_mlii_v1.shadow
IDENTYCZNY          bp_acc
IDENTYCZNY          bp_acc.desc
IDENT-PO-TIMESTAMP  bp_acc.meta
IDENTYCZNY          bp_acc.shadow
IDENTYCZNY          bp_out
IDENTYCZNY          bp_out.desc
IDENT-PO-TIMESTAMP  bp_out.meta
IDENTYCZNY          bp_out.shadow
IDENTYCZNY          bp_win
IDENTYCZNY          bp_win.desc
IDENT-PO-TIMESTAMP  bp_win.meta
IDENTYCZNY          bp_win.shadow
IDENTYCZNY          bpf.desc
IDENTYCZNY          d_acc
IDENTYCZNY          d_acc.desc
IDENT-PO-TIMESTAMP  d_acc.meta
IDENTYCZNY          d_acc.shadow
IDENTYCZNY          d_out
IDENTYCZNY          d_out.desc
IDENT-PO-TIMESTAMP  d_out.meta
IDENTYCZNY          d_out.shadow
IDENTYCZNY          detect_out
IDENTYCZNY          detect_out.desc
IDENT-PO-TIMESTAMP  detect_out.meta
IDENTYCZNY          detect_out.shadow
IDENTYCZNY          df.desc
IDENTYCZNY          ecg.desc
IDENTYCZNY          mlii
IDENTYCZNY          mlii.desc
IDENT-PO-TIMESTAMP  mlii.meta
IDENTYCZNY          mlii.shadow
IDENTYCZNY          mlii_win
IDENTYCZNY          mlii_win.desc
IDENT-PO-TIMESTAMP  mlii_win.meta
IDENTYCZNY          mlii_win.shadow
IDENTYCZNY          mwi
IDENTYCZNY          mwi.desc
IDENT-PO-TIMESTAMP  mwi.meta
IDENTYCZNY          mwi.shadow
IDENTYCZNY          mwi_long
IDENTYCZNY          mwi_long.desc
IDENT-PO-TIMESTAMP  mwi_long.meta
IDENTYCZNY          mwi_long.shadow
IDENTYCZNY          mwi_thr
IDENTYCZNY          mwi_thr.desc
IDENT-PO-TIMESTAMP  mwi_thr.meta
IDENTYCZNY          mwi_thr.shadow
IDENTYCZNY          mwi_win
IDENTYCZNY          mwi_win.desc
IDENT-PO-TIMESTAMP  mwi_win.meta
IDENTYCZNY          mwi_win.shadow
IDENTYCZNY          sq_out
IDENTYCZNY          sq_out.desc
IDENT-PO-TIMESTAMP  sq_out.meta
IDENTYCZNY          sq_out.shadow
IDENTYCZNY          v1
IDENTYCZNY          v1.desc
IDENT-PO-TIMESTAMP  v1.meta
IDENTYCZNY          v1.shadow
```

## Round-trip

```
c[2i] == b[i]: True
c[2i+1] == a[i]: True
a2 == a (bez rekordu zastepczego): True
b2 == b: True
wystarczajacy prefiks a2: True
wystarczajacy prefiks b2: True
records: a=19999 b=19999 c=39994 a2=19995 b2=19996
first: a=938 a2=938 b=916 b2=916
VERDICT: OK
```
