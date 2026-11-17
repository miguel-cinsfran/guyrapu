# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Tipografías de Windows y corte de avisos en líneas.

Sin wx, sin OBS y sin red. Su única razón para cambiar es medir y acomodar
texto con las tipografías que GDI ve en Windows.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

_DEFAULT_CHARSET = 1
_FW_NORMAL = 400
_FW_BOLD = 700
_OUT_DEFAULT_PRECIS = 0
_CLIP_DEFAULT_PRECIS = 0
_DEFAULT_QUALITY = 0
_DEFAULT_PITCH_AND_FAMILY = 0
_LF_FACESIZE = 32
_LF_FULLFACESIZE = 64


class _LOGFONTW(ctypes.Structure):
    _fields_ = [
        ("lfHeight", wintypes.LONG),
        ("lfWidth", wintypes.LONG),
        ("lfEscapement", wintypes.LONG),
        ("lfOrientation", wintypes.LONG),
        ("lfWeight", wintypes.LONG),
        ("lfItalic", wintypes.BYTE),
        ("lfUnderline", wintypes.BYTE),
        ("lfStrikeOut", wintypes.BYTE),
        ("lfCharSet", wintypes.BYTE),
        ("lfOutPrecision", wintypes.BYTE),
        ("lfClipPrecision", wintypes.BYTE),
        ("lfQuality", wintypes.BYTE),
        ("lfPitchAndFamily", wintypes.BYTE),
        ("lfFaceName", ctypes.c_wchar * _LF_FACESIZE),
    ]


class _ENUMLOGFONTEXW(ctypes.Structure):
    _fields_ = [
        ("elfLogFont", _LOGFONTW),
        ("elfFullName", ctypes.c_wchar * _LF_FULLFACESIZE),
        ("elfStyle", ctypes.c_wchar * _LF_FACESIZE),
        ("elfScript", ctypes.c_wchar * _LF_FACESIZE),
    ]


_PROCEDIMIENTO = ctypes.WINFUNCTYPE(
    ctypes.c_int, ctypes.POINTER(_ENUMLOGFONTEXW), ctypes.c_void_p,
    wintypes.DWORD, wintypes.LPARAM)


def _gdi32():
    biblioteca = ctypes.WinDLL("gdi32", use_last_error=True)
    biblioteca.EnumFontFamiliesExW.argtypes = (
        wintypes.HDC, ctypes.POINTER(_LOGFONTW), _PROCEDIMIENTO,
        wintypes.LPARAM, wintypes.DWORD)
    biblioteca.EnumFontFamiliesExW.restype = ctypes.c_int
    biblioteca.CreateCompatibleDC.argtypes = (wintypes.HDC,)
    biblioteca.CreateCompatibleDC.restype = wintypes.HDC
    biblioteca.CreateFontW.argtypes = (
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD, ctypes.c_wchar_p)
    biblioteca.CreateFontW.restype = wintypes.HFONT
    biblioteca.SelectObject.argtypes = (wintypes.HDC, wintypes.HGDIOBJ)
    biblioteca.SelectObject.restype = wintypes.HGDIOBJ
    biblioteca.GetTextExtentPoint32W.argtypes = (
        wintypes.HDC, ctypes.c_wchar_p, ctypes.c_int,
        ctypes.POINTER(wintypes.SIZE))
    biblioteca.GetTextExtentPoint32W.restype = wintypes.BOOL
    biblioteca.DeleteDC.argtypes = (wintypes.HDC,)
    biblioteca.DeleteDC.restype = wintypes.BOOL
    biblioteca.DeleteObject.argtypes = (wintypes.HGDIOBJ,)
    biblioteca.DeleteObject.restype = wintypes.BOOL
    return biblioteca


def _user32():
    biblioteca = ctypes.WinDLL("user32", use_last_error=True)
    biblioteca.GetDC.argtypes = (wintypes.HWND,)
    biblioteca.GetDC.restype = wintypes.HDC
    biblioteca.ReleaseDC.argtypes = (wintypes.HWND, wintypes.HDC)
    biblioteca.ReleaseDC.restype = ctypes.c_int
    return biblioteca


def familias():
    """Los nombres de las familias instaladas, sin las verticales."""
    nombres = set()

    def visitar(fuente, _metrica, _tipo, _datos):
        nombre = fuente.contents.elfLogFont.lfFaceName
        if not nombre.startswith("@"):
            nombres.add(nombre)
        return 1

    procedimiento = _PROCEDIMIENTO(visitar)
    logfont = _LOGFONTW()
    logfont.lfCharSet = _DEFAULT_CHARSET
    user32 = _user32()
    gdi32 = _gdi32()
    dc = user32.GetDC(None)
    try:
        gdi32.EnumFontFamiliesExW(dc, ctypes.byref(logfont),
                                  procedimiento, 0, 0)
    finally:
        user32.ReleaseDC(None, dc)
    return sorted(nombres)


class _Medidor:
    def __init__(self, gdi32, dc, fuente, anterior):
        self._gdi32 = gdi32
        self._dc = dc
        self._fuente = fuente
        self._anterior = anterior

    def __call__(self, texto):
        medida = wintypes.SIZE()
        self._gdi32.GetTextExtentPoint32W(
            self._dc, texto, len(texto), ctypes.byref(medida))
        return medida.cx

    def __del__(self):
        gdi32 = self._gdi32
        self._gdi32 = None
        if gdi32 is None:
            return
        gdi32.SelectObject(self._dc, self._anterior)
        gdi32.DeleteObject(self._fuente)
        gdi32.DeleteDC(self._dc)


def medidor(familia, px, negrita):
    """La función que mide un texto de una línea con esa fuente."""
    gdi32 = _gdi32()
    dc = gdi32.CreateCompatibleDC(None)
    fuente = gdi32.CreateFontW(
        int(px), 0, 0, 0, _FW_BOLD if negrita else _FW_NORMAL,
        0, 0, 0, _DEFAULT_CHARSET, _OUT_DEFAULT_PRECIS,
        _CLIP_DEFAULT_PRECIS, _DEFAULT_QUALITY, _DEFAULT_PITCH_AND_FAMILY,
        familia)
    anterior = gdi32.SelectObject(dc, fuente)
    return _Medidor(gdi32, dc, fuente, anterior)


def _partir_palabra(palabra, limite, medir):
    """Los trozos de una palabra que sola no entra, por caracteres."""
    trozos = []
    actual = ""
    for caracter in palabra:
        candidata = actual + caracter
        if actual and medir(candidata) > limite:
            trozos.append(actual)
            actual = caracter
        else:
            actual = candidata
    trozos.append(actual)
    return trozos


def partir_en_lineas(texto, ancho_max, medir):
    """Reparte el texto en líneas que no pasan del ancho, sin perder palabras."""
    limite = ancho_max if ancho_max > 0 else 1
    lineas = []
    for parrafo in str(texto).split("\n"):
        palabras = parrafo.split()
        if not palabras:
            lineas.append("")
            continue
        actual = ""
        for palabra in palabras:
            candidata = f"{actual} {palabra}" if actual else palabra
            if medir(candidata) <= limite:
                actual = candidata
                continue
            if actual:
                lineas.append(actual)
            if medir(palabra) <= limite:
                actual = palabra
            else:
                trozos = _partir_palabra(palabra, limite, medir)
                lineas.extend(trozos[:-1])
                actual = trozos[-1]
        lineas.append(actual)
    return lineas
