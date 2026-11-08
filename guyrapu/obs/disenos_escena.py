# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cálculo puro de diseños de escena para OBS.

Reparte el lienzo entre las fuentes de un diseño y devuelve la
transformación del cuadro delimitador de cada una. No habla con OBS ni con
wx: recibe el lienzo, las fuentes y el diseño, y devuelve diccionarios con
las claves que espera `SetSceneItemTransform`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from guyrapu.obs import obs_disposicion


CLASES = ("pantalla_completa", "imagen_en_imagen", "dividida")
ESQUINAS = ("superior-izquierda", "superior-derecha",
            "inferior-izquierda", "inferior-derecha")
TAMANOS = {"chica": 1 / 5, "mediana": 1 / 4, "grande": 1 / 3}
PROPORCIONES = ("mitades", "dos_tercios", "a_la_medida")
CHATS = ("ninguno", "superpuesto", "franja")
MODOS = ("", "ajustar", "llenar")

ESTADO_LLENA = "llena"
ESTADO_AJUSTA = "ajusta"
ESTADO_AJUSTA_SIN_ORIGEN = "ajusta_sin_origen"

_TIPO_BOUNDS = "OBS_BOUNDS_SCALE_INNER"


@dataclass(frozen=True)
class Fuente:
    """Una fuente de OBS con su tamaño de origen; 0 si OBS no lo informa."""

    nombre: str
    tipo: str = "otra"
    ancho: int = 0
    alto: int = 0


@dataclass(frozen=True)
class Diseno:
    """Los lugares y las opciones de un diseño de escena."""

    clase: str
    principal: str = ""
    secundaria: str = ""
    izquierda: str = ""
    derecha: str = ""
    esquina: str = "inferior-derecha"
    tamano: str = "mediana"
    proporcion: str = "mitades"
    chat: str = "ninguno"
    esquina_chat: str = "inferior-derecha"
    modos: dict = field(default_factory=dict)


def calcular(lienzo_ancho, lienzo_alto, fuentes, diseno):
    """Devuelve las transformaciones del diseño, de arriba abajo.

    La lista va del frente al fondo: primero el chat, después la secundaria
    y al final las demás fuentes. Cada diccionario lleva el nombre de la
    fuente y las claves de transformación que espera OBS.
    """
    if lienzo_ancho <= 0 or lienzo_alto <= 0:
        raise ValueError("El lienzo debe tener ancho y alto positivos")
    _validar_diseno(diseno)
    vertical = lienzo_alto > lienzo_ancho
    por_nombre = {fuente.nombre: fuente for fuente in fuentes}
    area_ancho, area_alto = _area(lienzo_ancho, lienzo_alto, diseno, vertical)
    lugares, orden = _lugares(area_ancho, area_alto, diseno, por_nombre,
                              vertical)
    chat_fuente = _fuente_chat(diseno, por_nombre)
    _validar_lugares(lugares, por_nombre, chat_fuente)
    por_lugar = {
        lugar: _resultado(por_nombre[nombre], rect, _modo(diseno, por_nombre[nombre]))
        for lugar, nombre, rect in lugares
    }
    chat = _resultado_chat(lienzo_ancho, lienzo_alto, area_ancho, area_alto,
                           diseno, chat_fuente, vertical)
    return ([chat] if chat is not None else []) + [por_lugar[lugar]
                                                   for lugar in orden]


def _validar_diseno(diseno):
    if diseno.clase not in CLASES:
        raise ValueError(f"Clase de diseño desconocida: {diseno.clase}")
    if diseno.chat not in CHATS:
        raise ValueError(f"Modo de chat desconocido: {diseno.chat}")
    if diseno.chat in ("superpuesto", "franja") and diseno.esquina_chat not in ESQUINAS:
        raise ValueError(f"Esquina desconocida: {diseno.esquina_chat}")
    if diseno.clase == "imagen_en_imagen":
        if diseno.esquina not in ESQUINAS:
            raise ValueError(f"Esquina desconocida: {diseno.esquina}")
        if diseno.tamano not in TAMANOS:
            raise ValueError(f"Tamaño desconocido: {diseno.tamano}")
    if diseno.clase == "dividida" and diseno.proporcion not in PROPORCIONES:
        raise ValueError(f"Proporción desconocida: {diseno.proporcion}")
    if any(modo not in MODOS for modo in diseno.modos.values()):
        raise ValueError("Modo de ajuste desconocido")


def _area(lienzo_ancho, lienzo_alto, diseno, vertical):
    if diseno.chat != "franja":
        return lienzo_ancho, lienzo_alto
    if vertical:
        franja = int(round(lienzo_alto / 4))
        return lienzo_ancho, lienzo_alto - franja
    franja = int(round(lienzo_ancho / 4))
    return lienzo_ancho - franja, lienzo_alto


def _lugares(area_ancho, area_alto, diseno, por_nombre, vertical):
    if diseno.clase == "pantalla_completa":
        return ([("principal", diseno.principal,
                  (0, 0, area_ancho, area_alto))], ["principal"])
    if diseno.clase == "imagen_en_imagen":
        secundaria = _lugar_secundaria(area_ancho, area_alto, diseno.esquina,
                                       diseno.tamano)
        return ([("principal", diseno.principal,
                  (0, 0, area_ancho, area_alto)),
                 ("secundaria", diseno.secundaria, secundaria)],
                ["secundaria", "principal"])
    izquierda, derecha = _lugares_dividida(area_ancho, area_alto, diseno,
                                           por_nombre, vertical)
    return ([("izquierda", diseno.izquierda, izquierda),
             ("derecha", diseno.derecha, derecha)],
            ["izquierda", "derecha"])


