# K22v4 — zatrzymanie

- `base/F1`: PASS 2000;
- `base/F2`: PASS 2000;
- `base/F3`: PASS 2000;
- `M1/F1`: FAIL przed porównaniem wartości; przy indeksie 26 RQL wyemitowało
  poprawną wartość 1974 pod nazwą `f1_out_1`, a Python i Flink pod nazwą
  `channel_2`;
- przyczyna: predeklaracja wymagała nazwy `channel_2`, której nie można nadać
  polu projekcji w RQL; nazwa RQL wynika pozycjonalnie z nazwy strumienia;
- D1/D2: nieotwarte i nieobliczone;
- decyzja: nie zmieniać zamrożonej aparatury; K22v5 ujednolica wyłącznie
  etykietę serializacji Pythona i Flinka do `f1_out_1`.
