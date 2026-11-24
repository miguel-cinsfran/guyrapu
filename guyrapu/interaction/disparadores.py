# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuándo se cumple un disparador de la interacción con el público.

Puro y sin wx. Única razón para cambiar: qué datos tiene un disparador,
cuándo un mensaje del directo lo cumple y cuáles dispara un atajo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from guyrapu.core import avisos_tiktok, plataformas
from guyrapu.core.idioma import N_, _
from guyrapu.interaction import comandos, contenido, filtro_publico, informe_ensayo
from guyrapu.interaction.texto import normalizar

CUANDOS = ("evento",)
VARIABLES = ("usuario", "cantidad", "regalo", "texto", "contador")
EVENTOS_DEL_DIRECTO = tuple(tipo for tipo, _modo in avisos_tiktok.EVENTOS
                            if tipo != "comando")
NOMBRES_EVENTOS = {
    "superchat": N_("Super Chats y regalos"),
    "miembro": N_("Membresías"),
    "entrada": N_("Entradas al directo"),
    "me_gusta": N_("Me gusta"),
    "seguir": N_("Seguidores nuevos"),
    "compartir": N_("Directo compartido"),
    "cofre": N_("Cofres"),
    "encuesta": N_("Encuestas"),
    "meta": N_("Metas"),
    "batalla": N_("Batallas"),
}
EVENTOS_SIN_ALERTA = ("encuesta", "meta")
EVENTOS_DE_ALERTA = tuple(tipo for tipo in EVENTOS_DEL_DIRECTO
                          if tipo not in EVENTOS_SIN_ALERTA)

_NUMERO_RE = re.compile(r"\d+(?:[.,]\d+)*")
_DECIMAL_RE = re.compile(r"[.,]\d{2}$")
_RACHA_RE = re.compile(r"\s+x\d+$")


@dataclass(frozen=True, slots=True)
class Disparador:
    """Un disparador de evento del directo con su qué y sus reglas."""

    nombre: str
    cuando: str = "evento"
    evento: str = ""
    minimo: float | None = None
    regalo: str = ""
    medio: str = ""
    destino: str = "video"
    tarjeta: str = ""
    estilo: str = ""
    segundos: int = 8
    permiso: str = "todos"
    nombres: tuple[str, ...] = ()
    espera_general: float = 5
    espera_persona: float = 30
    activo: bool = True
    avisar: bool = False

    def __post_init__(self):
        object.__setattr__(self, "segundos",
                           max(3, min(60, int(self.segundos))))


def cantidad_de(monto) -> float:
    """La cantidad que trae el monto: el primer número que aparece."""
    encontrado = _NUMERO_RE.search(str(monto or ""))
    if encontrado is None:
        return 0
    numero = encontrado.group(0)
    if _DECIMAL_RE.search(numero):
        entero = re.sub(r"[.,]", "", numero[:-3]) or "0"
        return float(entero + "." + numero[-2:])
    return float(re.sub(r"[.,]", "", numero))


def _es_el_regalo(disparador: Disparador, evento) -> bool:
    if evento.plataforma != plataformas.TIKTOK:
        return False
    nombre = _RACHA_RE.sub("", evento.texto or "")
    return normalizar(disparador.regalo) == normalizar(nombre)


def _cumple_evento(disparador: Disparador, evento) -> bool:
    if avisos_tiktok.evento_de(evento.tipo) != disparador.evento:
        return False
    if disparador.regalo and disparador.evento == "superchat" \
            and not _es_el_regalo(disparador, evento):
        return False
    if disparador.minimo is None:
        return True
    return cantidad_de(evento.monto) >= disparador.minimo


def _cumple(disparador: Disparador, evento) -> bool:
    return disparador.cuando == "evento" and _cumple_evento(disparador, evento)


def cumplidos(disparadores, evento, esperas, ahora) -> list[Disparador]:
    """Los disparadores que ese mensaje cumple, en el orden de la lista.

    Anota el uso de cada uno que devuelve, para que sus esperas cuenten.
    """
    logrados = []
    for disparador in disparadores:
        if not disparador.activo:
            continue
        if not _cumple(disparador, evento):
            continue
        if not comandos.puede_usarlo(disparador, evento):
            continue
        if not esperas.libre(disparador, evento, ahora):
            continue
        esperas.anotar(disparador, evento, ahora)
        logrados.append(disparador)
    return logrados


def motivo(disparadores, evento, esperas, ahora):
    """Por qué no respondió ninguna alerta, sin consumir esperas ni estado."""
    for disparador in disparadores:
        if not disparador.activo or not _cumple(disparador, evento):
            continue
        if not comandos.puede_usarlo(disparador, evento):
            continue
        segundos = esperas.faltan(disparador, evento, ahora)
        if segundos:
            return _(informe_ensayo.MOTIVO_ESPERA_ALERTA).format(
                nombre=disparador.nombre, segundos=segundos)
        return ""
    return ""


