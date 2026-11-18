# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Sonda de los eventos de accesibilidad que Windows manda al foco de una lista.

Abre una ventana con un botón, una lista simple, una lista de informe y un
libro con tres páginas, engancha los eventos de foco, selección, nombre y
estado de esa ventana con `SetWinEventHook` fuera de proceso y recorre las
listas con Tab de ida y vuelta. Al final cuenta por entrada cuántos eventos
de foco llegaron y escribe una línea por lista.

No compara ni falla: sirve para saber, sin NVDA, si Windows manda el foco
dos veces. Se corre con `python qa/sonda_foco_listas.py` y, para probar la
anotación de nombre de la aplicación, con `--con-nombre`.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "qa"))
from foco_ventanas import traer_al_frente

EVENTOS = {
    0x8005: "FOCUS",
    0x8006: "SELECTION",
    0x800A: "STATECHANGE",
    0x800C: "NAMECHANGE",
}
WINEVENT_OUTOFCONTEXT = 0
GA_ROOT = 2
VK_TAB = 0x09
VK_SHIFT = 0x10
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1
# IAccessible hereda de IDispatch: get_accName es el método 10 de la vtable.
VTABLE_GET_ACC_NAME = 10
VTABLE_RELEASE = 2
LISTAS = ("ListBox", "ListCtrl", "Listbook")


class VARIANT(ctypes.Structure):
    # Windows completa el hijo del evento y la sonda lo devuelve tal cual:
    # no interpreta sus campos.
    _fields_ = [
        ("vt", wintypes.WORD),
        ("r1", wintypes.WORD),
        ("r2", wintypes.WORD),
        ("r3", wintypes.WORD),
        ("datos", ctypes.c_byte * 16),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _UnionEntrada(ctypes.Union):
    # Windows mide la unión por la entrada de ratón, la más grande; la sonda
    # solo manda teclado y no necesita sus campos.
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("datos", ctypes.c_byte * 32),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _UnionEntrada),
    ]


WINEVENTPROC = ctypes.WINFUNCTYPE(
    None, ctypes.c_void_p, wintypes.DWORD, wintypes.HWND, wintypes.LONG,
    wintypes.LONG, wintypes.DWORD, wintypes.DWORD)


def _nombre_entrada(indice: int) -> str:
    """Cómo se nombra en el resumen el hijo `indice` de la lista."""
    return {0: "la lista", 1: "primera entrada", 2: "segunda",
            3: "tercera"}.get(indice, f"entrada {indice}")


def contar_focos(eventos, ventana):
    """Cuenta los eventos de foco por control y hijo, solo de `ventana`."""
    cuenta = {}
    for evento in eventos:
        if evento["ventana"] != ventana or evento["evento"] != "FOCUS":
            continue
        clave = (evento["control"], int(evento["id_hijo"]))
        cuenta[clave] = cuenta.get(clave, 0) + 1
    return cuenta


def resumen(eventos, ventana, controles=()):
    """Una línea por lista con los focos de cada entrada.

    Los eventos de otra ventana y los que no son de foco no cuentan. Con
    `controles` también sale la línea de las listas que no recibieron foco.
    """
    cuentas = contar_focos(eventos, ventana)
    por_control = {}
    for (control, hijo), cuantos in cuentas.items():
        por_control.setdefault(control, []).append((hijo, cuantos))
    orden = list(controles) if controles else list(por_control)
    lineas = []
    for control in orden:
        entradas = sorted(por_control.get(control, ()))
        if not entradas:
            lineas.append(f"{control}: sin focos")
            continue
        partes = []
        for posicion, (hijo, cuantos) in enumerate(entradas, 1):
            etiqueta = _nombre_entrada(hijo)
            if posicion == 1:
                partes.append(f"{etiqueta} {cuantos} focos")
            else:
                partes.append(f"{etiqueta} {cuantos}")
        lineas.append(f"{control}: " + ", ".join(partes))
    return lineas


def _entrada_tecla(codigo, soltar=False):
    entrada = INPUT()
    entrada.type = INPUT_KEYBOARD
    entrada.ki.wVk = codigo
    entrada.ki.dwFlags = KEYEVENTF_KEYUP if soltar else 0
    return entrada


