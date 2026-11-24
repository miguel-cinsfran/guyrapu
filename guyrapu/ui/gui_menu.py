# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Barra de menú de la ventana principal."""

from __future__ import annotations

import os
import webbrowser

import wx

from guyrapu.capture import traduccion_chat
from guyrapu.core import avisos_tiktok
from guyrapu.core import diagnostico
from guyrapu.core.config import (
    TIPO_MIEMBRO, TIPO_SUPERCHAT, TIPO_TEXTO, URL_REPOSITORIO, guardar_opcion)
from guyrapu.core.idioma import _, N_, idioma_actual
from guyrapu.core import paquetes_catalogo
from guyrapu.core import paths
from guyrapu.ui import ajuste_tono, ayuda_manual
from guyrapu.ui import confirmar
from guyrapu.ui import menu_interaccion
from guyrapu.ui import menu_obs
from guyrapu.ui import menu_reproductor
from guyrapu.ui import menu_transmision
from guyrapu.ui import voces_ventana
from guyrapu.ui.accesibilidad import anunciar, anunciar_con_sonido
from guyrapu.ui.atajos_captura import ETIQUETAS

logger = diagnostico.obtener_logger(__name__)

# La clave de cada filtro sale de CLAVES_FILTRO, que también valida config.ini.
FILTROS = [
    (N_("Todos"),        None,                      avisos_tiktok.CLAVES_FILTRO[0]),
    (N_("Solo texto"),   TIPO_TEXTO,                 avisos_tiktok.CLAVES_FILTRO[1]),
    (N_("Super Chats"),  TIPO_SUPERCHAT,             avisos_tiktok.CLAVES_FILTRO[2]),
    (N_("Membresías"),   TIPO_MIEMBRO,               avisos_tiktok.CLAVES_FILTRO[3]),
    # Traductores: filtro del chat que muestra solo los avisos de TikTok.
    (N_("Avisos"),       avisos_tiktok.TIPOS_AVISO,  avisos_tiktok.CLAVES_FILTRO[4]),
]


def construir_menu(frame):
    anterior = frame.GetMenuBar()
    mb = wx.MenuBar()

    # Archivo
    _construir_menu_archivo(frame, mb)
    # Ver
    _construir_menu_ver(frame, mb)

    # Chat
    _construir_menu_chat(frame, mb)

    _construir_menu_voz(frame, mb)

    menu_reproductor.construir(frame, mb)
    menu_transmision.construir(frame, mb)
    menu_obs.construir(frame, mb)
    menu_interaccion.construir(frame, mb)

    # Música
    _construir_menu_musica(frame, mb)

    # Herramientas
    _construir_menu_herramientas(frame, mb)

    _construir_menu_ayuda(frame, mb)

    frame.SetMenuBar(mb)
    # Al reconstruir (Preferencias), la barra vieja solo se desengancha: hay
    # que destruirla, y el item de pausa nace como «Pausar» aunque la
    # lectura siga pausada.
    if anterior is not None:
        try:    anterior.Destroy()
        except Exception as error: logger.debug("no se pudo destruir el menú anterior: %s", error)
    frame._sincronizar_pausa()
    _registrar_menus(frame)


def _construir_menu_archivo(frame, mb):
    m = wx.Menu()
    frame.mi_conectar = m.Append(wx.ID_ANY, _("&Conectar") + frame._accel("conectar"))
    frame.mi_desconectar = m.Append(wx.ID_ANY, _("&Desconectar") + frame._accel("desconectar"))
    frame.mi_copiar_enlace = m.Append(wx.ID_ANY, _("Copiar &enlace del directo") + frame._accel("copiar_enlace"))
    m.AppendSeparator()
    mi_historial = m.Append(wx.ID_ANY, _("&Historial de directos…") + frame._accel("abrir_historial"))
    m.AppendSeparator()
    mi_salir = m.Append(wx.ID_EXIT, _("&Salir") + "\tAlt+F4")
    mb.Append(m, _("&Archivo"))
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(frame._conectar_si_procede), frame.mi_conectar)
    frame.Bind(wx.EVT_MENU, lambda e: frame._desconectar_si_procede(), frame.mi_desconectar)
    frame._bind_menu(frame.mi_copiar_enlace,
                     frame._chat_acciones._copiar_enlace_directo)
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(frame._on_historial), mi_historial)
    frame.Bind(wx.EVT_MENU, lambda e: frame.Close(), mi_salir)


