# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Prepara un directo de Restream en horizontal y vertical a la vez.

Dos piezas: el `asegurar` del supervisor, que deja escrita la salida
«Guyrapu» del plugin antes de abrir OBS, y el `escribir` que usa la
preparación común para poner el servidor y la clave de Restream en esa
salida, copiar las escenas verticales y elegir la escena del lienzo.
"""

from __future__ import annotations

from guyrapu.core import diagnostico, paths
from guyrapu.core.idioma import N_, _
from guyrapu.obs import (
    config_lienzo_vertical, espejo_vertical, escena_gemela,
    gestor_vertical, lienzo_vertical, obs_activacion, obs_cliente,
    obs_destinos, obs_lanzador, perfiles_obs)
from guyrapu.youtube import emision

logger = diagnostico.obtener_logger(__name__)

MENSAJE_SIN_PLUGIN = N_(
    "Para transmitir en horizontal y vertical a la vez hace falta el plugin "
    "Vertical Canvas de Aitum en OBS. Descárgalo de "
    "github.com/Aitum/obs-vertical-canvas/releases, instálalo con OBS "
    "cerrado y vuelve a transmitir.")
MENSAJE_SALIDA_EN_MARCHA = N_(
    "OBS está grabando o transmitiendo. Detenlo y vuelve a transmitir: "
    "Guyrapu tiene que cerrar OBS un momento para preparar la salida "
    "vertical.")
MENSAJE_NO_SE_CERRO = N_(
    "OBS no se cerró. Ciérralo y vuelve a transmitir para preparar la "
    "salida vertical.")
MENSAJE_PREPARANDO_CIERRE = N_(
    "Guyrapu prepara la salida vertical del plugin: OBS se cierra y se "
    "vuelve a abrir.")
MENSAJE_FUENTES = N_("No se copiaron al vertical: {fuentes}.")
MENSAJE_AMBAS_SIN_YOUTUBE = N_(
    "Para transmitir en horizontal y vertical a la vez, marca YouTube: "
    "YouTube recibe el horizontal y los destinos de Restream, el vertical.")
MENSAJE_AMBAS_SIN_SESION = N_(
    "Para transmitir en horizontal y vertical a la vez, inicia la sesión de "
    "Google: YouTube recibe el horizontal.")


def _cliente_nuevo():
    return obs_cliente.ClienteObs(obs_cliente.leer_ajustes())


def _clave_cuenta(cuenta_mod):
    try:
        return cuenta_mod.clave_cuenta()
    except obs_cliente.ObsError:
        raise
    except Exception as error:
        raise obs_cliente.ObsError(str(error)) from error


def _escribir_salida(ruta, config, cuenta_mod) -> None:
    clave = _clave_cuenta(cuenta_mod)
    config_lienzo_vertical.escribir(
        ruta, config_lienzo_vertical.con_salida(
            config, clave.servidor, clave.clave))


def _comprobar_sin_salidas(crear_cliente, parada) -> None:
    cliente = crear_cliente()
    try:
        cliente.conectar(parada)
        try:
            perfiles_obs.comprobar_salidas(cliente, parada)
        except obs_cliente.ObsError as error:
            raise obs_cliente.ObsError(
                _(MENSAJE_SALIDA_EN_MARCHA)) from error
    finally:
        try:
            cliente.cerrar()
        except Exception as error:
            logger.debug("no se pudo cerrar la conexión de prueba: %s", error)


def asegurar(cuenta_mod, ruta=None, crear_cliente=None, en_ejecucion=None,
             cerrar=None, base=None):
    """Devuelve el `asegurar` que deja escrita la salida «Guyrapu»."""
    ruta = ruta or paths.carpeta_obs("lienzo_vertical")
    crear_cliente = crear_cliente or _cliente_nuevo
    en_ejecucion = en_ejecucion or obs_activacion.obs_esta_en_ejecucion
    cerrar = cerrar or obs_lanzador.cerrar_obs
    base = base or obs_lanzador.asegurar_obs

    def asegurar_salida(probar_conexion, al_anunciar=None, parada=None):
        config = config_lienzo_vertical.leer(ruta)
        if config is None:
            return base(probar_conexion, al_anunciar, parada)
        if config_lienzo_vertical.posicion_salida(config) is not None:
            return base(probar_conexion, al_anunciar, parada)
        if not en_ejecucion():
            _escribir_salida(ruta, config, cuenta_mod)
            return base(probar_conexion, al_anunciar, parada)
        _comprobar_sin_salidas(crear_cliente, parada)
        if al_anunciar is not None:
            al_anunciar(_(MENSAJE_PREPARANDO_CIERRE))
        if not cerrar():
            raise obs_cliente.ObsError(_(MENSAJE_NO_SE_CERRO))
        config = config_lienzo_vertical.leer(ruta)
        if config is not None:
            _escribir_salida(ruta, config, cuenta_mod)
        return base(probar_conexion, al_anunciar, parada)
    return asegurar_salida


def exigir_youtube(preparar, perfil, preparados):
    """Falla antes de tocar canales u OBS si «ambas» no puede ir a YouTube."""
    def preparar_ambas(cliente, parada=None):
        if not perfil.youtube:
            raise emision.EmisionError(_(MENSAJE_AMBAS_SIN_YOUTUBE))
        if preparados is None:
            raise emision.EmisionError(_(MENSAJE_AMBAS_SIN_SESION))
        return preparar(cliente, parada)
    return preparar_ambas


def _poner_salida(cliente, destino, parada) -> None:
    ruta = paths.carpeta_obs("lienzo_vertical")
    config = config_lienzo_vertical.leer(ruta)
    indice = (config_lienzo_vertical.posicion_salida(config)
              if config is not None else None)
    if indice is None:
        raise emision.EmisionError(_(MENSAJE_SIN_PLUGIN))
    lienzo_vertical.cambiar_servidor(
        cliente, indice, destino.servidor, parada)
    lienzo_vertical.cambiar_clave(cliente, indice, destino.clave, parada)


def _escena_al_aire(cliente, parada) -> str:
    datos = (cliente.pedir("GetCurrentProgramScene", parada=parada).get(
        "responseData", {}) or {})
    return datos.get("currentProgramSceneName", "") or ""


def _elegir_escena(cliente, copiadas, parada) -> str:
    escena = _escena_al_aire(cliente, parada)
    if not escena:
        return ""
    pareja = escena_gemela.nombre_gemela(escena)
    if pareja in (copiadas or ()):
        lienzo_vertical.cambiar_escena(cliente, pareja, parada)
        return pareja
    try:
        return lienzo_vertical.escena_actual(cliente, parada) or ""
    except Exception as error:
        logger.debug("no se pudo leer la escena del vertical: %s", error)
        return ""


def escribir_vertical(estado, al_anunciar):
    """Devuelve el `escribir` que prepara la salida vertical de «ambas»."""
    def escribir(cliente, destino, parada=None):
        lienzo = lienzo_vertical.detectar(cliente, parada)
        if lienzo is None:
            raise emision.EmisionError(_(MENSAJE_SIN_PLUGIN))
        _poner_salida(cliente, destino, parada)
        copiadas, omitidas = espejo_vertical.espejar(cliente, lienzo, parada)
        if omitidas:
            al_anunciar(_(MENSAJE_FUENTES).format(
                fuentes=", ".join(nombre for _vertical, nombre in omitidas)),
                "aviso")
        estado["lienzo"] = lienzo
        estado["escena"] = _elegir_escena(cliente, copiadas, parada)
    return escribir


def envolver_crear_gestor(estado, al_anunciar):
    """Envuelve el `crear_gestor` del supervisor con el gestor vertical."""
    def envolver(crear_base):
        def crear():
            return gestor_vertical.GestorVertical(
                crear_base(), al_anunciar, estado=estado)
        return crear
    return envolver


def aplicar_envoltura(parametros, extras):
    """Aplica la envoltura del gestor vertical a los parámetros del supervisor."""
    extras = dict(extras)
    envolver = extras.pop("envolver_crear_gestor", None)
    if envolver is not None:
        from guyrapu.obs.obs_panel import GestorPanelObs
        parametros["crear_gestor"] = envolver(
            parametros.get("crear_gestor") or GestorPanelObs)
    return parametros, extras


def armar(perfil, canales, al_anunciar, cuenta_mod, restaurador, preparados,
          preparar_emision):
    """Arma la preparación doble y devuelve sus extras y la restauración."""
    estado = {}
    preparar = preparar_emision(
        perfil, canales, al_anunciar, cuenta_mod, restaurador,
        escribir_vertical(estado, al_anunciar),
        preparados=preparados,
        preparar_destino=obs_destinos.preparar_destino)
    extras = {
        "asegurar": asegurar(cuenta_mod),
        "envolver_crear_gestor": envolver_crear_gestor(estado, al_anunciar),
    }
    if preparados is not None:
        extras["esperar_emision"] = preparados.get("esperar")
        extras["finalizar_emision"] = preparados.get("finalizar")
    return (exigir_youtube(preparar, perfil, preparados),
            restaurador.restaurar, extras)
