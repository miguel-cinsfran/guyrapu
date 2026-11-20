# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Muestras de Restream y del directo de YouTube, armadas como en sus pruebas.

Cada `armar(datos)` devuelve el cuadro ya construido, con datos de ejemplo
y sin red. Los dobles y el aislamiento de archivos los pone quien llama.
"""

from __future__ import annotations

MUESTRAS = []


def _registrar(nombre, clase, variante, armar):
    MUESTRAS.append((nombre, clase, variante, armar))


def _meta_destino(datos):
    from guyrapu.restream.api import MetaCanal
    from guyrapu.ui import restream_dialogos_destino

    return restream_dialogos_destino.DialogoMetaDestino(
        None, MetaCanal("Charlas", "Charlas del sábado"))


def _destino_manual(datos):
    from guyrapu.ui import restream_dialogos_destino

    plataformas = {67: "TikTok", 5: "YouTube", 10: "Facebook"}
    return restream_dialogos_destino.DialogoDestinoManual(None, plataformas)


def _perfil_restream(datos):
    from guyrapu.restream.perfiles import Perfil
    from guyrapu.ui import restream_perfil

    perfil = Perfil(nombre="Canal", canales=(1, 2),
                    orientacion="horizontal", youtube=True,
                    chat="youtube", directo={})
    canales = [(1, "TikTok: uno"), (2, "YouTube: dos")]
    return restream_perfil.DialogoPerfilRestream(None, perfil, canales, [])


def _directo_youtube(datos):
    from guyrapu.ui import gui_directo_youtube

    return gui_directo_youtube.DialogoDirectoYoutube(
        None, titulo="El directo del sábado",
        descripcion="Charlas con la comunidad",
        categoria="999", etiquetas="música, charlas")


_registrar("meta_destino", "DialogoMetaDestino", "con_datos", _meta_destino)
_registrar("destino_manual", "DialogoDestinoManual", "con_datos",
           _destino_manual)
_registrar("perfil_restream", "DialogoPerfilRestream", "con_datos",
           _perfil_restream)
_registrar("directo_youtube", "DialogoDirectoYoutube", "con_datos",
           _directo_youtube)
