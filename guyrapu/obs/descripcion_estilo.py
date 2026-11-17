# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La frase que describe un estilo de aviso, sin wx.

Puro y sin ventanas. Su única razón para cambiar es cómo se cuenta un
estilo cuando se elige Escuchar: qué se dice y en qué orden.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.interaction import animacion
from guyrapu.obs import estilos_aviso


def _numero(valor) -> str:
    """El número con coma decimal y sin ceros de más."""
    return f"{float(valor):g}".replace(".", ",")


def _nombre_de_lista(clave, opciones) -> str:
    """El nombre traducido de la opción, o la clave si no está en la lista."""
    for clave_opcion, nombre in opciones:
        if clave_opcion == clave:
            return _(nombre)
    return str(clave)


def _nombre_de_color(codigo) -> str:
    return estilos_aviso.nombre_de_color(codigo)


def describir(estilo: dict) -> str:
    """La frase completa: nombre, fuente, tamaño, colores, fondo, zona y
    animaciones, con el aviso de contraste si el estilo lo tiene."""
    frases = [
        _("{nombre}. Fuente {fuente}, tamaño {tamano} % del lado menor del "
          "vídeo.").format(
              nombre=_(estilo.get("nombre", "")),
              fuente=estilo.get("fuente", ""),
              tamano=_numero(estilo.get("tamano", 5))),
        _("Texto {texto} con contorno {contorno} de ancho {ancho}.").format(
            texto=_nombre_de_color(estilo.get("color_texto", "")),
            contorno=_nombre_de_color(estilo.get("color_contorno", "")),
            ancho=int(float(estilo.get("ancho_contorno", 0)))),
        _("Fondo {fondo} con una opacidad de {opacidad} %.").format(
            fondo=_nombre_de_color(estilo.get("color_fondo", "")),
            opacidad=int(float(estilo.get("opacidad_fondo", 0)))),
        _("Zona: {zona}.").format(zona=_nombre_de_lista(
            estilo.get("zona", ""), estilos_aviso.ZONAS)),
        _("Entrada: {entrada}, {ms} milisegundos.").format(
            entrada=_nombre_de_lista(estilo.get("entrada", ""),
                                     animacion.ENTRADAS),
            ms=int(float(estilo.get("ms_entrada", 0)))),
        _("Salida: {salida}, {ms} milisegundos.").format(
            salida=_nombre_de_lista(estilo.get("salida", ""),
                                    animacion.SALIDAS),
            ms=int(float(estilo.get("ms_salida", 0)))),
    ]
    aviso = estilos_aviso.aviso_contraste(estilo)
    if aviso:
        frases.append(aviso)
    return " ".join(frases)
