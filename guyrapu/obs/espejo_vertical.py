# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Copia al lienzo vertical las versiones verticales de las escenas.

La escena «X vertical» del lienzo principal se copia con el mismo nombre al
lienzo vertical, con las mismas fuentes y su presentación. Si la copia ya
existía, se borran sus fuentes y se vuelven a crear para no arrastrar lo
que se quitó del principal. Un grupo no se copia.
"""

from __future__ import annotations

from guyrapu.obs import escena_gemela, transformar_fuente


def parejas(escenas):
    """Las parejas (original, vertical) del principal, en su orden."""
    nombres = list(escenas)
    resultado = []
    for nombre in nombres:
        original = escena_gemela.original_de(nombre, nombres)
        if original is not None:
            resultado.append((original, nombre))
    return resultado


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {}) or {}


def _escenas_principales(cliente, parada):
    datos = _datos(cliente.pedir("GetSceneList", parada=parada))
    return [escena.get("sceneName", "")
            for escena in datos.get("scenes") or ()]


def _escenas_verticales(cliente, canvas_uuid, parada):
    datos = _datos(cliente.pedir(
        "GetSceneList", {"canvasUuid": canvas_uuid}, parada))
    return {escena.get("sceneName", ""): escena.get("sceneUuid")
            for escena in datos.get("scenes") or ()}


def _elementos(cliente, consulta, parada):
    datos = _datos(cliente.pedir("GetSceneItemList", consulta, parada))
    return sorted(datos.get("sceneItems") or (),
                  key=lambda elemento: elemento.get("sceneItemIndex", 0))


def _crear_escena(cliente, canvas_uuid, nombre, parada):
    datos = _datos(cliente.pedir("CreateScene", {
        "canvasUuid": canvas_uuid, "sceneName": nombre}, parada))
    return datos.get("sceneUuid")


def _vaciar(cliente, scene_uuid, parada):
    for elemento in _elementos(cliente, {"sceneUuid": scene_uuid}, parada):
        cliente.pedir("RemoveSceneItem", {
            "sceneUuid": scene_uuid,
            "sceneItemId": elemento.get("sceneItemId")}, parada)


def _copiar(cliente, scene_uuid, elemento, parada):
    datos = _datos(cliente.pedir("CreateSceneItem", {
        "sceneUuid": scene_uuid,
        "sourceName": elemento.get("sourceName", "")}, parada))
    identificador = datos.get("sceneItemId")
    if identificador is None:
        return
    transformacion = transformar_fuente.limpiar_transformacion(
        elemento.get("sceneItemTransform") or {})
    cliente.pedir("SetSceneItemTransform", {
        "sceneUuid": scene_uuid, "sceneItemId": identificador,
        "sceneItemTransform": transformacion}, parada)
    cliente.pedir("SetSceneItemEnabled", {
        "sceneUuid": scene_uuid, "sceneItemId": identificador,
        "sceneItemEnabled": bool(elemento.get("sceneItemEnabled", True))},
        parada)
    cliente.pedir("SetSceneItemLocked", {
        "sceneUuid": scene_uuid, "sceneItemId": identificador,
        "sceneItemLocked": bool(elemento.get("sceneItemLocked", False))},
        parada)


def espejar(cliente, lienzo, parada=None):
    """Copia cada versión vertical del principal al lienzo vertical.

    Devuelve las escenas copiadas y las fuentes omitidas, como dos tuplas.
    """
    canvas_uuid = (lienzo or {}).get("canvasUuid")
    if not canvas_uuid:
        return ((), ())
    principales = _escenas_principales(cliente, parada)
    existentes = _escenas_verticales(cliente, canvas_uuid, parada)
    copiadas, omitidas = [], []
    for original, vertical in parejas(principales):
        scene_uuid = existentes.get(vertical)
        if scene_uuid is None:
            scene_uuid = _crear_escena(cliente, canvas_uuid, vertical,
                                       parada)
            existentes[vertical] = scene_uuid
        else:
            _vaciar(cliente, scene_uuid, parada)
        for elemento in _elementos(
                cliente, {"sceneName": original}, parada):
            if elemento.get("isGroup"):
                omitidas.append((vertical, elemento.get("sourceName", "")))
                continue
            _copiar(cliente, scene_uuid, elemento, parada)
        copiadas.append(vertical)
    return (tuple(copiadas), tuple(omitidas))
