# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Atiende las metas del directo y pone su tarjeta en el vídeo.

Une la decisión pura de `metas` con la app: carga las metas guardadas, arma
el evento desde el mensaje y, con el chat conectado, suma el avance y pone
la tarjeta de la meta cumplida.

La atiende `chat_vivo.encolar`, que registra cualquier error sin cortar la
lectura del chat.
"""

from __future__ import annotations

import time

import wx

from guyrapu.capture import contador_me_gusta
from guyrapu.core import diagnostico, paths
from guyrapu.core.idioma import _
from guyrapu.interaction import (
    avisos_en_vivo, ensayo, medio_en_video, metas, metas_guardadas,
    rastro_en_vivo)
from guyrapu.interaction.cola_pantalla import Pieza
from guyrapu.interaction.evento import desde_entrante
from guyrapu.ui import gui_envio_chat
from guyrapu.ui.accesibilidad import anunciar_con_sonido

logger = diagnostico.obtener_logger(__name__)

# Los mismos diez segundos de fábrica de una tarjeta en el vídeo.
SEGUNDOS = 10
# Lo que hay que esperar como mucho para poner al día la pieza fija.
INTERVALO = 2.0


def _en_vivo(frame):
    en_vivo = getattr(frame, "_metas_en_vivo", None)
    if en_vivo is None:
        en_vivo = MetasEnVivo(frame)
        frame._metas_en_vivo = en_vivo
    return en_vivo


def atender(frame, registro) -> None:
    """Atiende el mensaje con la instancia de metas de esa ventana."""
    _en_vivo(frame).atender(registro)


def reiniciar(frame) -> None:
    """Vuelve a cero el avance de las metas y el total de esa ventana."""
    contador_me_gusta.reiniciar()
    en_vivo = getattr(frame, "_metas_en_vivo", None)
    if en_vivo is not None:
        en_vivo.reiniciar()


def _evento(registro):
    return desde_entrante(
        registro.autor, registro.texto, registro.tipo, registro.monto,
        registro.identificador, registro.rol, registro.plataforma)


class MetasEnVivo:
    """El avance de las metas de una sesión y su tarjeta en el vídeo."""

    def __init__(self, frame, reloj=None, programar=None):
        self._frame = frame
        self._reloj = reloj or time.monotonic
        self._programar = programar or wx.CallLater
        self._progresos = {}
        self._cargado = False
        self._mtime = None
        self._fijada = None
        self._texto = ""
        self._ultima = 0.0
        self._pendiente = None
        self._llamada = None
        self._umbrales = {}

    def atender(self, registro) -> None:
        if not ensayo.en_vivo_o_ensayo(self._frame):
            return
        self._recargar()
        evento = _evento(registro)
        total_me_gusta = (None if ensayo.en_ensayo(self._frame)
                          else contador_me_gusta.total())
        informe = ensayo.informe(self._frame)
        for progreso in self._progresos.values():
            if not progreso.meta.activa:
                continue
            anterior = progreso.valor
            if not progreso.sumar(evento, total_me_gusta):
                continue
            rastro_en_vivo.escribir(rastro_en_vivo.meta(
                progreso.meta.nombre, anterior, progreso.valor,
                progreso.meta.objetivo))
            if informe is not None:
                informe.meta(progreso.meta.nombre, progreso.valor,
                             progreso.meta.objetivo)
            self._avisar_avance(progreso, anterior)
            if progreso.recien_cumplida():
                rastro_en_vivo.escribir(rastro_en_vivo.meta_cumplida(
                    progreso.meta.nombre))
                self._cumplida(progreso)
        self._refrescar_fija()

    def reiniciar(self) -> None:
        """Olvida el avance y saca la pieza fija de la conexión anterior."""
        self._progresos = {}
        self._umbrales = {}
        self._cargado = False
        self._quitar_fija()

    def _avisar_avance(self, progreso, anterior) -> None:
        if not progreso.meta.avisar:
            return
        dichos = self._umbrales.setdefault(progreso.meta.nombre, set())
        frase = avisos_en_vivo.aviso_meta(
            progreso.meta.nombre, anterior, progreso.valor,
            progreso.meta.objetivo, dichos)
        if frase:
            anunciar_con_sonido(frase, "meta_avance")

    def _cumplida(self, progreso) -> None:
        anunciar_con_sonido(
            _("Meta cumplida: {nombre}.").format(nombre=progreso.meta.nombre),
            "meta_cumplida")
        self._poner(progreso)

    def _poner(self, progreso) -> None:
        meta = progreso.meta
        medio = medio_en_video.resolver(meta.festejo)
        segundos = SEGUNDOS
        datos = {"estilo": meta.estilo, "nombre": meta.nombre}
        datos, segundos = medio_en_video.con_medio(datos, segundos, medio)
        pieza = Pieza(tipo="meta", texto=metas.texto(meta, progreso.valor),
                      segundos=segundos, datos=datos)
        gui_envio_chat.capa_de_video(self._frame).agregar_pieza(pieza)

    def _refrescar_fija(self) -> None:
        """Pone al día la pieza fija con las metas que la piden."""
        fijas = [progreso for progreso in self._progresos.values()
                 if progreso.meta.activa and progreso.meta.en_video]
        if not fijas:
            self._quitar_fija()
            return
        texto = metas.texto_en_video(fijas)
        if texto == self._texto:
            return
        self._texto = texto
        pieza = Pieza(tipo="metas", texto=texto, segundos=0,
                      datos={"estilo": fijas[0].meta.estilo})
        capa = gui_envio_chat.capa_de_video(self._frame)
        if self._fijada is None:
            self._fijada = pieza
            self._ultima = self._reloj()
            capa.fijar_metas(pieza)
            return
        ahora = self._reloj()
        if ahora - self._ultima >= INTERVALO:
            self._aplicar_fija(capa, pieza, ahora)
            return
        self._pendiente = pieza
        if self._llamada is None:
            espera = int((INTERVALO - (ahora - self._ultima)) * 1000)
            self._llamada = self._programar(
                espera, self._entregar_pendiente)

    def _aplicar_fija(self, capa, pieza, ahora) -> None:
        capa.poner_al_dia_metas(pieza)
        self._fijada = pieza
        self._ultima = ahora
        self._pendiente = None
        self._cancelar_llamada()

    def _entregar_pendiente(self) -> None:
        self._llamada = None
        pieza = self._pendiente
        if pieza is None or self._fijada is None:
            return
        capa = gui_envio_chat.capa_de_video(self._frame)
        self._aplicar_fija(capa, pieza, self._reloj())

    def _quitar_fija(self) -> None:
        self._texto = ""
        self._pendiente = None
        self._cancelar_llamada()
        if self._fijada is None:
            return
        self._fijada = None
        gui_envio_chat.capa_de_video(self._frame).quitar_metas()

    def _cancelar_llamada(self) -> None:
        if self._llamada is not None:
            self._llamada.Stop()
            self._llamada = None

    def _recargar(self) -> None:
        """Vuelve a leer las metas si el archivo cambió, sin perder el avance."""
        ruta = paths.metas()
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if self._cargado and mtime == self._mtime:
            return
        self._cargado = True
        self._mtime = mtime
        anteriores = self._progresos
        self._progresos = {}
        for datos in metas_guardadas.cargar(ruta):
            meta = metas_guardadas.a_meta(datos)
            progreso = anteriores.get(meta.nombre)
            if progreso is None:
                progreso = metas.Progreso(meta)
            else:
                progreso.meta = meta
            self._progresos[meta.nombre] = progreso
