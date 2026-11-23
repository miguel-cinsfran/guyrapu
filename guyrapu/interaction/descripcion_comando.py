# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se describe un comando del chat en la lista y al escucharlo.

Puro y sin wx. Única razón para cambiar: las palabras con que la app cuenta
un comando guardado.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.interaction.comandos import Comando

_USUARIO_DE_EJEMPLO = "Ana"
_CONTADOR_DE_EJEMPLO = "1"


def _con_signo(nombre: str) -> str:
    return f"!{nombre}" if nombre else ""


def _nombre(comando: Comando, nombre: str) -> str:
    if comando.ubicacion == "cualquiera":
        return nombre
    return _con_signo(nombre)


def _atajo(comando: Comando) -> str:
    # Traductores: descripción del comando. {n} es el número del atajo.
    return _("Ctrl+Alt+Mayús+{n}").format(n=comando.atajo)


def destino(valor: str) -> str:
    """Las palabras con que se dice dónde se muestra algo."""
    return {"video": _("en el vídeo"), "chat": _("en el chat"),
            "ambos": _("en el vídeo y en el chat")}.get(
                valor, _("en el vídeo"))


def _quien(comando: Comando) -> str:
    if comando.permiso == "solo_atajo":
        return _("solo con el atajo")
    if comando.permiso == "moderadores":
        return _("solo moderadores")
    if comando.permiso == "lista":
        if comando.nombres:
            return _("una lista de nombres: {nombres}").format(
                nombres=", ".join(comando.nombres))
        return _("una lista de nombres")
    return _("todos")


def _numero(valor) -> str:
    numero = float(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:g}"


def fila(comando: Comando) -> str:
    """La línea de la lista: palabra, dónde sale, quién puede usarlo."""
    partes = [_nombre(comando, comando.nombre)]
    if comando.ubicacion == "cualquiera":
        partes.append(_("en cualquier parte del mensaje"))
    partes.append(destino(comando.destino))
    if comando.medio:
        partes.append(_("con el medio {medio}").format(medio=comando.medio))
    partes.append(_quien(comando))
    if comando.atajo:
        partes.append(_atajo(comando))
    if not comando.activo:
        partes.append(_("pausado"))
    return ", ".join(partes)


def respuesta_de_ejemplo(comando: Comando) -> str:
    """La respuesta del comando con los datos de ejemplo de la escucha."""
    return ((comando.respuesta or "")
            .replace("{usuario}", _USUARIO_DE_EJEMPLO)
            .replace("{contador}", _CONTADOR_DE_EJEMPLO)
            .replace("{texto}", ""))


def _partes_de_respuesta(comando: Comando) -> list[str]:
    if not (comando.respuesta or "").strip():
        return []
    return [_("Responde: {respuesta}.").format(
        respuesta=respuesta_de_ejemplo(comando))]


def _parte_del_medio(comando: Comando) -> list[str]:
    if not comando.medio:
        return []
    return [_("Muestra el medio {medio}.").format(medio=comando.medio)]


def escuchar(comando: Comando, estilo: str) -> str:
    """La frase que cuenta un comando entero al pedir Escuchar."""
    palabra = _nombre(comando, comando.nombre)
    partes = []
    if comando.alias:
        partes.append(_("Comando {palabra}, con los alias {alias}.").format(
            palabra=palabra,
            alias=", ".join(_nombre(comando, alias)
                            for alias in comando.alias)))
    else:
        partes.append(_("Comando {palabra}.").format(palabra=palabra))
    if comando.ubicacion == "cualquiera":
        partes.append(_("Responde cuando la palabra aparece en cualquier "
                        "parte del mensaje."))
    partes.extend(_partes_de_respuesta(comando))
    partes.extend(_parte_del_medio(comando))
    if comando.destino in ("video", "ambos"):
        partes.append(_("Se muestra {destino}, con el estilo {estilo} y "
                       "{segundos} segundos en pantalla.").format(
                           destino=destino(comando.destino), estilo=estilo,
                           segundos=comando.segundos))
    else:
        partes.append(_("Se muestra {destino}.").format(
            destino=destino(comando.destino)))
    partes.append(_("Puede usarlo: {quien}.").format(quien=_quien(comando)))
    partes.append(_("Espera {general} segundos entre usos y {persona} "
                   "segundos por persona.").format(
                        general=_numero(comando.espera_general),
                        persona=_numero(comando.espera_persona)))
    if comando.atajo:
        partes.append(_("Atajo: {atajo}.").format(atajo=_atajo(comando)))
    if not comando.activo:
        partes.append(_("Pausado."))
    return " ".join(partes)
