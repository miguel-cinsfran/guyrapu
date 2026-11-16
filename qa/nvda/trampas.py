# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las ventanas de prueba del carril: una limpia y una trampa por regla.

Cada trampa viola a propósito una sola regla de `reglas.py`, y la limpia
cumple todas. No se registran en la app ni se alcanzan desde ella.

La tabla `VENTANAS` declara el primer control y las acciones de cada una, que
es lo que lee `recorrido.py`. El módulo se puede importar sin wx: las
ventanas se construyen recién en `construir`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def _comando(nombre):
    return [sys.executable, str(Path(__file__).resolve()),
            "--ventana", nombre]


def _datos(nombre, regla, primero, acciones=(), titulo=""):
    return {
        "nombre": nombre,
        "titulo": titulo or f"Ventana de prueba {nombre}",
        "regla": regla,
        "comando": _comando(nombre),
        "primero": primero,
        "acciones": list(acciones),
    }


VENTANAS = {
    "limpia": _datos(
        "limpia", None, "Nombre completo",
        [{"control": "Anunciar", "gesto": "space"},
         {"control": "Mover foco", "gesto": "space"}],
        titulo="Ventana limpia del carril"),
    "sin_nombre": _datos("sin_nombre", "sin_nombre", "Antes"),
    "rol_contenedor": _datos(
        "rol_contenedor", "rol_contenedor", "Zona de prueba"),
    "nombre_repetido": _datos(
        "nombre_repetido", "nombre_repetido", "Volumen"),
    "ingles": _datos("ingles", "ingles", "Cancel"),
    "atajo_repetido": _datos(
        "atajo_repetido", "atajo_repetido", "Activar"),
    "paso_mudo": _datos(
        "paso_mudo", "paso_mudo", "Mudo",
        [{"control": "Mudo", "gesto": "space"}]),
    "foco_perdido": _datos(
        "foco_perdido", "foco_perdido", "Deshabilitar",
        [{"control": "Deshabilitar", "gesto": "space"}]),
    "recorrido": _datos("recorrido", "recorrido", "Entrada"),
}


def _anunciar() -> None:
    from guyrapu.voice.lector import Lector

    Lector().speak("Anuncio de prueba")


def nombre_accesible(control, nombre) -> None:
    """El nombre accesible de la app, con su anotación MSAA."""
    from guyrapu.ui.accesibilidad import nombre_accesible as poner

    poner(control, nombre)


def _construir_sin_nombre(wx, panel, caja, marco):
    campo = wx.TextCtrl(panel)
    nombre_accesible(campo, "Antes")
    caja.Add(campo, 0, wx.EXPAND | wx.ALL, 6)
    boton = wx.BitmapButton(panel, bitmap=wx.Bitmap(16, 16))
    boton.SetName("")
    caja.Add(boton, 0, wx.ALL, 6)
    return campo


def _construir_rol_contenedor(wx, panel, caja, marco):
    class PanelConFoco(wx.Window):

        def AcceptsFocus(self):
            return True

        def AcceptsFocusFromKeyboard(self):
            return True

    zona = PanelConFoco(panel, size=(200, 40))
    nombre_accesible(zona, "Zona de prueba")
    zona.SetCanFocus(True)
    caja.Add(zona, 0, wx.EXPAND | wx.ALL, 6)
    boton = wx.Button(panel, label="Siguiente")
    nombre_accesible(boton, "Siguiente")
    caja.Add(boton, 0, wx.ALL, 6)
    return zona


def _construir_nombre_repetido(wx, panel, caja, marco):
    cuadro = wx.StaticBox(panel, label="Volumen")
    nombre_accesible(cuadro, "Volumen")
    grupo = wx.StaticBoxSizer(cuadro, wx.VERTICAL)
    deslizador = wx.Slider(cuadro, value=50, minValue=0, maxValue=100)
    nombre_accesible(deslizador, "Volumen")
    grupo.Add(deslizador, 0, wx.EXPAND | wx.ALL, 6)
    caja.Add(grupo, 0, wx.EXPAND | wx.ALL, 6)
    return deslizador


def _construir_ingles(wx, panel, caja, marco):
    boton = wx.Button(panel, label="Cancel")
    nombre_accesible(boton, "Cancel")
    caja.Add(boton, 0, wx.ALL, 6)
    return boton


def _construir_atajo_repetido(wx, panel, caja, marco):
    activar = wx.CheckBox(panel, label="&Activar")
    nombre_accesible(activar, "Activar")
    caja.Add(activar, 0, wx.ALL, 6)
    aplicar = wx.CheckBox(panel, label="&Aplicar")
    nombre_accesible(aplicar, "Aplicar")
    caja.Add(aplicar, 0, wx.ALL, 6)
    return activar


