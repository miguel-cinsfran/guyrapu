# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Problemas de encuadre de una escena de OBS dichos en palabras.

Mira solo las fuentes visibles, de adelante hacia atrás, con el rectángulo
que dibuja OBS. Devuelve lo grave para los problemas y lo leve para los
avisos. Es lógica pura: recibe los elementos de `GetSceneItemList` y el
lienzo.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.idioma import N_, _
from guyrapu.obs import geometria_fuente, obs_disposicion

_FUERA_AVISO = 10.0
_FUERA_PROBLEMA = 50.0
_FUERA_ENTERA = 99.5
_TAPA_AVISO = 50.0
_TAPA_PROBLEMA = 95.0
_DEFORMA_AVISO = 10.0
_DEFORMA_PROBLEMA = 50.0
_VACIO_AVISO = 15.0
_VACIO_PROBLEMA = 50.0

_MOTIVOS = {
    "window_capture": N_("la ventana capturada no está abierta o está "
                         "minimizada"),
    "game_capture": N_("el juego no está abierto o OBS todavía no lo captura"),
    "monitor_capture": N_("OBS no puede capturar esa pantalla"),
    "dshow_input": N_("la cámara no está conectada o la está usando otra "
                      "aplicación"),
}


@dataclass(frozen=True, slots=True)
class Hallazgos:
    problemas: tuple
    avisos: tuple


def _area(rect) -> float:
    return max(0.0, rect[2]) * max(0.0, rect[3])


def _recortar(rect, ancho, alto):
    izquierda = max(0.0, rect[0])
    arriba = max(0.0, rect[1])
    derecha = min(float(ancho), rect[0] + rect[2])
    abajo = min(float(alto), rect[1] + rect[3])
    return izquierda, arriba, max(0.0, derecha - izquierda), \
        max(0.0, abajo - arriba)


def _union(rects) -> float:
    """Área exacta de la unión de rectángulos, por franjas verticales."""
    if not rects:
        return 0.0
    bordes = sorted({rect[0] for rect in rects}
                    | {rect[0] + rect[2] for rect in rects})
    area = 0.0
    for izquierda, derecha in zip(bordes, bordes[1:]):
        if derecha <= izquierda:
            continue
        intervalos = sorted(
            (rect[1], rect[1] + rect[3]) for rect in rects
            if rect[0] <= izquierda and rect[0] + rect[2] >= derecha)
        alto = 0.0
        inicio = fin = None
        for arriba, abajo in intervalos:
            if inicio is None:
                inicio, fin = arriba, abajo
            elif arriba > fin:
                alto += fin - inicio
                inicio, fin = arriba, abajo
            else:
                fin = max(fin, abajo)
        if inicio is not None:
            alto += fin - inicio
        area += (derecha - izquierda) * alto
    return area


def _lados(rect, ancho, alto) -> str:
    salidas = []
    if rect[0] < 0:
        salidas.append(_("por la izquierda"))
    if rect[0] + rect[2] > ancho:
        salidas.append(_("por la derecha"))
    if rect[1] < 0:
        salidas.append(_("por arriba"))
    if rect[1] + rect[3] > alto:
        salidas.append(_("por abajo"))
    # Traductores: conjunción entre los lados por los que se sale del vídeo.
    return _(" y ").join(salidas)


def _salida(rect, ancho, alto) -> tuple:
    porcentaje = obs_disposicion.fuera_del_lienzo(rect, ancho, alto)
    if porcentaje < _FUERA_AVISO:
        return None
    texto = (_("La fuente {nombre} queda entera fuera del vídeo el "
               "{porcentaje} por ciento, {lados}.")
             if porcentaje >= _FUERA_ENTERA else
             _("La fuente {nombre} queda fuera del vídeo el {porcentaje} "
               "por ciento, {lados}."))
    return porcentaje, texto


def _tapa(rect, delanteros) -> tuple:
    nombre = ""
    maximo = 0.0
    for otro_nombre, otro_rect in delanteros:
        porcentaje = obs_disposicion.solape(otro_rect, rect)
        if porcentaje > maximo:
            nombre, maximo = otro_nombre, porcentaje
    return nombre, maximo


def _deformacion(medida) -> tuple:
    factor = medida.deformacion
    if factor > 1:
        return (factor - 1) * 100, _("La fuente {nombre} está estirada a lo "
                                     "ancho el {porcentaje} por ciento.")
    if 0 < factor < 1:
        return (1 / factor - 1) * 100, _("La fuente {nombre} está estirada a "
                                         "lo alto el {porcentaje} por ciento.")
    return 0.0, ""