def _construir_menu_chat(frame, mb):
    traduccion_chat.configurar(frame._config, al_avisar=anunciar_con_sonido)
    m = wx.Menu()
    frame.mi_enviar_live = m.Append(
        wx.ID_ANY,
        _("&Enviar mensaje al chat del directo (solo YouTube)") + frame._accel("enviar_chat"))
    m.AppendSeparator()
    _construir_submenu_filtro_chat(frame, m)
    frame.mi_buscar_chat = m.Append(
        wx.ID_ANY, _("&Buscar en el chat…") + frame._accel("buscar_chat"))
    frame._bind_menu(frame.mi_buscar_chat,
                     lambda: frame._chat_acciones.abrir_busqueda())
    frame.mi_participacion_chat = m.Append(
        wx.ID_ANY, _("&Participación en el chat…") + frame._accel("participacion_chat"))
    frame._bind_menu(frame.mi_participacion_chat, lambda: frame._chat_acciones.abrir_participacion())
    frame.mi_traducir_chat = m.AppendCheckItem(
        wx.ID_ANY, _("&Traducir chat"))
    frame.mi_traducir_chat.Check(
        bool(frame._config.get("traducir_chat", False)))
    frame._bind_menu(frame.mi_traducir_chat, alternar_traduccion, frame)
    mb.Append(m, _("&Chat"))
    frame.Bind(wx.EVT_MENU, frame._on_enviar_live, frame.mi_enviar_live)


def alternar_traduccion(frame):
    """Cambia la casilla del menú, la guarda y anuncia el estado nuevo."""
    nuevo = not frame._config.get("traducir_chat", False)
    frame._config["traducir_chat"] = nuevo
    frame.mi_traducir_chat.Check(nuevo)
    from guyrapu.ui import gui as _gui
    guardar_opcion(_gui.RUTA_CONFIG, "lectura", "traducir_chat",
                   "true" if nuevo else "false")
    traduccion_chat.configurar(frame._config)
    anunciar(_("Traducción del chat activada") if nuevo
             else _("Traducción del chat desactivada"))


def _construir_menu_voz(frame, mb):
    m = wx.Menu()
    frame.mi_pausa = m.Append(wx.ID_ANY, _("&Pausar lectura") + frame._accel("pausa"))
    mi_det = m.Append(wx.ID_ANY, _("&Detener voz") + frame._accel("detener_tts"))
    mi_vac = m.Append(wx.ID_ANY, _("&Vaciar cola"))
    # Estas tres actúan sobre una lectura en curso: sin conexión no hay nada
    # que pausar/detener/vaciar. Los ajustes de voz de abajo sí quedan libres.
    frame._mi_voz_conexion = [frame.mi_pausa, mi_det, mi_vac]
    m.AppendSeparator()
    _agregar_ajustes_de_voz(frame, m)
    m.AppendSeparator()
    frame.mi_sil_lectura = m.AppendCheckItem(
        wx.ID_ANY, _("S&ilenciar lectura") + frame._accel("silenciar_lectura"))
    frame.mi_sil_sonidos = m.AppendCheckItem(
        wx.ID_ANY, _("Silenciar s&onidos") + frame._accel("silenciar_sonidos"))
    m.AppendSeparator()
    _publicar_menu_voz(frame, m, mb)
    frame._bind_menu(frame.mi_pausa, frame._on_pausa, None)
    frame._bind_menu(mi_det, frame._on_detener_tts, None)
    frame._bind_menu(mi_vac, frame._on_vaciar, None)
    frame._bind_menu(frame.mi_sil_lectura, frame._toggle_silenciar_lectura)
    frame._bind_menu(frame.mi_sil_sonidos, frame._toggle_silenciar_sonidos)


def _construir_menu_herramientas(frame, mb):
    m = wx.Menu()
    # Gestor de descargas: SIEMPRE habilitado (funciona sin conexión de
    # chat, abriendo una URL pegada a mano). Ctrl+S es el atajo.
    frame.mi_descargas = m.Append(
        wx.ID_ANY, _("Administrador de &descargas…") + frame._accel("descargas_abrir"))
    frame.mi_actualizar_ytdlp = m.Append(wx.ID_ANY, _("&Actualizar yt-dlp…"))
    m.AppendSeparator()
    mi_pref = m.Append(wx.ID_ANY, _("&Preferencias…") + frame._accel("abrir_preferencias"))
    mb.Append(m, _("&Herramientas"))
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(frame._abrir_descargas), frame.mi_descargas)
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(frame._on_actualizar_ytdlp, None),
              frame.mi_actualizar_ytdlp)
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(frame._on_preferencias, None), mi_pref)


