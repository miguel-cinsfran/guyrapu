# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Anima de verdad una tarjeta de texto en el OBS de esta PC.

Corre a mano en la PC donde nadie está: `python qa/animador_real.py`.
Crea una escena de prueba, la anima por el proceso real de Guyrapu, deja
OBS como estaba y sale con 1 si alguna comprobación falla.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from guyrapu.interaction import animacion  # noqa: E402
from guyrapu.obs import obs_activacion  # noqa: E402
from guyrapu.obs import obs_cliente  # noqa: E402
from guyrapu.obs import obs_lanzador  # noqa: E402
from guyrapu.obs import tipos_fuente  # noqa: E402
from guyrapu.obs.animador import Animador  # noqa: E402

ESCENA = "GVA animador"
FUENTE = "GVA texto animador"
FILTRO = "GVA opacidad animador"
TIPO_FILTRO = "color_filter_v2"
ANCHO_TARJETA = 400
ALTO_TARJETA = 100
DURACION = 350
TOPE = 20.0


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {}) or {}


def _pedir(cliente, tipo, datos=None):
    return _datos(cliente.pedir(tipo, datos))


def _comprobar(descripcion, bien, fallos):
    print(("OK " if bien else "FALLA ") + descripcion)
    if not bien:
        fallos.append(descripcion)


def _quitar_lo_creado(cliente):
    escenas = _pedir(cliente, "GetSceneList").get("scenes") or ()
    if any(escena.get("sceneName") == ESCENA for escena in escenas):
        _pedir(cliente, "RemoveScene", {"sceneName": ESCENA})
    entradas = _pedir(cliente, "GetInputList").get("inputs") or ()
    if any(entrada.get("inputName") == FUENTE for entrada in entradas):
        _pedir(cliente, "RemoveInput", {"inputName": FUENTE})


def _preparar(cliente):
    _quitar_lo_creado(cliente)
    _pedir(cliente, "CreateScene", {"sceneName": ESCENA})
    lienzo = _pedir(cliente, "GetVideoSettings")
    ancho = int(lienzo.get("baseWidth") or 1920)
    alto = int(lienzo.get("baseHeight") or 1080)
    tipos = _pedir(cliente, "GetInputKindList", {
        "unversioned": False}).get("inputKinds") or ()
    creada = _pedir(cliente, "CreateInput", {
        "sceneName": ESCENA,
        "inputName": FUENTE,
        "inputKind": tipos_fuente.tipo_de_texto(tipos),
        "inputSettings": {"text": ESCENA},
    })
    elemento = creada.get("sceneItemId")
    if elemento is None:
        raise RuntimeError("OBS no devolvió el id del elemento de prueba.")
    _pedir(cliente, "CreateSourceFilter", {
        "sourceName": FUENTE,
        "filterName": FILTRO,
        "filterKind": TIPO_FILTRO,
        "filterSettings": {"opacity": 1.0},
    })
    x, y = 300.0, 400.0
    _pedir(cliente, "SetSceneItemTransform", {
        "sceneName": ESCENA,
        "sceneItemId": elemento,
        "sceneItemTransform": {"positionX": x, "positionY": y},
    })
    _pedir(cliente, "SetCurrentProgramScene", {"sceneName": ESCENA})
    return elemento, ancho, alto, x, y


def _orden(elemento, x, y, cuadros):
    return {
        "tipo": "animar",
        "escena": ESCENA,
        "elemento": elemento,
        "fuente_filtro": FUENTE,
        "filtro": FILTRO,
        "x": x,
        "y": y,
        "cuadros": [[cuadro.ms, cuadro.dx, cuadro.dy, cuadro.opacidad]
                    for cuadro in cuadros],
    }


def _elemento_actual(cliente, elemento):
    datos = _pedir(cliente, "GetSceneItemList", {"sceneName": ESCENA})
    return next((item for item in datos.get("sceneItems") or ()
                 if item.get("sceneItemId") == elemento), {})


def _opacidad_actual(cliente):
    datos = _pedir(cliente, "GetSourceFilterList", {"sourceName": FUENTE})
    filtro = next((item for item in datos.get("filters") or ()
                   if item.get("filterName") == FILTRO), {})
    return (filtro.get("filterSettings") or {}).get("opacity")


def _restaurar(cliente, escena_anterior):
    if escena_anterior:
        _pedir(cliente, "SetCurrentProgramScene",
               {"sceneName": escena_anterior})
    _quitar_lo_creado(cliente)


def _comprobar_final(cliente, elemento, x, y, fallos):
    transformada = _elemento_actual(
        cliente, elemento).get("sceneItemTransform") or {}
    posicion_x = float(transformada.get("positionX", 0.0))
    posicion_y = float(transformada.get("positionY", 0.0))
    _comprobar("El elemento quedó en su posición",
               abs(posicion_x - x) < 0.5 and abs(posicion_y - y) < 0.5,
               fallos)
    opacidad = _opacidad_actual(cliente)
    _comprobar("El filtro quedó en opacidad 0",
               opacidad is not None and abs(float(opacidad)) < 0.001,
               fallos)


def principal():
    fallos = []
    estaba_abierto = obs_activacion.obs_esta_en_ejecucion()
    cliente = obs_cliente.ClienteObs(obs_cliente.leer_ajustes())
    animador = Animador()
    escena_anterior = ""
    try:
        obs_lanzador.asegurar_obs(cliente.conectar)
        if not estaba_abierto:
            time.sleep(5)
        escena_anterior = _pedir(
            cliente, "GetCurrentProgramScene").get(
                "currentProgramSceneName", "")
        elemento, ancho, alto, x, y = _preparar(cliente)
        desplazamiento_x, _sin_uso = animacion.desplazamiento(
            "derecha", x, y, ANCHO_TARJETA, ALTO_TARJETA, ancho, alto)
        entrada = animador.animar(_orden(
            elemento, x, y,
            animacion.cuadros_entrada("derecha", DURACION,
                                      desplazamiento_x, 0.0)), TOPE)
        _comprobar("La entrada desde la derecha terminó bien", entrada,
                   fallos)
        salida = animador.animar(_orden(
            elemento, x, y,
            animacion.cuadros_salida("fundido", DURACION, 0.0, 0.0)), TOPE)
        _comprobar("La salida con fundido terminó bien", salida, fallos)
        _comprobar_final(cliente, elemento, x, y, fallos)
    except Exception as error:
        print("FALLA El animador no pudo correr: %s" % error)
        fallos.append(str(error))
    finally:
        animador.cerrar()
        if cliente.conectado:
            try:
                _restaurar(cliente, escena_anterior)
            except Exception as error:
                print("FALLA No se pudo dejar OBS como estaba: %s" % error)
                fallos.append(str(error))
        cliente.cerrar()
        if not estaba_abierto:
            obs_lanzador.cerrar_obs()
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(principal())
