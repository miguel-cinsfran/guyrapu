# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué registro arma un mensaje de ensayo y qué destinos tiene.

No importa `MensajeChat`: `guyrapu.interaction` no puede importar de
`guyrapu.ui` (R16). El registro tiene la misma forma, así que el controlador
del chat lo recibe sin convertirlo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from guyrapu.core import plataformas
from guyrapu.core.config import (
    TIPO_COMPARTIR, TIPO_ME_GUSTA, TIPO_MIEMBRO, TIPO_SEGUIR,
    TIPO_SUPERCHAT, TIPO_TEXTO,
)
from guyrapu.core.idioma import N_
from guyrapu.core.sonidos_eventos import ROL_MODERADOR, ROL_PROPIETARIO
from guyrapu.interaction import informe_ensayo

MENSAJE = "mensaje"
SUPER_CHAT = "superchat"
REGALO = "regalo"
MEMBRESIA = "membresia"
SEGUIDOR = "seguidor"
ME_GUSTA = "me_gusta"
COMPARTIR = "compartir"

# Traductores: autor de fábrica de los mensajes de la ventana de ensayo.
AUTOR_PREDETERMINADO = N_("Público de prueba")

# Traductores: los roles que la captura de YouTube pone en el registro.
ROLES = (
    (N_("Público"), ""),
    (N_("Moderador"), ROL_MODERADOR),
    (N_("Propietario del canal"), ROL_PROPIETARIO),
)


@dataclass(frozen=True, slots=True)
class Tipo:
    """Un tipo de la ventana y el registro que produce en la captura."""

    clave: str
    rotulo: str
    plataformas: tuple[str, ...]
    campos: tuple[str, ...]
    tipo: str
    texto: str = ""
    monto: str = ""


# Una fila por tipo: la ventana lee aquí los rótulos y los campos que muestra,
# y `registro` lee aquí el tipo y el monto que la captura real pondría.
TIPOS = (
    Tipo(MENSAJE, N_("Mensaje"),
         (plataformas.YOUTUBE, plataformas.TIKTOK), ("mensaje",), TIPO_TEXTO,
         "mensaje"),
    Tipo(SUPER_CHAT, N_("Super Chat"), (plataformas.YOUTUBE,),
         ("cantidad", "mensaje"), TIPO_SUPERCHAT, "mensaje", "{cantidad}"),
    Tipo(MEMBRESIA, N_("Membresía"), (plataformas.YOUTUBE,), (),
         TIPO_MIEMBRO),
    Tipo(REGALO, N_("Regalo"), (plataformas.TIKTOK,),
         ("regalo", "cantidad"), TIPO_SUPERCHAT, "regalo",
         "{cantidad} diamantes"),
    Tipo(SEGUIDOR, N_("Seguidor nuevo"), (plataformas.TIKTOK,), (),
         TIPO_SEGUIR),
    Tipo(ME_GUSTA, N_("Me gusta"), (plataformas.TIKTOK,), (),
         TIPO_ME_GUSTA, "", "1"),
    Tipo(COMPARTIR, N_("Directo compartido"), (plataformas.TIKTOK,), (),
         TIPO_COMPARTIR),
)


def tipos_de(plataforma):
    """Los tipos que ofrece esa plataforma, en el orden de la tabla."""
    return tuple(tipo for tipo in TIPOS if plataforma in tipo.plataformas)


def tipo_de(clave):
    """La fila de la tabla con esa clave."""
    return next(tipo for tipo in TIPOS if tipo.clave == clave)


def con_rol(plataforma):
    """Si esa plataforma trae el rol de quien escribe."""
    return plataforma == plataformas.YOUTUBE


@dataclass(frozen=True, slots=True)
class MensajeEnsayo:
    """Una fila del chat de ensayo, con los campos que espera `chat_vivo`."""

    plataforma: str
    autor: str
    identificador: str
    texto: str
    hora: str
    tipo: str
    monto: str
    rol: str = ""
    nivel: int = 0


def registro(autor, mensaje, plataforma, tipo, cantidad="", ahora=None,
             rol="", regalo=""):
    """Arma el registro desde los campos de la ventana de ensayo."""
    momento = ahora or datetime.now()
    fila = tipo_de(tipo)
    valores = {"mensaje": mensaje, "regalo": regalo, "cantidad": cantidad}
    texto = valores[fila.texto] if fila.texto else ""
    monto = fila.monto.format(cantidad=cantidad) if fila.monto else ""
    return MensajeEnsayo(
        plataforma=plataforma, autor=autor, identificador="", texto=texto,
        hora=momento.strftime("%H:%M:%S"), tipo=fila.tipo, monto=monto,
        rol=rol)


def destinos():
    """El ensayo no tiene chat: solo va al vídeo."""
    return {"video"}


def en_ensayo(frame) -> bool:
    """Si la ventana de ensayo está abierta en ese marco."""
    return getattr(frame, "_ensayo", False) is True


def en_vivo_o_ensayo(frame) -> bool:
    """Si el marco está conectado al directo o en ensayo."""
    return bool(getattr(frame, "_conectado", False)) or en_ensayo(frame)


def empezar_informe(frame):
    """Prepara el informe de un envío, solo cuando hay un ensayo abierto."""
    if not en_ensayo(frame):
        return None
    actual = informe_ensayo.InformeEnsayo()
    frame._informe_ensayo = actual
    return actual


def informe(frame):
    """El informe del envío en curso, o None si no es un ensayo."""
    if not en_ensayo(frame):
        return None
    return getattr(frame, "_informe_ensayo", None)
