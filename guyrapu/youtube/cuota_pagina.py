# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Tabla de costos de la API de YouTube que publica Google.

Su única razón para cambiar es cómo se lee y se guarda esa tabla. La app la
intenta refrescar una vez por semana, en segundo plano: si la lectura cuadra
con los métodos que conoce, la usa; si no, sigue con la tabla del código.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import urllib.request

from guyrapu.core import archivos, diagnostico, paths

logger = diagnostico.obtener_logger(__name__)

PAGINA = "https://developers.google.com/youtube/v3/determine_quota_cost?hl=en"

# Medido el 15/11/2026: cada fila es <tr> con el recurso en un <h3> solo en
# su primera fila, el método en el segundo <td> y el costo en «quota-cost».
FILA = re.compile(r"<tr>(.*?)</tr>", re.S)
RECURSO = re.compile(r'<h3 id="([^"]+)"')
CELDA = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
COSTO = re.compile(r'<td class="quota-cost">\s*(\d+)\s*</td>')
# El \b inicial no cambia la búsqueda: evita que el inventario de textos lea
# la expresión como una frase para el usuario.
FECHA = re.compile(r"\bLast updated (\d{4})-(\d{2})-(\d{2})")

DIAS_ENTRE_LECTURAS = 7
SEGUNDOS_DESCARGA = 15


def tabla_de_la_pagina(texto):
    """{«recurso.método»: costo} y la fecha en dd/mm/aaaa, de la página."""
    costos, recurso = {}, None
    for fila in FILA.findall(texto):
        encontrado = RECURSO.search(fila)
        if encontrado:
            recurso = encontrado.group(1)
        costo = COSTO.search(fila)
        celdas = CELDA.findall(fila)
        if recurso and costo and len(celdas) >= 2:
            metodo = html.unescape(re.sub(r"<[^>]+>", "", celdas[1])).strip()
            costos[f"{recurso}.{metodo}"] = int(costo.group(1))
    fecha = FECHA.search(texto)
    return costos, (f"{fecha.group(3)}/{fecha.group(2)}/{fecha.group(1)}"
                    if fecha else "")


def cuadra(costos, fecha, metodos) -> bool:
    """Dice si la lectura trae fecha y un costo para cada método conocido."""
    if not fecha:
        return False
    return all(isinstance(costos.get(metodo), int) for metodo in metodos)


def toca_leer(guardado, ahora) -> bool:
    """Dice si la última lectura buena tiene más de una semana o no existe."""
    if not isinstance(guardado, dict):
        return True
    try:
        leida = dt.date.fromisoformat(guardado.get("leida", ""))
    except (TypeError, ValueError):
        return True
    return (ahora - leida).days > DIAS_ENTRE_LECTURAS


def leer_guardado():
    """El último guardado válido, o None si falta o está roto."""
    datos = archivos.leer_json(paths.cuota_youtube_pagina(), None)
    if not isinstance(datos, dict) or not isinstance(datos.get("costos"), dict):
        return None
    return datos


def descargar(url, segundos=SEGUNDOS_DESCARGA) -> str:
    """El texto de `url`; lanza si no responde dentro de `segundos`."""
    pedido = urllib.request.Request(url, headers={"User-Agent": "guyrapu"})
    with urllib.request.urlopen(pedido, timeout=segundos) as respuesta:
        return respuesta.read().decode("utf-8", "replace")


def actualizar_en_segundo_plano():
    """Lee la página en un hilo si toca; la ventana no espera esa lectura."""
    if not toca_leer(leer_guardado(), dt.date.today()):
        return None
    hilo = diagnostico.crear_hilo(_actualizar, "CuotaDeYouTube")
    hilo.start()
    return hilo


def _actualizar():
    """Reemplaza el guardado si la lectura cuadra; nunca lanza."""
    from guyrapu.youtube import cuota
    try:
        costos, fecha = tabla_de_la_pagina(descargar(PAGINA))
        if not cuadra(costos, fecha, cuota.COSTOS):
            logger.warning(
                "La tabla de costos de Google no cuadra con la de la app: "
                "se sigue con la tabla del código.")
            return
        archivos.escribir_json_atomico(
            paths.cuota_youtube_pagina(),
            {"fecha": fecha, "leida": dt.date.today().isoformat(),
             "costos": costos})
    except Exception as exc:
        logger.warning(
            "No se pudo leer la tabla de costos de Google: %s", exc)