def _construir_submenu_filtro_chat(frame, menu):
    sub_f = wx.Menu()
    frame._chat_acciones.fi_items = []
    for i, (nombre, _valor, _clave) in enumerate(FILTROS):
        it = sub_f.AppendRadioItem(wx.ID_ANY, _(nombre))
        frame._chat_acciones.fi_items.append(it)
        frame._bind_menu(it, frame._chat_acciones._aplicar_filtro, i)
    frame._mi_filtro_sub = menu.AppendSubMenu(sub_f, _("&Filtro de mensajes"))


def _agregar_ajustes_de_voz(frame, menu):
    """Ajustes de velocidad, volumen y tono, cada uno con sus dos teclas."""
    mi_vmenos = menu.Append(wx.ID_ANY, _("Bajar ve&locidad de la voz") + frame._accel("velocidad_menos"))
    mi_vmas   = menu.Append(wx.ID_ANY, _("Subi&r velocidad de la voz") + frame._accel("velocidad_mas"))
    mi_volm   = menu.Append(wx.ID_ANY, _("&Bajar volumen de la voz") + frame._accel("volumen_menos"))
    mi_volM   = menu.Append(wx.ID_ANY, _("&Subir volumen de la voz") + frame._accel("volumen_mas"))
    mi_tonom  = menu.Append(wx.ID_ANY, _("Bajar &tono de la voz") + frame._accel("tono_menos"))
    mi_tonoM  = menu.Append(wx.ID_ANY, _("S&ubir tono de la voz") + frame._accel("tono_mas"))
    frame._bind_menu(mi_vmenos, frame._ajustar_rate, -1)
    frame._bind_menu(mi_vmas, frame._ajustar_rate, +1)
    frame._bind_menu(mi_volm, frame._ajustar_volume, -5)
    frame._bind_menu(mi_volM, frame._ajustar_volume, +5)
    frame._bind_menu(mi_tonom, ajuste_tono.ajustar_tono, frame, -5)
    frame._bind_menu(mi_tonoM, ajuste_tono.ajustar_tono, frame, +5)


def _publicar_menu_voz(frame, menu, barra):
    """Cierra el menú Voz con Administrar voces y lo pone en la barra."""
    frame.mi_administrar_voces = menu.Append(wx.ID_ANY, _("&Administrar voces…"))
    barra.Append(menu, _("Vo&z"))
    frame.Bind(wx.EVT_MENU, lambda e: voces_ventana.abrir(frame),
               frame.mi_administrar_voces)


def _construir_menu_ayuda(frame, mb):
    m = wx.Menu()
    mi_manual = m.Append(wx.ID_ANY, _("Manual de &uso") + "\tF1")
    mi_novedades = m.Append(wx.ID_ANY, _("&Novedades"))
    mi_guia = m.Append(wx.ID_ANY, _("&Guía de configuración de la API"))
    # Traductores: entrada del menú Ayuda, abre la licencia de cada paquete de voces.
    mi_licencias = m.Append(wx.ID_ANY, _("&Licencias de las voces"))
    mi_incidente = m.Append(wx.ID_ANY, _("&Marcar incidencia") + frame._accel("marcar_incidencia"))
    mi_registros = m.Append(wx.ID_ANY, _("Abrir carpeta de &registros"))
    mi_actualizar_app = m.Append(wx.ID_ANY, _("&Buscar actualizaciones…"))
    mi_about = m.Append(wx.ID_ABOUT, _("&Acerca de…"))
    mb.Append(m, _("A&yuda"))
    frame.Bind(wx.EVT_MENU, lambda e: abrir_documento_paquete(
        frame, "MANUAL", _("Manual de uso")), mi_manual)
    frame.Bind(wx.EVT_MENU, lambda e: abrir_documento_paquete(
        frame, "CHANGELOG", _("Novedades")), mi_novedades)
    frame.Bind(wx.EVT_MENU, lambda e: webbrowser.open(
        f"{URL_REPOSITORIO}/blob/main/docs/CONFIGURACION_API.md"),
        mi_guia)
    frame.Bind(wx.EVT_MENU, lambda e: webbrowser.open(
        paquetes_catalogo.URL_LICENCIAS), mi_licencias)
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(
        frame._on_marcar_incidencia, None), mi_incidente)
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(
        abrir_carpeta_registros, frame), mi_registros)
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(
        frame._on_actualizar_app, None), mi_actualizar_app)
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(frame._on_about, None), mi_about)


