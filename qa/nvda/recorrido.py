# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se conduce una ventana del carril y se juntan sus paradas.

Abre la ventana en un proceso aparte, espera el foco en su primer control,
hace la ida con Tab hasta volver a la primera parada o llegar al tope, la
vuelta con Mayús+Tab igual, y después cada acción: llega con Tab al control
nombrado y manda el gesto.

Antes de cada tecla se comprueba que la ventana en primer plano sea del
proceso recorrido. Si la tomó otra, es instrumento roto, nunca un hallazgo
de la app.

Antes de la primera tecla se espera a que NVDA calle, y lo dicho en esa
espera se descarta para que dos corridas den la misma transcripción.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

from qa import foco_ventanas
from qa.nvda.reglas import identidad

TOPE_PASOS = 40
VAR_SONIDOS = "GUYRAPU_QA_SONIDOS"
INTERVALO_SILENCIO_S = 0.2
SILENCIO_S = 0.8
TOPE_SILENCIO_S = 8.0


class InstrumentoRoto(RuntimeError):
    """La ventana no tomó el foco o el primer plano es de otro proceso."""


class Sonidos:
    """Los sonidos nuevos del archivo que escribe la sonda del carril."""

    def __init__(self, ruta):
        self._ruta = Path(ruta) if ruta else None
        self._pos = 0

    def nuevos(self):
        if not self._ruta:
            return []
        try:
            with open(self._ruta, encoding="utf-8") as archivo:
                archivo.seek(self._pos)
                lineas = archivo.read().splitlines()
                self._pos = archivo.tell()
        except OSError:
            return []
        return [linea.strip() for linea in lineas if linea.strip()]


def _comprobar_primer_plano(cliente, pid) -> None:
    respuesta = cliente.foco_completo()
    plano = respuesta.get("primer_plano") or {}
    if not foco_ventanas.es_proceso_o_descendiente(plano.get("pid"), pid):
        raise InstrumentoRoto(
            f"tomó el primer plano «{plano.get('nombre')}» "
            f"(proceso {plano.get('pid')})")


def _ms_hasta_la_ultima_habla(hora, habla):
    if hora is None or not habla:
        return None
    ultima = max(float(evento.get("hora") or 0) for evento in habla)
    return max(0, round((ultima - float(hora)) * 1000))


def _paso(cliente, tecla, fase, pid, lector=None) -> dict:
    _comprobar_primer_plano(cliente, pid)
    datos = cliente.paso(tecla)
    eventos = datos.get("eventos") or []
    habla = [evento for evento in eventos if evento.get("tipo") == "habla"]
    paso = {
        "tecla": tecla,
        "fase": fase,
        "habla": habla,
        "foco": datos.get("foco") or {},
        "agotado": bool(datos.get("agotado")),
        "ms_habla": _ms_hasta_la_ultima_habla(datos.get("hora"), habla),
    }
    if lector is not None:
        paso["sonidos"] = lector.nuevos()
    return paso


def _es_primero(foco, nombre, lista) -> bool:
    """El foco esperado, o una fila de la lista declarada como primero."""
    if foco.get("nombre") == nombre:
        return True
    if not lista:
        return False
    rol = str(foco.get("rol_nombre") or foco.get("rol") or "")
    return rol.casefold() == "listitem" and foco.get("padre") == lista


def _cierra_ciclo(foco, primero, nombre, lista) -> bool:
    """El mismo control por identidad, o una fila de la lista declarada."""
    if identidad(foco) == identidad(primero):
        return True
    if not lista:
        return False
    return _es_primero(foco, nombre, lista)


def _esperar_foco(cliente, nombre, tope_s, dormir, lista=None) -> dict:
    limite = time.monotonic() + tope_s
    foco = {}
    while time.monotonic() < limite:
        foco = cliente.foco_completo().get("foco") or {}
        if _es_primero(foco, nombre, lista):
            return foco
        dormir(0.05)
    raise InstrumentoRoto(
        f"la ventana no puso el foco en {nombre!r}: el último foco fue "
        f"nombre={foco.get('nombre')!r}, rol={foco.get('rol')!r}, "
        f"rol_nombre={foco.get('rol_nombre')!r}, "
        f"padre={foco.get('padre')!r}")


def _ir_a(cliente, nombre, pid, tope, lector=None) -> None:
    for _ in range(tope):
        foco = cliente.foco_completo().get("foco") or {}
        if foco.get("nombre") == nombre:
            return
        _paso(cliente, "tab", "navegacion", pid, lector)
    foco = cliente.foco_completo().get("foco") or {}
    if foco.get("nombre") != nombre:
        raise InstrumentoRoto(f"no se llegó con Tab a «{nombre}»")


def _foco_de(cliente) -> dict:
    return cliente.foco_completo().get("foco") or {}


def _elegir_pagina(cliente, ventana, pid, tope, lector=None) -> list:
    """Va con Shift+Tab a la lista de páginas y elige la pedida con flechas.

    La lista de un `wx.Listbook` se maneja con las flechas; entrar a la página
    con Tab es lo que hace un usuario, no elegirla por código.
    """
    pagina = ventana["pagina"]
    paginas = list(ventana.get("paginas") or ())
    if pagina not in paginas:
        raise InstrumentoRoto(f"la lista de páginas no tiene «{pagina}»")
    pasos = []
    for _ in range(tope):
        if _foco_de(cliente).get("nombre") in paginas:
            break
        pasos.append(_paso(cliente, "shift+tab", "pagina", pid, lector))
    else:
        raise InstrumentoRoto(
            f"no se llegó a la lista de páginas para «{pagina}»")
    actual = paginas.index(_foco_de(cliente).get("nombre"))
    destino = paginas.index(pagina)
    tecla = "downArrow" if destino > actual else "upArrow"
    for _ in range(abs(destino - actual)):
        pasos.append(_paso(cliente, tecla, "pagina", pid, lector))
    if _foco_de(cliente).get("nombre") != pagina:
        raise InstrumentoRoto(f"la lista de páginas no llegó a «{pagina}»")
    pasos.append(_paso(cliente, "tab", "pagina", pid, lector))
    return pasos


