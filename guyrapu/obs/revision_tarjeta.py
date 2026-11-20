# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué se le dice al usuario de una tarjeta armada, sin wx ni OBS.

Puro. Su única razón para cambiar es la frase que describe cómo se verá una
tarjeta: la zona, cuánto ocupa y los avisos de posición, fuente y contraste.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.interaction import zonas
from guyrapu.obs import estilos_aviso


def _nombre_de_zona(estilo, ancho, alto) -> str:
    clave = zonas.resolver(
        str(estilo.get("zona", "automatica")), ancho, alto)
    for referencia, nombre in estilos_aviso.ZONAS:
        if referencia == clave:
            return _(nombre)
    return clave


def _por_ciento(parte, total) -> int:
    if not total:
        return 0
    return int(round(100 * parte / total))


def _se_sale_del_centro(tarjeta, ancho, alto) -> bool:
    margen_x = ancho * 0.1
    margen_y = alto * 0.1
    return (tarjeta.x < margen_x
            or tarjeta.y < margen_y
            or tarjeta.x + tarjeta.ancho > ancho - margen_x
            or tarjeta.y + tarjeta.alto > alto - margen_y)


def revisar(tarjeta, ancho, alto, estilo) -> str:
    """La frase que describe la tarjeta: zona, tamaño y avisos, en ese orden."""
    frases = [
        _("Zona: {zona}.").format(
            zona=_nombre_de_zona(estilo, ancho, alto)),
        _("Ocupa el {ancho} por ciento del ancho y el {alto} por ciento del "
          "alto del vídeo.").format(
              ancho=_por_ciento(tarjeta.ancho, ancho),
              alto=_por_ciento(tarjeta.alto, alto)),
    ]
    if _se_sale_del_centro(tarjeta, ancho, alto):
        frases.append(_("La tarjeta queda fuera del 80 por ciento central del "
                        "vídeo."))
    if tarjeta.aviso_fuente:
        frases.append(tarjeta.aviso_fuente)
    aviso_contraste = estilos_aviso.aviso_contraste(estilo)
    if aviso_contraste:
        frases.append(aviso_contraste)
    return " ".join(frases)