def abrir_carpeta_registros(frame) -> None:
    """Abre en el explorador la carpeta con los registros de la aplicación."""
    try:
        os.startfile(str(paths.carpeta_datos()))  # noqa: S606
    except Exception as exc:
        confirmar.avisar(frame, _("No se pudo abrir la carpeta de registros:\n\n{exc}").format(exc=exc),
                         _("Carpeta de registros"), _("Aceptar"), icono=confirmar.ICON_ERROR)


def abrir_documento_paquete(frame, nombre: str, titulo: str, ancla: str | None = None) -> None:
    """Abre en el navegador un documento de la instalación."""
    try:
        os.startfile(str(ayuda_manual.destino_documento(nombre, idioma_actual(), ancla, titulo)))  # noqa: S606
    except Exception as exc:
        confirmar.avisar(frame, _("No se pudo abrir el documento:\n\n{exc}").format(exc=exc),
                         titulo, _("Aceptar"), icono=confirmar.ICON_ERROR)


def _registrar_menus(frame) -> None:
    """Anota cada comando del menú principal sin impedir que corra.

    Se enlaza después que los manejadores propios: wx llama primero al
    último enlazado, así este registra y con `Skip` sigue el del ítem.
    """
    def al_elegir(evento) -> None:
        ident = evento.GetId()
        logger.debug("MENU id=%s etiqueta=%s", ident,
                     _etiqueta_menu(frame, ident))
        evento.Skip()

    frame.Bind(wx.EVT_MENU, al_elegir)


def _etiqueta_menu(frame, ident: int) -> str:
    """El texto del ítem con ese id en la barra, sin `&` ni atajo."""
    try:
        barra = frame.GetMenuBar()
        for indice in range(barra.GetMenuCount()):
            etiqueta = _buscar_en_menu(barra.GetMenu(indice), ident)
            if etiqueta is not None:
                return etiqueta
    except Exception:
        return "?"
    return "?"


def _buscar_en_menu(menu, ident: int):
    for item in menu.GetMenuItems():
        if item.GetId() == ident:
            return item.GetItemLabelText().replace("&", "").split("\t")[0]
        if item.IsSubMenu():
            etiqueta = _buscar_en_menu(item.GetSubMenu(), ident)
            if etiqueta is not None:
                return etiqueta
    return None


def _abrir_ia(frame):
    from guyrapu.ui import ia_ventana
    ia_ventana.abrir_ventana(frame)


def _consulta_rapida(frame):
    from guyrapu.ui import ia_consulta_rapida
    ia_consulta_rapida.consultar(frame)


def _construir_menu_ver(frame, mb):
    from guyrapu.ui.gui import (
        PAG_CHAT, PAG_COMENTARIOS, REG_CONEXION, REG_REPRODUCTOR,
    )
    m = wx.Menu()
    mi_sig = m.Append(wx.ID_ANY, _("Región &siguiente") + "\tF6")
    mi_ant = m.Append(wx.ID_ANY, _("Región &anterior") + "\tShift+F6")
    m.AppendSeparator()
    mi_conx = m.Append(wx.ID_ANY, _("Ir a co&nexión"))
    mi_lista = m.Append(wx.ID_ANY, _("Ir a la &lista del panel actual") + frame._accel("ir_lista"))
    mi_chat = m.Append(wx.ID_ANY, _("Ir al &chat del directo"))
    mi_com  = m.Append(wx.ID_ANY, _("Ir a co&mentarios"))
    mi_rep  = m.Append(wx.ID_ANY, _("Ir al &reproductor"))
    m.AppendSeparator()
    mi_estado = m.Append(wx.ID_ANY, _("Anunciar &estado") + frame._accel("anunciar_estado"))
    mi_autor = m.Append(wx.ID_ANY, _("Anunciar a&utor del último mensaje") + frame._accel("anunciar_autor"))
    sub_rec = wx.Menu()
    for n in range(1, 11):
        accion = f"chat_reciente_{n}"
        item = sub_rec.Append(wx.ID_ANY, _(ETIQUETAS[accion]) + frame._accel(accion))
        frame._bind_menu(item, frame._leer_reciente, n)
    m.AppendSubMenu(sub_rec, _("Mensajes recientes &del chat"))
    mi_escena = m.Append(wx.ID_ANY, _("Describir escena de &OBS") + frame._accel("describir_escena"))
    mi_ia = m.Append(wx.ID_ANY, _("Preguntar a la &IA sobre la imagen…") + frame._accel("preguntar_ia"))
    mi_rapida = m.Append(wx.ID_ANY, _("Consul&ta rápida a la IA") + frame._accel("consulta_rapida_ia"))
    mb.Append(m, _("&Ver"))
    frame.Bind(wx.EVT_MENU, lambda e: frame._navegar_region(+1), mi_sig)
    frame.Bind(wx.EVT_MENU, lambda e: frame._navegar_region(-1), mi_ant)
    frame.Bind(wx.EVT_MENU, lambda e: frame._ir_region(REG_CONEXION), mi_conx)
    frame.Bind(wx.EVT_MENU, lambda e: frame._ir_lista(), mi_lista)
    frame.Bind(wx.EVT_MENU, lambda e: frame._ir_pestana(PAG_CHAT), mi_chat)
    frame.Bind(wx.EVT_MENU, lambda e: frame._ir_pestana(PAG_COMENTARIOS), mi_com)
    frame.Bind(wx.EVT_MENU, lambda e: frame._ir_region(REG_REPRODUCTOR), mi_rep)
    frame._bind_menu(mi_estado, frame._anunciar_estado)
    frame._bind_menu(mi_autor, frame._anunciar_autor)
    frame._bind_menu(mi_escena, frame._describir_escena)
    frame._bind_menu(mi_ia, _abrir_ia, frame)
    frame._bind_menu(mi_rapida, _consulta_rapida, frame)
    # De «Ver», solo tiene sentido con conexión la navegación por paneles;
    # «Ir a conexión» y «Anunciar estado» quedan siempre disponibles.
    frame._mi_ver_conexion = [mi_sig, mi_ant, mi_lista, mi_chat, mi_com, mi_rep]