def _construir_paso_mudo(wx, panel, caja, marco):
    boton = wx.Button(panel, label="Mudo")
    nombre_accesible(boton, "Mudo")
    boton.Bind(wx.EVT_BUTTON, lambda evento: None)
    caja.Add(boton, 0, wx.ALL, 6)
    return boton


def _construir_foco_perdido(wx, panel, caja, marco):
    boton = wx.Button(panel, label="Deshabilitar")
    nombre_accesible(boton, "Deshabilitar")
    boton.Bind(wx.EVT_BUTTON, lambda evento: boton.Disable())
    caja.Add(boton, 0, wx.ALL, 6)
    return boton


def _construir_recorrido(wx, panel, caja, marco):
    entrada = wx.Button(panel, label="Entrada")
    nombre_accesible(entrada, "Entrada")
    caja.Add(entrada, 0, wx.ALL, 6)
    campo = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_TAB)
    nombre_accesible(campo, "Campo con Tab")
    caja.Add(campo, 1, wx.EXPAND | wx.ALL, 6)
    return entrada


def _construir_limpia(wx, panel, caja, marco):
    nombre = wx.TextCtrl(panel)
    nombre_accesible(nombre, "Nombre completo")
    caja.Add(nombre, 0, wx.EXPAND | wx.ALL, 6)
    imagen = wx.BitmapButton(panel, bitmap=wx.Bitmap(16, 16))
    nombre_accesible(imagen, "Imagen")
    caja.Add(imagen, 0, wx.ALL, 6)
    cuadro = wx.StaticBox(panel, label="Audio")
    nombre_accesible(cuadro, "Audio")
    grupo = wx.StaticBoxSizer(cuadro, wx.VERTICAL)
    nivel = wx.Slider(cuadro, value=50, minValue=0, maxValue=100)
    nombre_accesible(nivel, "Nivel")
    grupo.Add(nivel, 0, wx.EXPAND | wx.ALL, 6)
    caja.Add(grupo, 0, wx.EXPAND | wx.ALL, 6)
    activar = wx.CheckBox(panel, label="&Activar")
    nombre_accesible(activar, "Activar")
    caja.Add(activar, 0, wx.ALL, 6)
    mostrar = wx.CheckBox(panel, label="&Mostrar")
    nombre_accesible(mostrar, "Mostrar")
    caja.Add(mostrar, 0, wx.ALL, 6)
    anunciar = wx.Button(panel, label="Anunciar")
    nombre_accesible(anunciar, "Anunciar")
    anunciar.Bind(wx.EVT_BUTTON, lambda evento: _anunciar())
    caja.Add(anunciar, 0, wx.ALL, 6)
    mover = wx.Button(panel, label="Mover foco")
    nombre_accesible(mover, "Mover foco")
    destino = wx.TextCtrl(panel)
    nombre_accesible(destino, "Destino")
    caja.Add(destino, 0, wx.EXPAND | wx.ALL, 6)

    def mover_foco(evento):
        destino.SetFocus()
        mover.Disable()

    mover.Bind(wx.EVT_BUTTON, mover_foco)
    caja.Add(mover, 0, wx.ALL, 6)
    libre = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
    nombre_accesible(libre, "Campo libre")
    caja.Add(libre, 1, wx.EXPAND | wx.ALL, 6)
    return nombre


_CONSTRUCTORES = {
    "limpia": _construir_limpia,
    "sin_nombre": _construir_sin_nombre,
    "rol_contenedor": _construir_rol_contenedor,
    "nombre_repetido": _construir_nombre_repetido,
    "ingles": _construir_ingles,
    "atajo_repetido": _construir_atajo_repetido,
    "paso_mudo": _construir_paso_mudo,
    "foco_perdido": _construir_foco_perdido,
    "recorrido": _construir_recorrido,
}


def construir(nombre):
    """Arma la ventana pedida, sin mostrarla, y deja listo su primer control."""
    import wx

    datos = VENTANAS[nombre]
    marco = wx.Frame(None, title=datos["titulo"])
    panel = wx.Panel(marco)
    caja = wx.BoxSizer(wx.VERTICAL)
    primero = _CONSTRUCTORES[nombre](wx, panel, caja, marco)
    panel.SetSizer(caja)
    marco.Fit()
    marco.Centre()
    marco.primero = primero

    def al_mostrar(evento):
        if evento.IsShown():
            primero.SetFocus()

    marco.Bind(wx.EVT_SHOW, al_mostrar)
    return marco


def main(argv=None) -> int:
    import wx

    analizador = argparse.ArgumentParser(
        description="Ventanas de prueba del carril de NVDA.")
    analizador.add_argument("--ventana", required=True,
                            choices=sorted(VENTANAS))
    args = analizador.parse_args(argv)
    app = wx.App(False)
    marco = construir(args.ventana)
    marco.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
