# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Comando de transmitir y finalizar el directo, con wx.

Reúne en un solo lugar lo que pasa al transmitir o finalizar el directo:
pedir el destino, guardarlo, comprobar la cuenta de Restream, atender al
supervisor, revisar OBS, confirmar, iniciar y finalizar, con el cierre de
YouTube. Los botones del directo solo lo llaman y muestran el estado que
el comando les avisa.
"""

from __future__ import annotations

import wx

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.obs import obs_cliente
from guyrapu.obs import obs_estado
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
        self._supervisar = getattr(marco, "_supervisar_transmision", None)
        self._transmitiendo = False
        self._deteniendo = False
        self._revisando = False
        self._suscriptores = []

    @property
    def transmitiendo(self) -> bool:
        return self._transmitiendo

    @property
    def deteniendo(self) -> bool:
        return self._deteniendo

    def suscribir(self, al_cambiar) -> None:
        self._suscriptores.append(al_cambiar)

    def desuscribir(self, al_cambiar) -> None:
        try:
            self._suscriptores.remove(al_cambiar)
        except ValueError:
            pass

    def sincronizar(self, transmitiendo, deteniendo=False) -> None:
        """Toma el estado que muestran los botones para decidir al pulsar."""
        transmitiendo = bool(transmitiendo)
        deteniendo = bool(deteniendo)
        if (transmitiendo, deteniendo) == (self._transmitiendo,
                                           self._deteniendo):
            return
        self._transmitiendo = transmitiendo
        self._deteniendo = deteniendo
        self._avisar()

    def _avisar(self) -> None:
        if not self._marco._alive:
            return
        for al_cambiar in tuple(self._suscriptores):
            al_cambiar()

    def pulsar(self, padre) -> None:
        if self._revisando:
            anunciar(_("Revisando OBS antes de transmitir."))
            return
        if self._deteniendo:
            anunciar(_("Deteniendo la transmisión. Esperando a que OBS confirme."))
            return
        if self._transmitiendo:
            self._finalizar(padre)
        else:
            self._transmitir(padre)

    def _preguntar(self, accion) -> bool:
        if self._supervisar is None:
            return False
        try:
            return bool(self._supervisar(accion))
        except Exception:
            return False

    def _detener_supervision(self) -> None:
        if self._supervisar is None:
            return
        try:
            self._supervisar("detener")
        except Exception as error:
            logger.debug("no se pudo detener la supervisión: %s", error)

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
        usuario = self._usuario_para(destino, usuario)
        destino_obs = (ganchos.destino_de_opcion(destino)
                       if transmitir.es_restream(destino) else destino)
        decision = transmision_directa.decidir_transmision(
            hay_supervisor=self._supervisar is not None,
            deteniendo=lambda: self._preguntar("deteniendo"),
            con_supervisor=lambda: self._preguntar("activo"),
            transmitiendo=self._transmitiendo,
            destino=destino, usuario_tiktok=lambda: usuario)
        if self._atender_decision(decision):
            return
        _snd.reproducir("conectando")
        anunciar(_("Revisando OBS antes de transmitir."))
        self._revisando = True

        def _revisar():
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

    def _usuario_para(self, destino, usuario) -> str:
        if transmitir.es_restream(destino) or destino != "TikTok":
            return ""
        from guyrapu.capture import tiktok_vivo
        return tiktok_vivo.usuario_tiktok(usuario or "")

    def _atender_decision(self, decision) -> bool:
        """Resuelve las decisiones que no llegan a preparar OBS."""
        if decision == transmision_directa.ALTERNAR:
            self._alternar()
            return True
        if decision == transmision_directa.ESPERAR_DETENCION:
            anunciar(_("Deteniendo la transmisión. "
                       "Esperando a que OBS confirme."))
            return True
        if decision == transmision_directa.DETENER_SUPERVISADA:
            self._detener_supervision()
            self._mostrar_transmision(False)
            return True
        if decision == transmision_directa.FALTA_DESTINO:
            avisar(_("Elige primero a dónde transmitir, en Transmitir a."), "error", error=True)
            return True
        if decision == transmision_directa.FALTA_USUARIO:
            anunciar(_("Escribe tu usuario de TikTok en Usuario de TikTok."))
            self._avisar()
            return True
        return False

    def _alternar(self) -> None:
        def _trabajar():
            try:
                activa = bool(GestorPanelObs().alternar_transmision())
            except Exception as error:
                wx.CallAfter(self._fallo_obs, error)
            else:
                wx.CallAfter(self._transmision_alternada, activa)

        diagnostico.crear_hilo(_trabajar, "ComandoDirectoAlternar").start()

    def _transmision_alternada(self, activa) -> None:
        if not self._marco._alive:
            return
        self._marco._obs_transmitiendo = bool(activa)
        self._mostrar_transmision(bool(activa))
        accion = "transmision_iniciada" if activa else "transmision_detenida"
        avisar(obs_estado.frase_resultado(accion),
               obs_estado.sonido_resultado(accion))

    def _mostrar_transmision(self, activa, deteniendo=False) -> None:
        self.sincronizar(activa, deteniendo)

    def _revision_fallida(self, error):
        self._revisando = False
        self._fallo_obs(error)

    def _fallo_obs(self, error):
        if not self._marco._alive:
            return
        avisar(obs_cliente.mensaje_de_fallo_obs(error), "error", error=True)

    def _revision_lista(self, padre, preparacion, destino, destino_obs, usuario):
        marco = self._marco
        if not marco._alive:
            return
        self._revisando = False

        def _ya_transmitiendo():
            marco._obs_transmitiendo = True
            self._mostrar_transmision(True)

        def _confirmar(revision):
            return confirmar_transmision(
                padre, revision, getattr(preparacion, "destinos_de_mas", ()))

        def _iniciar():
            self._mostrar_transmision(True)
            marco._actualizar_boton_directo()

        transmision_directa.resolver_revision(
            preparacion, destino, destino_obs, usuario,
            confirmar=_confirmar,
            supervisar=self._supervisar,
            anunciar=anunciar,
            ya_transmitiendo=_ya_transmitiendo,
            iniciar=_iniciar,
            recordar_destino=lambda: None,
            guardar_usuario=lambda: None,
            tras_anunciar=marco._actualizar_boton_directo)

    def _finalizar(self, padre):
        if not confirmar_finalizar(padre):
            anunciar(_("Sigues transmitiendo."))
            return
        if self._preguntar("activo"):
            self._detener_supervision()
            self._mostrar_transmision(True, deteniendo=True)
            wx.CallLater(2000, self._esperar_supervisor)
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

    def _esperar_supervisor(self) -> None:
        if not self._marco._alive or not self._deteniendo:
            return
        if self._preguntar("deteniendo"):
            wx.CallLater(2000, self._esperar_supervisor)
            return
        self._mostrar_transmision(False)

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
        self._mostrar_transmision(False)
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
