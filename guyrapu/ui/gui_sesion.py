# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué hace la ventana principal al conectar y al desconectar.

Única razón para cambiar: validar la dirección, conectar, poner la ventana
en conectada o desconectada, reiniciar los datos de la sesión y anunciarlo.
Las funciones reciben la ventana, como `gui_cierre`.
"""

from __future__ import annotations

import wx

from guyrapu.capture import deteccion
from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.ui import confirmar
from guyrapu.ui import gui_construccion
from guyrapu.ui import menu_habilitado
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.ui.sesion_conectada import SesionConectada
from guyrapu.voice import sound_player as _snd

logger = diagnostico.obtener_logger(__name__)


def on_conectar(ventana, event):
    if ventana._conectado or ventana._conectando:
        # Desconectar o, si aún estaba «Conectando…», cancelar: el callback
        # cierra la sesión y lo que devuelva ese hilo se descarta.
        cancelando = not ventana._conectado
        if ventana.on_desconectar_cb:
            ventana.on_desconectar_cb()
        ventana.set_conectado(False)
        if cancelando:
            anunciar(_("Conexión cancelada"))
            ventana.txt_url.SetFocus()
    else:
        url = ventana.txt_url.GetValue().strip()
        if not url:
            confirmar.avisar(ventana, _("Introduce un enlace o un ID de YouTube."),
                             _("Falta el enlace"), _("Aceptar"), icono=confirmar.ICON_WARNING)
            ventana.txt_url.SetFocus()
            return
        ventana._conectando = True
        # El botón y «Desconectar» siguen activos para poder cancelar una
        # conexión que no responde.
        ventana.btn_conectar.SetLabel(_("&Cancelar conexión"))
        ventana.btn_conectar.Enable()
        menu_habilitado.habilitar(ventana.mi_conectar, False)
        menu_habilitado.habilitar(ventana.mi_desconectar, True)
        ventana.txt_url.Disable()
        _snd.reproducir("conectando")
        # Traductores: aviso mientras se conecta.
        anunciar(_("Conectando"))
        if ventana.on_conectar_cb:
            ventana.on_conectar_cb(url)
        ventana._actualizar_boton_directo()


def url_invalida(ventana):
    """La URL/ID no es válida: restaurar la UI y avisar (sin esperas)."""
    if not ventana._alive:
        return
    _snd.reproducir("error")
    ventana._set_conectado_ui(False)
    anunciar(_("No se reconoce el enlace o el ID de YouTube"))
    ventana.txt_url.SetFocus()
    confirmar.avisar(ventana, _("No se reconoce el enlace o el ID de YouTube. Comprueba el enlace pegado."),
                     _("Enlace no reconocido"), _("Aceptar"), icono=confirmar.ICON_WARNING)


def set_conectado(ventana, conectado: bool,
                  sonido_desconexion: str = "desconectado") -> None:
    from guyrapu.ui import gui

    if not ventana._alive:
        return
    estaba = ventana._conectado
    ventana._conectado = conectado
    if conectado:
        if not estaba:
            ventana._mostrar_zona(True)
            ventana._region_idx = gui.REG_CONTENIDO
            ventana._anunciar_conectado()
            wx.CallAfter(ventana._foco_contenido)
    else:
        ventana._reiniciar_datos_sesion()
        # Solo si veníamos de una conexión real: ocultar, sonar y avisar.
        # (Un fallo de conexión nunca llegó a "conectado", así que no suena.)
        if estaba:
            ventana._mostrar_zona(False)
            ventana.set_titulo_stream("")
            gui_construccion.fijar_tipo(ventana, _(gui.MENSAJE_INICIAL))
            # El fin del directo de TikTok llega con su propio sonido;
            # el resto de los cortes sigue sonando «desconectado».
            _snd.reproducir(sonido_desconexion)
            # Traductores: aviso al desconectar.
            anunciar(_("Desconectado"))
            # Sacar el foco del panel del reproductor ANTES de que quede
            # oculto: si el foco sigue dentro, wx tarda en repintar y el
            # panel «se queda» visible hasta que tabulas. Al campo URL.
            wx.CallAfter(ventana.txt_url.SetFocus)
    ventana._set_conectado_ui(conectado)
    ventana._actualizar_estado_online()


def reiniciar_datos_sesion(ventana) -> None:
    """Borra TODO el estado de la sesión para que volver a conectar sea como
    recién abierta la app y nada del directo anterior se solape: chat,
    comentarios, reproductor, cola de lectura, super chats y contadores. NO
    toca las preferencias del usuario (filtro, voz, sonidos, tema)."""
    ventana.sesion = SesionConectada()
    # Chat: datos, lista visible y lo que aún estaba en cola sin volcar (es
    # de la sesión que se cierra; no debe colarse en la siguiente).
    ventana.chat_vivo.vaciar()
    try:    ventana.lb_chat.Clear()
    except Exception as error: logger.debug("no se pudo limpiar el chat: %s", error)
    ventana._sc_totales.clear()
    # Panel de información del vídeo.
    ventana._metadatos = {}
    try:    ventana.txt_info.SetValue("")
    except Exception as error: logger.debug("no se pudo limpiar la información: %s", error)
    # Reproductor y panel de comentarios.
    try:    ventana._rep_panel.detener_todo()
    except Exception as error: logger.debug("no se pudo detener el reproductor: %s", error)
    try:    ventana._com_panel.limpiar()
    except Exception as error: logger.debug("no se pudo limpiar los comentarios: %s", error)
    # Cola de lectura y lo que se esté leyendo ahora mismo.
    try:
        ventana._worker.vaciar_cola()
        ventana._worker.detener_actual()
    except Exception as error: logger.debug("no se pudo vaciar la cola: %s", error)
    # Contadores a cero.
    try:    ventana._stats.reset()
    except Exception as error: logger.debug("no se pudo reiniciar los contadores: %s", error)
    ventana._actualizar_sb()


def mostrar_zona(ventana, mostrar: bool) -> None:
    ventana._zona.Show(mostrar)
    ventana._panel_principal.Layout()
    gui_construccion.ajustar_minimo_ventana(ventana)


def anunciar_conectado(ventana) -> None:
    t = ventana.sesion.tipo_video
    if t == deteccion.LIVE:
        msg = _("Conectado al directo. Leyendo el chat.")
    elif t == deteccion.UPCOMING:
        msg = _("Directo programado. Aún no hay chat; puedes ver los comentarios.")
    elif t == deteccion.VOD:
        msg = _("Vídeo conectado. Comentarios y reproductor disponibles.")
    else:
        # Traductores: aviso genérico al conectar.
        msg = _("Conectado.")
    anunciar(msg)