def _pasos_de_pagina(cliente, ventana, pid, tope, lector=None) -> list:
    """Los pasos de elegir la página, o ninguno si no lleva una."""
    if not ventana.get("pagina"):
        return []
    return _elegir_pagina(cliente, ventana, pid, tope, lector)


def _esperar_silencio(cliente, dormir, intervalo_s=INTERVALO_SILENCIO_S,
                      silencio_s=SILENCIO_S, tope_s=TOPE_SILENCIO_S) -> None:
    """Deja que NVDA termine de hablar antes de la primera tecla.

    Lo dicho en esta espera no se guarda: el primer paso toma su marca
    después, así que no hereda el habla con que se abrió la ventana.
    """
    indice = cliente.marca()
    tope = max(1, round(tope_s / intervalo_s))
    silencio = max(1, round(silencio_s / intervalo_s))
    quietos = 0
    for _ in range(tope):
        dormir(intervalo_s)
        if any(evento.get("tipo") == "habla"
               for evento in cliente.desde(indice)):
            indice = cliente.marca()
            quietos = 0
        else:
            quietos += 1
            if quietos >= silencio:
                return


def conducir(cliente, ventana, tope=TOPE_PASOS, tope_foco_s=20.0,
             dormir=time.sleep) -> dict:
    """La ida, la vuelta y las acciones de una ventana ya abierta."""
    pid = int(ventana["pid"])
    lector = Sonidos(os.environ.get(VAR_SONIDOS))
    lector.nuevos()
    _esperar_silencio(cliente, dormir)
    pasos = _pasos_de_pagina(cliente, ventana, pid, tope, lector)
    if ventana.get("pulsar"):
        _ir_a(cliente, ventana["pulsar"], pid, tope, lector)
        pasos.append(_paso(cliente, "space", "pulsar", pid, lector))
    nombre = ventana["primero"]
    lista = ventana.get("primero_lista")
    primero = _esperar_foco(cliente, nombre, tope_foco_s, dormir, lista)
    for _ in range(tope):
        paso = _paso(cliente, "tab", "ida", pid, lector)
        pasos.append(paso)
        if _cierra_ciclo(paso["foco"], primero, nombre, lista):
            break
    for _ in range(tope):
        paso = _paso(cliente, "shift+tab", "vuelta", pid, lector)
        pasos.append(paso)
        if _cierra_ciclo(paso["foco"], primero, nombre, lista):
            break
    for accion in ventana.get("acciones") or ():
        _ir_a(cliente, accion["control"], pid, tope, lector)
        espera = accion.get("espera")
        marca = cliente.marca() if espera else None
        paso = _paso(cliente, accion.get("gesto", "space"), "accion", pid)
        if espera:
            respuesta = cliente.esperar_frase(
                espera, marca, float(accion.get("plazo_s", 5.0)))
            paso["espera"] = espera
            paso["oida"] = respuesta["oida"]
            paso["espera_dicho"] = " ".join(
                str(evento.get("texto") or "")
                for evento in respuesta["eventos"]
                if evento.get("tipo") == "habla").strip()
        paso["sonidos"] = lector.nuevos()
        pasos.append(paso)
    return {
        "ventana": ventana.get("nombre") or ventana.get("titulo"),
        "pid": pid,
        "primero": primero,
        "primero_lista": lista,
        "pasos": pasos,
    }


def cerrar(cliente, pid) -> None:
    """Cierra la ventana con Alt+F4, comprobando antes el primer plano."""
    _comprobar_primer_plano(cliente, pid)
    cliente.tecla("alt+f4")


def _esperar_proceso(proceso) -> None:
    try:
        proceso.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(timeout=5)


def _esperar_pid(ruta, tope_s, dormir) -> int:
    limite = time.monotonic() + tope_s
    while time.monotonic() < limite:
        try:
            texto = Path(ruta).read_text(encoding="utf-8").strip()
        except OSError:
            texto = ""
        if texto.isdigit():
            return int(texto)
        dormir(0.05)
    raise InstrumentoRoto(f"la ventana no escribió su pid en {ruta} a tiempo")


def recorrer(ventana, cliente, tope=TOPE_PASOS, tope_foco_s=20.0,
             tope_pid_s=20.0, dormir=time.sleep) -> dict:
    """Abre la ventana en otro proceso, la conduce y la cierra."""
    with tempfile.TemporaryDirectory() as base:
        ruta_pid = Path(base) / "ventana.pid"
        comando = list(ventana["comando"]) + ["--pid-file", str(ruta_pid)]
        proceso = subprocess.Popen(comando)
        try:
            pid = _esperar_pid(ruta_pid, tope_pid_s, dormir)
            datos = conducir(cliente, {**ventana, "pid": pid},
                             tope, tope_foco_s, dormir)
            cerrar(cliente, pid)
            _esperar_proceso(proceso)
            return datos
        except Exception:
            proceso.kill()
            proceso.wait(timeout=5)
            raise
