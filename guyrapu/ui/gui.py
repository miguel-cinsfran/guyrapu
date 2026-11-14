# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Interfaz wxPython accesible: barra de menú nativa + paneles en notebook.

Rediseño: una sola ventana con barra de menú (que NVDA lee de forma nativa y
que muestra los atajos), barra superior con URL+Conectar, y un notebook con los
paneles Chat en vivo, Comentarios y Reproductor. Al conectar se detecta si la
URL es un directo o un vídeo subido y se ajustan los paneles.
"""

from __future__ import annotations

import random
import threading
import time
import webbrowser  # noqa: F401  (reexport para las pruebas)

import wx

from guyrapu.core.config import APP_NAME, APP_VERSION, TIPO_TEXTO
from guyrapu.core.version_legible import version_legible
from guyrapu.ui.gui_menu import FILTROS
from guyrapu.ui.chat_acciones import AccionesChat, IDX_FILTRO
from guyrapu.core.config import parsear_atajos, detectar_conflictos_atajos, guardar_opcion
from guyrapu.core.idioma import N_, _
from guyrapu.core import acerca_de, paths
from guyrapu.core import anuncio_ajuste
from guyrapu.capture import chat_adicional, deteccion
from guyrapu.capture import metadatos
from guyrapu.capture import estado_sesion
from guyrapu.core import historial
from guyrapu.ui.lista_chat import MensajeChat
from guyrapu.ui import atajos_captura, confirmar
from guyrapu.ui import gui_cierre
from guyrapu.ui import gui_construccion
from guyrapu.ui import gui_sesion
from guyrapu.voice import escala_voz
from guyrapu.voice import sound_player as _snd
from guyrapu.youtube import credenciales
from guyrapu.youtube import youtube_api
from guyrapu.core import diagnostico, vigia_interfaz
from guyrapu.capture.montos import sumar_monto, texto_importes
from guyrapu.obs import overlay_servidor  # noqa: F401  (reexport para gui_estado y gui_transmitir)
from guyrapu.capture import programados
from guyrapu.capture import descartes
from guyrapu.capture import redaccion  # noqa: F401  (reexport para gui_envio_chat)
from guyrapu.obs import obs_entradas_audio
from guyrapu.obs import obs_estado
from guyrapu.obs import obs_vigilante
from guyrapu.obs import obs_activacion
from guyrapu.obs import obs_cliente
from guyrapu.obs.obs_panel import GestorPanelObs
from guyrapu.player import flujo_tiktok
from guyrapu.ui import titulo_ventana
from guyrapu.ui.sesion_conectada import SesionConectada

MAX_ITEMS_CHAT  = 500
TIMER_STATUS_MS = 1000
TIMER_DIAGNOSTICO_MS = 100
ANCHO_DEFECTO   = 860
ALTO_DEFECTO    = 700

# Mensaje bajo la barra de URL cuando no hay conexión. Breve pero completo:
# qué se puede pegar y cómo conectar.
MENSAJE_INICIAL = N_("Sin conectar. Pega un enlace de YouTube (directo o vídeo) o "
                     "de un directo de TikTok y pulsa Conectar (Alt+C). En YouTube "
                     "podrás leer el chat y los comentarios; en TikTok, el chat del "
                     "directo.")
RUTA_CONFIG = None  # se asigna en iniciar_gui() con paths.config_ini()

# Índices de las páginas del notebook (solo chat y comentarios; el reproductor
# es una región fija, no una pestaña).
PAG_CHAT = 0
PAG_COMENTARIOS = 1

# Regiones que recorre F6 / Shift+F6.
REG_CONEXION = 0
REG_CONTENIDO = 1
REG_REPRODUCTOR = 2
# Traductores: regiones que recorre F6 en la ventana principal.
_NOMBRE_REGION = (N_("Conexión"), N_("Contenido"), N_("Reproductor"))

logger = diagnostico.obtener_logger(__name__)
_OBS_COMPONENTES = frozenset(("obs_transmision", "obs_grabacion", "obs_escena"))


# Reexportados: muchos módulos todavía los piden a gui.
from guyrapu.ui.accesibilidad import (
    ContadorAccesible, _lector_init, anunciar,
    anunciar_con_sonido,
    nombre_accesible,  # noqa: F401  (reexport para la interfaz)
)
from guyrapu.ui.tema import ALTO_CONTRASTE, _T, _tc  # noqa: F401  (reexports)


def anunciar_conflictos_atajos(raw: dict | None) -> None:
    for perdedora, conservada, combinacion in detectar_conflictos_atajos(raw):
        anunciar(
            _("{combinacion} ya está asignado a {conservada}. "
              "Se desactivó el atajo de {perdedora}.").format(
                perdedora=perdedora, conservada=conservada, combinacion=combinacion))


def caja_de_grupo(panel, titulo):
    """Crea una caja y devuelve el sizer junto al padre de sus controles."""
    caja = wx.StaticBox(panel, label=titulo)
    return wx.StaticBoxSizer(caja, wx.VERTICAL), caja


_ACCEL_NOMBRES = {
    "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift",
    "enter": "Enter", "left": "Left", "right": "Right",
    "up": "Up", "down": "Down", "space": "Space", "end": "End",
}


def _fmt_accel(texto: str) -> str:
    """'f5'->'F5', 'ctrl+left'->'Ctrl+Left', 'alt+enter'->'Alt+Enter'.

    Formato que entiende wx para los aceleradores de menú.
    """
    if not texto:
        return ""
    partes = []
    for p in texto.split("+"):
        partes.append(_ACCEL_NOMBRES.get(p, p.upper()))
    return "+".join(partes)


class _LogWx(wx.Log):
    """Reenvia el log de wx al logger del modulo sin recortar el texto."""

    def DoLogRecord(self, level, msg, info):
        # Mensaje entero, sin recortar: es lo unico para diagnosticar
        if level in (wx.LOG_FatalError, wx.LOG_Error, wx.LOG_Warning):
            logger.warning("wx: %s", msg)
        else:
            logger.debug("wx: %s", msg)


# ── Frame principal ──────────────────────────────────────────────────────────

class VentanaPrincipal(chat_adicional.MixinChatAdicional, wx.Frame):

    # La construcción (gui_construccion) crea estos controles sobre la ventana.
    _boton_directo: object
    _com_panel: object
    _diagnostico_timer: wx.Timer
    _inicio: object
    _mi_filtro_sub: object
    _musica: object
    _pag_chat: object
    _pag_info: object
    _panel_principal: object
    _recientes: object
    _regiones: list
    _rep_panel: object
    _timer: wx.Timer
    _zona: object

    def __init__(self, parent, config, cola, stats, worker, parada):
        super().__init__(
            parent,
            # Traductores: título de la ventana: nombre de la app y versión.
            title=_("{app} {version}").format(
                app=APP_NAME, version=version_legible(APP_VERSION)),
            size=(ANCHO_DEFECTO, ALTO_DEFECTO),
            name="VentanaPrincipal",
        )
        # Piso de la ventana: sin esto, se podía achicar hasta el punto de
        # aplastar el chat, el reproductor y los textos, cortándolos.
        try:
            self.SetMinSize((640, 480))
        except Exception as error:
            logger.debug("no se pudo fijar el tamaño mínimo de la ventana: %s", error)
        self._config    = config
        self._cola      = cola
        self._stats     = stats
        self._worker    = worker
        self._parada    = parada
        self._alive     = True
        self._apagando  = False
        self._conectado = False
        self._conectando = False   # entre pulsar Conectar y la respuesta
        self._texto_tipo = _(MENSAJE_INICIAL)   # texto de lbl_tipo sin saltos de Wrap
        self._titulo_stream = ""
        self.sesion = SesionConectada()
        self._obs_transmitiendo = False   # OBS emite sin supervisor a la vista

        self._sc_totales: dict[str, float] = {}
        self.programador = programados.ProgramadorMensajes(
            programados.cargar(paths.mensajes_programados()))

        # Voz activa: se elige en Preferencias, Voces.
        self._voces_menu = []
        self._voz_idx = 0
        self._voz_nombre = "—"

        self.on_conectar_cb    = None
        self.on_desconectar_cb = None

        self._atajos = parsear_atajos(config.get("atajos_raw", {}))
        anunciar_conflictos_atajos(config.get("atajos_raw", {}))
        self._diagnostico_marca = time.monotonic()
        self._diagnostico_censo = self._diagnostico_marca
        self._diagnostico_parada = threading.Event()
        self._obs_vigilante = None
        self._supervisor = None
        self._descripcion_escena_en_curso = False

        # El menú arma los ítems del filtro antes que la lista del chat, así
        # que las acciones existen desde acá y toman la lista al crearse.
        self._chat_acciones = AccionesChat(
            None, None, self._cola, self._config, lambda: self.sesion, self)
        self._build_menubar()
        if self._config.get("overlay_activo", False):
            self._cambiar_overlay(True)
        gui_construccion.construir(self)
        gui_construccion.enlazar_eventos(self)
        gui_construccion.iniciar_temporizadores(self)
        self._actualizar_vigilante_obs()
        diagnostico.crear_hilo(
            lambda: vigia_interfaz.vigilar_hilo_interfaz(
                lambda: self._diagnostico_marca, self._diagnostico_parada),
            "VigilanteInterfaz").start()
        self.Centre()

    # ── Barra de menú ────────────────────────────────────────────────────────

    def _accel(self, accion: str) -> str:
        at = self._atajos.get(accion)
        return ("\t" + _fmt_accel(at.texto)) if at else ""

    def _bind_menu(self, item, fn, *args):
        """Difiere el anuncio hasta que el menú se cerró y volvió el foco."""
        if isinstance(item, tuple):
            menu, identificador = item
            menu.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(fn, *args), id=identificador)
        else:
            self.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(fn, *args), item)

    def _build_menubar(self):
        from guyrapu.ui import gui_menu
        gui_menu.construir_menu(self)

    def _sincronizar_pausa(self) -> None:
        try:    pausado = bool(self._worker.esta_pausado())
        except Exception: return
        self.mi_pausa.SetItemLabel(
            (_("&Reanudar lectura") if pausado else _("&Pausar lectura")) + self._accel("pausa"))

    def _cambiar_overlay(self, encender):
        from guyrapu.ui import gui_transmitir
        return gui_transmitir.cambiar_overlay(self, encender)

    def _guardar_usuario_tiktok(self, usuario):
        from guyrapu.ui import gui_transmitir
        return gui_transmitir.guardar_usuario_tiktok(self, usuario)

    def _guardar_destino_transmision(self, destino):
        from guyrapu.ui import gui_transmitir
        return gui_transmitir.guardar_destino_transmision(self, destino)

    def _alternar_aviso_sobrecarga(self):
        from guyrapu.ui import gui_transmitir
        gui_transmitir.alternar_aviso_sobrecarga(self)

    def _guardar_datos_directo_youtube(self, titulo, descripcion, privacidad,
                                        latencia=None, ninos=False, dvr=True,
                                        categoria="", etiquetas=None,
                                        miniatura="", lista="",
                                        lista_titulo=""):
        from guyrapu.ui import gui_transmitir
        return gui_transmitir.guardar_datos_directo_youtube(
            self, titulo, descripcion, privacidad, latencia, ninos, dvr,
            categoria, etiquetas, miniatura, lista, lista_titulo)

    def _actualizar_boton_directo(self) -> None:
        from guyrapu.ui import gui_transmitir
        gui_transmitir.actualizar_boton_directo(self)

    def _al_terminar_supervisor(self) -> None:
        from guyrapu.ui import gui_transmitir
        gui_transmitir.al_terminar_supervisor(self)

    def _supervisar_transmision(self, accion, destino="", usuario="", revision=None):
        from guyrapu.ui import gui_transmitir
        return gui_transmitir.supervisar_transmision(self, accion, destino, usuario, revision)

    def _on_actualizar_ytdlp(self, event):
        from guyrapu.ui import gui_actualizar_ytdlp
        gui_actualizar_ytdlp.abrir_ventana_actualizacion(self)

    def _on_actualizar_app(self, event):
        from guyrapu.ui import gui_actualizar_app
        gui_actualizar_app.abrir_ventana_actualizacion(self)

    def _on_activate(self, event):
        if event.GetActive() and self._alive:
            # Diferido: wx repone el foco en el último control tras este evento.
            wx.CallAfter(self._foco_al_activar)
        event.Skip()

    def _foco_al_activar(self) -> None:
        """Al volver a la app, llevar el foco al contenido (o a la URL si no hay
        conexión) SOLO si no quedó ya en un control de la ventana: al cerrarse
        un diálogo o un aviso, el usuario vuelve a donde estaba (reproductor,
        redacción…) y no hay que arrastrarlo al chat."""
        if not self._alive:
            return
        foco = wx.Window.FindFocus()
        if foco is not None and self._es_descendiente(foco):
            return
        if self._conectado:
            self._foco_contenido()
        else:
            self.txt_url.SetFocus()

    def _es_descendiente(self, ventana) -> bool:
        while ventana is not None:
            if ventana is self:
                return True
            try:    ventana = ventana.GetParent()
            except Exception: return False
        return False

    def _arrancar_precalentamiento(self) -> None:
        if self._alive:
            self._rep_panel._precalentar()

    # ── Navegación de paneles ────────────────────────────────────────────────

    def _navegar_region(self, delta: int):
        if not self._conectado:
            self.txt_url.SetFocus()
            anunciar(_("Conéctate primero para usar los paneles"))
            return
        self._region_idx = (self._region_idx + delta) % len(self._regiones)
        self._ir_region(self._region_idx)

    def _ir_region(self, idx: int):
        if not (0 <= idx < len(self._regiones)):
            return
        if idx != REG_CONEXION and not self._conectado:
            anunciar(_("Conéctate primero para usar los paneles"))
            return
        self._region_idx = idx
        try:    self._regiones[idx]()
        except Exception as exc: logger.debug("ir_region %d: %s", idx, exc)
        nombre = _(_NOMBRE_REGION[idx])
        if idx == REG_CONTENIDO:
            # Traductores: región actual y pestaña al moverse con F6.
            nombre = _("{region}: {pagina}").format(
                region=nombre, pagina=self.nb.GetPageText(self.nb.GetSelection()))
        anunciar(nombre)

    def _ir_lista(self):
        """Alt+L: foco directo a la lista de la pestaña actual (chat o comentarios)."""
        if not self._conectado:
            anunciar(_("Conéctate primero"))
            return
        self._region_idx = REG_CONTENIDO
        self._foco_contenido()

    def _foco_contenido(self):
        pag = self.nb.GetCurrentPage()
        if pag is self._pag_chat:
            self.lb_chat.SetFocus()
        elif pag is self._com_panel:
            self._com_panel.anclar_foco()
        elif pag is self._pag_info:
            self.txt_info.SetFocus()
        else:
            self.nb.SetFocus()

    def _ir_pestana(self, idx: int):
        """Selecciona una pestaña del notebook y deja el foco en su contenido."""
        if 0 <= idx < self.nb.GetPageCount():
            # ChangeSelection no dispara EVT_NOTEBOOK_PAGE_CHANGED (SetSelection
            # sí): si no, enlazar_anuncio_de_pestana anunciaba la pestaña y aquí
            # otra vez.
            self.nb.ChangeSelection(idx)
            self._region_idx = REG_CONTENIDO
            self._foco_contenido()
            anunciar(self.nb.GetPageText(idx))

    def _rep_accion(self, metodo: str, *args):
        if getattr(self, "_rep_panel", None) is None:
            anunciar(_("El reproductor no está disponible"))
            return
        try:
            getattr(self._rep_panel, metodo)(*args)
        except Exception as exc:
            logger.debug("acción reproductor %s: %s", metodo, exc)

    def _toggle_botones_rep(self):
        """Desde el menú: alterna los botones del reproductor. El panel avisa de
        vuelta (on_botones_toggle → _on_botones_rep_cambio) para sincronizar."""
        try:    self._rep_panel.alternar_botones()
        except Exception as exc:
            logger.debug("alternar botones reproductor: %s", exc)

    def _on_botones_rep_cambio(self, visibles: bool):
        """El panel cambió la visibilidad de los botones (por su interruptor o por
        el menú): sincronizar la casilla del menú y guardar la preferencia."""
        try:    self.mi_rep_botones.Check(bool(visibles))
        except Exception as error: logger.debug("no se pudo marcar la casilla: %s", error)
        self._config["mostrar_botones_reproductor"] = bool(visibles)
        guardar_opcion(RUTA_CONFIG, "ui", "mostrar_botones_reproductor",
                       "true" if visibles else "false")

    # ── Historial de directos ────────────────────────────────────────────────

    def _ruta_historial(self):
        return paths.historial_lives()

    def registrar_historial(self, plataforma: str, clave: str, url: str,
                            titulo: str, canal: str, directo: bool = False) -> None:
        """Guarda (o actualiza) una entrada del historial al conectar con éxito.
        Lo llama main vía wx.CallAfter cuando ya tiene título y canal."""
        if not self._alive or not clave:
            return
        try:
            ruta = self._ruta_historial()
            lista = historial.upsert(historial.cargar(ruta), plataforma, clave,
                                     url, titulo, canal, directo=directo)
            historial.guardar(ruta, lista)
            # Solo un directo deja enlace copiable; un vídeo grabado lo vacía.
            if directo:
                self.sesion.enlace_directo = url
            else:
                self.sesion.enlace_directo = ""
        except Exception as exc:
            logger.debug("registrar historial: %s", exc)

    def _on_historial(self):
        self._inicio.abrir_historial()

    def _reconectar_desde_historial(self, url: str) -> None:
        """Desde el historial: si hay una sesión, desconecta; luego pone la URL
        elegida y conecta."""
        if not url:
            return
        if self._conectado:
            if self.on_desconectar_cb:
                try:    self.on_desconectar_cb()
                except Exception as error: logger.debug("no se pudo desconectar: %s", error)
            self.set_conectado(False)
        self.txt_url.SetValue(url)
        wx.CallAfter(self._on_conectar, None)

    # ── Handlers de conexión ─────────────────────────────────────────────────

    def _conectar_si_procede(self):
        if not self._conectado:
            self._on_conectar(None)

    def _desconectar_si_procede(self):
        if self._conectado or self._conectando:
            self._on_conectar(None)

    def _on_conectar(self, event):
        gui_sesion.on_conectar(self, event)

    def url_invalida(self):
        gui_sesion.url_invalida(self)

    def _on_preferencias(self, event):
        try:
            from guyrapu.ui.gui_preferencias import abrir_preferencias
            avisos = []
            acepto = abrir_preferencias(self, self._config, avisos=avisos)
            # La lista ya se guardó en disco al tocar sus botones: se relee
            # haya aceptado o no, y el reloj se arma de nuevo con la lista nueva.
            self.programador.recargar(programados.cargar(paths.mensajes_programados()))
            if acepto:
                # El anuncio se difiere para que NVDA termine de decir el foco
                # de la ventana principal antes de hablar, y sin interrumpir lo
                # que diga _aplicar_preferencias_en_caliente.
                def _aplicar_y_avisar():
                    if not self._alive:
                        return
                    self._aplicar_preferencias_en_caliente()
                    if avisos:
                        anunciar(" ".join(avisos), urgente=False)
                wx.CallLater(300, _aplicar_y_avisar)
        except Exception as exc:
            logger.warning("No se pudo abrir preferencias: %s", exc)
            confirmar.avisar(self, _("No se pudo abrir Preferencias:\n{detalle}").format(detalle=exc),
                             # Traductores: título de un cuadro de error.
                             _("Error"), _("Aceptar"), icono=confirmar.ICON_ERROR)
        # La pestaña API puede haber cambiado la sesión: refrescar.
        self._actualizar_estado_online()

    def _on_obs_micro(self, event):
        def avisar(texto, sonido):
            def _avisar():
                if sonido:
                    _snd.reproducir(sonido)
                anunciar(texto)
            wx.CallAfter(_avisar)

        anterior = self.mi_obs_micro.IsChecked()
        def _alternar():
            obs_entradas_audio.microfono_por_atajo(
                self._config.get("obs_microfono", ""), avisar,
                lambda e: wx.CallAfter(self.mi_obs_micro.Check, anterior if e is None else e))

        diagnostico.crear_hilo(_alternar, "MicrofonoObs").start()

    # ── Gestor de descargas (gui_descargas) ──────────────────────────────────
    # Abre el diálogo siempre (no requiere conexión). Si le llega una URL, la
    # precarga (caso "Descargar este vídeo"). Importamos gui_descargas perezoso
    # para que el ciclo de imports (gui → gui_descargas → gui) no se queje.

    def _abrir_descargas(self, url: str | None = None) -> None:
        try:
            from guyrapu.ui.gui_descargas import abrir
        except Exception as exc:
            logger.warning("No se pudo abrir el gestor de descargas: %s", exc)
            confirmar.avisar(self, _("No se pudo abrir el Administrador de descargas:\n{detalle}").format(detalle=exc),
                             # Traductores: título de un cuadro de error.
                             _("Error"), _("Aceptar"), icono=confirmar.ICON_ERROR)
            return
        try:
            abrir(self, url, self._reconectar_desde_historial, self._musica)
        except Exception as exc:
            logger.warning("gestor de descargas: %s", exc)
            confirmar.avisar(self, _("Error en el Administrador de descargas:\n{detalle}").format(detalle=exc),
                             # Traductores: título de un cuadro de error.
                             _("Error"), _("Aceptar"), icono=confirmar.ICON_ERROR)

    def _aplicar_preferencias_en_caliente(self):
        from guyrapu.ui import gui_aplicar_preferencias
        gui_aplicar_preferencias.aplicar_en_caliente(self)

    def _actualizar_vigilante_obs(self):
        activos = set(self._config.get("estado_toggles") or ())
        con_titulo = bool(self._config.get("titulo_estado_obs", False))
        if con_titulo or _OBS_COMPONENTES.intersection(activos):
            if self._obs_vigilante is None:
                self._obs_vigilante = obs_vigilante.VigilanteObs(al_anunciar=anunciar_con_sonido)
                self._obs_vigilante.iniciar()
        elif self._obs_vigilante is not None:
            self._obs_vigilante.detener()
            self._obs_vigilante = None

    def _on_about(self, event):
        confirmar.avisar(
            self, acerca_de.texto(APP_VERSION),
            _("Acerca de"), _("Aceptar"), icono=confirmar.ICON_INFORMATION)

    def _on_marcar_incidencia(self, event):
        diagnostico.marcar_incidencia()
        anunciar(_("La marca de incidencia se guardó"))

    # ── Handlers de voz / TTS ────────────────────────────────────────────────

    def _on_pausa(self, event):
        self._worker.toggle_pausa()
        pausado = self._worker.esta_pausado()
        self._sincronizar_pausa()
        _snd.reproducir("pausa" if pausado else "reanudar")
        # Traductores: lectura en pausa o reanudada.
        anunciar(_("Pausado") if pausado else _("Reanudado"))

    def _on_vaciar(self, event):
        self._worker.vaciar_cola()
        _snd.reproducir("cola_vaciada")
        anunciar(_("Cola vaciada"))

    def _on_detener_tts(self, event):
        self._worker.detener_actual()
        anunciar(_("Voz detenida"))

    def _aplicar_voz(self, idx: int):
        self._worker.cambiar_voz(idx)
        self._voz_idx = idx
        self._voz_nombre = self._nombre_voz(idx)
        # Se guarda el NOMBRE, no el número: con el índice, instalar una voz
        # corre la lista y la app hablaría con otra sin avisar.
        self._config["voz"] = self._voz_nombre
        guardar_opcion(RUTA_CONFIG, "voz", "voz", self._voz_nombre)
        _snd.reproducir("voz_cambiada")
        # Traductores: {nombre} es la voz activa.
        anunciar(_("Voz: {nombre}").format(nombre=self._voz_nombre))

    def _nombre_voz(self, idx: int) -> str:
        if 0 <= idx < len(self._voces_menu):
            return self._voces_menu[idx]
        return "—"

    def _ajustar_rate(self, delta):
        # El worker mueve su porcentaje al instante (lo aplica en su hilo), así
        # que get_rate() ya devuelve el valor nuevo sin predecirlo aquí.
        self._worker.cambiar_rate(delta)
        pct = self._worker.get_rate()
        guardar_opcion(RUTA_CONFIG, "voz", "velocidad_voz", str(pct))
        anunciar(anuncio_ajuste.anuncio_velocidad(pct))

    def _ajustar_volume(self, delta):
        self._worker.cambiar_volumen(delta)
        v = self._worker.get_volume()
        guardar_opcion(RUTA_CONFIG, "voz", "volumen", f"{v / 100:.2f}")
        anunciar(anuncio_ajuste.anuncio_volumen(v))

    def _toggle_silenciar_sonidos(self):
        nuevo = not _snd.esta_silenciado()
        _snd.silenciar_todo(nuevo)
        self._config["silenciar_sonidos"] = nuevo
        self.mi_sil_sonidos.Check(nuevo)
        guardar_opcion(RUTA_CONFIG, "ui", "silenciar_sonidos", "true" if nuevo else "false")
        anunciar(_("Sonidos silenciados") if nuevo else _("Sonidos activados"))

    def _toggle_silenciar_lectura(self):
        nuevo = not self._config.get("silenciar_lectura", False)
        self._config["silenciar_lectura"] = nuevo
        self.mi_sil_lectura.Check(nuevo)
        guardar_opcion(RUTA_CONFIG, "sesion", "silenciar_lectura", "true" if nuevo else "false")
        anunciar(_("Lectura silenciada") if nuevo else _("Lectura activada"))

    def _snapshot_sesion(self) -> estado_sesion.SnapshotSesion:
        from guyrapu.ui import gui_estado
        return gui_estado.snapshot_sesion(self)

    def _total_aportes_texto(self) -> str:
        from guyrapu.ui import gui_estado
        return gui_estado.total_aportes_texto(self)

    def _anunciar_estado(self):
        from guyrapu.ui import gui_estado
        gui_estado.anunciar_estado(self)

    def _anunciar_autor(self):
        from guyrapu.ui import gui_estado
        gui_estado.anunciar_autor(self)

    def _leer_reciente(self, n: int):
        self._recientes.leer(n)

    def _describir_escena(self):
        from guyrapu.ui import gui_estado
        gui_estado.describir_escena(self)

    def _anunciar_descripcion_escena(self, texto):
        self._descripcion_escena_en_curso = False
        anunciar(texto or _("Sin información de la escena."))

    # ── Enviar al chat del directo (API oficial) ─────────────────────────────

    def _on_enviar_live(self, event):
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.on_enviar_live(self, event)

    def _enviar_live_redactado(self, texto):
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.enviar_live_redactado(self, texto)

    def _accion_api(self, accion, mensaje_ok: str, sonido: str = "enviado") -> None:
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.accion_api(self, accion, mensaje_ok, sonido)

    def _api_ok(self, mensaje, sonido: str = "enviado"):
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.api_ok(self, mensaje, sonido)

    def _api_err(self, exc):
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.api_err(self, exc)

    def _actualizar_estado_online(self):
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.actualizar_estado_online(self)

    def _actualizar_motivo_redaccion(self):
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.actualizar_motivo_redaccion(self)

    def _sesion_api_disponible(self) -> bool:
        return bool(youtube_api.google_disponible() and credenciales.hay_sesion())

    def _iniciar_programados_si_corresponde(self, ahora: float) -> None:
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.iniciar_programados_si_corresponde(self, ahora)

    def _enviar_programado(self, mensaje: dict, ahora: float) -> None:
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.enviar_programado(self, mensaje, ahora)

    def _programado_enviado(self, mensaje: dict) -> None:
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.programado_enviado(self, mensaje)

    def _programado_fallo(self, exc) -> None:
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.programado_fallo(self, exc)

    def _procesar_programado(self) -> None:
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.procesar_programado(self)

    def _moderar(self, autor: str, canal_id: str, segundos: int | None) -> None:
        from guyrapu.ui import gui_envio_chat
        gui_envio_chat.moderar(self, autor, canal_id, segundos)

    # ── Timer ────────────────────────────────────────────────────────────────

    def _on_timer(self, event):
        if self._alive:
            try:    self._actualizar_sb()
            except Exception as error: logger.debug("no se pudo actualizar la barra: %s", error)
            try:    self._procesar_programado()
            except Exception as error: logger.debug("no se pudo enviar lo programado: %s", error)
            try:    self._avisar_descartes()
            except Exception as error: logger.debug("no se pudo avisar descartes: %s", error)
            try:    titulo_ventana.aplicar(self)
            except Exception as error: logger.debug("no se pudo actualizar el título: %s", error)

    def _avisar_descartes(self) -> None:
        if descartes.hay_que_avisar(self._stats.descartados, self.sesion.descartes_avisado):
            try:
                _snd.reproducir("aviso")
            except Exception as error:
                logger.debug("no se pudo reproducir el aviso de descartes: %s", error)
            anunciar(descartes.frase_aviso(self._config.get("umbral_solo_nombre", 0)))
            self.sesion.descartes_avisado = True

    def _on_diagnostico_timer(self, event):
        if not self._alive:
            return
        ahora = time.monotonic()
        self._diagnostico_marca = ahora
        censo = diagnostico.debe_censar_hilos(self._diagnostico_censo, ahora)
        if censo:
            self._diagnostico_censo, texto = censo
            diagnostico.logger.info("%s", texto)

    # ── API pública (main.py la invoca vía wx.CallAfter) ─────────────────────

    def agregar_mensaje_chat(self, autor: str, mensaje: str, hora: str,
                             tipo: str = TIPO_TEXTO, monto: str = "",
                             canal_id: str = "", plataforma: str = "",
                             rol: str = "") -> None:
        if not self._alive:
            return
        # Si ya no estamos conectados, descartar: puede ser un mensaje rezagado
        # de un hilo de captura anterior (bloqueado en una lectura de red) que
        # llega tras desconectar. Si no, se solaparía con el directo siguiente.
        # La captura solo emite mensajes tras «conectado», así que en uso normal
        # esto no descarta nada legítimo.
        if not self._conectado:
            return
        # No tocar el modelo ni la lista aquí: se encola y se procesa en el
        # volcado agrupado (ver volcar) para no disparar un
        # Append/Delete por mensaje mientras NVDA navega la lista.
        registro = MensajeChat(
            plataforma=plataforma, autor=autor, identificador=canal_id,
            texto=mensaje, hora=hora, tipo=tipo, monto=monto, rol=rol)
        self.chat_vivo.encolar(registro)

    def set_conectado(self, conectado: bool,
                        sonido_desconexion: str = "desconectado") -> None:
        gui_sesion.set_conectado(self, conectado, sonido_desconexion)

    def _reiniciar_datos_sesion(self) -> None:
        gui_sesion.reiniciar_datos_sesion(self)

    def _mostrar_zona(self, mostrar: bool) -> None:
        gui_sesion.mostrar_zona(self, mostrar)

    def _anunciar_conectado(self) -> None:
        gui_sesion.anunciar_conectado(self)

    def set_live_chat_id(self, live_chat_id: str, causa: str = "",
                         video_id: str | None = None, propio: bool = False) -> None:
        if not self._alive:
            return
        if not self.sesion.acepta_chat_de(video_id):
            return
        self.sesion.live_chat_id = live_chat_id or ""
        self.sesion.causa_sin_chat = causa or ""
        self.sesion.chat_propio = bool(propio)
        self._actualizar_estado_online()

    def set_espectadores(self, n: int, total: int | None = None) -> None:
        """Espectadores en vivo; TikTok lo refresca cada pocos segundos."""
        if not self._alive:
            return
        for clave, valor in (p for p in (("vistas", n), ("vistas_total", total)) if p[1] is not None):
            try:    self._metadatos[clave] = int(valor)
            except Exception as error: logger.debug("no se pudo anotar %s: %s", clave, error)

    def set_inicio_directo(self, comienzo: str) -> None:
        if not self._alive:
            return
        self._metadatos["comienzo_directo"] = comienzo or ""

    def set_tipo_video(self, tipo: str, video_id: str) -> None:
        if not self._alive:
            return
        self.sesion.tipo_video = tipo
        self.sesion.video_id = video_id or ""
        self.sesion.es_tiktok = False   # esta ruta es la de YouTube
        # Empezar el chat en limpio en cada conexión: el reset al desconectar ya
        # lo hace, pero así garantizamos que nunca quede nada del vídeo anterior.
        self.chat_vivo.descartar()
        self.chat_vivo.modelo.limpiar()
        self._sc_totales.clear()
        try:    self.lb_chat.Clear()
        except Exception as error: logger.debug("no se pudo limpiar el chat: %s", error)
        es_live = deteccion.tiene_chat_en_vivo(tipo)
        autoplay = bool(self._config.get("autoplay_reproductor", True))
        # Comentarios: autocargar solo cuando no hay chat en vivo (en un directo
        # no queremos saturar). Reproductor: siempre, con autoplay según prefs.
        try:    self._com_panel.set_video(video_id, autocargar=not es_live)
        except Exception as error: logger.debug("no se pudo mostrar los comentarios: %s", error)
        try:    self._rep_panel.set_video(video_id, autoplay=autoplay)
        except Exception as error: logger.debug("no se pudo mostrar el reproductor: %s", error)

        # ChangeSelection: sin anuncio de pestaña; el de «conectado» que viene
        # después ya dice qué hay disponible.
        if tipo == deteccion.LIVE:
            gui_construccion.fijar_tipo(self, _("Directo: leyendo el chat."))
            self.nb.ChangeSelection(PAG_CHAT)
        elif tipo == deteccion.UPCOMING:
            gui_construccion.fijar_tipo(self, _("Directo programado: aún sin chat. Hay comentarios."))
            self.nb.ChangeSelection(PAG_COMENTARIOS)
        elif tipo == deteccion.VOD:
            gui_construccion.fijar_tipo(self, _("Vídeo subido: comentarios y reproductor."))
            self.nb.ChangeSelection(PAG_COMENTARIOS)
        else:
            gui_construccion.fijar_tipo(self, _("Tipo no determinado: intentando leer el chat."))
        self._actualizar_boton_directo()

    def configurar_tiktok(self, usuario: str, url_flujo: str) -> None:
        """Prepara la ventana para un directo de TikTok: chat en limpio, pestaña
        de chat al frente, comentarios fuera (TikTok no los tiene aquí) y el
        reproductor con el flujo de TikTok (FLV, o HLS si no hay FLV). Lo llama main vía wx.CallAfter."""
        if not self._alive:
            return
        reconexion = self.sesion.es_reconexion_tiktok(usuario)
        previo = self.sesion.url_flujo_tiktok
        self.sesion.tipo_video = deteccion.LIVE
        self.sesion.es_tiktok = True
        self.sesion.usuario_tiktok = usuario or ""
        self.sesion.url_flujo_tiktok = url_flujo or ""
        if not reconexion:
            self.chat_vivo.descartar()
            self.chat_vivo.modelo.limpiar()
            self._sc_totales.clear()
            try:    self.lb_chat.Clear()
            except Exception as error: logger.debug("no se pudo limpiar el chat: %s", error)
        try:    self._com_panel.mostrar_no_disponible(
                    _("Los comentarios no están disponibles en los directos de TikTok."))
        except Exception as error: logger.debug("no se pudo mostrar el aviso: %s", error)
        if not (reconexion
                and flujo_tiktok.mismo_flujo(url_flujo, previo)):
            autoplay = (False if reconexion
                        else bool(self._config.get("autoplay_reproductor", True)))
            try:    self._rep_panel.set_flujo(url_flujo, autoplay=autoplay)
            except Exception as exc: logger.debug("reproductor tiktok: %s", exc)
        gui_construccion.fijar_tipo(
            self, _("Directo de TikTok de @{usuario}: leyendo el chat.").format(
                usuario=usuario))
        if not reconexion:
            self.nb.ChangeSelection(PAG_CHAT)
        self._actualizar_boton_directo()

    def set_url(self, url: str) -> None:
        self.txt_url.SetValue(url)

    def set_metadatos(self, meta: dict) -> None:
        """Rellena el panel de información con lo que trae yt-dlp. Se llama desde
        el hilo de conexión vía wx.CallAfter; el panel puede estar oculto por
        preferencia (igual guardamos el texto, para que aparezca ya hecho si lo
        muestran)."""
        if not self._alive:
            return
        self._metadatos = meta or {}
        try:
            self.txt_info.SetValue(metadatos.formatear(self._metadatos))
            self.txt_info.SetInsertionPoint(0)   # que el lector empiece arriba
        except Exception as exc:
            logger.debug("set_metadatos: %s", exc)

    def _idx_pag_info(self) -> int:
        for i in range(self.nb.GetPageCount()):
            if self.nb.GetPage(i) is self._pag_info:
                return i
        return -1

    def set_metadatos_visible(self, visible: bool) -> None:
        """Añade o quita la pestaña de Información según la preferencia. Al
        ocultarla NO se destruye el panel, así reaparece con su contenido."""
        idx = self._idx_pag_info()
        if visible and idx == -1:
            # Traductores: pestaña con los datos del vídeo.
            self.nb.AddPage(self._pag_info, _("Información"))
            self._pag_info.Show()
        elif not visible and idx != -1:
            self.nb.RemovePage(idx)
            self._pag_info.Hide()
        self._zona.Layout()

    def set_titulo_stream(self, titulo: str) -> None:
        if not self._alive:
            return
        self._titulo_stream = (titulo or "").strip()
        titulo_ventana.aplicar(self)

    def auto_conectar(self) -> None:
        self._on_conectar(None)

    def poblar_voces(self, voces: list, idx_actual: int = 0) -> None:
        self._voces_menu = list(voces)
        if not voces:
            self._voz_nombre = "—"
            return
        idx_actual = idx_actual if 0 <= idx_actual < len(voces) else 0
        self._voz_idx = idx_actual
        self._voz_nombre = voces[idx_actual]

    def _sincronizar_checks(self):
        try:    self.mi_sil_sonidos.Check(_snd.esta_silenciado())
        except Exception as error: logger.debug("no se pudo marcar el silencio: %s", error)
        try:    self.mi_sil_lectura.Check(self._config.get("silenciar_lectura", False))
        except Exception as error: logger.debug("no se pudo marcar la lectura: %s", error)

    def _set_conectado_ui(self, conectado: bool) -> None:
        # Botón (toggle), items de menú Conectar/Desconectar y campo URL. El
        # resto (ocultar zona, sonido, título) lo gestiona set_conectado.
        self._conectando = False
        self.btn_conectar.SetLabel(_("&Desconectar") if conectado else _("&Conectar"))
        self.btn_conectar.Enable()
        self.mi_conectar.Enable(not conectado)
        self.mi_desconectar.Enable(conectado)
        self.txt_url.Enable(not conectado)
        self._actualizar_menus_por_conexion()
        self._actualizar_boton_directo()

    def _actualizar_menus_por_conexion(self) -> None:
        """Deshabilita en la barra de menú lo que solo aplica con una conexión
        activa: navegar por paneles, el filtro y las acciones de voz sobre una
        lectura en curso. Así el usuario no llega por el menú a paneles que no
        existen aún. Los ajustes de voz y «Ir a conexión» /
        «Anunciar estado» quedan siempre disponibles.

        El ítem «Descargar este vídeo» sigue las reglas del diseño: solo se
        habilita con conexión YouTube NO-live (TikTok y live están deshabilitados
        en v1). Si la URL no se puede obtener del reproductor, se deshabilita."""
        con = bool(self._conectado)
        for it in getattr(self, "_mi_ver_conexion", []):
            try:    it.Enable(con)
            except Exception as error: logger.debug("no se pudo activar el menú: %s", error)
        try:    self._mi_filtro_sub.Enable(con)
        except Exception as error: logger.debug("no se pudo activar el filtro: %s", error)
        for it in getattr(self, "_mi_voz_conexion", []):
            try:    it.Enable(con)
            except Exception as error: logger.debug("no se pudo activar el menú: %s", error)

        # Descargar este vídeo: YouTube + conexión + no live + URL disponible.
        # El panel del reproductor gestiona sus propios avisos, pero afinamos
        # el ítem para que:
        #   - TikTok → off (es TikTok, no YouTube)
        #   - Live   → off (out of scope v1, ver spec R: Live y TikTok off)
        #   - sin URL → off (no hay nada que descargar)
        try:
            descargar_este_on = False
            if con and not self.sesion.es_tiktok and getattr(self, "_rep_panel", None):
                try:
                    if not self._rep_panel.get_es_live():
                        descargar_este_on = bool(self._rep_panel.get_url_para_descarga())
                except Exception:
                    descargar_este_on = False
            if hasattr(self, "mi_descargar_este"):
                self.mi_descargar_este.Enable(descargar_este_on)
        except Exception as exc:
            logger.debug("enable mi_descargar_este: %s", exc)

    def _actualizar_sb(self) -> None:
        sin_tts = _(" [lectura silenciada]") if self._config.get("silenciar_lectura", False) else ""
        if self._conectado and self._titulo_stream:
            # Traductores: {titulo} es el vídeo; {sin_tts} avisa si la lectura está silenciada.
            estado = _("Conectado: {titulo}{sin_tts}").format(titulo=self._titulo_stream[:35], sin_tts=sin_tts)
        elif self._conectado:
            # Traductores: {sin_tts} avisa si la lectura está silenciada.
            estado = _("Conectado{sin_tts}").format(sin_tts=sin_tts)
        else:
            # Traductores: {sin_tts} avisa si la lectura está silenciada.
            estado = _("Desconectado{sin_tts}").format(sin_tts=sin_tts)
        self.sb.SetStatusText(estado, 0)

        try:    self.sb.SetStatusText(_("Velocidad: {valor}").format(valor=self._worker.get_rate()), 1)
        except Exception: self.sb.SetStatusText(_("Velocidad: --"), 1)

        nombre = self._voz_nombre or "—"
        if len(nombre) > 28:
            nombre = nombre[:25] + "..."
        # Traductores: {nombre} es la voz activa.
        self.sb.SetStatusText(_("Voz: {nombre}").format(nombre=nombre), 2)

        # Traductores: {n} son los mensajes en cola.
        try:    self.sb.SetStatusText(_("Cola: {n}").format(n=self._cola.qsize()), 3)
        # Traductores: la raya indica que no hay dato.
        except Exception: self.sb.SetStatusText(_("Cola: —"), 3)
        # Traductores: {n} son los mensajes leídos.
        try:    self.sb.SetStatusText(_("Leídos: {n}").format(n=self._stats.leidos), 4)
        # Traductores: la raya indica que no hay dato.
        except Exception: self.sb.SetStatusText(_("Leídos: —"), 4)

        try:    self.sb.SetStatusText(_("Volumen: {valor} %").format(valor=self._worker.get_volume()), 5)
        except Exception: self.sb.SetStatusText(_("Volumen: --"), 5)

        if self._config.get("mostrar_total_superchats", True):
            self.sb.SetStatusText(self._formato_total_sc(), 6)
        else:
            self.sb.SetStatusText("", 6)

    # ── Acumulación de Super Chats ───────────────────────────────────────────

    def _sumar_superchat(self, monto: str) -> None:
        sumar_monto(self._sc_totales, monto)

    def _formato_total_sc(self) -> str:
        try:    n = self._stats.superchats
        except Exception: n = 0
        importes = texto_importes(self._sc_totales)
        # Traductores: {n} e {importes} son cantidad e importes.
        if not importes:
            return _("Super Chats: {n}").format(n=n)
        return _("Super Chats: {n} ({importes})").format(n=n, importes=importes)


# ── Portapapeles ─────────────────────────────────────────────────────────────
# Compartido con el panel de comentarios: primero wx y, si falla (p. ej. otro
# proceso tiene el portapapeles abierto), la vía Win32 directa como respaldo.

def copiar_al_portapapeles(text: str) -> None:
    try:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Flush()
            finally:
                wx.TheClipboard.Close()
            return
    except Exception as error:
        logger.debug("no se pudo copiar con wx: %s", error)
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        u32 = ctypes.windll.user32
        if not u32.OpenClipboard(0):
            return
        try:
            u32.EmptyClipboard()
            encoded = text.encode("utf-16-le") + b"\x00\x00"
            h = k32.GlobalAlloc(0x0042, len(encoded))
            if not h:
                return
            p = k32.GlobalLock(h)
            if not p:
                k32.GlobalFree(h)
                return
            ctypes.memmove(p, encoded, len(encoded))
            k32.GlobalUnlock(h)
            if not u32.SetClipboardData(13, h):  # CF_UNICODETEXT
                k32.GlobalFree(h)
        finally:
            u32.CloseClipboard()
    except Exception as error:
        logger.debug("no se pudo copiar con Win32: %s", error)


# ── Entrada ──────────────────────────────────────────────────────────────────

_gui_frame: VentanaPrincipal | None = None


class AplicacionPrincipal(wx.App):
    def OnInit(self):
        self.Bind(wx.EVT_END_SESSION, self._on_fin_sesion)
        # Hay que guardar la referencia en la app, si el recolector la libera
        # wx queda llamando a memoria liberada
        try:
            self._wx_log = _LogWx()
            wx.Log.SetActiveTarget(self._wx_log)
        except Exception as exc:
            logger.warning("No se pudo instalar el registro de wx: %s", exc)
        return True

    def OnAssert(self, archivo, linea, condicion, mensaje):
        # En un ejecutable empaquetado las aserciones de wx se pierden enteras.
        logger.warning("wx aserción archivo=%s línea=%s condición=%s mensaje=%s",
                       archivo, linea, condicion, mensaje)

    def _on_fin_sesion(self, event):
        if _gui_frame is not None:
            gui_cierre.on_close(_gui_frame, event)


def iniciar_gui(config, cola, stats, worker, parada,
                url_inicial: str = "",
                iniciar_captura_cb=None,
                detener_captura_cb=None) -> None:
    global _gui_frame, RUTA_CONFIG

    RUTA_CONFIG = paths.config_ini()

    app = AplicacionPrincipal(redirect=False)
    # El lector de JAWS crea su COM en el hilo que lo inicializa: tiene que ser
    # con la aplicación de wx ya en pie, y antes de crear el frame.
    _lector_init()
    # El worker avisa por acá cuando un motor falla y se cae a la voz de
    # Windows; el sonido y el anuncio se reenvían al hilo de la interfaz.
    worker.al_avisar = lambda texto: anunciar_con_sonido(texto, "aviso")
    frame = VentanaPrincipal(None, config, cola, stats, worker, parada)
    _gui_frame = frame
    frame.on_conectar_cb    = iniciar_captura_cb
    frame.on_desconectar_cb = detener_captura_cb

    voces = worker.voces()
    idx_voz = escala_voz.resolver_voz(config.get("voz"), voces)
    frame.poblar_voces(voces, 0 if idx_voz is None else idx_voz)

    # Conversión de una sola vez: los números de voz viejos pasan a nombre y se
    # fijan en config.ini, así instalar una voz no cambia la voz elegida.
    for clave in ("voz", "voz_eventos", "voz_secundaria"):
        nombre = escala_voz.migrar_voz(config.get(clave), voces)
        if nombre is not None:
            config[clave] = nombre
            guardar_opcion(RUTA_CONFIG, "voz", clave, nombre)

    # Restaurar filtro de la sesión anterior.
    fa = config.get("filtro_activo", "todos")
    idx_f = IDX_FILTRO.get(fa, 0)
    if 0 <= idx_f < len(FILTROS):
        frame.chat_vivo.filtro = FILTROS[idx_f][1]
        frame._chat_acciones._marcar_filtro()

    # Restaurar silenciado de sonidos si la sesión anterior lo tenía activo.
    if config.get("silenciar_sonidos", False):
        _snd.silenciar_todo(True)
    frame._sincronizar_checks()

    if url_inicial:
        frame.set_url(url_inicial)

    frame.Show()
    try:
        frame.Raise()
        frame.txt_url.SetFocus()
    except Exception as error:
        logger.debug("no se pudo enfocar el campo de dirección: %s", error)
    from guyrapu.ui import gui_actualizar_app, gui_directo_huerfano
    gui_actualizar_app.programar_confirmacion_arranque()
    gui_actualizar_app.programar_resultado_actualizacion(frame)
    gui_actualizar_app.programar_aviso_version(frame)
    gui_directo_huerfano.programar_revision(frame)
    if config.get("sonido_inicio", True):
        diagnostico.crear_hilo(lambda: _snd.reproducir("app_inicio"), "SonidoInicio").start()
    wx.CallAfter(frame._arrancar_precalentamiento)

    if url_inicial and iniciar_captura_cb:
        wx.CallAfter(frame.auto_conectar)

    app.MainLoop()
    _gui_frame = None
