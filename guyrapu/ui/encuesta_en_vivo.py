# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La encuesta abierta de la sesión.

Una sola razón para cambiar: qué se hace mientras hay una encuesta abierta.
Abrirla, sumar votos, poner al día lo que se ve, cerrarla por tiempo o a mano
y repartir el resultado. Los sitios (la página, el menú y el atajo) solo
llaman a sus funciones.
"""

from __future__ import annotations

import time

from guyrapu.core.idioma import _
from guyrapu.interaction import (
    comandos, encuestas, encuestas_guardadas, ensayo)
from guyrapu.interaction.cola_pantalla import Pieza

# Cada cuánto late el temporizador y cada cuánto, como mucho, se pone al día
# el texto que ya se ve.
INTERVALO = 1000
ACTUALIZACION = 2.0
# Diez segundos, los mismos de fábrica de un mensaje automático en pantalla.
SEGUNDOS_RESULTADO = 10


def _capa(frame):
    from guyrapu.ui import gui_envio_chat
    return gui_envio_chat.capa_de_video(frame)


def _avisar(frase, sonido):
    from guyrapu.ui.accesibilidad import anunciar_con_sonido
    anunciar_con_sonido(frase, sonido)


def _enviar_chat(frame, texto):
    from guyrapu.ui import comandos_en_vivo
    return comandos_en_vivo.enviar_respuesta(frame, texto)


def _temporizador(frame, manejador):
    import wx
    timer = wx.Timer(frame)
    frame.Bind(wx.EVT_TIMER, manejador, timer)
    return timer


def _sesion(frame, reloj=None):
    sesion = getattr(frame, "_encuesta_en_vivo", None)
    if sesion is None:
        sesion = SesionEncuesta(frame, reloj or time.monotonic)
        frame._encuesta_en_vivo = sesion
    return sesion


def abierta(frame) -> bool:
    """Si hay una encuesta abierta en esa sesión."""
    sesion = getattr(frame, "_encuesta_en_vivo", None)
    return bool(sesion is not None and sesion.encuesta is not None
                and sesion.encuesta.abierta(sesion.ahora()))


def iniciar(frame, datos, ahora=None, reloj=None) -> None:
    """Abre la encuesta guardada con su duración, su destino y su estilo."""
    _sesion(frame, reloj).iniciar(datos, ahora)


def votar(frame, evento, ahora=None) -> bool:
    """Anota el voto si es una cifra; dice si el mensaje era para la encuesta."""
    sesion = getattr(frame, "_encuesta_en_vivo", None)
    if sesion is None:
        return False
    return sesion.votar(evento, ahora)


def cerrar(frame, por_tiempo=False, ahora=None) -> bool:
    """Cierra la encuesta, reparte el resultado y dice si había alguna."""
    sesion = getattr(frame, "_encuesta_en_vivo", None)
    if sesion is None:
        return False
    return sesion.cerrar(por_tiempo, ahora)


def descartar(frame) -> bool:
    """Cierra la encuesta sin anunciar ni publicar su resultado."""
    sesion = getattr(frame, "_encuesta_en_vivo", None)
    if sesion is None or sesion.encuesta is None:
        return False
    sesion._descartar()
    return True


def frase_estado(frame) -> str:
    """La frase de F2 con la encuesta abierta, o "" si no hay ninguna."""
    sesion = getattr(frame, "_encuesta_en_vivo", None)
    if sesion is None:
        return ""
    return sesion.frase_estado()


class SesionEncuesta:
    """La encuesta abierta de una sesión y su temporizador."""

    def __init__(self, frame, reloj):
        self._frame = frame
        self._reloj = reloj
        self.encuesta = None
        self._destino = "video"
        self._estilo = ""
        self._sesion = None
        self._en_video = False
        self._ultima = 0.0
        self._timer = None

    def ahora(self):
        return self._reloj()

    def iniciar(self, datos, ahora=None) -> None:
        momento = self.ahora() if ahora is None else ahora
        datos = encuestas_guardadas.normalizar(datos)
        self.encuesta = encuestas.Encuesta(
            datos["pregunta"], datos["opciones"], datos["segundos"])
        self.encuesta.abrir(momento)
        self._destino = datos["destino"]
        self._estilo = datos["estilo"]
        self._sesion = getattr(self._frame, "sesion", None)
        self._en_video = self._va_al_video()
        self._ultima = momento
        self._arrancar_timer()
        if self._en_video:
            _capa(self._frame).fijar_encuesta(self._pieza(momento))
        _avisar(
            # Traductores: aviso al iniciar una encuesta; {pregunta} es su pregunta.
            _("Encuesta abierta: {pregunta}").format(
                pregunta=datos["pregunta"]), "listo")

    def votar(self, evento, ahora=None) -> bool:
        momento = self.ahora() if ahora is None else ahora
        if self.encuesta is None or not self.encuesta.abierta(momento):
            return False
        invocacion = comandos.leer(evento.texto)
        if invocacion is None or not invocacion.nombre.isdecimal():
            return False
        self.encuesta.votar(evento, momento)
        if momento - self._ultima >= ACTUALIZACION:
            self._poner_al_dia(momento)
        return True

    def cerrar(self, por_tiempo=False, ahora=None) -> bool:
        if self.encuesta is None:
            return False
        momento = self.ahora() if ahora is None else ahora
        encuesta = self.encuesta
        encuesta.cerrar()
        self.encuesta = None
        self._detener_timer()
        texto = encuesta.resumen(momento)
        _avisar(texto, "encuesta_cerrada" if por_tiempo else "listo")
        if self._en_video:
            capa = _capa(self._frame)
            capa.quitar_encuesta()
            if ensayo.en_vivo_o_ensayo(self._frame):
                capa.agregar_pieza(self._pieza_resultado(texto))
        if self._destino in ("chat", "ambos"):
            _enviar_chat(self._frame, texto)
        return True

    def frase_estado(self) -> str:
        if self.encuesta is None or not self._sigue_la_sesion():
            return ""
        momento = self.ahora()
        if not self.encuesta.abierta(momento):
            return ""
        return self.encuesta.resumen(momento)

    def _latido(self):
        if self.encuesta is None:
            self._detener_timer()
            return
        momento = self.ahora()
        if not self._sigue_la_sesion():
            self._descartar()
            return
        if not self.encuesta.abierta(momento):
            self.cerrar(por_tiempo=True, ahora=momento)
            return
        if momento - self._ultima >= ACTUALIZACION:
            self._poner_al_dia(momento)

    def _sigue_la_sesion(self) -> bool:
        if not getattr(self._frame, "_alive", True):
            return False
        parada = getattr(self._frame, "_parada", None)
        if parada is not None and parada.is_set():
            return False
        if self._sesion is not None and getattr(
                self._frame, "sesion", None) is not self._sesion:
            return False
        if not hasattr(self._frame, "_conectado"):
            return True
        return ensayo.en_vivo_o_ensayo(self._frame)

    def _descartar(self) -> None:
        self.encuesta = None
        self._detener_timer()
        if self._en_video:
            _capa(self._frame).quitar_encuesta()

    def _va_al_video(self) -> bool:
        return (self._destino in ("video", "ambos")
                and ensayo.en_vivo_o_ensayo(self._frame))

    def _poner_al_dia(self, ahora) -> None:
        if self.encuesta is None or not self._en_video:
            return
        _capa(self._frame).poner_al_dia_encuesta(self._pieza(ahora))
        self._ultima = ahora

    def _pieza(self, ahora):
        return Pieza(tipo="encuesta", texto=self.encuesta.resumen(ahora),
                     segundos=0, datos={"estilo": self._estilo})

    def _pieza_resultado(self, texto):
        return Pieza(tipo="encuesta", texto=texto,
                     segundos=SEGUNDOS_RESULTADO,
                     datos={"estilo": self._estilo})

    def _arrancar_timer(self) -> None:
        if self._timer is None:
            self._timer = _temporizador(self._frame, self._al_tiempo)
        self._timer.Start(INTERVALO)

    def _detener_timer(self) -> None:
        if self._timer is not None:
            self._timer.Stop()

    def _al_tiempo(self, _evento) -> None:
        self._latido()
