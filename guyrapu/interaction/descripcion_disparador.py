# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se describe un disparador en la lista y al escucharlo.

Puro y sin wx. Única razón para cambiar: las palabras con que la app cuenta
un disparador guardado.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.interaction import descripcion_comando
from guyrapu.interaction.disparadores import NOMBRES_EVENTOS, Disparador


def _numero(valor) -> str:
    numero = float(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:g}"


def _cuando(disparador: Disparador) -> str:
    if not disparador.evento:
        return _("sin evento")
    if disparador.evento == "superchat" and disparador.regalo:
        nombre = _("el regalo {regalo}").format(regalo=disparador.regalo)
    else:
        nombre = _(NOMBRES_EVENTOS.get(disparador.evento, ""))
    if disparador.minimo is None:
        return _("cuando llega {evento}").format(evento=nombre)
    return _("cuando llega {evento} desde {minimo}").format(
        evento=nombre, minimo=_numero(disparador.minimo))


def medio(nombre) -> str:
    """Cómo se nombra un medio al describir lo que sale."""
    nombre = (nombre or "").strip()
    # Traductores: descripción de lo que sale. {medio} es el nombre del medio.
    return _("muestra el medio {medio}").format(medio=nombre) if nombre else ""


def _que(disparador: Disparador) -> str:
    medio_elegido = (disparador.medio or "").strip()
    tarjeta = (disparador.tarjeta or "").strip()
    if medio_elegido and tarjeta:
        return _("muestra el medio {medio} y la tarjeta «{tarjeta}»").format(
            medio=medio_elegido, tarjeta=tarjeta)
    if medio_elegido:
        return medio(medio_elegido)
    return _("muestra la tarjeta «{tarjeta}»").format(tarjeta=tarjeta)


def fila(disparador: Disparador) -> str:
    """La línea de la lista: nombre, cuándo, dónde sale y si está en pausa."""
    partes = [disparador.nombre, _cuando(disparador),
              descripcion_comando.destino(disparador.destino)]
    if not disparador.activo:
        partes.append(_("pausado"))
    return ", ".join(partes)


def escuchar(disparador: Disparador) -> str:
    """La frase que cuenta un disparador entero al pedir Escuchar."""
    frase = _("{nombre}: {cuando}, {que}.").format(
        nombre=disparador.nombre, cuando=_cuando(disparador),
        que=_que(disparador))
    # Traductores: descripción de la alerta. {destino} es en el vídeo, en el chat o en el vídeo y en el chat.
    frase += " " + _("Se muestra {destino}.").format(
        destino=descripcion_comando.destino(disparador.destino))
    if not disparador.activo:
        frase += " " + _("En pausa.")
    return frase
