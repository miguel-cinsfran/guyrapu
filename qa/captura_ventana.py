# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Captura de ventanas wx de nivel superior con `PrintWindow`.

Saca el dibujo fuera de pantalla, sin mover el foco ni mandar teclas, para
que sirva tanto a la sonda del banco como a la galería de ventanas. Módulo
de Windows: importa wx y ctypes dentro de las funciones que los usan.
"""

from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes

from galeria_geometria import es_region_plana

logger = logging.getLogger(__name__)

# La bandera 2 de `PrintWindow`: dibuja fuera de pantalla, con la ventana
# tapada y con la cortina de pantalla de NVDA, que ennegrece cualquier
# captura de la pantalla física. `ImageGrab` o `mss` no sirven acá.
PW_RENDERFULLCONTENT = 2


class _Cabecera(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class _Info(ctypes.Structure):
    _fields_ = [("bmiHeader", _Cabecera),
                ("bmiColors", wintypes.DWORD * 3)]


def _leer_bits(gdi32, hdc_mem, hbmp, ancho, alto):
    """Saca los bytes BGRA del bitmap y los pasa a RGB."""
    info = _Info()
    info.bmiHeader.biSize = ctypes.sizeof(_Cabecera)
    info.bmiHeader.biWidth = ancho
    # Alto negativo: de arriba hacia abajo.
    info.bmiHeader.biHeight = -alto
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0
    bufer = ctypes.create_string_buffer(ancho * alto * 4)
    if not gdi32.GetDIBits(hdc_mem, hbmp, 0, alto, bufer,
                           ctypes.byref(info), 0):
        raise RuntimeError("GetDIBits devolvió cero")
    import capturas
    return capturas.bgra_a_rgb(bufer.raw)


def _dibujar_ventana_a_rgb(ventana):
    """Dibuja la ventana con `PrintWindow` y devuelve `(ancho, alto, rgb)`.

    Los bytes salen BGRA de 32 bits de arriba hacia abajo y se pasan a RGB
    con `capturas.bgra_a_rgb`, que es lo que espera `wx.Image`. Libera
    siempre el bitmap y los DC, en un `finally`.
    """
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hwnd = ventana.GetHandle()
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("no se pudo leer el rectángulo de la ventana")
    ancho = rect.right - rect.left
    alto = rect.bottom - rect.top
    if ancho <= 0 or alto <= 0:
        raise RuntimeError(f"tamaño inválido: {ancho}x{alto}")
    hdc_pantalla = user32.GetDC(None)
    if not hdc_pantalla:
        raise RuntimeError("no se pudo pedir el DC de pantalla")
    try:
        hdc_mem = gdi32.CreateCompatibleDC(hdc_pantalla)
        if not hdc_mem:
            raise RuntimeError("no se pudo crear el DC compatible")
        try:
            hbmp = gdi32.CreateCompatibleBitmap(hdc_pantalla, ancho, alto)
            if not hbmp:
                raise RuntimeError("no se pudo crear el bitmap")
            try:
                anterior = gdi32.SelectObject(hdc_mem, hbmp)
                try:
                    if not user32.PrintWindow(hwnd, hdc_mem,
                                             PW_RENDERFULLCONTENT):
                        raise RuntimeError("PrintWindow devolvió falso")
                    rgb = _leer_bits(gdi32, hdc_mem, hbmp, ancho, alto)
                finally:
                    gdi32.SelectObject(hdc_mem, anterior)
            finally:
                gdi32.DeleteObject(hbmp)
        finally:
            gdi32.DeleteDC(hdc_mem)
    finally:
        user32.ReleaseDC(None, hdc_pantalla)
    return ancho, alto, rgb


def _dejar_pintar(ventana) -> None:
    """Deja que la ventana se pinte antes de capturarla.

    Cede el bucle durante 400 ms: rondas de `SafeYield()` y `Update()`
    con `time.sleep(0.01)` entre ellas. Sin la espera real la captura
    sale en negro porque el pintado no alcanza a llegar.
    """
    import wx
    try:
        ventana.Refresh()
    except Exception as exc:
        logger.debug("No se pudo refrescar la ventana: %s", exc)
    try:
        ventana.Update()
    except Exception as exc:
        logger.debug("No se pudo actualizar la ventana: %s", exc)
    inicio = time.monotonic()
    while time.monotonic() - inicio < 0.4:
        try:
            wx.SafeYield()
        except Exception as exc:
            logger.debug("No se pudo ceder el bucle: %s", exc)
            break
        try:
            ventana.Update()
        except Exception as exc:
            logger.debug("No se pudo actualizar al pintar: %s", exc)
        time.sleep(0.01)


def pintar_completo(ventana, controles):
    """Fuerza el pintado de la ventana y de todo su árbol antes de capturar.

    Un botón que se crea al abrir una página a veces sigue siendo un
    rectángulo liso cuando `PrintWindow` corre. Refrescar y actualizar cada
    control, ceder el bucle y esperar el pintado lo evita.
    """
    import wx
    for control in controles:
        try:
            control.Refresh()
        except Exception as exc:
            logger.debug("No se pudo refrescar un control: %s", exc)
        try:
            control.Update()
        except Exception as exc:
            logger.debug("No se pudo actualizar un control: %s", exc)
    wx.SafeYield()
    _dejar_pintar(ventana)


def botones_sin_pintar(imagen, controles, desplazamiento):
    """Botones con etiqueta cuyo rectángulo salió liso en el PNG."""
    dx, dy = desplazamiento
    ancho_img, alto_img = imagen.GetWidth(), imagen.GetHeight()
    planos = []
    for c in controles:
        if not (c["visible"] and c["clase"] == "wxButton"
                and c["etiqueta"].strip()):
            continue
        x, y, ancho_c, alto_c = c["rect"]
        paso_x, paso_y = max(2, ancho_c // 8), max(2, alto_c // 8)
        pixeles = [
            (imagen.GetRed(xx, yy), imagen.GetGreen(xx, yy),
             imagen.GetBlue(xx, yy))
            for yy in range(y + dy, min(y + dy + alto_c, alto_img), paso_y)
            for xx in range(x + dx, min(x + dx + ancho_c, ancho_img), paso_x)]
        if pixeles and es_region_plana(pixeles):
            planos.append(c["nombre"])
    return planos


def _guardar_png(ventana, ruta) -> tuple:
    """Guarda la ventana en `ruta` como PNG y devuelve su tamaño."""
    import wx
    ancho, alto, rgb = _dibujar_ventana_a_rgb(ventana)
    imagen = wx.Image(ancho, alto, bytes(rgb))
    if not imagen.IsOk():
        raise RuntimeError("la imagen quedó vacía")
    if not imagen.SaveFile(str(ruta), wx.BITMAP_TYPE_PNG):
        raise RuntimeError(f"no se pudo guardar {ruta}")
    return ancho, alto
