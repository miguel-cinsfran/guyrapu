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
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

from qa.nvda.reglas import identidad

TOPE_PASOS = 40


class InstrumentoRoto(RuntimeError):
    """La ventana no tomó el foco o el primer plano es de otro proceso."""


def _comprobar_primer_plano(cliente, pid) -> None:
    respuesta = cliente.foco_completo()
    plano = respuesta.get("primer_plano") or {}
    if int(plano.get("pid") or 0) != int(pid):
        raise InstrumentoRoto(
            f"tomó el primer plano «{plano.get('nombre')}» "
            f"(proceso {plano.get('pid')})")


def _ms_hasta_la_ultima_habla(hora, habla):
    if hora is None or not habla:
        return None
    ultima = max(float(evento.get("hora") or 0) for evento in habla)
    return max(0, round((ultima - float(hora)) * 1000))


def _paso(cliente, tecla, fase, pid) -> dict:
    _comprobar_primer_plano(cliente, pid)
    datos = cliente.paso(tecla)
    eventos = datos.get("eventos") or []
    habla = [evento for evento in eventos if evento.get("tipo") == "habla"]
    return {
        "tecla": tecla,
        "fase": fase,
        "habla": habla,
        "foco": datos.get("foco") or {},
        "agotado": bool(datos.get("agotado")),
        "ms_habla": _ms_hasta_la_ultima_habla(datos.get("hora"), habla),
    }


def _esperar_foco(cliente, nombre, tope_s, dormir) -> dict:
    limite = time.monotonic() + tope_s
    foco = {}
    while time.monotonic() < limite:
        foco = cliente.foco_completo().get("foco") or {}
        if foco.get("nombre") == nombre:
            return foco
        dormir(0.05)
    nombre_visto = foco.get("nombre") or "sin nombre"
    rol_visto = foco.get("rol_nombre") or foco.get("rol") or "sin rol"
    visto = f"«{nombre_visto}», rol {rol_visto}"
    if foco.get("padre"):
        visto += f", padre «{foco['padre']}»"
    raise InstrumentoRoto(
        f"la ventana no puso el foco en «{nombre}»: "
        f"el último foco fue {visto}")


def _ir_a(cliente, nombre, pid, tope) -> None:
    for _ in range(tope):
        foco = cliente.foco_completo().get("foco") or {}
        if foco.get("nombre") == nombre:
            return
        _paso(cliente, "tab", "navegacion", pid)
    foco = cliente.foco_completo().get("foco") or {}
    if foco.get("nombre") != nombre:
        raise InstrumentoRoto(f"no se llegó con Tab a «{nombre}»")


def conducir(cliente, ventana, tope=TOPE_PASOS, tope_foco_s=20.0,
             dormir=time.sleep) -> dict:
    """La ida, la vuelta y las acciones de una ventana ya abierta."""
    pid = int(ventana["pid"])
    primero = _esperar_foco(cliente, ventana["primero"], tope_foco_s, dormir)
    pasos = []
    identidad_primera = identidad(primero)
    for _ in range(tope):
        paso = _paso(cliente, "tab", "ida", pid)
        pasos.append(paso)
        if identidad(paso["foco"]) == identidad_primera:
            break
    for _ in range(tope):
        paso = _paso(cliente, "shift+tab", "vuelta", pid)
        pasos.append(paso)
        if identidad(paso["foco"]) == identidad_primera:
            break
    for accion in ventana.get("acciones") or ():
        _ir_a(cliente, accion["control"], pid, tope)
        pasos.append(_paso(cliente, accion.get("gesto", "space"),
                           "accion", pid))
    return {
        "ventana": ventana.get("nombre") or ventana.get("titulo"),
        "pid": pid,
        "primero": primero,
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
