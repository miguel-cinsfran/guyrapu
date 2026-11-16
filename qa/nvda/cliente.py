# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cliente del carril: habla con el complemento por 127.0.0.1.

Una orden es una línea JSON con la clave que el complemento dejó en
`carril.json`. La respuesta es otra línea JSON. El cliente no sabe nada de
NVDA: lee el estado, conecta y devuelve lo que el complemento contestó.
"""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path


class ErrorCliente(Exception):
    """El complemento no está, no contestó o rechazó la orden."""


def leer_estado(ruta) -> dict:
    """El `carril.json` que escribe el complemento al abrir el puerto."""
    try:
        with open(ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except FileNotFoundError:
        raise ErrorCliente("todavía no existe carril.json") from None
    except (OSError, ValueError) as exc:
        raise ErrorCliente(f"carril.json ilegible: {exc}") from None
    if not isinstance(datos, dict) or not {"puerto", "clave"} <= set(datos):
        raise ErrorCliente("carril.json no trae puerto y clave")
    return datos


class Cliente:

    def __init__(self, ruta_estado, espera_s=5.0):
        self._ruta = Path(ruta_estado)
        self._espera_s = espera_s
        self._estado = None

    def estado(self) -> dict:
        if self._estado is None:
            self._estado = leer_estado(self._ruta)
        return self._estado

    def _pedir(self, **orden) -> dict:
        estado = self.estado()
        pedido = dict(orden)
        pedido["clave"] = estado["clave"]
        linea = (json.dumps(pedido, ensure_ascii=False) + "\n").encode("utf-8")
        with socket.create_connection(
                ("127.0.0.1", int(estado["puerto"])),
                timeout=self._espera_s) as conexion:
            archivo = conexion.makefile("rwb")
            archivo.write(linea)
            archivo.flush()
            respuesta = archivo.readline()
        if not respuesta:
            raise ErrorCliente("el complemento cerró sin contestar")
        try:
            datos = json.loads(respuesta.decode("utf-8"))
        except ValueError as exc:
            raise ErrorCliente(f"respuesta ilegible: {exc}") from None
        if not datos.get("ok"):
            raise ErrorCliente(datos.get("error") or "orden rechazada")
        return datos

    def version(self) -> str:
        return self._pedir(orden="version")["version"]

    def marca(self) -> int:
        return int(self._pedir(orden="marca")["indice"])

    def desde(self, indice) -> list:
        return self._pedir(orden="desde", indice=int(indice))["eventos"]

    def foco(self) -> dict:
        return self._pedir(orden="foco")["foco"]

    def tecla(self, gesto, silencio_ms=400, tope_ms=10000) -> dict:
        return self._pedir(orden="tecla", gesto=gesto,
                           silencio_ms=int(silencio_ms),
                           tope_ms=int(tope_ms))

    def paso(self, gesto, silencio_ms=400, tope_ms=10000) -> dict:
        """Manda una tecla y devuelve lo dicho y el foco desde antes."""
        antes = self.marca()
        respuesta = self.tecla(gesto, silencio_ms, tope_ms)
        return {
            "tecla": gesto,
            "agotado": bool(respuesta.get("agotado")),
            "eventos": self.desde(antes),
            "foco": self.foco(),
        }


def esperar_cliente(ruta_estado, tope_s=30.0, dormir=time.sleep) -> Cliente:
    """Espera a que el complemento escriba el estado y conteste `version`."""
    limite = time.monotonic() + tope_s
    ultimo = "sin intentos"
    while time.monotonic() < limite:
        try:
            cliente = Cliente(ruta_estado)
            cliente.version()
            return cliente
        except (OSError, KeyError, ValueError, ErrorCliente) as exc:
            ultimo = str(exc)
            dormir(0.25)
    raise ErrorCliente(
        f"el complemento no respondió en {tope_s:.0f} s: {ultimo}")
