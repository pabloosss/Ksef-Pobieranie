# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

selenium_datas, selenium_binaries, selenium_hidden = collect_all("selenium")
selenium_hidden += [
    "selenium.webdriver.edge.webdriver",
    "selenium.webdriver.edge.service",
    "selenium.webdriver.edge.options",
    "selenium.webdriver.common.selenium_manager",
]

a = Analysis(
    ["ksef_stable.py"],
    pathex=[],
    binaries=selenium_binaries,
    datas=selenium_datas,
    hiddenimports=selenium_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Ksef-Pobieranie",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
