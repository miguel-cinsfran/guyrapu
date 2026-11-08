# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Resumen de un directo terminado: fotogramas perdidos y qué cambiar.

Puro salvo `datos_del_perfil`, que consulta el perfil y el codificador de
OBS con un cliente que tiene `pedir(tipo, datos=None, parada=None)`. Sin
estadísticas de `GetStats` (un doble viejo o un fallo) se informa solo la
pérdida por red, que sale de `GetStreamStatus`.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.obs.codificadores_obs import codificador_simple

# Debajo de estos fotogramas en el directo no hay proporción que valga.
UMBRAL_FOTOGRAMAS = 30


def _diferencia(final, inicial, clave) -> int:
    try:
        return int(final.get(clave, 0)) - int(inicial.get(clave, 0))
    except (TypeError, ValueError):
        return 0


def _porcentaje(perdidos, totales) -> int:
    """Porcentaje entero de fotogramas perdidos; cero si no corresponde."""
    if totales <= 0 or perdidos <= 0:
        return 0
    return int(round(100 * perdidos / totales))


def _porcentajes(estado_inicial, estado_final, estadisticas_iniciales,
                 estadisticas_finales) -> dict:
    red = _porcentaje(
        _diferencia(estado_final, estado_inicial, "outputSkippedFrames"),
        _diferencia(estado_final, estado_inicial, "outputTotalFrames"))
    codificar = dibujar = 0
    if (isinstance(estadisticas_iniciales, dict)
            and isinstance(estadisticas_finales, dict)):
        codificar = _porcentaje(
            _diferencia(estadisticas_finales, estadisticas_iniciales,
                        "outputSkippedFrames"),
            _diferencia(estadisticas_finales, estadisticas_iniciales,
                        "outputTotalFrames"))
        dibujar = _porcentaje(
            _diferencia(estadisticas_finales, estadisticas_iniciales,
                        "renderSkippedFrames"),
            _diferencia(estadisticas_finales, estadisticas_iniciales,
                        "renderTotalFrames"))
    return {"red": red, "codificar": codificar, "dibujar": dibujar}


def _frase_de_perdida(porcentajes) -> str:
    partes = []
    if porcentajes["red"] >= 1:
        partes.append(_("el {n} por ciento de los fotogramas por la red")
                      .format(n=porcentajes["red"]))
    if porcentajes["codificar"] >= 1:
        if partes:
            partes.append(_("el {n} por ciento al codificar")
                          .format(n=porcentajes["codificar"]))
        else:
            partes.append(_("el {n} por ciento de los fotogramas al codificar")
                          .format(n=porcentajes["codificar"]))
    if porcentajes["dibujar"] >= 1:
        if partes:
            partes.append(_("el {n} por ciento al dibujar la escena")
                          .format(n=porcentajes["dibujar"]))
        else:
            partes.append(_("el {n} por ciento de los fotogramas al dibujar "
                            "la escena").format(n=porcentajes["dibujar"]))
    if not partes:
        return _("Se perdió menos del 1 por ciento de los fotogramas.")
    if len(partes) == 1:
        return _("Se perdió {partes}.").format(partes=partes[0])
    if len(partes) == 2:
        return _("Se perdió {uno} y {dos}.").format(
            uno=partes[0], dos=partes[1])
    return _("Se perdió {uno}, {dos} y {tres}.").format(
        uno=partes[0], dos=partes[1], tres=partes[2])


def _causa_mas_alta(porcentajes) -> str:
    # Empate: red, después codificar, después dibujar.
    causa = ""
    mejor = 0
    for nombre in ("red", "codificar", "dibujar"):
        if porcentajes[nombre] > mejor:
            mejor = porcentajes[nombre]
            causa = nombre
    return causa


def _recomendacion(causa, perfil, codificador, disponibles) -> str:
    nombre = perfil or _("de OBS")
    if causa == "red":
        return _("Para el próximo directo, baja la velocidad de bits de "
                 "vídeo del perfil {perfil} o usa una conexión por cable.").format(
                     perfil=nombre)
    if causa == "codificar":
        if codificador == "x264" and any(
                nombre_codificador != "x264"
                for nombre_codificador in disponibles):
            return _("Para el próximo directo, usa el codificador de la "
                     "gráfica en el perfil {perfil}.").format(perfil=nombre)
        return _("Para el próximo directo, baja la resolución o los "
                 "fotogramas por segundo del perfil {perfil}.").format(
                     perfil=nombre)
    return _("Para el próximo directo, baja los fotogramas por segundo del "
             "perfil {perfil} o cierra programas que usen la gráfica.").format(
                 perfil=nombre)


def resumir(estado_inicial, estado_final, estadisticas_iniciales,
            estadisticas_finales, perfil, codificador, disponibles) -> str:
    """Texto del resumen, o "" si el directo tuvo menos de 30 fotogramas."""
    if not isinstance(estado_inicial, dict) or not isinstance(
            estado_final, dict):
        return ""
    totales = _diferencia(estado_final, estado_inicial, "outputTotalFrames")
    if totales < UMBRAL_FOTOGRAMAS:
        return ""
    porcentajes = _porcentajes(
        estado_inicial, estado_final, estadisticas_iniciales,
        estadisticas_finales)
    texto = _frase_de_perdida(porcentajes)
    causa = _causa_mas_alta(porcentajes)
    if causa:
        texto = "{} {}".format(
            texto, _recomendacion(causa, perfil, codificador, disponibles))
    return texto


def _parametro(cliente, categoria, nombre, parada) -> str:
    datos = cliente.pedir(
        "GetProfileParameter",
        {"parameterCategory": categoria, "parameterName": nombre},
        parada=parada)
    return (datos.get("responseData", {}) or {}).get("parameterValue", "")


def datos_del_perfil(cliente, parada) -> tuple:
    """(perfil, codificador) del perfil activo; "" si no se pudo leer.

    En modo Avanzado el codificador no se puede traducir a un nombre del
    modo Sencillo, así que queda "" (desconocido). Nunca lanza: un fallo al
    preguntar deja la vigilancia sin datos en vez de cortarla.
    """
    try:
        perfil = (cliente.pedir("GetProfileList", parada=parada)
                  .get("responseData", {}) or {}).get(
                      "currentProfileName", "") or ""
        modo = _parametro(cliente, "Output", "Mode", parada)
        if str(modo).strip().lower() != "simple":
            return perfil, ""
        identificador = _parametro(
            cliente, "SimpleOutput", "StreamEncoder", parada)
        return perfil, codificador_simple(identificador)
    except Exception:
        return "", ""
