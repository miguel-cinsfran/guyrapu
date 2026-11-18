# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se describe un disparador en la lista y al escucharlo.

Puro y sin wx. Única razón para cambiar: las palabras con que la app cuenta
un disparador guardado.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.interaction.disparadores import NOMBRES_EVENTOS, Disparador


def _con_signo(nombre: str) -> str:
    return f"!{nombre}" if nombre else ""


def _numero(valor) -> str:
    numero = float(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:g}"


def _cuando(disparador: Disparador) -> str:
    if disparador.cuando == "atajo":
        return _("con Ctrl+Alt+Mayús+{numero}").format(
            numero=disparador.atajo)
    if disparador.cuando == "evento":
        if disparador.evento == "superchat" and disparador.regalo:
            nombre = _("el regalo {regalo}").format(regalo=disparador.regalo)
        else:
            nombre = _(NOMBRES_EVENTOS.get(disparador.evento, ""))
        if disparador.minimo is None:
            return _("cuando llega {evento}").format(evento=nombre)
        return _("cuando llega {evento} desde {minimo}").format(
            evento=nombre, minimo=_numero(disparador.minimo))
    nombres = ", ".join(_con_signo(nombre)
                        for nombre in disparador.comandos)
    return _("cuando alguien escribe {comandos}").format(comandos=nombres)


def _que(disparador: Disparador) -> str:
    medio = (disparador.medio or "").strip()
    tarjeta = (disparador.tarjeta or "").strip()
    if medio and tarjeta:
        return _("muestra el medio {medio} y la tarjeta «{tarjeta}»").format(
            medio=medio, tarjeta=tarjeta)
    if medio:
        return _("muestra el medio {medio}").format(medio=medio)
    return _("muestra la tarjeta «{tarjeta}»").format(tarjeta=tarjeta)


def fila(disparador: Disparador) -> str:
    """La línea de la lista: nombre, cuándo y si está en pausa."""
    partes = [disparador.nombre, _cuando(disparador)]
    if not disparador.activo:
        partes.append(_("pausado"))
    return ", ".join(partes)


def escuchar(disparador: Disparador) -> str:
    """La frase que cuenta un disparador entero al pedir Escuchar."""
    frase = _("{nombre}: {cuando}, {que}.").format(
        nombre=disparador.nombre, cuando=_cuando(disparador),
        que=_que(disparador))
    if not disparador.activo:
        frase += " " + _("En pausa.")
    return frase
