# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Anima tarjetas en OBS desde un proceso propio, sin la carga de la app.

Su única razón para cambiar es cómo se reproducen los cuadros fuera del
proceso de la app. No calcula curvas: los cuadros llegan armados desde
`interaction/animacion.py`, y acá solo se mandan a OBS en su instante.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import threading
import time
from multiprocessing.connection import Client, Listener

from guyrapu.core import paths
from guyrapu.obs import obs_cliente


VARIABLE_CLAVE = "GUYRAPU_CLAVE_ANIMADOR"


def reproducir(cliente, orden, reloj=time.perf_counter, dormir=time.sleep):
    """Manda los cuadros a OBS en su instante y saltea los que ya vencieron."""
    cuadros = list(orden.get("cuadros") or ())
    if not cuadros:
        return
    inicio = reloj()
    posicion = None
    opacidad = None
    indice = 0
    while indice < len(cuadros):
        instante = inicio + cuadros[indice][0] / 1000.0
        ahora = reloj()
        if instante > ahora:
            dormir(instante - ahora)
            ahora = reloj()
        elegido = indice
        while (elegido + 1 < len(cuadros)
               and inicio + cuadros[elegido + 1][0] / 1000.0 <= ahora):
            elegido += 1
        _sin_uso, dx, dy, nueva_opacidad = cuadros[elegido]
        nueva_posicion = (orden["x"] + dx, orden["y"] + dy)
        if nueva_posicion != posicion:
            cliente.pedir("SetSceneItemTransform", {
                "sceneName": orden["escena"],
                "sceneItemId": orden["elemento"],
                "sceneItemTransform": {
                    "positionX": nueva_posicion[0],
                    "positionY": nueva_posicion[1],
                },
            })
            posicion = nueva_posicion
        if nueva_opacidad != opacidad:
            cliente.pedir("SetSourceFilterSettings", {
                "sourceName": orden["fuente_filtro"],
                "filterName": orden["filtro"],
                "filterSettings": {"opacity": nueva_opacidad},
            })
            opacidad = nueva_opacidad
        indice = elegido + 1


def _nuevo_cliente():
    return obs_cliente.ClienteObs(obs_cliente.leer_ajustes())


def _cerrar(cliente):
    try:
        cliente.cerrar()
    except OSError:
        pass


def atender(conexion, cliente_fn=None):
    """Atiende una orden por vez y contesta en el mismo orden."""
    if cliente_fn is None:
        cliente_fn = _nuevo_cliente
    cliente = None
    try:
        while True:
            try:
                orden = conexion.recv()
            except (EOFError, OSError):
                return
            if orden.get("tipo") == "eco":
                respuesta = {"ok": True}
            else:
                try:
                    if cliente is None:
                        cliente = cliente_fn()
                        cliente.conectar()
                    reproducir(cliente, orden)
                except Exception as error:
                    respuesta = {"ok": False, "error": str(error)}
                    if cliente is not None:
                        _cerrar(cliente)
                        cliente = None
                else:
                    respuesta = {"ok": True}
            try:
                conexion.send(respuesta)
            except (EOFError, OSError):
                return
    finally:
        if cliente is not None:
            _cerrar(cliente)


def principal(argumentos):
    """Entra al canal que le pasa la app y reproduce sus órdenes."""
    if not argumentos:
        return 1
    clave = os.environ.get(VARIABLE_CLAVE, "")
    if not clave:
        return 1
    try:
        conexion = Client(argumentos[0], authkey=clave.encode("utf-8"))
    except OSError:
        return 1
    with conexion:
        atender(conexion)
    return 0


class Animador:
    """El lado de la app: arranca el proceso, manda órdenes y espera."""

    def __init__(self):
        self._listener = None
        self._conexion = None
        self._proceso = None

    def animar(self, orden, tope):
        """Reproduce una orden en el proceso y dice si salió bien."""
        inicio = time.monotonic()
        try:
            if not self._vivo():
                self._arrancar(tope)
        except OSError:
            self._descartar()
            return False
        conexion = self._conexion
        if conexion is None:
            self._descartar()
            return False
        try:
            conexion.send(orden)
            restante = max(0.0, tope - (time.monotonic() - inicio))
            if not conexion.poll(restante):
                self._descartar()
                return False
            respuesta = conexion.recv()
        except (EOFError, OSError):
            self._descartar()
            return False
        return bool(respuesta.get("ok"))

    def cerrar(self):
        self._descartar()

    def _vivo(self):
        return (self._proceso is not None and self._proceso.poll() is None
                and self._conexion is not None)

    def _arrancar(self, tope):
        self._descartar()
        clave = secrets.token_hex(32)
        self._listener = Listener(authkey=clave.encode("utf-8"))
        entorno = dict(os.environ)
        entorno[VARIABLE_CLAVE] = clave
        self._proceso = subprocess.Popen(
            paths.orden_de_la_app() + ["--animador", self._listener.address],
            env=entorno,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self._conexion = self._aceptar(tope)

    def _aceptar(self, tope):
        listener = self._listener
        resultado = {}

        def aceptar():
            try:
                resultado["conexion"] = listener.accept()
            except OSError as error:
                resultado["error"] = error

        hilo = threading.Thread(target=aceptar, daemon=True)
        hilo.start()
        hilo.join(tope)
        if hilo.is_alive():
            return None
        return resultado.get("conexion")

    def _descartar(self):
        conexion, self._conexion = self._conexion, None
        listener, self._listener = self._listener, None
        proceso, self._proceso = self._proceso, None
        if conexion is not None:
            try:
                conexion.close()
            except OSError:
                pass
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        if proceso is not None and proceso.poll() is None:
            proceso.terminate()
            try:
                proceso.wait(5)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait()
