# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Atiende los comandos del chat y manda sus respuestas.

Une la decisión pura de `atencion` con la app: carga los comandos del
archivo, arma el evento desde el mensaje, agrega la tarjeta al vídeo, manda
la respuesta al chat de YouTube y avisa una sola vez si la cuota la corta.

La atiende `chat_vivo.encolar`, que registra cualquier error sin cortar la
lectura del chat.
"""

from __future__ import annotations

import time
from dataclasses import replace

import wx

from guyrapu.capture.estado_espectadores import _fmt_num
from guyrapu.core import diagnostico, paths, plataformas
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.core.idioma import _
from guyrapu.core.sonidos_eventos import ROL_PROPIETARIO
from guyrapu.downloads import busqueda_youtube
from guyrapu.interaction import (
    atencion, comandos, comandos_guardados, conversion_disparadores, ensayo,
    filtro_publico, informe_ensayo, medio_en_video, pedido_musica)
from guyrapu.music.modelo import Tema
from guyrapu.interaction.evento import desde_entrante
from guyrapu.ui import encuesta_en_vivo, gui_envio_chat, preguntas_en_vivo
from guyrapu.ui.accesibilidad import anunciar_con_sonido
from guyrapu.youtube import cuota

# Con más de 8000 unidades usadas quedan menos de 2000 de las 10 000.
CUOTA_BAJA = 8000

logger = diagnostico.obtener_logger(__name__)


def _en_vivo(frame):
    en_vivo = getattr(frame, "_comandos_en_vivo", None)
    if en_vivo is None:
        en_vivo = ComandosEnVivo(frame)
        frame._comandos_en_vivo = en_vivo
    return en_vivo


def _cuota_baja() -> bool:
    return cuota.usadas_hoy() > CUOTA_BAJA


def atender(frame, registro, ahora) -> None:
    """Atiende el mensaje con la instancia de comandos de esa ventana."""
    _en_vivo(frame).atender(registro, ahora)


def enviar_respuesta(frame, texto) -> bool:
    """Manda un texto al chat como las respuestas de los comandos."""
    return _en_vivo(frame).enviar_respuesta(texto)


def disparar(frame, numero, ahora=None) -> None:
    """Usa el comando de ese número con la instancia de la ventana."""
    _en_vivo(frame).disparar(numero, ahora)


def _evento(registro):
    return desde_entrante(
        registro.autor, registro.texto, registro.tipo, registro.monto,
        registro.identificador, registro.rol, registro.plataforma)


def _evento_del_dueno():
    return desde_entrante(
        "", "", TIPO_TEXTO, "", "", ROL_PROPIETARIO, plataformas.YOUTUBE)


class ComandosEnVivo:
    """Los comandos de una sesión, con sus respuestas y su freno de cuota."""

    def __init__(self, frame):
        conversion_disparadores.convertir_en_disco()
        self._frame = frame
        self._atencion = atencion.Atencion()
        self._cargado = False
        self._mtime = None
        self._cargado_palabras = False
        self._mtime_palabras = None
        self._avisado_cuota = False
        self._respondidos = 0
        self._ultimo = ("", "")
        self._pausados = False

    def alternar_pausa(self) -> bool:
        """Invierte el freno de todos los comandos y devuelve el estado nuevo."""
        self._pausados = not self._pausados
        return self._pausados

    def atender(self, registro, ahora) -> None:
        if registro.tipo != TIPO_TEXTO:
            return
        evento = _evento(registro)
        if encuesta_en_vivo.votar(self._frame, evento, ahora):
            return
        informe = ensayo.informe(self._frame)
        if self._pausados:
            if informe is not None:
                informe.motivo(_(informe_ensayo.MOTIVO_PAUSA_GENERAL))
            return
        if preguntas_en_vivo.recibir(self._frame, evento, ahora):
            return
        self._recargar()
        respuesta = self._atencion.atender(
            evento, ahora,
            chat_disponible=self._chat_disponible(),
            cuota_baja=_cuota_baja())
        if respuesta is not None:
            if informe is not None:
                informe.comando(respuesta.nombre)
            if respuesta.especial == comandos.ESPECIAL_MUSICA:
                self._pedir_musica(respuesta, registro.autor, registro.texto)
            else:
                self._mandar(respuesta, registro.autor)
        elif informe is not None:
            informe.motivo(self._atencion.motivo(evento, ahora))

    def disparar(self, numero, ahora=None) -> None:
        """Usa el comando de ese número como si lo pidiera el dueño."""
        if not ensayo.en_vivo_o_ensayo(self._frame):
            anunciar_con_sonido(
                _("Conecta un directo para usar los atajos de los comandos"),
                "error")
            return
        self._recargar()
        if ahora is None:
            ahora = time.monotonic()
        respuesta = self._atencion.atender(
            _evento_del_dueno(), ahora, atajo=numero,
            chat_disponible=self._chat_disponible(),
            cuota_baja=_cuota_baja())
        if respuesta is None:
            anunciar_con_sonido(
                _("Ningún comando usa Ctrl+Alt+Mayús+{numero}").format(
                    numero=numero), "error")
            return
        self._mandar(respuesta, "")

    def _pedir_musica(self, respuesta, autor, texto) -> None:
        """Resuelve el pedido en otro hilo por si la búsqueda tarda."""
        invocacion = comandos.leer(texto)
        pedido = invocacion.argumentos if invocacion else ""
        diagnostico.crear_hilo(
            self._resolver_musica, "PedidoMusica",
            args=(respuesta, autor, pedido)).start()

    def _resolver_musica(self, respuesta, autor, texto) -> None:
        pedido = pedido_musica.resolver(texto, busqueda_youtube.buscar)
        wx.CallAfter(self._terminar_musica, respuesta, autor, pedido)

    def _terminar_musica(self, respuesta, autor, pedido) -> None:
        if pedido.motivo:
            # Traductores: aviso al streamer cuando el público pide música y no se agrega. {usuario} es quien lo pidió y {motivo} por qué no se sumó.
            anunciar_con_sonido(
                _("Pedido de música de {usuario} no agregado: {motivo}").format(
                    usuario=autor or _("el público"), motivo=_(pedido.motivo)),
                "pedido_musica_rechazado")
            return
        tema = Tema(origen=pedido.tema.url, titulo=pedido.tema.titulo,
                    duracion_ms=pedido.tema.duracion * 1000)
        self._frame._musica.agregar_temas([tema])
        titulo = self._atencion.tapar(pedido.tema.titulo)
        respuesta = replace(
            respuesta, texto=respuesta.texto.replace("{titulo}", titulo))
        self._mandar(respuesta, autor)

    def _mandar(self, respuesta, autor) -> None:
        self._respondidos += 1
        palabra = respuesta.nombre
        if not palabra.startswith("!"):
            palabra = "!" + palabra
        self._ultimo = (palabra, autor)
        self._poner_en_video(respuesta)
        if respuesta.al_chat and respuesta.texto.strip():
            gui_envio_chat.enviar_respuesta_chat(self._frame, respuesta.texto)
        if respuesta.freno_cuota:
            self._avisar_cuota()

    def _poner_en_video(self, respuesta) -> None:
        if not ensayo.en_vivo_o_ensayo(self._frame):
            return
        medio = medio_en_video.resolver(respuesta.medio)
        texto = respuesta.texto if respuesta.al_video else ""
        if not texto and medio is None:
            return
        gui_envio_chat.capa_de_video(self._frame).agregar_comando(
            respuesta, medio)

    def enviar_respuesta(self, texto) -> bool:
        """Manda un texto al chat con el mismo freno de cuota de los comandos."""
        if not self._chat_disponible():
            return False
        if _cuota_baja():
            self._avisar_cuota()
            return False
        gui_envio_chat.enviar_respuesta_chat(self._frame, texto)
        return True

    def frase_estado(self) -> str:
        """La frase para F2, o "" si no hay pausa ni comandos respondidos."""
        resumen = ""
        if self._respondidos:
            palabra, autor = self._ultimo
            # Traductores: parte del estado F2 (comandos). {n} es el nº de comandos
            # respondidos, {palabra} el último comando y {autor} quien lo pidió.
            resumen = _(
                "Comandos respondidos: {n}, el último {palabra} de {autor}").format(
                    n=_fmt_num(self._respondidos), palabra=palabra, autor=autor)
        if not self._pausados:
            return resumen
        return _("Comandos en pausa") + (". " + resumen if resumen else "")

    def _recargar(self) -> None:
        """Vuelve a leer los comandos y las palabras si cambiaron."""
        self._recargar_comandos()
        self._recargar_palabras()

    def _recargar_comandos(self) -> None:
        ruta = paths.comandos()
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if self._cargado and mtime == self._mtime:
            return
        self._cargado = True
        self._mtime = mtime
        self._atencion.fijar_comandos([
            comandos_guardados.a_comando(datos)
            for datos in comandos_guardados.cargar(ruta)])

    def _recargar_palabras(self) -> None:
        ruta = paths.palabras_bloqueadas()
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if self._cargado_palabras and mtime == self._mtime_palabras:
            return
        self._cargado_palabras = True
        self._mtime_palabras = mtime
        self._atencion.fijar_palabras_bloqueadas(
            filtro_publico.cargar(ruta))

    def _chat_disponible(self) -> bool:
        return "chat" in gui_envio_chat.destinos_disponibles(self._frame)

    def _avisar_cuota(self) -> None:
        if self._avisado_cuota:
            return
        self._avisado_cuota = True
        from guyrapu.ui import gui as _gui
        # Traductores: aviso único de la sesión cuando la poca cuota de YouTube corta las respuestas al chat.
        _gui.anunciar_con_sonido(
            _("Queda poca cuota de YouTube: las respuestas de los comandos "
              "ya no se muestran en el chat, solo en el vídeo."),
            "aviso")
