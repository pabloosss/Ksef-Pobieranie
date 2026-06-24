CO TO NAPRAWIA
- blad przy klikaniu "Otwórz KSeF":
  No module named selenium.webdriver.edge.webdriver

CO ZROBIC
1. Rozpakuj ten ZIP.
2. Podmien w swoim folderze plik build_exe.bat na ten z paczki
   albo zmien nazwe build_exe_fix_selenium.bat na build_exe.bat.
3. Uruchom nowy BAT.
4. Zbuduj EXE jeszcze raz.
5. Odpal nowy plik:
   dist\Ksef-Pobieranie.exe

WAZNE
- logo.png ma lezec obok pliku EXE albo obok plikow zrodlowych przed buildem.
- Jezeli nadal bedzie blad po przebudowie, najlepiej zrob build na Pythonie 3.12.
