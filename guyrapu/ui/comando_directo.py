# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Comando de transmitir y finalizar el directo, con wx.

Reúne en un solo lugar lo que pasa al transmitir o finalizar el directo:
pedir el destino, guardarlo, comprobar la cuenta de Restream, revisar OBS,
confirmar, iniciar y finalizar, con el cierre de YouTube. Los botones del
directo solo lo llaman.
"""

from __future__ import annotations

import wx

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.obs import obs_cliente
from guyrapu.obs import obs_lanzador
from guyrapu.obs import transmision_directa
from guyrapu.obs.obs_panel import GestorPanelObs
from guyrapu.restream import ganchos, transmitir
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.ui.aviso_importante import avisar
from guyrapu.ui.confirmar_transmision import (
    confirmar_finalizar, confirmar_transmision)
from guyrapu.voice import sound_player as _snd

logger = diagnostico.obtener_logger(__name__)


class ComandoDirecto:
    """Transmite y finaliza el directo desde cualquier botón del directo."""

    def __init__(self, marco):
        self._marco = marco
        self._boton = None
        self._transmitiendo = False
        self._deteniendo = False

    def usar_boton(self, boton) -> None:
        """Botón del directo que se deshabilita mientras se revisa OBS."""
        self._boton = boton

    def sincronizar(self, transmitiendo, deteniendo=False) -> None:
        """Toma el estado que muestran los botones para decidir al pulsar."""
        self._transmitiendo = bool(transmitiendo)
        self._deteniendo = bool(deteniendo)

    def pulsar(self, padre) -> None:
        if self._deteniendo:
            anunciar(_("Deteniendo la transmisión. Esperando a que OBS confirme."))
            return
        if self._transmitiendo:
            self._finalizar(padre)
        else:
            self._transmitir(padre)

    def _transmitir(self, padre):
        marco = self._marco
        from guyrapu.ui.gui_elegir_destino import pedir_destino
        destino_guardado = marco._config.get("transmision_destino", "") or ""
        usuario_guardado = marco._config.get("tiktok_usuario", "") or ""
        elegido = pedir_destino(padre, destino_guardado, usuario_guardado)
        if elegido is None:
            anunciar(_("No se transmitió."))
            return
        destino, usuario = elegido
        try:
            marco._guardar_destino_transmision(destino)
        except Exception as error:
            logger.warning("no se pudo guardar el destino de transmisión: %s", error)
        if destino == "TikTok":
            try:
                usuario = marco._guardar_usuario_tiktok(usuario)
            except Exception as error:
                logger.warning("no se pudo guardar el usuario de TikTok: %s", error)
        if not transmision_directa.cuenta_restream_conectada(destino, avisar):
            return
        _snd.reproducir("conectando")
        anunciar(_("Revisando OBS antes de transmitir."))
        self._boton.Disable()

        def _revisar():
            destino_obs = (ganchos.destino_de_opcion(destino)
                           if transmitir.es_restream(destino) else destino)
            try:
                preparacion = transmision_directa.preparar(
                    GestorPanelObs(), destino_obs, obs_lanzador.asegurar_obs,
                    lambda frase: wx.CallAfter(anunciar, frase),
                    opcion=destino)
            except Exception as error:
                wx.CallAfter(self._revision_fallida, error)
            else:
                wx.CallAfter(self._revision_lista, padre, preparacion, destino,
                             destino_obs, usuario)

        diagnostico.crear_hilo(_revisar, "ComandoDirectoRevisar").start()

    def _revision_fallida(self, error):
        if not self._marco._alive:
            return
        self._boton.Enable()
        avisar(obs_cliente.mensaje_de_fallo_obs(error), "error", error=True)

    def _revision_lista(self, padre, preparacion, destino, destino_obs, usuario):
        marco = self._marco
        if not marco._alive:
            return
        self._boton.Enable()

        def _ya_transmitiendo():
            marco._obs_transmitiendo = True

        def _confirmar(revision):
            return confirmar_transmision(
                padre, revision, getattr(preparacion, "destinos_de_mas", ()))

        transmision_directa.resolver_revision(
            preparacion, destino, destino_obs, usuario,
            confirmar=_confirmar,
            supervisar=marco._supervisar_transmision,
            anunciar=anunciar,
            ya_transmitiendo=_ya_transmitiendo,
            iniciar=marco._actualizar_boton_directo,
            recordar_destino=lambda: None,
            guardar_usuario=lambda: None,
            tras_anunciar=marco._actualizar_boton_directo)

    def _finalizar(self, padre):
        marco = self._marco
        if not confirmar_finalizar(padre):
            anunciar(_("Sigues transmitiendo."))
            return
        if marco._supervisar_transmision("activo"):
            marco._supervisar_transmision("detener")
            marco._actualizar_boton_directo()
            return

        finalizar_youtube = self._cierre_en_youtube()

        def _detener():
            try:
                transmision_directa.finalizar(
                    GestorPanelObs(),
                    finalizar_youtube=finalizar_youtube)
            except Exception as error:
                wx.CallAfter(self._finalizada_con_error, error)
            else:
                wx.CallAfter(self._finalizada)

        diagnostico.crear_hilo(_detener, "ComandoDirectoFinalizar").start()

    def _cierre_en_youtube(self):
        """Callable sin argumentos que cierra el directo en YouTube.

        Solo con sesión iniciada, con las mismas credenciales que arma
        `gui.py` al supervisar: busca las emisiones activas atadas al
        flujo reutilizable de la cuenta y las finaliza. Sin sesión
        devuelve None y OBS se detiene como hoy.
        """
        try:
            from guyrapu.youtube import credenciales, emision, youtube_api
        except Exception:
            return None
        try:
            datos = credenciales.cargar()
        except Exception:
            return None
        if not credenciales.hay_sesion(datos):
            return None
        try:
            cliente = youtube_api.ClienteYouTube(
                credenciales.efectivas(datos))
        except Exception:
            return None

        def _cerrar():
            try:
                flujo = cliente.flujo_reutilizable()
                id_flujo = flujo[0] if flujo else ""
                if not id_flujo:
                    return
                for id_video, atado, _titulo in cliente.emisiones_activas():
                    if atado == id_flujo:
                        emision.finalizar_en_youtube(cliente, id_video)
            finally:
                try:
                    nuevo = cliente.token_actualizado()
                except Exception:
                    nuevo = None
                if nuevo:
                    try:
                        credenciales.guardar_campo("token", nuevo)
                    except Exception as error:
                        logger.warning("no se pudo guardar el token actualizado: %s", error)

        return _cerrar

    def _finalizada(self):
        marco = self._marco
        if not marco._alive:
            return
        marco._obs_transmitiendo = False
        avisar(_("Transmisión detenida."), "desconectado")
        marco._actualizar_boton_directo()

    def _finalizada_con_error(self, error):
        if not self._marco._alive:
            return
        if isinstance(error, transmision_directa.FalloCierreYoutube):
            avisar(str(error), "error", error=True)
            logger.warning(
                "cierre en YouTube sin supervisor: %s",
                error.__cause__ or error)
            return
        avisar(obs_cliente.mensaje_de_fallo_obs(error), "error", error=True)
