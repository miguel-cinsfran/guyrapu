# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se crea y se acomoda la versión vertical de una escena del Panel.

La parte con OBS corre en los hilos del Panel y el cuadro de diseños en el
hilo de la interfaz, entre dos pasos: el primero crea la escena, pasa al
perfil vertical y lee las fuentes; el segundo aplica el diseño y vuelve al
perfil que había.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import (
    aplicar_diseno, chat_en_video, consultas_transmision, disenos_fabrica,
    disenos_guardados, escena_gemela, escenas_obs, obs_cliente, perfiles_obs)
from guyrapu.ui import escena_disenos
from guyrapu.ui.accesibilidad import anunciar

logger = diagnostico.obtener_logger(__name__)

MENSAJE_SIN_PERFIL = N_(
    "Elige primero el perfil para transmitir en vertical, en Preferencias, "
    "Transmisión.")
MENSAJE_YA_EXISTE = N_(
    "Ya existe la escena {escena} vertical. Para acomodarla, usa Aplicar "
    "diseño sobre ella.")
MENSAJE_EMPEZANDO = N_("Creando la versión vertical…")
MENSAJE_CANCELADA = N_("Versión vertical cancelada.")
MENSAJE_CREADA = N_(
    "Versión vertical creada: {escena} vertical. Diseño: {diseño}.")


def _config(pagina):
    ventana = getattr(pagina, "_ventana", None)
    if ventana is None:
        ventana = getattr(getattr(pagina, "pagina_fuentes", None),
                          "_ventana", None)
    principal = getattr(ventana, "_principal", None)
    return getattr(principal, "_config", None) or {}


def _registro(pagina):
    registro = getattr(pagina, "_registro", None)
    if registro is None:
        registro = getattr(getattr(pagina, "pagina_fuentes", None),
                           "_registro", None)
    return registro


def perfil_vertical(pagina) -> str:
    """El perfil para transmitir en vertical, vacío si no hay ninguno."""
    return str(_config(pagina).get("perfil_vertical", "") or "")


def _puerto(pagina):
    return chat_en_video.puerto_del_panel(_config(pagina))


def _nombres_visibles(pagina):
    ventana = getattr(pagina, "_ventana", None)
    pagina_escena = getattr(ventana, "_pagina_escena", None)
    if pagina_escena is None:
        return ()
    return pagina_escena._nombres()


def es_gemela_con_original(pagina, escena) -> bool:
    """Si la escena es una versión vertical y su original todavía existe."""
    return escena_gemela.original_de(
        escena, _nombres_visibles(pagina)) is not None


def _quitar(pagina, escena):
    try:
        escenas_obs.eliminar(pagina._gestor._pedir, escena)
    except obs_cliente.ObsError as error:
        logger.debug("no se pudo quitar la escena %s: %s", escena, error)


def _volver(cliente, anterior):
    """Vuelve al perfil que había; devuelve su nombre o "" si no pudo."""
    if not anterior:
        return ""
    try:
        if perfiles_obs.listar_perfiles(cliente)[1] == anterior:
            return anterior
        perfiles_obs.cambiar(cliente, anterior)
        return anterior
    except obs_cliente.ObsError as error:
        logger.debug("no se pudo volver al perfil de OBS %s: %s",
                     anterior, error)
        return ""


def _con_vuelta(cliente, anterior, accion):
    """Corre la acción y vuelve al perfil, también si la acción falla."""
    try:
        resultado = accion()
    except Exception as error:
        if _volver(cliente, anterior):
            raise obs_cliente.ObsError(
                f"{error} OBS volvió al perfil {anterior}.") from error
        raise
    _volver(cliente, anterior)
    return resultado


def _primer_paso(pagina, escena, perfil, gemela):
    cliente = pagina._gestor._cliente
    perfiles_obs.comprobar_salidas(cliente)
    anterior = perfiles_obs.listar_perfiles(cliente)[1]
    escenas_obs.duplicar(pagina._gestor._pedir, escena, gemela)
    cambiado = False
    try:
        if anterior and anterior != perfil:
            perfiles_obs.cambiar(cliente, perfil)
            cambiado = True
        fuentes, vertical = aplicar_diseno.fuentes_y_lienzo(
            pagina._gestor, gemela)
    except Exception as error:
        _quitar(pagina, gemela)
        if cambiado:
            _volver(cliente, anterior)
            raise obs_cliente.ObsError(
                f"{error} OBS volvió al perfil {anterior}.") from error
        raise
    return {"fuentes": fuentes, "vertical": vertical, "anterior": anterior,
            "gemela": gemela}


def _segundo_paso(pagina, escena, gemela, datos, elegido):
    cliente = pagina._gestor._cliente

    def aplicar():
        if elegido is None:
            escenas_obs.eliminar(pagina._gestor._pedir, gemela)
            return None
        nombre, diseno = elegido
        aplicado = aplicar_diseno.aplicar_diseno(
            pagina._gestor, _registro(pagina), gemela, diseno,
            _puerto(pagina))
        return nombre, aplicado

    resultado = _con_vuelta(cliente, datos["anterior"], aplicar)
    creada = gemela if resultado is not None else escena
    return resultado, pagina._leer_escenas(creada)


