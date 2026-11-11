# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Lector de pantalla (Prism, opcional)
Si Prism no está instalado o no hay un lector de pantalla activo, los
`anunciar()` son no-ops silenciosos; la app funciona igual.

Nombre accesible reforzado (MSAA)
En Windows, `SetName` por sí solo no siempre lo anuncian NVDA/JAWS de forma
fiable (sobre todo en deslizadores y en ventanas genéricas como la superficie
de vídeo). Se refuerza con la anotación dinámica de Windows, que cambia solo
el nombre y deja intactos el rol y el estado que informa el control.
"""

from __future__ import annotations

import wx

from guyrapu.core import diagnostico, nombre_msaa
from guyrapu.voice import sound_player


logger = diagnostico.obtener_logger(__name__)

_lector = None


def _lector_init():
    global _lector
    try:
        from guyrapu.voice.lector import Lector
        _lector = Lector()
        logger.info("Lector de pantalla: %s", _lector.nombre() or "ninguno")
    except Exception as exc:
        logger.warning("La aplicación se quedó sin salida para lector de pantalla: %s", exc)


def anunciar(texto: str, urgente: bool = True) -> None:
    if _lector is None:
        logger.info("ANUNCIO sin lector %s", texto)
        return
    if not wx.IsMainThread():
        # Prism habla por COM (JAWS) y no es seguro desde otros hilos; el
        # vigilante de OBS y las descargas anuncian desde los suyos, así que se
        # reenvía al hilo de la interfaz, que es donde se crea y se usa el
        # lector porque JAWS crea su COM ahí.
        try:
            wx.CallAfter(anunciar, texto, urgente)
        except Exception as exc:
            logger.debug("No se pudo pasar el anuncio al hilo de la interfaz: %s", exc)
        return
    logger.info("ANUNCIO %s", texto)
    try:
        # Casi todos responden a una tecla y deben llegar antes del próximo foco.
        _lector.speak(texto, interrupt=urgente)
    except Exception as exc:
        logger.warning("No se pudo anunciar con voz: %s", exc)
    # También a la línea braille, como hace TWBlue (output.speak): quien usa
    # pantalla braille sin voz recibe igualmente los anuncios de la app.
    try:
        _lector.braille(texto)
    except Exception as exc:
        logger.debug("No se pudo enviar el anuncio a la línea braille: %s", exc)


def anunciar_con_sonido(frase: str, sonido: str | None = None) -> None:
    """Reproduce el sonido y anuncia la frase desde el hilo de la interfaz."""
    def _avisar():
        if sonido:
            sound_player.reproducir(sonido)
        anunciar(frase)

    try:
        wx.CallAfter(_avisar)
    except Exception as exc:
        logger.debug("No se pudo diferir el aviso con sonido: %s", exc)


def enlazar_anuncio_de_pestana(notebook) -> None:
    """Anuncia el nombre de la pestaña al cambiarla, porque wx no lo hace solo."""
    def _al_cambiar(event):
        idx = event.GetSelection()
        if 0 <= idx < notebook.GetPageCount():
            anunciar(notebook.GetPageText(idx))
        event.Skip()
    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _al_cambiar)


def entregar_intro(lista, manejador) -> None:
    """Entrega Intro a `manejador` desde `EVT_CHAR_HOOK`, porque una
    `wx.ListBox` no lo manda por `EVT_KEY_DOWN` (medido el 07/11/2026)."""
    def _al_entregar(evento):
        if (evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER)
                and evento.GetModifiers() == wx.MOD_NONE):
            manejador(evento)
        else:
            evento.Skip()
    lista.Bind(wx.EVT_CHAR_HOOK, _al_entregar)


def nombre_accesible(ctrl, nombre: str, msaa: bool = True) -> None:
    """Pone el nombre accesible de un control. Mantiene su tooltip rico y su
    texto de ayuda; el nombre va por la anotación dinámica de Windows, que no
    cambia el rol ni el estado. `msaa=False` se salta la anotación y se usa en
    listas de contenido dinámico (chat, comentarios), que no la necesitan."""
    ctrl.SetName(nombre)
    if not ctrl.GetToolTip():
        ctrl.SetToolTip(nombre)
    try:
        ctrl.SetHelpText(nombre)   # JAWS lee el help text en algunos controles
    except Exception as exc:
        logger.debug("El control no admite texto de ayuda: %s", exc)
    if not msaa:
        return
    hwnd = ctrl.GetHandle()
    if not nombre_msaa.poner(hwnd, nombre):
        return
    if getattr(ctrl, "_nombre_msaa_atado", False):
        return
    ctrl._nombre_msaa_atado = True

    def _al_destruir(evento):
        if evento.GetEventObject() is ctrl:
            nombre_msaa.quitar(hwnd)
        evento.Skip()

    ctrl.Bind(wx.EVT_WINDOW_DESTROY, _al_destruir)


class ContadorAccesible(wx.SpinCtrl):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_SET_FOCUS, self._on_focus)

    def _on_focus(self, event):
        # Selecciona el valor para reemplazarlo sin borrarlo antes.
        self.SetSelection(0, len(self.GetTextValue()))
        event.Skip()

