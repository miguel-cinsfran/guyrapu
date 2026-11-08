# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La regla de los tres usos de un perfil de OBS: transmitir y grabar.

Puro y sin wx. Las claves son las mismas que escribe Preferencias en
`[transmision]`: una cadena vacía significa que se usa el perfil que tenga
OBS en ese momento.
"""

from __future__ import annotations

from guyrapu.core.idioma import N_, _

SECCION = "transmision"

USOS = (
    ("perfil_horizontal", N_("transmitir en horizontal")),
    ("perfil_vertical", N_("transmitir en vertical")),
    ("perfil_grabar", N_("grabar")),
)


def _texto(clave):
    for nombre_clave, texto in USOS:
        if nombre_clave == clave:
            return _(texto)
    return clave


def usos_de(nombre, config):
    """Claves de los usos asignados a `nombre`, en el orden de `USOS`."""
    if not nombre:
        return []
    return [clave for clave, _texto_uso in USOS
            if (config.get(clave) or "") == nombre]


def texto_para(usos):
    """«para transmitir en horizontal y para grabar», con los usos dados."""
    partes = [_("para {uso}").format(uso=_texto(clave))
              for clave, _texto_uso in USOS if clave in usos]
    return _(" y ").join(partes)


def etiqueta_fila(nombre, en_uso, usos):
    """El nombre del perfil con su estado y los usos que tiene asignados."""
    partes = []
    if en_uso:
        partes.append(_("en uso"))
    partes.extend(_("para {uso}").format(uso=_texto(clave))
                  for clave, _texto_uso in USOS if clave in usos)
    if not partes:
        return nombre
    return _("{nombre} ({partes})").format(
        nombre=nombre, partes=", ".join(partes))


def cambios(nombre, marcados, config):
    """Pares (clave, valor) que cambian al aceptar las casillas marcadas.

    Solo mira las claves presentes en `marcados`: una marcada asigna el
    perfil, una desmarcada deja el uso vacío. Lo que no cambia no vuelve.
    """
    resultado = []
    for clave, _texto_uso in USOS:
        if clave not in marcados:
            continue
        actual = config.get(clave) or ""
        if marcados[clave]:
            valor = nombre
        elif actual == nombre:
            valor = ""
        else:
            continue
        if actual != valor:
            resultado.append((clave, valor))
    return resultado


def cambios_al_eliminar(nombre, config):
    """Pares (clave, "") de los usos que quedan libres al eliminar el perfil."""
    return [(clave, "") for clave in usos_de(nombre, config)]


def texto_al_eliminar(nombre, config):
    """Frase que avisa qué usos quedan vacíos, o cadena vacía si no tiene."""
    usos = usos_de(nombre, config)
    if not usos:
        return ""
    if len(usos) == 1:
        return _("Se usa {usos}: ese uso quedará con el perfil que tenga "
                 "OBS.").format(usos=texto_para(usos))
    return _("Se usa {usos}: esos usos quedarán con el perfil que tenga "
             "OBS.").format(usos=texto_para(usos))
