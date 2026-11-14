# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se presenta el catálogo de paquetes de voces al usuario.

Junta el catálogo y lo instalado, filtra, ordena y arma los textos de las
filas, las voces y los detalles. No lee red ni disco y no sabe de ventanas:
la única razón de este módulo para cambiar es cómo se presentan las voces.
"""

from __future__ import annotations

from typing import NamedTuple

from guyrapu.core import paquetes_catalogo
from guyrapu.core.idioma import N_, _, idioma_actual, ngettext

_MEGA = 1024 * 1024

_IDIOMAS = {
    "es": N_("español"),
    "en": N_("inglés"),
    "pt": N_("portugués"),
    "es-ES": N_("español (España)"),
    "es-MX": N_("español (México)"),
    "es-AR": N_("español (Argentina)"),
    "en-US": N_("inglés (Estados Unidos)"),
    "en-GB": N_("inglés (Reino Unido)"),
    "pt-BR": N_("portugués (Brasil)"),
    "pt-PT": N_("portugués (Portugal)"),
}

_GENEROS = {
    "female": N_("femenina"),
    "male": N_("masculina"),
    "femenina": N_("femenina"),
    "masculina": N_("masculina"),
}

_ESTADOS = {
    "sin_descargar": N_("disponible"),
    "instalado": N_("instalado"),
    "actualizable": N_("actualización disponible"),
    "fuera_del_catalogo": N_("instalado"),
}

_ORDEN_MOTOR = {"phonon": 0, "piper": 1}


class PaqueteVoz(NamedTuple):
    """Un paquete del catálogo y su ficha instalada, si la tiene."""

    catalogo: dict | None
    instalado: dict | None


def _ficha(entrada):
    if entrada.catalogo is not None:
        return entrada.catalogo
    return entrada.instalado or {}


def _base(codigo) -> str:
    return str(codigo or "").replace("_", "-").split("-", 1)[0].lower()


def _inicial(texto):
    return texto[:1].upper() + texto[1:] if texto else texto


def reunir(catalogo, instalados) -> list[PaqueteVoz]:
    """Junta el catálogo con lo instalado, también lo que ya no está en él."""
    por_id = {ficha.get("id"): ficha for ficha in instalados or []
              if isinstance(ficha, dict)}
    entradas = []
    vistos = set()
    for paquete in catalogo or []:
        if not isinstance(paquete, dict):
            continue
        identificador = paquete.get("id")
        vistos.add(identificador)
        entradas.append(PaqueteVoz(paquete, por_id.get(identificador)))
    for ficha in instalados or []:
        if isinstance(ficha, dict) and ficha.get("id") not in vistos:
            entradas.append(PaqueteVoz(None, ficha))
    return entradas


def identificador(entrada):
    return _ficha(entrada).get("id")


def nombre(entrada) -> str:
    return str(_ficha(entrada).get("nombre") or nombre_corto(entrada))


def motor_de(entrada) -> str:
    return str(_ficha(entrada).get("proveedor") or "")


def nombre_motor(entrada) -> str:
    return motor_de(entrada).capitalize()


def voces(entrada) -> list[dict]:
    listado = _ficha(entrada).get("voces")
    if not isinstance(listado, list):
        return []
    return [voz for voz in listado if isinstance(voz, dict)]


def nombre_corto(entrada) -> str:
    listado = voces(entrada)
    if len(listado) == 1:
        nombre_voz = listado[0].get("nombre")
        if isinstance(nombre_voz, str) and nombre_voz.strip():
            return nombre_voz
    return nombre_motor(entrada)


def nombre_idioma(codigo) -> str:
    """«español (España)», «español» o el código tal cual."""
    texto = str(codigo or "").strip()
    if not texto:
        return ""
    normalizado = texto.replace("_", "-")
    elegido = _IDIOMAS.get(normalizado)
    if elegido is None:
        minusculas = normalizado.lower()
        for clave, valor in _IDIOMAS.items():
            if clave.lower() == minusculas:
                elegido = valor
                break
    if elegido is not None:
        return _(elegido)
    base = _base(normalizado)
    if base in _IDIOMAS:
        return _(_IDIOMAS[base])
    return texto


def _idioma_de(entrada) -> str:
    codigo = _ficha(entrada).get("idioma")
    if isinstance(codigo, str) and codigo.strip():
        return codigo
    listado = voces(entrada)
    if listado:
        return str(listado[0].get("idioma") or "")
    return ""


def idioma_mostrado(entrada) -> str:
    listado = voces(entrada)
    codigos = {str(voz.get("idioma")) for voz in listado
               if isinstance(voz.get("idioma"), str) and voz.get("idioma")}
    if len(codigos) == 1:
        return nombre_idioma(codigos.pop())
    if codigos:
        return nombre_idioma(_base(_idioma_de(entrada)))
    return nombre_idioma(_idioma_de(entrada))


def tamano(entrada) -> str:
    total = 0
    archivos = _ficha(entrada).get("archivos")
    if isinstance(archivos, list):
        total = sum(archivo.get("bytes", 0) for archivo in archivos
                    if isinstance(archivo, dict)
                    and isinstance(archivo.get("bytes"), int))
    megas = round(total / _MEGA)
    if megas < 1:
        return _("menos de 1 MB")
    return _("{n} MB").format(n=megas)


def estado_codigo(entrada) -> str:
    return paquetes_catalogo.estado(entrada.catalogo, entrada.instalado)


def estado(entrada) -> str:
    return _(_ESTADOS[estado_codigo(entrada)])


def fila(entrada) -> str:
    listado = voces(entrada)
    if len(listado) == 1:
        partes = [nombre_corto(entrada), nombre_motor(entrada)]
    else:
        partes = [nombre_motor(entrada)]
    partes.append(idioma_mostrado(entrada))
    if len(listado) > 1:
        partes.append(
            ngettext("{n} voz", "{n} voces", len(listado)).format(
                n=len(listado)))
    partes.extend((tamano(entrada), estado(entrada)))
    return ", ".join(parte for parte in partes if parte)


def fila_voz(voz) -> str:
    partes = [str(voz.get("nombre") or "")]
    genero = _GENEROS.get(str(voz.get("genero") or "").lower())
    if genero:
        partes.append(_(genero))
    partes.append(nombre_idioma(str(voz.get("idioma") or "")))
    return ", ".join(parte for parte in partes if parte)


def filas_voces(entrada) -> list[str]:
    return [fila_voz(voz) for voz in voces(entrada)]


def _idiomas_distintos(entrada) -> list[str]:
    idiomas = []
    vistos = set()
    for voz in voces(entrada):
        codigo = str(voz.get("idioma") or "")
        if codigo and codigo not in vistos:
            vistos.add(codigo)
            idiomas.append(nombre_idioma(codigo))
    if not idiomas:
        idiomas.append(nombre_idioma(_idioma_de(entrada)))
    return idiomas


def detalles(entrada) -> str:
    ficha = _ficha(entrada)
    listado = voces(entrada)
    idiomas = _inicial(", ".join(_idiomas_distintos(entrada)))
    lineas = [
        "{} {}".format(_("Nombre:"), nombre(entrada)),
        "{} {}".format(_("Motor de voz:"), nombre_motor(entrada)),
        "{} {}".format(_("Idioma:"), idiomas),
        "{} {}".format(_("Voces:"), len(listado)),
        "{} {}".format(_("Tamaño:"), tamano(entrada)),
        "{} {}".format(_("Estado:"), estado(entrada)),
        "{} {}".format(_("Licencia:"), str(ficha.get("licencia") or "")),
    ]
    if "NC" in str(ficha.get("licencia") or ""):
        lineas.append(_("Esta licencia no permite el uso comercial."))
    lineas.append("{} {}".format(
        _("Enlace de la licencia:"), str(ficha.get("licencia_url") or "")))
    return "\n".join(lineas)


def texto_vacio(cargando, fallo, con_filtro) -> str:
    """La línea de una lista sin paquetes, según lo que esté pasando."""
    if cargando:
        return _("Cargando paquetes de voces…")
    if con_filtro:
        return _("No hay paquetes de voces con este filtro.")
    if fallo:
        return _("No hay paquetes de voces instalados. Revisa la conexión a "
                 "internet y vuelve a abrir esta ventana.")
    return _("No hay paquetes de voces.")


def opciones_idioma(entradas) -> list[tuple[str, str]]:
    nombres = {}
    for entrada in entradas:
        base = _base(_idioma_de(entrada))
        if base and base not in nombres:
            nombres[base] = _inicial(nombre_idioma(base))
    opciones = [(_("Todos los idiomas"), "")]
    opciones.extend((nombres[base], base) for base in
                    sorted(nombres, key=lambda codigo: nombres[codigo].casefold()))
    return opciones


def opciones_motor(entradas) -> list[tuple[str, str]]:
    nombres = {}
    for entrada in entradas:
        codigo = motor_de(entrada)
        if codigo and codigo not in nombres:
            nombres[codigo] = nombre_motor(entrada)

    def _orden(codigo):
        return (_ORDEN_MOTOR.get(codigo, len(_ORDEN_MOTOR)),
                nombres[codigo].casefold())

    opciones = [(_("Todos los motores"), "")]
    opciones.extend((nombres[codigo], codigo)
                    for codigo in sorted(nombres, key=_orden))
    return opciones


def idioma_inicial(entradas) -> str:
    base = _base(idioma_actual())
    if any(_base(_idioma_de(entrada)) == base for entrada in entradas):
        return base
    return ""


def filtrar(entradas, idioma="", motor="") -> list[PaqueteVoz]:
    return [entrada for entrada in entradas
            if (not idioma or _base(_idioma_de(entrada)) == idioma)
            and (not motor or motor_de(entrada) == motor)]


def ordenar(entradas) -> list[PaqueteVoz]:
    interfaz = _base(idioma_actual())

    def _clave(entrada):
        base = _base(_idioma_de(entrada))
        motor = motor_de(entrada)
        return (0 if base == interfaz else 1,
                nombre_idioma(base).casefold(),
                _ORDEN_MOTOR.get(motor, len(_ORDEN_MOTOR)),
                nombre_corto(entrada).casefold())

    return sorted(entradas, key=_clave)