def _construir_menu_musica(frame, mb):
    m = wx.Menu()
    frame.mi_musica_ventana = m.Append(
        wx.ID_ANY, _("&Elegir música…") + frame._accel("musica_ventana"))
    m.AppendSeparator()
    frame.mi_musica_play = m.Append(
        wx.ID_ANY, _("Reproducir o &pausar") + frame._accel("musica_play"))
    frame.mi_musica_siguiente = m.Append(
        wx.ID_ANY, _("&Siguiente canción") + frame._accel("musica_siguiente"))
    frame.mi_musica_anterior = m.Append(
        wx.ID_ANY, _("Canción &anterior") + frame._accel("musica_anterior"))
    frame.mi_musica_vol_mas = m.Append(
        wx.ID_ANY, _("Subir &volumen") + frame._accel("musica_vol_mas"))
    frame.mi_musica_vol_menos = m.Append(
        wx.ID_ANY, _("&Bajar volumen") + frame._accel("musica_vol_menos"))
    frame.mi_musica_que_suena = m.Append(
        wx.ID_ANY, _("Anunciar &canción actual") + frame._accel("musica_que_suena"))
    frame.mi_musica_adelantar = m.Append(
        wx.ID_ANY, _("Avanzar 10 segu&ndos") + frame._accel("musica_adelantar"))
    frame.mi_musica_retroceder = m.Append(
        wx.ID_ANY, _("Re&troceder 10 segundos") + frame._accel("musica_retroceder"))
    m.AppendSeparator()
    frame.mi_musica_silenciar = m.AppendCheckItem(
        wx.ID_ANY, _("Silenciar &música") + frame._accel("musica_silenciar"))
    mi_detener = m.Append(
        wx.ID_ANY, _("&Detener música") + frame._accel("musica_detener"))
    frame.mi_musica_aleatorio = m.AppendCheckItem(
        wx.ID_ANY, _("&Orden aleatorio") + frame._accel("musica_aleatorio"))
    frame.mi_musica_aleatorio.Check(
        bool(frame._config.get("musica_aleatorio", False)))
    mi_repetir = m.Append(
        wx.ID_ANY, _("Cambiar &repetición") + frame._accel("musica_repetir"))
    mb.Append(m, _("&Música"))
    for item, accion in (
            (frame.mi_musica_ventana, "abrir_ventana"),
            (frame.mi_musica_play, "reproducir_o_pausar"),
            (frame.mi_musica_siguiente, "siguiente"),
            (frame.mi_musica_anterior, "anterior"),
            (frame.mi_musica_vol_mas, "subir_volumen"),
            (frame.mi_musica_vol_menos, "bajar_volumen"),
            (frame.mi_musica_que_suena, "que_suena"),
            (frame.mi_musica_adelantar, "adelantar"),
            (frame.mi_musica_retroceder, "retroceder"),
            (frame.mi_musica_silenciar, "alternar_silencio"),
            (mi_detener, "detener"),
            (frame.mi_musica_aleatorio, "alternar_aleatorio"),
            (mi_repetir, "ciclar_repetir")):
        frame._bind_menu(item, lambda a=accion: getattr(frame._musica, a)())
