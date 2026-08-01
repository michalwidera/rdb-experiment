# K22v3 — zatrzymanie

- `base/F1`: PASS 2000;
- `base/F2`: PASS 2000;
- `base/F3`: timeout 200 s po wytworzeniu 2966 rekordów (wymagano 2000);
- przyczyna: runner podał 4200 cykli wszystkim F3, choć taki zapas jest
  potrzebny tylko M3/F3;
- D1/D2: nieotwarte i nieobliczone;
- decyzja: nie zmieniać zamrożonej aparatury; K22v4 rozdziela 2850/4200.