def _revisar_fuente(elemento, ancho, alto, delanteros, problemas, avisos):
    """Suma los hallazgos de una fuente y dice si contó para el encuadre."""
    nombre = str(elemento.get("sourceName") or _("sin nombre"))
    clase = str(elemento.get("inputKind") or "")
    medida = geometria_fuente.medir(elemento.get("sceneItemTransform"))
    if medida is None or not medida.tiene_imagen:
        motivo = _MOTIVOS.get(clase)
        if motivo:
            # Traductores: {nombre} es la fuente y {motivo} el porqué.
            avisos.append(_("La fuente {nombre} no muestra imagen: "
                            "{motivo}.").format(nombre=nombre,
                                                motivo=_(motivo)))
        return False, False, None
    rect = medida.rectangulo
    hubo_encuadre = hubo_problema = False
    salida = _salida(rect, ancho, alto)
    if salida is not None:
        porcentaje, texto = salida
        destino = problemas if porcentaje >= _FUERA_PROBLEMA else avisos
        destino.append(texto.format(
            nombre=nombre, porcentaje=int(round(porcentaje)),
            lados=_lados(rect, ancho, alto)))
        hubo_encuadre = True
        hubo_problema = porcentaje >= _FUERA_PROBLEMA
    entera = salida is not None and salida[0] >= _FUERA_ENTERA
    if not entera:
        tapa, tapada = _tapa(rect, delanteros)
        if tapa and tapada >= _TAPA_AVISO:
            destino = problemas if tapada >= _TAPA_PROBLEMA else avisos
            # Traductores: {porcentaje} es un número y {tapa} una fuente.
            destino.append(_("La fuente {nombre} está tapada el "
                             "{porcentaje} por ciento por "
                             "{tapa}.").format(
                                 nombre=nombre,
                                 porcentaje=int(round(tapada)), tapa=tapa))
            hubo_encuadre = True
            hubo_problema = hubo_problema or tapada >= _TAPA_PROBLEMA
    deformada, texto = _deformacion(medida)
    if deformada >= _DEFORMA_AVISO:
        destino = problemas if deformada >= _DEFORMA_PROBLEMA else avisos
        destino.append(texto.format(
            nombre=nombre, porcentaje=int(round(deformada))))
        hubo_encuadre = True
        hubo_problema = hubo_problema or deformada >= _DEFORMA_PROBLEMA
    delanteros.append((nombre, rect))
    return hubo_encuadre, hubo_problema, rect


def revisar(elementos, lienzo_ancho, lienzo_alto) -> Hallazgos:
    """Problemas y avisos de encuadre de la escena, en frases."""
    try:
        ancho = float(lienzo_ancho)
        alto = float(lienzo_alto)
    except (TypeError, ValueError):
        return Hallazgos((), ())
    if ancho <= 0 or alto <= 0:
        return Hallazgos((), ())
    problemas = []
    avisos = []
    delanteros = []
    rectangulos = []
    hubo_encuadre = False
    hubo_problema = False
    for elemento in sorted(
            elementos or (),
            key=lambda elemento: elemento.get("sceneItemIndex", 0),
            reverse=True):
        if not bool(elemento.get("sceneItemEnabled", True)):
            continue
        conto, grave, rect = _revisar_fuente(
            elemento, ancho, alto, delanteros, problemas, avisos)
        hubo_encuadre = hubo_encuadre or conto
        hubo_problema = hubo_problema or grave
        if rect is not None:
            rectangulos.append(_recortar(rect, ancho, alto))
    if any(_area(rect) > 0 for rect in rectangulos):
        vacio = (ancho * alto - _union(rectangulos)) / (ancho * alto) * 100
        if vacio >= _VACIO_AVISO:
            destino = problemas if vacio >= _VACIO_PROBLEMA else avisos
            # Traductores: {porcentaje} es un número.
            destino.append(_("Queda vacío el {porcentaje} por ciento del "
                             "vídeo, sin ninguna fuente visible con "
                             "imagen.").format(porcentaje=int(round(vacio))))
            hubo_encuadre = True
            hubo_problema = hubo_problema or vacio >= _VACIO_PROBLEMA
    if hubo_encuadre:
        consejo = _("Para acomodar la escena, usa Aplicar diseño, en la "
                    "pestaña Escena del Panel de OBS.")
        (problemas if hubo_problema else avisos).append(consejo)
    return Hallazgos(tuple(problemas), tuple(avisos))