def _nombre_del_regalo(disparador: Disparador, evento) -> str:
    if (disparador.cuando == "evento" and disparador.evento == "superchat"
            and evento.plataforma == plataformas.TIKTOK):
        return _RACHA_RE.sub("", evento.texto or "")
    return ""


def texto_de_tarjeta(disparador: Disparador, evento, contador,
                     bloqueadas) -> str:
    """El texto de la tarjeta con sus variables ya llenas."""
    publico = evento.texto or ""
    if filtro_publico.es_casi_todo_simbolos(publico):
        publico = ""
    publico = filtro_publico.tapar(publico, bloqueadas)[:100]
    texto = (disparador.tarjeta or "").replace(
        "{usuario}",
        filtro_publico.tapar(evento.autor or "", bloqueadas))
    texto = texto.replace("{cantidad}", evento.monto or "")
    texto = texto.replace("{regalo}", _nombre_del_regalo(disparador, evento))
    texto = texto.replace("{contador}", str(contador))
    return texto.replace("{texto}", publico)


def _error_de_nombre(disparador: Disparador, otros) -> tuple[str, str]:
    if not normalizar(disparador.nombre):
        # Traductores: validación de alertas del directo (error).
        return "nombre", _("La alerta necesita un nombre.")
    for otro in otros:
        if normalizar(otro.nombre) == normalizar(disparador.nombre):
            # Traductores: validación de alertas del directo (error). {nombre} es la alerta que ya existe.
            return "nombre", _("La alerta {nombre} ya existe.").format(
                nombre=disparador.nombre)
    return "", ""


def _error_de_cuando(disparador: Disparador, _otros) -> tuple[str, str]:
    if disparador.cuando not in CUANDOS:
        # Traductores: validación de alertas del directo (error).
        return "nombre", _("Ese tipo de alerta todavía no existe.")
    return "", ""


def _error_de_evento(disparador: Disparador, _otros) -> tuple[str, str]:
    if disparador.cuando != "evento":
        return "", ""
    if disparador.evento not in EVENTOS_DEL_DIRECTO:
        # Traductores: validación de alertas del directo (error). {evento} es el nombre del evento desconocido.
        return "evento", _("El evento {evento} no existe.").format(
            evento=disparador.evento)
    if disparador.minimo is not None and disparador.minimo < 0:
        # Traductores: validación de alertas del directo (error).
        return "minimo", _("El mínimo no puede ser negativo.")
    return "", ""


def _error_de_que(disparador: Disparador, _otros) -> tuple[str, str]:
    # Traductores: validación de alertas del directo (error).
    mensaje = contenido.validar(
        disparador.tarjeta, disparador.medio, disparador.destino,
        nombre=_("La alerta"),
        # Traductores: validación de alertas del directo (error). {actual} es el largo y {maximo} el tope del chat.
        error_largo=_("La tarjeta tiene {actual} caracteres y el máximo para el "
                      "chat es {maximo}."))
    return ("tarjeta", mensaje) if mensaje else ("", "")


def variables_desconocidas(tarjeta) -> list[str]:
    return [variable
            for variable in comandos._VARIABLE_RE.findall(tarjeta or "")
            if variable not in VARIABLES]


def _error_de_variables(disparador: Disparador, _otros) -> tuple[str, str]:
    desconocidas = variables_desconocidas(disparador.tarjeta)
    if desconocidas:
        # Traductores: validación de alertas del directo (error). {variable} es la variable desconocida y las demás son las que se pueden usar.
        return "tarjeta", _("La variable {variable} no existe. Puedes usar {usuario}, "
                 "{cantidad}, {regalo}, {texto} y {contador}.").format(
                     variable="{" + desconocidas[0] + "}",
                     usuario="{" + VARIABLES[0] + "}",
                     cantidad="{" + VARIABLES[1] + "}",
                     regalo="{" + VARIABLES[2] + "}",
                     texto="{" + VARIABLES[3] + "}",
                     contador="{" + VARIABLES[4] + "}")
    return "", ""


def error_y_campo(disparador: Disparador, otros) -> tuple[str, str]:
    """El campo y el mensaje del primer error, o ("", "") si no hay ninguno."""
    comprobaciones = (_error_de_nombre, _error_de_cuando, _error_de_evento,
                      _error_de_que, _error_de_variables)
    for comprobar in comprobaciones:
        campo, mensaje = comprobar(disparador, otros)
        if mensaje:
            return campo, mensaje
    return "", ""


def validar(disparador: Disparador, otros) -> str:
    """Un texto de error, o "" si el disparador se puede guardar."""
    return error_y_campo(disparador, otros)[1]
