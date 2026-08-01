# Manifest K22v4

| Pole | Wartość |
|---|---|
| Identyfikator | `results_20260801_K22v4` |
| Branch eksperymentu | `experiment/20260801_K22` |
| Pilot baz | `rdb-experiment@8ca125806a6f302eb3cc51636110d784f4a24390` |
| Korpus wariantów | 36 rdzeni identycznych z `rdb-experiment@2b31d90ffefc1110950d8d5d22a62fc9d58a8bf9` |
| Silnik | `retractordb@dd733e3792fbcd5727db244b802610a6d710b8dc` |
| Plan | `paper-arXiv@236ef97` |
| Zamrożenie aparatury | `rdb-experiment@3eada1230c638e755b5b178a19f333a23e2ecb0d` |
| Worker RT | nieużywany |
| Python | zapisywany przez `freeze_check.sh` |
| Java/Flink | zapisywane przez `freeze_check.sh` |
| `xretractor` | ścieżka, SHA-256 i `--build-info` zapisywane przez `freeze_check.sh` |

Hash dziewięciu rdzeni bazowych oraz środowiska powstaje przed wariantami w
`results/environment.tsv` i `results/base_sha256.tsv`.

Zamrożone wartości oczekiwane baz:

```text
d8416e7edefdcfcf85f483bc9ed30d366bf793746657f8cad93d37a61fb5b8d7  F1/flink
f4068f9bd9b9af1b0bf15ae9336520aef0ddd36a74ff0710c032649eb7ac0d29  F1/python
87071c253b010fb75b9f78dcbc20967880bab40e89f71abd28d3314de29cfc03  F1/rql
9727e8b1826a847ad38a4b8d42e000b370dabc2acf38e68130d189f47889abdb  F2/flink
fea30a7397ad0b9d0e6f0aac692dd957573bd1399aafb5fcd7adafb0e0f93c96  F2/python
b1f17b0e7dd5641c822147c2b6f9ebdc9dc0e7e7fe3008316c8968cff9d09046  F2/rql
e15e5ff1e28cf40a74527b4f3577b3cd1454ce64fc2511f3e9dafb68580e80df  F3/flink
489c8299a663c704a423cb8ca3a0c3564a9a53d5843bb0373e2b390900cf7aef  F3/python
373c22b73a93447741371a088112e1eb231399ff3cbc1118a8c570f1da16b26e  F3/rql
```