def _lugar_secundaria(area_ancho, area_alto, esquina, tamano):
    ancho = int(round(area_ancho * TAMANOS[tamano]))
    alto = int(round(ancho * 9 / 16))
    x, y, _mascara = obs_disposicion.coordenadas(esquina, area_ancho, area_alto)
    izquierda = x if "izquierda" in esquina else x - ancho
    arriba = y if "superior" in esquina else y - alto
    return int(round(izquierda)), int(round(arriba)), ancho, alto


def _lugares_dividida(area_ancho, area_alto, diseno, por_nombre, vertical):
    fuente = por_nombre.get(diseno.izquierda)
    if vertical:
        alto = _eje_del_primero(area_alto, area_ancho, diseno.proporcion,
                                fuente, vertical=True)
        return ((0, 0, area_ancho, alto),
                (0, alto, area_ancho, area_alto - alto))
    ancho = _eje_del_primero(area_ancho, area_alto, diseno.proporcion,
                             fuente, vertical=False)
    return ((0, 0, ancho, area_alto),
            (ancho, 0, area_ancho - ancho, area_alto))


def _eje_del_primero(eje, otro_eje, proporcion, fuente, vertical):
    if proporcion == "dos_tercios":
        return int(round(eje * 2 / 3))
    if proporcion != "a_la_medida":
        return eje // 2
    if fuente is None or fuente.ancho <= 0 or fuente.alto <= 0:
        return eje // 2
    if vertical:
        deseado = otro_eje * fuente.alto / fuente.ancho
    else:
        deseado = otro_eje * fuente.ancho / fuente.alto
    return int(round(min(max(deseado, eje / 4), eje * 3 / 4)))


def _validar_lugares(lugares, por_nombre, chat_fuente=None):
    nombres = [nombre for _lugar, nombre, _rect in lugares]
    if any(not nombre or nombre not in por_nombre for nombre in nombres):
        raise ValueError("Hay un lugar sin fuente")
    if len(set(nombres)) != len(nombres):
        raise ValueError("La misma fuente está en dos lugares")
    if chat_fuente is not None and chat_fuente.nombre in nombres:
        raise ValueError("La misma fuente está en dos lugares")


def _fuente_chat(diseno, por_nombre):
    if diseno.chat == "ninguno":
        return None
    for fuente in por_nombre.values():
        if fuente.tipo == "chat":
            return fuente
    raise ValueError("El diseño pide chat y no hay una fuente de chat")


def _modo(diseno, fuente):
    modo = diseno.modos.get(fuente.nombre, "")
    if modo:
        return modo
    return "llenar" if fuente.tipo == "camara" else "ajustar"


def _resultado(fuente, rect, modo):
    x, y, ancho, alto = rect
    if modo == "llenar" and fuente.ancho > 0 and fuente.alto > 0:
        recortes = _recortes(fuente.ancho, fuente.alto, ancho, alto)
        estado = ESTADO_LLENA
    else:
        recortes = (0, 0, 0, 0)
        estado = ESTADO_AJUSTA_SIN_ORIGEN if modo == "llenar" else ESTADO_AJUSTA
    return {
        "nombre": fuente.nombre,
        "positionX": x,
        "positionY": y,
        "alignment": 5,
        "boundsType": _TIPO_BOUNDS,
        "boundsAlignment": 0,
        "boundsWidth": ancho,
        "boundsHeight": alto,
        "cropLeft": recortes[0],
        "cropRight": recortes[1],
        "cropTop": recortes[2],
        "cropBottom": recortes[3],
        "estado": estado,
    }


def _recortes(ancho_fuente, alto_fuente, ancho_lugar, alto_lugar):
    """Recortes para que el origen tenga la proporción del lugar.

    El recorte sobrante se reparte por igual a los dos lados del eje que
    sobra, y el píxel impar queda en el segundo lado. Con la proporción
    corregida, el cuadro delimitador llena el lugar sin deformar ni
    pasarse.
    """
    proporcion_lugar = ancho_lugar / alto_lugar
    if ancho_fuente / alto_fuente > proporcion_lugar:
        restante = alto_fuente * proporcion_lugar
        izquierda, derecha = _repartir(
            max(0, int(round(ancho_fuente - restante))))
        return izquierda, derecha, 0, 0
    restante = ancho_fuente / proporcion_lugar
    arriba, abajo = _repartir(max(0, int(round(alto_fuente - restante))))
    return 0, 0, arriba, abajo


def _repartir(total):
    primero = total // 2
    return primero, total - primero


def _resultado_chat(lienzo_ancho, lienzo_alto, area_ancho, area_alto, diseno,
                    fuente, vertical):
    if fuente is None:
        return None
    if diseno.chat == "franja":
        if vertical:
            return {"nombre": fuente.nombre, "positionX": 0,
                    "positionY": area_alto, "alignment": 5,
                    "ancho": lienzo_ancho, "alto": lienzo_alto - area_alto}
        return {"nombre": fuente.nombre, "positionX": area_ancho,
                "positionY": 0, "alignment": 5,
                "ancho": lienzo_ancho - area_ancho, "alto": lienzo_alto}
    x, y, alineacion = obs_disposicion.coordenadas(
        diseno.esquina_chat, lienzo_ancho, lienzo_alto)
    return {"nombre": fuente.nombre, "positionX": x, "positionY": y,
            "alignment": alineacion}
