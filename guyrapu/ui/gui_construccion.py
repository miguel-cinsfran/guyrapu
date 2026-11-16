# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Construcción de la ventana principal y de sus páginas.

Única razón para cambiar: qué controles tiene la ventana principal y cómo se
acomodan. Las funciones reciben el marco, como `gui_menu.construir_menu(frame)`.
"""

from __future__ import annotations

import wx
from wx.lib.wordwrap import wordwrap

from guyrapu.capture import chat_adicional
from guyrapu.capture import redaccion
from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.ui import comando_directo
from guyrapu.ui import gui_cierre
from guyrapu.ui import paleta
from guyrapu.ui import recientes_inicio as recientes
from guyrapu.ui.accesibilidad import (
    enlazar_anuncio_de_pestana, nombre_accesible)
from guyrapu.ui.barra_estado import anchos_barra_estado
from guyrapu.ui.busqueda_teclado import instalar_busqueda_tipo
from guyrapu.ui.chat_vivo import ControladorChat
from guyrapu.ui.gui_redactar import PanelRedactar
from guyrapu.ui.tema import _T, _pintar, _tc, _titulo

logger = diagnostico.obtener_logger(__name__)


def construir(frame):
    # Importes diferidos para evitar el ciclo (esos módulos importan de gui).
    from guyrapu.ui.gui_comentarios import ComentariosPanel
    from guyrapu.player.reproductor import ReproductorPanel
    from guyrapu.ui import gui as _gui

    panel = wx.Panel(frame, name="PanelPrincipal")
    vs = wx.BoxSizer(wx.VERTICAL)

    _barra_superior(frame, panel, vs)
    _zona_contenido(frame, panel, vs, ComentariosPanel, ReproductorPanel)

    panel.SetSizer(vs)
    frame._panel_principal = panel

    # Control de la música: nace sin tocar VLC ni el disco.
    from guyrapu.ui import gui_musica
    frame._musica = gui_musica.ControlMusica(frame)

    # Regiones que recorre F6 / Shift+F6.
    frame._region_idx = _gui.REG_CONTENIDO
    frame._regiones = [
        lambda: frame.txt_url.SetFocus(),
        frame._foco_contenido,
        frame._rep_panel.anclar_foco,
    ]

    frame.sb = frame.CreateStatusBar(7, name="BarraEstado")
    # (Sin fondo: la barra de estado nativa lo ignora.)
    _pintar(frame.sb, fg=_T.dim)
    frame.sb.SetStatusWidths(
        anchos_barra_estado(lambda t: frame.sb.GetTextExtent(t)[0]))
    frame._actualizar_sb()
    frame._set_conectado_ui(False)   # estado inicial: desconectado
    paleta.pintar_ventana(frame)


def _barra_superior(frame, panel, vs):
    from guyrapu.ui import gui as _gui

    # ── Barra superior: URL + tipo + Conectar ──
    row = wx.BoxSizer(wx.HORIZONTAL)
    lbl = wx.StaticText(panel, label=_("&Enlace o ID:"), name="EtiquetaURL")
    _titulo(lbl)
    row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    frame.txt_url = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER, name=_("Enlace del directo o vídeo"))
    frame.txt_url.SetToolTip(
        _("Enlace de YouTube (directo o vídeo) o de un directo de TikTok "
          "(tiktok.com/@usuario/live). También vale el ID de 11 caracteres de "
          "YouTube. Pulsa Intro para conectar."))
    row.Add(frame.txt_url, 1, wx.EXPAND | wx.RIGHT, 8)
    # Traductores: nombre accesible del botón para conectar.
    frame.btn_conectar = wx.Button(panel, label=_("&Conectar"), name=_("Conectar"))
    _pintar(frame.btn_conectar, _T.primary, _T.primary_t)
    frame.btn_conectar.SetFont(frame.btn_conectar.GetFont().Bold())
    row.Add(frame.btn_conectar, 0, wx.ALIGN_CENTER_VERTICAL)
    from guyrapu.ui.boton_directo import BotonDirecto
    frame._boton_directo = BotonDirecto(
        panel, frame.btn_conectar, frame, comando_directo.ComandoDirecto(frame))
    row.Add(frame._boton_directo.boton, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
    vs.Add(row, 0, wx.EXPAND | wx.ALL, 12)

    frame.lbl_tipo = wx.StaticText(panel, label=frame._texto_tipo, name="TipoVideo")
    _pintar(frame.lbl_tipo, fg=_T.dim)
    # Ancho mínimo fijo: si no, el mínimo del sizer (y el piso de la
    # ventana) seguiría al texto sin partir, es decir, al ancho actual.
    frame.lbl_tipo.SetMinSize((200, -1))
    frame.lbl_tipo.Wrap(_gui.ANCHO_DEFECTO - 40)
    vs.Add(frame.lbl_tipo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)


def _zona_contenido(frame, panel, vs, ComentariosPanel, ReproductorPanel):
    # ── Zona de contenido: notebook + reproductor. Se oculta hasta que hay
    # conexión y se vuelve a ocultar al desconectar (queda solo la barra
    # superior), para que no aparezca todo a medio cargar. ──
    frame._zona = wx.Panel(panel, name="ZonaContenido")
    zvs = wx.BoxSizer(wx.VERTICAL)

    # Traductores: cuaderno con los paneles.
    frame.nb = wx.Notebook(frame._zona, name=_("Paneles"))
    _tc(frame.nb, bg=_T.surface)
    frame._pag_chat = construir_pagina_chat(frame, frame.nb)
    frame._com_panel = ComentariosPanel(frame.nb, frame._cola, frame._config)
    frame.nb.AddPage(frame._pag_chat, _("Chat del directo"))
    # Traductores: pestaña de comentarios.
    frame.nb.AddPage(frame._com_panel, _("Comentarios"))
    # Pestaña de información del vídeo (solo lectura). Se añade SIEMPRE al
    # final, para no alterar los índices de Chat/Comentarios, y se puede
    # ocultar por preferencia. La rellena set_metadatos con lo de yt-dlp.
    frame._pag_info = construir_pagina_info(frame, frame.nb)
    frame._metadatos = {}
    if bool(frame._config.get("mostrar_metadatos", True)):
        # Traductores: pestaña con los datos del vídeo.
        frame.nb.AddPage(frame._pag_info, _("Información"))
    else:
        frame._pag_info.Hide()
    # Piso para que la lista del chat, los comentarios y la información no
    # queden aplastados por el reproductor en ventanas bajas: 170 dejaba
    # ver 2-3 mensajes; con esto se ven varios más sin tocar el reproductor.
    frame.nb.SetMinSize((-1, 260))
    zvs.Add(frame.nb, 4, wx.EXPAND | wx.BOTTOM, 10)

    # Proporción 4/1 para lo que sobra, pero a 860x700 mandan los mínimos, que ya superan los 700.
    frame._rep_panel = ReproductorPanel(frame._zona, frame._config)
    # Al alternar los botones del reproductor (desde su interruptor o el menú),
    # sincronizamos la casilla del menú y persistimos la preferencia.
    frame._rep_panel.on_botones_toggle = frame._on_botones_rep_cambio
    zvs.Add(frame._rep_panel, 1, wx.EXPAND)

    frame._zona.SetSizer(zvs)
    vs.Add(frame._zona, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
    frame._zona.Hide()
    frame._inicio = recientes.armar(
        panel, vs, frame._zona, frame._reconectar_desde_historial)


def construir_pagina_chat(frame, parent) -> wx.Panel:
    from guyrapu.ui import gui as _gui

    pag = wx.Panel(parent, name="PaginaChat")
    vs = wx.BoxSizer(wx.VERTICAL)

    lbl = wx.StaticText(pag, label=_("Mensajes del chat:"), name="EtiquetaChat")
    _titulo(lbl)
    vs.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

    frame.lb_chat = wx.ListBox(
        pag, style=wx.LB_SINGLE | wx.LB_HSCROLL, name=_("Chat del directo"))
    pt = int(frame._config.get("tamanio_fuente_chat", 12))
    frame.lb_chat.SetFont(wx.Font(
        pt, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
    frame.lb_chat.SetToolTip(
        _("Mensajes del chat. Intro copia el mensaje. "
          "La tecla de aplicaciones abre el menú contextual."))
    # msaa=False: ver el porqué en nombre_accesible() (lista dinámica).
    nombre_accesible(frame.lb_chat, _("Chat del directo"), msaa=False)
    frame.chat_vivo = ControladorChat(
        frame.lb_chat, _gui.MAX_ITEMS_CHAT,
        activo=lambda: frame._alive and frame._conectado,
        autor_oculto=lambda autor: frame._chat_acciones._autor_esta_oculto(autor),
        formatear=lambda *args: frame._chat_acciones._format_display(*args),
        al_superchat=frame._sumar_superchat,
        config=frame._config, varios_chats=chat_adicional.activo)
    frame._chat_acciones.lb_chat = frame.lb_chat
    frame._chat_acciones.chat_vivo = frame.chat_vivo
    vs.Add(frame.lb_chat, 1, wx.EXPAND | wx.ALL, 8)

    frame._panel_redactar = PanelRedactar(
        pag, _("&Mensaje:"), redaccion.MAXIMO_CHAT, frame._enviar_live_redactado)
    vs.Add(frame._panel_redactar, 0,
           wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    pag.SetSizer(vs)
    frame._actualizar_motivo_redaccion()
    # Mensajes recientes: lee con Ctrl+Mayús y un número, también fuera.
    # Nace acá, donde ya existe lb_chat.
    from guyrapu.ui import chat_recientes
    frame._recientes = chat_recientes.LecturaRecientes(
        frame, frame.lb_chat, frame._config, frame._cola)
    return pag


def construir_pagina_info(frame, parent) -> wx.Panel:
    pag = wx.Panel(parent, name="PaginaInfo")
    vs = wx.BoxSizer(wx.VERTICAL)

    lbl = wx.StaticText(pag, label=_("Información del vídeo:"), name="EtiquetaInfo")
    _titulo(lbl)
    vs.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

    # Solo lectura y multilínea. TE_AUTO_URL (con TE_RICH2, necesario en
    # Windows) hace clicables los enlaces de la descripción SIN romper la
    # lectura con NVDA, que recorre el cuadro como texto normal (flechas,
    # selección, copiar). Es la opción accesible frente a un wx.html.
    frame.txt_info = wx.TextCtrl(
        pag, value="", name=_("Información del vídeo"),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL | wx.TE_RICH2)
    frame.txt_info.SetToolTip(
        _("Datos del vídeo: canal, vistas, descripción. Solo lectura. Para "
          "abrir un enlace, cópialo y pégalo en el navegador."))
    vs.Add(frame.txt_info, 1, wx.EXPAND | wx.ALL, 8)

    pag.SetSizer(vs)
    frame.txt_info.Bind(wx.EVT_TEXT_URL, lambda event: on_info_url(frame, event))
    return pag


def on_info_url(frame, event):
    # TE_AUTO_URL dispara este evento para CADA movimiento del ratón sobre el
    # enlace; abrir solo al soltar el botón izquierdo (si no, abriría a cada
    # paso del cursor).
    mouse = event.GetMouseEvent()
    if mouse.LeftUp():
        url = frame.txt_info.GetRange(event.GetURLStart(), event.GetURLEnd())
        if url:
            import webbrowser
            webbrowser.open(url)
    else:
        event.Skip()


# ── Enlaces de eventos ───────────────────────────────────────────────────────

def enlazar_eventos(frame):
    from guyrapu.ui import gui_sesion
    frame.Bind(wx.EVT_CLOSE, lambda event: gui_cierre.on_close(frame, event))
    frame.Bind(wx.EVT_ACTIVATE, frame._on_activate)
    # En el panel, no en el frame: cuando el frame recibe EVT_SIZE el panel
    # aún tiene el tamaño viejo y cada Wrap iba un evento tarde.
    frame._panel_principal.Bind(
        wx.EVT_SIZE, lambda event: on_resize(frame, event))
    frame.btn_conectar.Bind(wx.EVT_BUTTON, frame._on_conectar)
    frame.txt_url.Bind(
        wx.EVT_TEXT_ENTER, lambda event: gui_sesion.on_enlace_enter(frame, event))
    enlazar_anuncio_de_pestana(frame.nb)
    frame.lb_chat.Bind(wx.EVT_LISTBOX_DCLICK,
                       lambda e: frame._chat_acciones._copiar_mensaje())
    enlazar_eventos_chat(frame)
    instalar_busqueda_tipo(
        frame.lb_chat,
        lambda: [frame.lb_chat.GetString(i)
                 for i in range(frame.lb_chat.GetCount())])


def enlazar_eventos_chat(frame):
    frame.lb_chat.Bind(wx.EVT_KEY_DOWN, frame._chat_acciones._on_chat_key)
    frame.lb_chat.Bind(wx.EVT_CHAR_HOOK, frame._chat_acciones._on_chat_char_hook)
    frame.lb_chat.Bind(wx.EVT_CONTEXT_MENU, frame._chat_acciones._on_chat_menu)


def on_resize(frame, event):
    # Primero el Wrap y luego Skip: así el Layout por defecto del panel ya
    # cuenta con la altura nueva de la etiqueta.
    ajustar_ancho_tipo(frame)
    event.Skip()


def ajustar_ancho_tipo(frame) -> None:
    """Parte lbl_tipo al ancho actual sin StaticText.Wrap, que a veces no parte."""
    if not hasattr(frame, "lbl_tipo"):
        return
    try:
        ancho = max(200, frame.lbl_tipo.GetParent().GetClientSize().Width - 20)
        dc = wx.ClientDC(frame.lbl_tipo)
        dc.SetFont(frame.lbl_tipo.GetFont())
        frame.lbl_tipo.SetLabel(
            wordwrap(frame._texto_tipo, ancho, dc).rstrip("\n"))
    except Exception as error:
        logger.debug("no se pudo ajustar el ancho del tipo de directo: %s", error)


def fijar_tipo(frame, texto: str) -> None:
    frame._texto_tipo = texto
    ajustar_ancho_tipo(frame)
    try:    frame._panel_principal.Layout()
    except Exception as error: logger.debug("no se pudo reajustar el panel: %s", error)


def ajustar_minimo_ventana(frame) -> None:
    """Piso real de la ventana: lo que pide el sizer (con el reproductor a
    la vista ronda los 850 px de alto, muy por encima de 640×480, y el
    vídeo quedaba cortado por abajo). Se limita a la pantalla y, si la
    ventana era más chica, se agranda para que quepa todo."""
    try:
        minimo = frame._panel_principal.GetSizer().GetMinSize()
        area = wx.Display(frame).GetClientArea()
        # Descontar título, menú, barra de estado y bordes.
        ancho = max(640, min(minimo.width, area.width - 40))
        alto = max(480, min(minimo.height, area.height - 110))
        frame.SetMinClientSize((ancho, alto))
        actual = frame.GetClientSize()
        if frame.IsMaximized() or (actual.width >= ancho and actual.height >= alto):
            return
        frame.SetClientSize((max(actual.width, ancho), max(actual.height, alto)))
        rect = frame.GetRect()
        x = max(area.x, min(rect.x, area.right - rect.width))
        y = max(area.y, min(rect.y, area.bottom - rect.height))
        if (x, y) != (rect.x, rect.y):
            frame.Move((x, y))
    except Exception as exc:
        logger.debug("ajustar mínimo de la ventana: %s", exc)


def iniciar_temporizadores(frame):
    from guyrapu.ui import gui as _gui

    frame._timer = wx.Timer(frame)
    frame.Bind(wx.EVT_TIMER, frame._on_timer, frame._timer)
    frame._timer.Start(_gui.TIMER_STATUS_MS)
    frame._diagnostico_timer = wx.Timer(frame)
    frame.Bind(wx.EVT_TIMER, frame._on_diagnostico_timer, frame._diagnostico_timer)
    frame._diagnostico_timer.Start(_gui.TIMER_DIAGNOSTICO_MS)
