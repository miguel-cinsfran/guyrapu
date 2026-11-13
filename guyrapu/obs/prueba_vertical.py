# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se suma el lienzo vertical a una grabación de la prueba del equipo.

Envuelve al cliente de OBS y delega todo, salvo `StartRecord` y
`StopRecord`: el vertical arranca después del principal y se detiene antes
que él. Al detenerlo se borran las grabaciones nuevas de su carpeta y, si
el búfer no estaba encendido antes de la prueba, se apaga.
"""

from __future__ import annotations

from pathlib import Path

from guyrapu.core import diagnostico, esperas, paths
from guyrapu.core.archivos import en_uso
from guyrapu.obs import config_lienzo_vertical, lienzo_vertical, obs_cliente

logger = diagnostico.obtener_logger(__name__)

_ESPERA_DETENCION = 10.0
_PASO_DETENCION = 0.2
_ESPERA_BORRADO = 5.0
_PASO_BORRADO = 0.25


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {}) or {}


def _carpeta_config(config):
    """La carpeta propia del plugin, si la configuración la fija."""
    for lienzo in (config or {}).get("canvas") or ():
        ruta = str((lienzo or {}).get("record_path") or "").strip()
        if ruta:
            return Path(ruta)
    return None


def _verticales(carpeta):
    if carpeta is None:
        return set()
    try:
        return {ruta.name for ruta in carpeta.iterdir()
                if ruta.is_file() and "-vertical" in ruta.name}
    except OSError:
        return set()


def _borrar(ruta):
    """Borra la grabación vertical; False si OBS la siguió tomando."""

    def intentar():
        try:
            ruta.unlink(missing_ok=True)
        except OSError as error:
            return error

    resultado = esperas.esperar(
        intentar, lambda error: error is None or not en_uso(error),
        cadencia=esperas.Fija(_PASO_BORRADO), plazo=_ESPERA_BORRADO)
    if resultado.valor is not None:
        logger.warning("la grabación vertical quedó en %s: %s", ruta, resultado.valor)
    return resultado.valor is None


class ClienteVertical:
    """El cliente de OBS que graba y borra también el lienzo vertical."""

    def __init__(self, cliente, carpeta=None):
        self._cliente = cliente
        self._carpeta = Path(carpeta) if carpeta is not None else None
        self._bufer_inicial = None
        self._previos = None
        self._activa = False

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "StartRecord":
            return self._arrancar(datos, parada)
        if tipo == "StopRecord":
            return self._detener(datos, parada)
        return self._cliente.pedir(tipo, datos, parada)

    def _arrancar(self, datos, parada):
        respuesta = self._cliente.pedir("StartRecord", datos, parada)
        self._preparar_vertical(parada)
        return respuesta

    def _preparar_vertical(self, parada):
        if self._bufer_inicial is None:
            try:
                self._bufer_inicial = lienzo_vertical.estado(
                    self._cliente, parada)["bufer"]
            except obs_cliente.ObsError as error:
                logger.debug("no se pudo leer el búfer vertical: %s", error)
        self._carpeta = self._carpeta or self._carpeta_de_grabacion(parada)
        self._previos = _verticales(self._carpeta)
        self._activa = True
        lienzo_vertical.arrancar_grabacion(self._cliente, parada)

    def _carpeta_de_grabacion(self, parada):
        try:
            config = config_lienzo_vertical.leer(
                paths.carpeta_obs("lienzo_vertical"))
        except (OSError, ValueError) as error:
            logger.debug("no se pudo leer la configuración del vertical: %s",
                         error)
            config = None
        ruta = _carpeta_config(config)
        if ruta is not None:
            return ruta
        datos = _datos(self._cliente.pedir("GetRecordDirectory", {}, parada))
        texto = str(datos.get("recordDirectory") or "").strip()
        return Path(texto) if texto else None

    def _detener(self, datos, parada):
        if self._activa:
            self._bajar_vertical()
        return self._cliente.pedir("StopRecord", datos, parada)

    def _bajar_vertical(self):
        try:
            lienzo_vertical.detener_grabacion(self._cliente)
        except obs_cliente.ObsError as error:
            logger.warning("no se pudo detener la grabación vertical: %s",
                           error)
        self._esperar_detencion()
        self._borrar_nuevas()
        if self._bufer_inicial is False:
            try:
                lienzo_vertical.apagar_bufer(self._cliente)
            except obs_cliente.ObsError as error:
                logger.warning("no se pudo apagar el búfer vertical: %s",
                               error)
        self._activa = False

    def _esperar_detencion(self):
        try:
            resultado = esperas.esperar(
                lambda: lienzo_vertical.estado(self._cliente).get("grabando"),
                lambda grabando: not grabando,
                cadencia=esperas.Fija(_PASO_DETENCION),
                plazo=_ESPERA_DETENCION)
        except obs_cliente.ObsError as error:
            logger.debug("no se pudo leer el estado vertical: %s", error)
            return False
        return resultado.motivo == esperas.MOTIVO_LISTO

    def _borrar_nuevas(self):
        if self._carpeta is None or self._previos is None:
            return
        for nombre in _verticales(self._carpeta) - self._previos:
            _borrar(self._carpeta / nombre)
