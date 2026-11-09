# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Sonidos del estado de Restream y del aviso de otros destinos.

Se generan en memoria con las primitivas de `scripts/sound_gen.py`, que se
carga al generar y no al importar este módulo.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _base():
    raiz = str(RAIZ)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from scripts import sound_gen
    return sound_gen


def gen_restream_destino_caido():
    # Descenso E4→C4: un destino dejó de recibir, sin la insistencia grave
    # de transmision_problema (A3) ni los tres pulsos de directo_con_cortes.
    base = _base()
    n1 = base._perc(base._seno(base.E4, 0.12, 0.36), 0.004, 0.09)
    n2 = base._perc(base._seno(base.C4, 0.22, 0.36), 0.004, 0.16)
    return base._normalizar(base._concat(n1, n2), 0.7)


def gen_restream_destino_vuelve():
    # Subida A4→D5: el destino vuelve a recibir. Distinta de la vuelta de la
    # conexión (G4→C5) y del reintento del directo (B4→E5).
    base = _base()
    n1 = base._perc(base._seno(base.A4, 0.09, 0.34), 0.004, 0.07)
    n2 = base._perc(base._seno(base.D5, 0.18, 0.36), 0.004, 0.14)
    return base._normalizar(base._concat(n1, n2), 0.7)


def gen_restream_sin_senal():
    # Barrido grave A3→D3 que se apaga: la señal de OBS no llega.
    base = _base()
    return base._normalizar(
        base._perc(base._glide(base.A3, base.D3, 0.36, 0.38), 0.005, 0.22),
        0.7)


def gen_restream_senal_vuelve():
    # Barrido E4→A4, cálido y ascendente: la señal vuelve. No comparte el
    # G4→C5 de transmision_recuperada ni el E4→B4 de grabacion_reanudada.
    base = _base()
    return base._normalizar(
        base._perc(base._glide(base.E4, base.A4, 0.30, 0.34), 0.005, 0.20),
        0.68)


def gen_restream_senal_debil():
    # Dos toques iguales G4 con hueco: advertencia, la señal baja. No es la
    # repetición A4-A4 de grabacion_en_pausa.
    base = _base()
    nota = base._perc(base._seno(base.G4, 0.10, 0.34), 0.004, 0.07)
    return base._normalizar(
        base._concat(nota, base._silencio(0.07), nota), 0.68)


def gen_destinos_de_mas():
    # Pregunta antes de seguir: A4→C5→A4, sube y vuelve. Distinta de la
    # alarma grave de transmision_problema (A3 repetido), del tic de copiar
    # (C6) y del descenso de error (A3→F3).
    base = _base()
    n1 = base._perc(base._seno(base.A4, 0.09, 0.32), 0.004, 0.07)
    n2 = base._perc(base._seno(base.C5, 0.09, 0.34), 0.004, 0.07)
    n3 = base._perc(base._seno(base.A4, 0.16, 0.32), 0.004, 0.13)
    return base._normalizar(base._concat(n1, n2, n3), 0.7)


def s_restream_destino_caido():
    # Descenso E4→C4 en madera cálida: un destino dejó de recibir.
    base = _base()
    return base._seq(base._madera(base.E4, 0.12, 0.36, 0.09),
                     base._madera(base.C4, 0.22, 0.36, 0.16))


def s_restream_destino_vuelve():
    # Subida A4→D5 en madera: el destino vuelve a recibir.
    base = _base()
    return base._seq(base._madera(base.A4, 0.09, 0.34, 0.07),
                     base._madera(base.D5, 0.18, 0.36, 0.14))


def s_restream_sin_senal():
    # Barrido grave A3→D3 en madera: la señal de OBS no llega.
    base = _base()
    return base._normalizar(
        base._perc(base._glide(base.A3, base.D3, 0.34, 0.34), 0.006, 0.22),
        0.65)


def s_restream_senal_vuelve():
    # Barrido E4→A4, el mismo alivio en madera cálida.
    base = _base()
    return base._normalizar(
        base._perc(base._glide(base.E4, base.A4, 0.30, 0.30), 0.006, 0.20),
        0.65)


def s_restream_senal_debil():
    # Dos toques iguales G4 con hueco: advertencia, la señal baja.
    base = _base()
    nota = base._madera(base.G4, 0.10, 0.34, 0.07)
    return base._normalizar(
        base._concat(nota, base._silencio(0.07), nota), 0.68)


def s_destinos_de_mas():
    # La misma pregunta en madera cálida: A4→C5→A4.
    base = _base()
    return base._seq(base._madera(base.A4, 0.09, 0.32, 0.07),
                     base._madera(base.C5, 0.09, 0.34, 0.07),
                     base._madera(base.A4, 0.16, 0.32, 0.13))
