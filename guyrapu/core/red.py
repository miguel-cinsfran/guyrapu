# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo la app habla HTTP, en un solo lugar.

Es el único módulo de `guyrapu/` que importa `urllib.request`: arma los
pedidos HTTP de la app y descarga por bloques con aviso de progreso y
función de cancelación.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

from guyrapu.core.config import USER_AGENT


TIEMPO_ESPERA = 30


class DescargaCancelada(Exception):
    pass


def descargar_archivo(url: str, destino: Path, aviso=None, cancelar=None,
                      cabeceras=None) -> None:
    encabezados = {"User-Agent": USER_AGENT}
    if cabeceras:
        encabezados.update(cabeceras)
    solicitud = Request(url, headers=encabezados)
    with urlopen(solicitud, timeout=TIEMPO_ESPERA) as respuesta:
        total = None
        try:
            total = int(respuesta.headers.get("Content-Length"))
        except (AttributeError, TypeError, ValueError):
            pass
        descargado = 0
        with destino.open("wb") as archivo:
            while True:
                if cancelar is not None and cancelar():
                    raise DescargaCancelada
                bloque = respuesta.read(1024 * 1024)
                if not bloque:
                    break
                archivo.write(bloque)
                descargado += len(bloque)
                if aviso is not None:
                    if total:
                        aviso(min(100, max(0, int(descargado * 100 / total))))
                    else:
                        aviso(None)


def abrir_pedido(url: str, cabeceras=None, tiempo: float = TIEMPO_ESPERA,
                 abrir=None, datos: bytes | None = None,
                 metodo: str | None = None):
    abrir = abrir or urlopen
    encabezados = {"User-Agent": USER_AGENT}
    if cabeceras:
        encabezados.update(cabeceras)
    solicitud = Request(url, data=datos, headers=encabezados, method=metodo)
    return abrir(solicitud, timeout=tiempo)


def pedir(url: str, datos: bytes | None = None, cabeceras=None,
          metodo: str | None = None, tiempo: float = TIEMPO_ESPERA,
          abrir=None) -> bytes:
    with abrir_pedido(url, cabeceras=cabeceras, tiempo=tiempo, abrir=abrir,
                      datos=datos, metodo=metodo) as respuesta:
        return respuesta.read()


def pedir_texto(url: str) -> str:
    return pedir(url).decode("utf-8")


def pedir_json(url: str):
    return json.loads(pedir(url))
