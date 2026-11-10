# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se dice cada valor de un perfil de OBS y qué opciones se ofrecen.

Sin wx: el cuadro de ajustes y la pestaña de perfiles toman de acá las
etiquetas, y las pruebas las revisan sin abrir ventanas.
"""

from __future__ import annotations

from guyrapu.core.idioma import N_, _
from guyrapu.obs import ajustes_perfil

CODIFICADORES = (
    ("nvenc", N_("Gráfica NVIDIA (NVENC)")),
    ("qsv", N_("Gráfica Intel (QuickSync)")),
    ("amd", N_("Gráfica AMD")),
    ("x264", N_("Procesador (x264)")),
)

CALIDADES = (
    ("Stream", N_("Igual que la transmisión")),
    ("Small", N_("Alta calidad, archivo mediano")),
    ("HQ", N_("Calidad indistinguible, archivo grande")),
    ("Lossless", N_("Sin pérdida, archivo muy grande")),
)

FORMATOS = (
    ("mkv", "MKV"),
    ("mp4", "MP4"),
    ("hybrid_mp4", N_("Híbrido MP4")),
    ("mov", "MOV"),
    ("flv", "FLV"),
)

MUESTREOS = (
    (44100, "44,1 kHz"),
    (48000, "48 kHz"),
)

CANALES = (
    ("Mono", N_("Mono")),
    ("Stereo", N_("Estéreo")),
)

PRESETS = {
    "x264": (
        ("ultrafast", N_("Ultrarrápido")),
        ("superfast", N_("Superrápido")),
        ("veryfast", N_("Muy rápido")),
        ("faster", N_("Más rápido")),
        ("fast", N_("Rápido")),
        ("medium", N_("Medio")),
    ),
    "qsv": (
        ("speed", N_("Velocidad")),
        ("balanced", N_("Equilibrado")),
        ("quality", N_("Calidad")),
    ),
    "amd": (
        ("speed", N_("Velocidad")),
        ("balanced", N_("Equilibrado")),
        ("quality", N_("Calidad")),
    ),
    "nvenc": (
        ("p1", N_("La más rápida")),
        ("p2", N_("Muy rápida")),
        ("p3", N_("Rápida")),
        ("p4", N_("Equilibrado")),
        ("p5", N_("Buena calidad")),
        ("p6", N_("Mejor calidad")),
        ("p7", N_("La mejor calidad")),
    ),
}


def _decir(opciones, valor):
    for clave, etiqueta in opciones:
        if clave == valor:
            return _(etiqueta)
    return valor


def _pares(opciones):
    return tuple((valor, _(etiqueta)) for valor, etiqueta in opciones)


def opciones_codificador(disponibles=None) -> tuple:
    """Los codificadores de la PC, en el orden de preferencia."""
    if disponibles is None:
        return _pares(CODIFICADORES)
    vistos = set(disponibles)
    return _pares(tuple(opcion for opcion in CODIFICADORES
                        if opcion[0] in vistos))


def decir_codificador(valor) -> str:
    return _decir(CODIFICADORES, valor)


def opciones_preset(codificador) -> tuple:
    etiquetas = PRESETS.get(str(codificador or "").strip().lower(), ())
    valores = ajustes_perfil.presets_para(codificador)
    por_valor = dict(etiquetas)
    return tuple((valor, _(por_valor[valor]) if valor in por_valor else valor)
                 for valor in valores)


def decir_preset(codificador, valor) -> str:
    etiquetas = PRESETS.get(str(codificador or "").strip().lower(), ())
    return _decir(etiquetas, valor)


def opciones_calidad() -> tuple:
    return _pares(CALIDADES)


def decir_calidad(valor) -> str:
    return _decir(CALIDADES, valor)


def opciones_formato() -> tuple:
    return _pares(FORMATOS)


def decir_formato(valor) -> str:
    return _decir(FORMATOS, valor)


def opciones_muestreo() -> tuple:
    return _pares(MUESTREOS)


def decir_muestreo(valor) -> str:
    return _decir(MUESTREOS, valor)


def opciones_canales() -> tuple:
    return _pares(CANALES)


def decir_canales(valor) -> str:
    return _decir(CANALES, valor)


def opciones_fps() -> tuple:
    return tuple((valor, str(valor)) for valor in ajustes_perfil.FPS_VALIDOS)


def opciones_bitrate_audio() -> tuple:
    return tuple((valor, str(valor))
                 for valor in ajustes_perfil.BITRATES_AUDIO)


RESOLUCIONES = {
    False: ((1920, 1080), (1600, 900), (1280, 720)),
    True: ((1080, 1920), (900, 1600), (720, 1280)),
}


def cabe(salida, lienzo) -> bool:
    """La salida no puede ser mayor que el lienzo."""
    return salida[0] <= lienzo[0] and salida[1] <= lienzo[1]


def opciones_resolucion(vertical, actual=None) -> tuple:
    """Las resoluciones de esa orientación, más la que ya tiene el perfil."""
    opciones = list(RESOLUCIONES[bool(vertical)])
    if actual is not None and tuple(actual) not in opciones:
        opciones.append(tuple(actual))
    return tuple(opciones)


def opciones_salida(vertical, lienzo, actual=None) -> tuple:
    """Las salidas que no superan el lienzo, con la actual si cabe."""
    opciones = [resolucion for resolucion in RESOLUCIONES[bool(vertical)]
                if cabe(resolucion, lienzo)]
    if not opciones:
        opciones = [tuple(lienzo)]
    if (actual is not None and cabe(tuple(actual), lienzo)
            and tuple(actual) not in opciones):
        opciones.append(tuple(actual))
    return tuple(opciones)


def equivalente(valor, vertical):
    """La misma resolución en la otra orientación, si está entre las ofrecidas."""
    if valor is None:
        return RESOLUCIONES[bool(vertical)][0]
    ancho, alto = valor
    if bool(vertical) and ancho > alto:
        return (alto, ancho)
    if not bool(vertical) and alto > ancho:
        return (alto, ancho)
    return valor