def _pulsar_tab(user32, con_shift):
    """Manda Tab, o Mayús+Tab, con `SendInput` a la ventana al frente."""
    pasos = []
    if con_shift:
        pasos.append(_entrada_tecla(VK_SHIFT))
    pasos.append(_entrada_tecla(VK_TAB))
    pasos.append(_entrada_tecla(VK_TAB, True))
    if con_shift:
        pasos.append(_entrada_tecla(VK_SHIFT, True))
    arreglo = (INPUT * len(pasos))(*pasos)
    user32.SendInput.argtypes = [
        wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    user32.SendInput(len(pasos), arreglo, ctypes.sizeof(INPUT))


def _nombre_msaa(oleacc, oleaut32, hwnd, id_objeto, id_hijo):
    """El nombre MSAA del objeto del evento, o vacío si no se puede leer."""
    puntero = ctypes.c_void_p()
    hijo = VARIANT()
    resultado = oleacc.AccessibleObjectFromEvent(
        hwnd, id_objeto, id_hijo, ctypes.byref(puntero), ctypes.byref(hijo))
    if resultado < 0 or not puntero:
        return ""
    vtable = ctypes.cast(
        puntero, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    try:
        prototipo = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, VARIANT,
            ctypes.POINTER(ctypes.c_void_p))
        bstr = ctypes.c_void_p()
        if (prototipo(vtable[VTABLE_GET_ACC_NAME])(
                puntero, hijo, ctypes.byref(bstr)) < 0 or not bstr):
            return ""
        try:
            return ctypes.wstring_at(bstr)
        finally:
            oleaut32.SysFreeString(bstr)
    finally:
        soltar = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
        soltar(vtable[VTABLE_RELEASE])(puntero)


class Escucha:
    """Gancho fuera de proceso de los eventos de accesibilidad de una ventana."""

    def __init__(self, hwnd, etiquetas):
        self.hwnd = hwnd
        self.etiquetas = etiquetas
        self.eventos = []
        self._usuario = ctypes.WinDLL("user32")
        self._oleacc = ctypes.WinDLL("oleacc")
        self._oleaut32 = ctypes.WinDLL("oleaut32")
        self._callback = None
        self._hook = None

    def instalar(self):
        self._usuario.SetWinEventHook.argtypes = [
            wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            WINEVENTPROC, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
        self._usuario.SetWinEventHook.restype = ctypes.c_void_p
        self._usuario.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self._usuario.GetAncestor.restype = wintypes.HWND
        self._usuario.UnhookWinEvent.argtypes = [ctypes.c_void_p]
        self._usuario.UnhookWinEvent.restype = wintypes.BOOL
        self._usuario.GetClassNameW.argtypes = [
            wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
        self._oleacc.AccessibleObjectFromEvent.argtypes = [
            wintypes.HWND, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(VARIANT)]
        self._oleacc.AccessibleObjectFromEvent.restype = ctypes.c_long
        self._oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]
        self._callback = WINEVENTPROC(self._al_evento)
        self._hook = self._usuario.SetWinEventHook(
            min(EVENTOS), max(EVENTOS), None, self._callback, 0, 0,
            WINEVENT_OUTOFCONTEXT)
        return bool(self._hook)

    def soltar(self):
        if self._hook:
            self._usuario.UnhookWinEvent(self._hook)
            self._hook = None

    def _clase(self, hwnd):
        buffer = ctypes.create_unicode_buffer(256)
        self._usuario.GetClassNameW(hwnd, buffer, 256)
        return buffer.value or "ventana"

    def _al_evento(self, _hook, evento, hwnd, id_objeto, id_hijo,
                   _hilo, _hora):
        if evento not in EVENTOS or not hwnd:
            return
        if self._usuario.GetAncestor(hwnd, GA_ROOT) != self.hwnd:
            return
        nombre = _nombre_msaa(
            self._oleacc, self._oleaut32, hwnd, id_objeto, id_hijo)
        control = self.etiquetas.get(hwnd) or self._clase(hwnd)
        registro = {
            "ms": int(time.time() * 1000),
            "evento": EVENTOS[evento],
            "ventana": self.hwnd,
            "control": control,
            "id_hijo": int(id_hijo),
            "nombre": nombre,
        }
        self.eventos.append(registro)
        print(f"{registro['ms']} ms {registro['evento']} {control} "
              f"hijo={registro['id_hijo']} nombre={nombre!r}", flush=True)


class Secuencia:
    """Los Tab de ida y vuelta, uno por turno del bucle de la ventana."""

    PASOS = ("tab", "shift", "tab", "tab", "shift", "tab", "tab", "shift",
             "tab")

    def __init__(self, marco, al_terminar, boton):
        self._marco = marco
        self._al_terminar = al_terminar
        self._boton = boton
        self._usuario = ctypes.WinDLL("user32")
        self._paso = 0

    def empezar(self):
        traer_al_frente(self._marco.GetHandle(), os.getpid())
        self._boton.SetFocus()
        self._siguiente()

    def _siguiente(self):
        import wx
        if self._paso >= len(self.PASOS):
            wx.CallLater(600, self._al_terminar)
            return
        if not self._tiene_foco():
            print("El foco no está en la ventana de la sonda: no se pulsa "
                  "Tab.", flush=True)
            wx.CallLater(200, self._al_terminar)
            return
        _pulsar_tab(self._usuario, self.PASOS[self._paso] == "shift")
        self._paso += 1
        wx.CallLater(140, self._siguiente)

    def _tiene_foco(self):
        import wx
        self._usuario.GetForegroundWindow.restype = wintypes.HWND
        if self._usuario.GetForegroundWindow() != self._marco.GetHandle():
            return False
        foco = wx.Window.FindFocus()
        return (foco is not None
                and wx.GetTopLevelParent(foco) is self._marco)


def _crear_ventana(con_nombre):
    import wx

    app = wx.App(False)
    marco = wx.Frame(None, title="Sonda de foco de listas")
    panel = wx.Panel(marco)
    caja = wx.BoxSizer(wx.VERTICAL)
    boton = wx.Button(panel, label="Antes de las listas")
    lista = wx.ListBox(
        panel, choices=["primera", "segunda", "tercera"], style=wx.LB_SINGLE)
    lista.SetSelection(1)
    tabla = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    tabla.InsertColumn(0, "Entrada", width=220)
    for texto in ("primera", "segunda", "tercera"):
        tabla.InsertItem(tabla.GetItemCount(), texto)
    tabla.SetItemState(
        1, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
        wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
    libro = wx.Listbook(panel)
    for texto in ("primera", "segunda", "tercera"):
        pagina = wx.Panel(libro)
        wx.StaticText(pagina, label=texto)
        libro.AddPage(pagina, texto)
    if con_nombre:
        from guyrapu.ui import accesibilidad
        accesibilidad.nombre_accesible(lista, "Lista simple de prueba")
        accesibilidad.nombre_accesible(tabla, "Lista de informe de prueba")
        accesibilidad.nombre_accesible(
            libro.GetListView(), "Libro de prueba")
    for control in (boton, lista, tabla, libro):
        caja.Add(control, 0, wx.EXPAND | wx.ALL, 8)
    panel.SetSizer(caja)
    marco.SetClientSize((520, 460))
    marco.Centre()
    return app, marco, boton, lista, tabla, libro


def _etiquetas(marco, boton, lista, tabla, libro):
    return {
        marco.GetHandle(): "Ventana",
        boton.GetHandle(): "Button",
        lista.GetHandle(): "ListBox",
        tabla.GetHandle(): "ListCtrl",
        libro.GetHandle(): "Listbook",
        libro.GetListView().GetHandle(): "Listbook",
    }


def _informe(escucha, hwnd):
    cuentas = contar_focos(escucha.eventos, hwnd)
    for (control, hijo), cuantos in sorted(cuentas.items()):
        if control in LISTAS:
            print(f"{control} hijo {hijo}: {cuantos} eventos de foco")
    for linea in resumen(escucha.eventos, hwnd, LISTAS):
        print(linea)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Cuenta los eventos de accesibilidad que Windows manda "
                    "al foco de una lista.")
    parser.add_argument(
        "--con-nombre", action="store_true",
        help="Nombra las listas con nombre_accesible, como la aplicación.")
    args = parser.parse_args(argv)
    try:
        import wx
    except ImportError as exc:
        print(f"No se pudo abrir la ventana de la sonda: {exc}")
        return 2
    ctypes.WinDLL("ole32").OleInitialize(None)
    try:
        app, marco, boton, lista, tabla, libro = _crear_ventana(
            args.con_nombre)
    except Exception as exc:
        print(f"No se pudo abrir la ventana de la sonda: {exc}")
        return 2
    escucha = Escucha(marco.GetHandle(),
                      _etiquetas(marco, boton, lista, tabla, libro))
    try:
        enganchado = escucha.instalar()
    except Exception as exc:
        print(f"No se pudieron enganchar los eventos: {exc}")
        return 2
    if not enganchado:
        print("No se pudieron enganchar los eventos de accesibilidad.")
        return 2

    def terminar():
        _informe(escucha, marco.GetHandle())
        escucha.soltar()
        marco.Destroy()
        app.ExitMainLoop()

    secuencia = Secuencia(marco, terminar, boton)
    marco.Show()
    wx.CallLater(800, secuencia.empezar)
    app.MainLoop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
