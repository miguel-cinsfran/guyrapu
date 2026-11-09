# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Acompaña al gestor del horizontal con el lienzo vertical del plugin.

Envuelve al gestor que crea el supervisor y le delega todo. Solo el gestor
que arrancó la transmisión vigila: arranca el vertical después del
horizontal, sigue la escena al aire, reintenta el vertical si se interrumpe y lo
detiene cuando el horizontal termina o cuando se pide detener.
"""

from __future__ import annotations

import time

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import escena_gemela, lienzo_vertical

logger = diagnostico.obtener_logger(__name__)

MENSAJE_ARRANQUE = N_("El vertical también está transmitiendo.")
MENSAJE_CORTE = N_(
    "El vertical se interrumpió. El horizontal sigue y Guyrapu lo vuelve a "
    "intentar cada 30 segundos.")
MENSAJE_VUELTA = N_("El vertical volvió.")
MENSAJE_SIN_PAREJA = N_(
    "La escena {escena} no tiene versión vertical: el vertical sigue en "
    "{vertical}. Créala con Crear la versión vertical.")
MENSAJE_FIN = N_("También se detuvo el vertical.")

INTERVALO_REINTENTO = 30.0


class GestorVertical:
    """Envuelve un gestor de OBS y coordina la salida del lienzo vertical."""

    def __init__(self, base, al_anunciar, lienzo=None, escena=None,
                 estado=None, lienzo_mod=lienzo_vertical,
                 reloj=time.monotonic, intervalo=INTERVALO_REINTENTO):
        self._base = base
        self._al_anunciar = al_anunciar or (lambda frase, sonido: None)
        self._lienzo_mod = lienzo_mod
        self._reloj = reloj
        self._intervalo = intervalo
        self._estado = estado if estado is not None else {}
        if lienzo is not None:
            self._estado.setdefault("lienzo", lienzo)
        if escena is not None:
            self._estado.setdefault("escena", escena)
        self._arrancado = False
        self._vigilando = False
        self._vertical_activo = False
        self._cortado = False
        self._ultimo_intento = 0.0
        self._escena_horizontal = ""
        self._vertical_actual = ""
        self._sin_pareja = set()

    def __getattr__(self, nombre):
        if nombre == "_base":
            raise AttributeError(nombre)
        return getattr(self._base, nombre)

    def iniciar_transmision(self, parada=None) -> None:
        self._base.iniciar_transmision(parada)
        self._arrancado = True
        self._vigilando = True
        self._escena_horizontal = self._escena_al_aire(parada)
        self._vertical_actual = self._estado.get("escena") or ""
        cliente = self._cliente_obs()
        if not self._vertical_actual:
            self._vertical_actual = self._escena_vertical(cliente, parada)
        self._intentar_arrancar(parada, inicial=True)

    def detener_transmision(self, parada=None) -> None:
        self._vigilando = False
        self._detener_vertical(parada)
        self._vertical_activo = False
        self._base.detener_transmision(parada)

    def estado_transmision(self, parada=None) -> dict:
        estado = self._base.estado_transmision(parada)
        if not self._arrancado or not self._vigilando:
            return estado
        if not estado.get("outputActive"):
            self._terminar_por_horizontal(parada)
            return estado
        try:
            self._revisar_vertical(parada)
            self._seguir_escena(parada)
        except Exception as error:
            logger.debug("falló la vigilancia del vertical: %s", error)
        return estado

    def _cliente_obs(self):
        return getattr(self._base, "_cliente", self._base)

    def _intentar_arrancar(self, parada, inicial=False) -> None:
        try:
            self._lienzo_mod.arrancar(self._cliente_obs(), parada)
        except Exception as error:
            logger.debug("no se pudo arrancar el vertical: %s", error)
            self._marcar_corte(parada)
            return
        if not inicial:
            return
        self._vertical_activo = True
        self._cortado = False
        self._anunciar(_(MENSAJE_ARRANQUE), "conectado")

    def _marcar_corte(self, parada) -> None:
        if self._cortado:
            return
        self._cortado = True
        self._vertical_activo = False
        self._ultimo_intento = self._reloj()
        self._anunciar(_(MENSAJE_CORTE), "transmision_problema")

    def _revisar_vertical(self, parada) -> None:
        try:
            activo = bool(self._lienzo_mod.estado(
                self._cliente_obs(), parada).get("transmitiendo"))
        except Exception as error:
            logger.debug("no se pudo leer el estado del vertical: %s", error)
            activo = False
        if activo:
            if self._cortado:
                self._anunciar(_(MENSAJE_VUELTA),
                               "transmision_recuperada")
            self._cortado = False
            self._vertical_activo = True
            return
        if not self._cortado:
            self._marcar_corte(parada)
            return
        ahora = self._reloj()
        if ahora - self._ultimo_intento < self._intervalo:
            return
        self._ultimo_intento = ahora
        self._intentar_arrancar(parada)

    def _seguir_escena(self, parada) -> None:
        escena = self._escena_al_aire(parada)
        if not escena or escena == self._escena_horizontal:
            return
        self._escena_horizontal = escena
        pareja = escena_gemela.nombre_gemela(escena)
        if not self._existe_pareja(pareja, parada):
            self._avisar_sin_pareja(escena)
            return
        try:
            self._lienzo_mod.cambiar_escena(
                self._cliente_obs(), pareja, parada)
        except Exception as error:
            logger.debug("no se pudo cambiar el vertical a %s: %s",
                         pareja, error)
            self._avisar_sin_pareja(escena)
            return
        self._vertical_actual = pareja
        self._sin_pareja.discard(escena)

    def _existe_pareja(self, pareja, parada) -> bool:
        lienzo = self._estado.get("lienzo") or {}
        uuid = lienzo.get("canvasUuid")
        if not uuid:
            return False
        try:
            respuesta = self._cliente_obs().pedir(
                "GetSceneList", {"canvasUuid": uuid}, parada)
        except Exception as error:
            logger.debug("no se pudieron leer las escenas del vertical: %s",
                         error)
            return False
        datos = (respuesta or {}).get("responseData", respuesta or {}) or {}
        return any(escena.get("sceneName", "") == pareja
                   for escena in datos.get("scenes") or ())

    def _avisar_sin_pareja(self, escena) -> None:
        if escena in self._sin_pareja:
            return
        self._sin_pareja.add(escena)
        self._anunciar(_(MENSAJE_SIN_PAREJA).format(
            escena=escena, vertical=self._vertical_actual), "aviso")

    def _terminar_por_horizontal(self, parada) -> None:
        self._vigilando = False
        if not self._vertical_activo:
            return
        if not self._vertical_sigue(parada):
            self._vertical_activo = False
            return
        self._detener_vertical(parada)
        self._vertical_activo = False
        self._anunciar(_(MENSAJE_FIN), "transmision_problema")

    def _vertical_sigue(self, parada) -> bool:
        try:
            return bool(self._lienzo_mod.estado(
                self._cliente_obs(), parada).get("transmitiendo"))
        except Exception as error:
            logger.debug("no se pudo leer el estado del vertical: %s", error)
            return False

    def _detener_vertical(self, parada) -> None:
        try:
            self._lienzo_mod.detener(self._cliente_obs(), parada)
        except Exception as error:
            logger.debug("no se pudo detener el vertical: %s", error)

    def _escena_al_aire(self, parada) -> str:
        try:
            return self._base.escena_al_aire(parada) or ""
        except Exception as error:
            logger.debug("no se pudo leer la escena al aire: %s", error)
            return ""

    def _escena_vertical(self, cliente, parada) -> str:
        try:
            return self._lienzo_mod.escena_actual(cliente, parada) or ""
        except Exception as error:
            logger.debug("no se pudo leer la escena del vertical: %s", error)
            return ""

    def _anunciar(self, frase, sonido) -> None:
        try:
            self._al_anunciar(frase, sonido)
        except Exception as error:
            logger.debug("no se pudo anunciar el estado del vertical: %s",
                         error)
