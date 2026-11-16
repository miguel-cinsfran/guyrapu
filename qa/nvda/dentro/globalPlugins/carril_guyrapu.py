# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Complemento global del carril: guarda lo que NVDA dice y atiende órdenes.

Escucha el habla, los cambios de foco, los pitidos y los sonidos, y los deja
en memoria y en `eventos.jsonl`. Abre un socket en 127.0.0.1 con una clave
de un solo uso escrita en `carril.json`. Cada orden es una línea JSON; una
sin la clave se ignora y se anota.

Lo que toca NVDA se hace en su hilo principal. Las teclas se emulan con
`emulateGesture`, como las pruebas de sistema de NV Access, y se espera a
que la cola de eventos pase un centinela y el núcleo duerma.
"""

from __future__ import annotations

import json
import secrets
import socket
import threading
import time
from pathlib import Path

import api
import config
import controlTypes
import globalPluginHandler
import inputCore
import keyboardHandler
import nvwave
import queueHandler
import tones
import versionInfo
import watchdog
from speech.extensions import pre_speech, speechCanceled

TOPE_ESPERA_MS = 10000.0


def clave_valida(pedido, clave) -> bool:
    return isinstance(pedido, dict) and pedido.get("clave") == clave


def texto_de_secuencia(secuencia) -> str:
    return " ".join(str(x) for x in secuencia
                    if isinstance(x, str) and x.strip())


def _texto(valor) -> str:
    return "" if valor is None else str(valor)


def _atributo(obj, nombre, defecto=""):
    try:
        valor = getattr(obj, nombre, defecto)
    except Exception:
        return defecto
    return defecto if valor is None else valor


def _estados_texto(role, estados) -> str:
    try:
        etiquetas = controlTypes.processAndLabelStates(
            role, estados, controlTypes.OutputReason.FOCUS, [], [])
    except Exception:
        return ""
    return ", ".join(etiquetas)


def describir_foco(obj) -> dict:
    """Los datos del objeto con foco, con el texto legible de rol y estados."""
    role = _atributo(obj, "role", None)
    estados = _atributo(obj, "states", set()) or set()
    nombres = sorted(_texto(getattr(estado, "name", estado))
                     for estado in estados)
    texto_estados = _estados_texto(role, estados)
    datos = {
        "nombre": _texto(_atributo(obj, "name")),
        "rol": _texto(role),
        "rol_texto": _texto(getattr(role, "displayString", "")),
        "rol_nombre": _texto(getattr(role, "name", "")),
        "estados": nombres,
        "estados_texto": texto_estados,
        "valor": _texto(_atributo(obj, "value")),
        "descripcion": _texto(_atributo(obj, "description")),
        "atajo": _texto(_atributo(obj, "keyboardShortcut")),
        "hwnd": int(_atributo(obj, "windowHandle", 0) or 0),
        "pid": int(_atributo(obj, "processID", 0) or 0),
    }
    datos["texto"] = ", ".join(
        parte for parte in (datos["nombre"], datos["rol_texto"],
                            texto_estados, datos["valor"],
                            datos["descripcion"], datos["atajo"]) if parte)
    return datos


class LectorEventos:
    """Guarda cada evento con índice, hora y tipo, y lo copia a un `.jsonl`."""

    def __init__(self, ruta=None, reloj=time.monotonic):
        self._ruta = Path(ruta) if ruta else None
        self._reloj = reloj
        self._inicio = reloj()
        self._ultima_habla = self._inicio
        self._eventos = []
        self._cancelado = False
        self._cerrojo = threading.Lock()

    def agregar(self, tipo, **datos) -> dict:
        with self._cerrojo:
            evento = {
                "indice": len(self._eventos),
                "hora": round(self._reloj() - self._inicio, 3),
                "tipo": tipo,
                "speechCanceled": self._cancelado,
            }
            evento.update(datos)
            self._eventos.append(evento)
            if tipo == "habla":
                self._ultima_habla = self._reloj()
            self._copiar(evento)
            return evento

    def _copiar(self, evento) -> None:
        if not self._ruta:
            return
        try:
            with open(self._ruta, "a", encoding="utf-8") as archivo:
                archivo.write(
                    json.dumps(evento, ensure_ascii=False) + "\n")
        except OSError:
            # Un fallo al escribir la copia no puede cortar el habla.
            pass

    def marcar_habla(self) -> None:
        with self._cerrojo:
            self._cancelado = False

    def marcar_cancelado(self) -> None:
        with self._cerrojo:
            self._cancelado = True

    def marca(self) -> int:
        with self._cerrojo:
            return len(self._eventos)

    def desde(self, indice) -> list:
        with self._cerrojo:
            return self._eventos[max(0, int(indice)):]

    def ultima_habla(self) -> float:
        with self._cerrojo:
            return self._ultima_habla

    def ahora(self) -> float:
        with self._cerrojo:
            return round(self._reloj() - self._inicio, 3)


class ServidorCarril:
    """Puerto local con clave para atender órdenes del cliente."""

    def __init__(self, ruta_estado, al_pedido, al_rechazo=None):
        self._al_pedido = al_pedido
        self._al_rechazo = al_rechazo
        self._cerrado = False
        self._ruta = Path(ruta_estado)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(4)
        self._socket.settimeout(0.5)
        self.puerto = self._socket.getsockname()[1]
        self.clave = secrets.token_hex(16)
        self._ruta.write_text(
            json.dumps({"puerto": self.puerto, "clave": self.clave}),
            encoding="utf-8")
        self._hilo = threading.Thread(target=self._aceptar,
                                      name="carril-socket", daemon=True)
        self._hilo.start()

    def _aceptar(self) -> None:
        while not self._cerrado:
            try:
                conexion, _ = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self._atender, args=(conexion,),
                             daemon=True).start()

    def _atender(self, conexion) -> None:
        with conexion:
            archivo = conexion.makefile("rwb")
            linea = archivo.readline()
            if not linea:
                return
            try:
                pedido = json.loads(linea.decode("utf-8"))
            except ValueError:
                pedido = None
            if not clave_valida(pedido, self.clave):
                if self._al_rechazo:
                    self._al_rechazo()
                respuesta = {"ok": False, "error": "clave inválida"}
            else:
                try:
                    respuesta = self._al_pedido(pedido)
                except Exception as exc:
                    respuesta = {"ok": False, "error": str(exc)}
            archivo.write(
                (json.dumps(respuesta, ensure_ascii=False) + "\n")
                .encode("utf-8"))
            archivo.flush()

    def cerrar(self) -> None:
        self._cerrado = True
        try:
            self._socket.close()
        except OSError:
            pass
        self._ruta.unlink(missing_ok=True)


def _enviar_gesto(nombre, resultado, listo, eventos) -> None:
    try:
        gesto = keyboardHandler.KeyboardInputGesture.fromName(nombre)
        resultado["hora"] = eventos.ahora()
        inputCore.manager.emulateGesture(gesto)
    except Exception as exc:
        resultado["error"] = str(exc)
    finally:
        queueHandler.queueFunction(queueHandler.eventQueue, listo.set)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self):
        super().__init__()
        config_dir = Path(config.WritePaths.configDir)
        self._eventos = LectorEventos(config_dir / "eventos.jsonl")
        self._servidor = ServidorCarril(
            config_dir / "carril.json", self._atender, self._rechazo)
        self._registrar()

    def terminate(self):
        self._desregistrar()
        self._servidor.cerrar()
        super().terminate()

    def _registrar(self) -> None:
        pre_speech.register(self._al_hablar)
        speechCanceled.register(self._al_cancelar)
        tones.decide_beep.register(self._al_pitar)
        nvwave.decide_playWaveFile.register(self._al_sonar)

    def _desregistrar(self) -> None:
        for extension, manejador in (
                (pre_speech, self._al_hablar),
                (speechCanceled, self._al_cancelar),
                (tones.decide_beep, self._al_pitar),
                (nvwave.decide_playWaveFile, self._al_sonar)):
            try:
                extension.unregister(manejador)
            except ValueError:
                pass

    def _al_hablar(self, speechSequence=(), **kwargs) -> None:
        self._eventos.marcar_habla()
        texto = texto_de_secuencia(speechSequence)
        if texto:
            partes = [str(x) for x in speechSequence
                      if isinstance(x, str) and x.strip()]
            self._eventos.agregar("habla", texto=texto, partes=partes)

    def _al_cancelar(self, **kwargs) -> None:
        self._eventos.marcar_cancelado()
        self._eventos.agregar("cancelado")

    def _al_pitar(self, **kwargs) -> bool:
        self._eventos.agregar(
            "pitido", hz=kwargs.get("hz"), largo_ms=kwargs.get("length"))
        return True

    def _al_sonar(self, **kwargs) -> bool:
        self._eventos.agregar(
            "sonido", archivo=str(kwargs.get("fileName") or ""))
        return True

    def event_gainFocus(self, obj, nextHandler) -> None:
        self._eventos.agregar("foco", **describir_foco(obj))
        nextHandler()

    def _rechazo(self) -> None:
        self._eventos.agregar("orden", aceptada=False)

    def _atender(self, pedido) -> dict:
        orden = pedido.get("orden")
        if orden == "version":
            return {"ok": True, "version": versionInfo.version}
        if orden == "marca":
            return {"ok": True, "indice": self._eventos.marca()}
        if orden == "desde":
            return {"ok": True,
                    "eventos": self._eventos.desde(pedido.get("indice", 0))}
        if orden == "foco":
            return self._en_principal(self._foco_actual)
        if orden == "tecla":
            return self._tecla(pedido)
        return {"ok": False, "error": "orden desconocida"}

    def _foco_actual(self) -> dict:
        plano = api.getForegroundObject()
        return {
            "ok": True,
            "foco": describir_foco(api.getFocusObject()),
            "primer_plano": {
                "pid": int(_atributo(plano, "processID", 0) or 0),
                "nombre": _texto(_atributo(plano, "name")),
            },
        }

    def _en_principal(self, funcion, tope=5.0) -> dict:
        resultado = {}
        listo = threading.Event()

        def correr():
            try:
                resultado["valor"] = funcion()
            except Exception as exc:
                resultado["error"] = str(exc)
            finally:
                listo.set()

        queueHandler.queueFunction(queueHandler.eventQueue, correr)
        if not listo.wait(tope):
            return {"ok": False, "error": "NVDA no atendió la orden"}
        if "error" in resultado:
            return {"ok": False, "error": resultado["error"]}
        return resultado["valor"]

    def _tecla(self, pedido) -> dict:
        nombre = str(pedido.get("gesto") or "tab")
        silencio = float(pedido.get("silencio_ms", 400)) / 1000.0
        tope = min(float(pedido.get("tope_ms", TOPE_ESPERA_MS)),
                   TOPE_ESPERA_MS) / 1000.0
        limite = time.monotonic() + tope
        listo = threading.Event()
        resultado = {}
        queueHandler.queueFunction(
            queueHandler.eventQueue,
            lambda: _enviar_gesto(nombre, resultado, listo, self._eventos))
        agotado = not listo.wait(tope)
        if "error" in resultado:
            return {"ok": False, "error": resultado["error"]}
        if not agotado:
            restante = max(0.0, limite - time.monotonic())
            agotado = not self._esperar_quieto(silencio, restante)
        return {"ok": True, "indice": self._eventos.marca(),
                "agotado": agotado, "hora": resultado.get("hora")}

    def _esperar_quieto(self, silencio, tope) -> bool:
        limite = time.monotonic() + tope
        while time.monotonic() < limite:
            callado = (time.monotonic()
                       - self._eventos.ultima_habla()) >= silencio
            if watchdog.isCoreAsleep() and callado:
                return True
            time.sleep(0.02)
        return False
