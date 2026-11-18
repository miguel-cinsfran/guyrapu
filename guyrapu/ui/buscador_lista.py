# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué acciones tiene la lista de resultados del buscador de descargas.

Una sola razón para cambiar: qué acciones ofrece la lista y cómo se llama
cada una. Los motivos salen de `buscador_acciones`.
"""

from __future__ import annotations

from guyrapu.ui import buscador_acciones
from guyrapu.ui.lista_pura import Accion


def _unico(resultados):
    """El resultado de la fila única, o None si hay otra cantidad."""
    return resultados[0] if len(resultados) == 1 else None


def acciones_de(elegidos, hay_app, hay_musica, acciones, al_ver_contenido,
                al_agregar, al_escuchar) -> tuple:
    """Las acciones de la lista, con el rótulo y el motivo de cada una."""
    textos = buscador_acciones.textos()

    def motivo(opcion, indices):
        return buscador_acciones.motivo_de(
            opcion, elegidos(indices), hay_app, hay_musica)

    return (
        Accion("agregar", textos["agregar"], lambda: al_agregar(),
               varios=True,
               motivo_indices=lambda indices: motivo("agregar", indices)),
        Accion("escuchar", textos["escuchar"],
               lambda: al_escuchar(_unico(elegidos())),
               motivo_indices=lambda indices: motivo("escuchar", indices)),
        Accion("audio", textos["audio"],
               lambda: acciones.como_audio(elegidos()), varios=True,
               motivo_indices=lambda indices: motivo("audio", indices)),
        Accion("video", textos["video"],
               lambda: acciones.como_video(elegidos()), varios=True,
               motivo_indices=lambda indices: motivo("video", indices)),
        Accion("formato", textos["formato"],
               lambda: acciones.elegir_formato(_unico(elegidos())),
               motivo_indices=lambda indices: motivo("formato", indices)),
        Accion("app", textos["app"],
               lambda: acciones.en_app(_unico(elegidos())),
               motivo_indices=lambda indices: motivo("app", indices)),
        Accion("musica", textos["musica"],
               lambda: acciones.a_musica(_unico(elegidos())),
               motivo_indices=lambda indices: motivo("musica", indices)),
        Accion("contenido", textos["contenido"],
               lambda: al_ver_contenido(_unico(elegidos())),
               motivo_indices=lambda indices: motivo("contenido", indices)),
        Accion("copiar", textos["copiar"],
               lambda: acciones.copiar(_unico(elegidos())),
               motivo_indices=lambda indices: motivo("copiar", indices)),
        Accion("navegador", textos["navegador"],
               lambda: acciones.abrir_en_navegador(_unico(elegidos())),
               motivo_indices=lambda indices: motivo("navegador", indices)),
        Accion("sitios", textos["sitios"], lambda: acciones.ver_sitios(),
               necesita_elemento=False),
    )
