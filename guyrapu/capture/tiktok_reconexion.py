# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Política de reconexión de TikTok: qué hace el bucle tras cada sesión.

Es puro: no importa wx, asyncio ni TikTokLive. Solo decide si el bucle
sigue reintentando (devuelve None) o termina (devuelve una tupla
`(tipo, texto)`), y arma los textos de reintento. El orden de las
decisiones es el contrato: el mismo del bucle de `capturar_con_reconexion`.
"""

from guyrapu.capture.tiktok_errores import (CLASES_OFFLINE, ESPERA_LIMITE,
    es_error_permanente, es_limite, es_sala_no_lista, mensaje_error, nombre)
from guyrapu.core.idioma import N_, _

# Cuánto se espera a que TikTok dé los datos de una sala recién abierta,
# desde el primer fallo por ese motivo, en segundos.
LIMITE_SALA_NO_LISTA = 180

# Traductores: estado que se anuncia y se muestra en la barra de estado.
_TEXTO_SALA_NO_LISTA_ESPERA = N_(
    "TikTok todavía no deja leer el chat de este directo. Se sigue intentando.")

# Traductores: error que se anuncia y se muestra en la barra de estado.
_TEXTO_SALA_NO_LISTA_AGOTADA = N_(
    "TikTok no deja leer el chat de este directo. Puede estar restringido por edad.")


def sala_no_lista(err, *, conecto_alguna, primer_fallo, ahora):
    """Qué hacer ante un fallo de sala restringida.

    Devuelve None cuando se decide como siempre (el chat ya conectó alguna
    vez, u otro error). Si no, `(tipo, texto)`: «reintentando» con la frase
    la primera vez, «reintentando» con None en las siguientes (se espera
    sin anunciar), o «error» con el texto de la edad si ya pasó el límite.
    `primer_fallo` es la hora del primer fallo de sala, o None si es este."""
    if conecto_alguna or not es_sala_no_lista(err):
        return None
    if primer_fallo is None:
        return ("reintentando", _(_TEXTO_SALA_NO_LISTA_ESPERA))
    if ahora - primer_fallo >= LIMITE_SALA_NO_LISTA:
        return ("error", _(_TEXTO_SALA_NO_LISTA_AGOTADA))
    return ("reintentando", None)


# Texto del estado permanente cuando la TikTokLive instalada no trae lo que
# la captura necesita (llega a la GUI por on_estado como los demás estados).
# Traductores: error permanente que se anuncia y se muestra en la barra de estado.
_TEXTO_VERSION_INCOMPATIBLE = N_(
    "La versión instalada de TikTokLive no es compatible con la aplicación.")


def desenlace(err, *, parado, conecto_alguna, offline_pasajero, reconectar):
    """Qué hace el bucle tras una sesión. None para seguir; si termina,
    `(tipo, texto)` con el estado a anunciar, o tipo None para salir
    callado (la parada pedida). `conecto_alguna` dice si conectó alguna
    vez (el reinicio de intentos lo hace el bucle antes de llamar)."""
    if isinstance(err, (ImportError, AttributeError)):
        # Preparación imposible con esta versión de la librería: no vale
        # la pena reintentar, se avisa una vez y se termina.
        return ("error_permanente", _(_TEXTO_VERSION_INCOMPATIBLE))
    if parado:
        return (None, "")
    if err is not None and es_error_permanente(err) and not (
            offline_pasajero and nombre(err) in CLASES_OFFLINE
            and not conecto_alguna):
        return ("error_permanente", mensaje_error(err))
    if err is None:
        # Conexión que terminó sola (fin del directo): no reintentamos.
        # Suena «fin_directo», no «desconectado» (ese sigue para YouTube
        # y el resto de los cortes).
        # Traductores: estado final que se anuncia y se muestra en la barra de estado.
        return ("fin_directo", _("El directo de TikTok terminó."))
    if not reconectar:
        return ("error", mensaje_error(err))
    return None


def paso_tras_sesion(err, *, parado, conecto_alguna, offline_pasajero,
                     reconectar, intentos, maximo, primer_fallo, ahora,
                     espera):
    """Qué hace el bucle tras una sesión, en un solo paso puro.

    Devuelve `(accion, estado, espera, intentos, primer_fallo)`. La acción
    es «parar» (con `estado` si hay algo que anunciar), «esperar» (la espera
    por sala restringida, que no cuenta el intento) o «reintentar» (el
    reintento de siempre, con el intento ya contado)."""
    fin = desenlace(err, parado=parado, conecto_alguna=conecto_alguna,
                    offline_pasajero=offline_pasajero, reconectar=reconectar)
    if fin is not None:
        return ("parar", fin if fin[0] is not None else None, 0, intentos,
                primer_fallo)
    sala = sala_no_lista(err, conecto_alguna=conecto_alguna,
                         primer_fallo=primer_fallo, ahora=ahora)
    if sala is None:
        return _reintento(err, intentos, maximo, primer_fallo, espera)
    primer_fallo = primer_fallo if primer_fallo is not None else ahora
    if sala[0] == "error":
        return ("parar", sala, 0, intentos, primer_fallo)
    return ("esperar", sala if sala[1] is not None else None, espera,
            intentos, primer_fallo)


def _reintento(err, intentos, maximo, primer_fallo, espera):
    """El reintento de siempre: cuenta el intento, y si se agotaron, termina."""
    intentos += 1
    if maximo > 0 and intentos >= maximo:
        return ("parar", ("error", texto_agotado(maximo)), 0, intentos,
                primer_fallo)
    espera = espera_tras(err, espera)
    return ("reintentar",
            ("reintentando", texto_reintento(espera, intentos, maximo)),
            espera, intentos, primer_fallo)


def espera_tras(err, espera) -> int:
    """Espera antes del próximo intento. Con el límite de TikTok se espera
    lo que dura el bloqueo, nunca menos de lo ya configurado."""
    if err is not None and es_limite(err):
        return max(espera, ESPERA_LIMITE)
    return espera


def texto_agotado(maximo):
    """Texto cuando se acaban los intentos de reconexión, ya formateado."""
    # Traductores: error que se anuncia y se muestra en la barra de estado. {intentos} es cuántos intentos se hicieron.
    return _("Se agotaron los {intentos} intentos de reconexión.").format(
        intentos=maximo)


def texto_reintento(segundos, intento, maximo):
    """Texto del estado «reintentando», ya formateado. Con máximo 0 sale la
    frase sin «de {maximo}»."""
    if maximo:
        # Traductores: estado que se anuncia y se muestra en la barra de estado. {segundos} es la espera, {intento} el intento actual y {maximo} el máximo.
        return _("Reintentando en {segundos} segundos (intento {intento} de {maximo})…").format(
            segundos=segundos, intento=intento, maximo=maximo)
    # Traductores: estado que se anuncia y se muestra en la barra de estado. {segundos} es la espera y {intento} el intento actual.
    return _("Reintentando en {segundos} segundos (intento {intento})…").format(
        segundos=segundos, intento=intento)
