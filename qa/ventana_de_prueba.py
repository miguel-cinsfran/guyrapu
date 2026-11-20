# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana de color liso para la prueba del directo real.

La abre `qa/directo_real.py` por duplicado (verde «Cámara de prueba» y
magenta «Aplicación de prueba») para armar una escena de OBS como la de
quien usa la app, con capturas encima del panel de chat. Se queda abierta
hasta que la cierren y no tiene ningún control. Con QA_VENTANA_NUMERO dibuja
el número que lee de ese archivo y lo cambia cuando el archivo cambia.
"""

from __future__ import annotations

import argparse
import os
import sys

ANCHO = 640
ALTO = 360


def color_desde_texto(texto: str) -> tuple[int, int, int]:
    """Terna (rojo, verde, azul) desde un hexadecimal «RRGGBB», con o sin #."""
    limpio = (texto or "").strip().lstrip("#")
    if len(limpio) != 6:
        raise ValueError(f"color inválido «{texto}»: tiene que ser RRGGBB")
    try:
        return (int(limpio[0:2], 16), int(limpio[2:4], 16),
                int(limpio[4:6], 16))
    except ValueError:
        raise ValueError(
            f"color inválido «{texto}»: tiene que ser RRGGBB") from None


def numero_de_archivo(ruta: str) -> str:
    """El texto del archivo sin espacios, o vacío si no hay ruta o archivo."""
    if not ruta:
        return ""
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def dibujar(marco, fondo, numero) -> None:
    """Pinta el fondo liso y el número centrado, en blanco y negrita."""
    import wx
    contexto = wx.PaintDC(marco)
    contexto.SetBackground(wx.Brush(fondo))
    contexto.Clear()
    if not numero:
        return
    alto = ALTO // 3
    fuente = wx.Font(alto, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL,
                     wx.FONTWEIGHT_BOLD)
    contexto.SetFont(fuente)
    contexto.SetTextForeground(wx.Colour(255, 255, 255))
    ancho, _ = contexto.GetTextExtent(numero)
    contexto.DrawText(numero, (ANCHO - ancho) // 2, (ALTO - alto) // 2)


def vigilante(marco, ruta, estado):
    """Devuelve el manejador que releva el número y repinta si cambió."""
    def actualizar(evento):
        nuevo = numero_de_archivo(ruta)
        if nuevo != estado["numero"]:
            estado["numero"] = nuevo
            marco.Refresh()
    return actualizar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ventana de color liso para tapar el panel en la prueba "
                    "del directo real.")
    parser.add_argument("--titulo", default="Ventana de prueba")
    parser.add_argument("--color", default="00C000")
    args = parser.parse_args(argv)
    try:
        rojo, verde, azul = color_desde_texto(args.color)
    except ValueError as exc:
        print(exc)
        return 2

    import wx
    ruta_numero = os.environ.get("QA_VENTANA_NUMERO", "")
    estado = {"numero": numero_de_archivo(ruta_numero)}
    app = wx.App(False)
    marco = wx.Frame(None, title=args.titulo)
    marco.SetClientSize((ANCHO, ALTO))
    fondo = wx.Colour(rojo, verde, azul)
    marco.Bind(wx.EVT_PAINT, lambda evento: dibujar(marco, fondo, estado["numero"]))
    if ruta_numero:
        temporizador = wx.Timer(marco)
        marco.Bind(wx.EVT_TIMER, vigilante(marco, ruta_numero, estado), temporizador)
        temporizador.Start(300)
    # Sin activar: la ventana aparece detrás sin robar el foco.
    marco.ShowWithoutActivating()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