def _terminado(pagina, escena, resultado):
    datos, leida = resultado
    pagina._mostrar_leidas(leida)
    if datos is None:
        anunciar(_(MENSAJE_CANCELADA))
        return
    nombre, _aplicado = datos
    anunciar(_(MENSAJE_CREADA).format(escena=escena, diseño=nombre))


def _abrir_diseno(pagina, escena, datos):
    if not any(fuente.tipo != "chat" for fuente in datos["fuentes"]):
        anunciar(_("La escena no tiene fuentes para un diseño."))
        pagina._operaciones.en_hilo(
            lambda: _segundo_paso(pagina, escena, datos["gemela"], datos, None),
            lambda resultado: _terminado(pagina, escena, resultado))
        return
    guardados = disenos_guardados.cargar()
    elegido = escena_disenos.pedir_diseno(
        pagina, datos["fuentes"], guardados, True)
    pagina.lst_escenas.SetFocus()
    pagina._operaciones.en_hilo(
        lambda: _segundo_paso(
            pagina, escena, datos["gemela"], datos, elegido),
        lambda resultado: _terminado(pagina, escena, resultado))


def crear(pagina):
    """Crea la versión vertical de la escena elegida y le aplica un diseño."""
    escena = pagina.escena()
    if not escena or pagina._operaciones.en_vuelo:
        return
    gemela = escena_gemela.nombre_gemela(escena)
    if gemela in pagina._nombres():
        anunciar(_(MENSAJE_YA_EXISTE).format(escena=escena))
        return
    perfil = perfil_vertical(pagina)
    if not perfil:
        anunciar(_(MENSAJE_SIN_PERFIL))
        return
    anunciar(_(MENSAJE_EMPEZANDO))
    pagina._operaciones.en_hilo(
        lambda: _primer_paso(pagina, escena, perfil, gemela),
        lambda datos: _abrir_diseno(pagina, escena, datos))


def _leer_con_perfil(pagina, escena, perfil):
    cliente = pagina._gestor._cliente
    anterior = perfiles_obs.listar_perfiles(cliente)[1]
    cambiado = False
    try:
        if anterior and anterior != perfil:
            perfiles_obs.cambiar(cliente, perfil)
            cambiado = True
        fuentes, vertical = aplicar_diseno.fuentes_y_lienzo(
            pagina._gestor, escena)
    except Exception as error:
        if cambiado:
            _volver(cliente, anterior)
            raise obs_cliente.ObsError(
                f"{error} OBS volvió al perfil {anterior}.") from error
        raise
    return {"fuentes": fuentes, "vertical": vertical, "anterior": anterior}


def _aplicar_en_perfil(pagina, escena, datos, elegido):
    cliente = pagina._gestor._cliente

    def aplicar():
        if elegido is None:
            return None
        nombre, diseno = elegido
        aplicado = aplicar_diseno.aplicar_diseno(
            pagina._gestor, _registro(pagina), escena, diseno,
            _puerto(pagina))
        return nombre, aplicado

    resultado = _con_vuelta(cliente, datos["anterior"], aplicar)
    filas = consultas_transmision.leer_filas(pagina._gestor, escena)
    return resultado, filas


def _gemela_aplicada(pagina, datos):
    resultado, filas = datos
    pagina.cargar(filas, pagina.fuente())
    if resultado is None:
        return
    nombre, aplicado = resultado
    anunciar(disenos_fabrica.resumen(
        nombre, aplicado[0], sin_mover=aplicado[1]))


def aplicar_a_gemela(pagina, escena):
    """Aplica un diseño a una versión vertical con el perfil vertical activo."""
    perfil = perfil_vertical(pagina)
    if not perfil:
        return
    pagina._operaciones.en_hilo(
        lambda: _leer_con_perfil(pagina, escena, perfil),
        lambda datos: _abrir_diseno_gemela(pagina, escena, datos))


def _abrir_diseno_gemela(pagina, escena, datos):
    if not any(fuente.tipo != "chat" for fuente in datos["fuentes"]):
        anunciar(_("La escena no tiene fuentes para un diseño."))
        pagina._operaciones.en_hilo(
            lambda: _aplicar_en_perfil(pagina, escena, datos, None),
            lambda resultado: _gemela_aplicada(pagina, resultado))
        return
    guardados = disenos_guardados.cargar()
    elegido = escena_disenos.pedir_diseno(
        pagina, datos["fuentes"], guardados, datos["vertical"])
    pagina.btn_diseno.SetFocus()
    pagina._operaciones.en_hilo(
        lambda: _aplicar_en_perfil(pagina, escena, datos, elegido),
        lambda resultado: _gemela_aplicada(pagina, resultado))
