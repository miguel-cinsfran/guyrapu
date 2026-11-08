# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las salidas de audio que ofrece OBS para el dispositivo de monitoreo.

Los dispositivos no se listan por una consulta propia: se toman de las
propiedades de la entrada de audio del escritorio (`wasapi_output_capture`),
con el mismo identificador que usa el monitoreo del perfil. Sin esa entrada,
OBS solo ofrece el predeterminado del sistema.
"""

from __future__ import annotations

from guyrapu.core.idioma import N_, _

TIPO_SALIDA = "wasapi_output_capture"
NOMBRE_POR_DEFECTO = N_("Por defecto")
VALOR_POR_DEFECTO = "default"


def _datos(cliente, tipo, datos=None, parada=None):
    respuesta = cliente.pedir(tipo, datos, parada=parada)
    return (respuesta or {}).get("responseData", respuesta or {})


def _entrada_de_salida(cliente, parada):
    entradas = _datos(cliente, "GetInputList", parada=parada).get("inputs", ())
    return next((entrada for entrada in entradas
                 if entrada.get("inputKind") == TIPO_SALIDA
                 and entrada.get("inputName")), None)


def salidas(cliente, parada=None) -> tuple:
    """Pares (nombre, valor) de las salidas, con el predeterminado primero."""
    entrada = _entrada_de_salida(cliente, parada)
    if entrada is None:
        return ((_(NOMBRE_POR_DEFECTO), VALOR_POR_DEFECTO),)
    items = _datos(
        cliente, "GetInputPropertiesListPropertyItems",
        {"inputName": entrada["inputName"], "propertyName": "device_id"},
        parada).get("propertyItems", ())
    pares = tuple((str(item.get("itemName", "")), str(item.get("itemValue", "")))
                  for item in items if item.get("itemName"))
    return pares or ((_(NOMBRE_POR_DEFECTO), VALOR_POR_DEFECTO),)
