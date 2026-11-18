# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pone y saca un medio de la biblioteca en la escena propia de Guyrapu.

Sin wx. Recibe un cliente con `pedir(tipo, datos=None, parada=None)` como
`EscenaGuyrapu` y no crea conexiones. Su única razón para cambiar es cómo se
muestra y se reproduce un medio dentro de OBS.
"""

from __future__ import annotations

from guyrapu.interaction import medios
from guyrapu.obs import escena_guyrapu, obs_cliente

# Fijos, sin traducir: son identificadores dentro de OBS.
IMAGEN, MEDIO = "Guyrapu imagen", "Guyrapu medio"

MONITOR_Y_SALIDA = "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT"
REINICIAR = "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"
DETENER = "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_STOP"


def _no_existe(error) -> bool:
    return str(getattr(error, "codigo", "")) == "600"


class MedioObs:
    """Deja un medio debajo de la tarjeta, en la escena «Guyrapu»."""

    def __init__(self, cliente):
        self._cliente = cliente

    def _pedir(self, tipo, datos=None, parada=None):
        respuesta = self._cliente.pedir(tipo, datos, parada)
        return (respuesta or {}).get("responseData", respuesta or {})

    def _item(self, nombre, parada):
        items = self._pedir("GetSceneItemList", {
            "sceneName": escena_guyrapu.ESCENA}, parada).get("sceneItems", ())
        return next((item for item in items
                     if item.get("sourceName") == nombre), None)

    def _asegurar(self, nombre, clase, parada):
        """Crea la entrada y su elemento en la escena si faltan."""
        entradas = {entrada.get("inputName", "") for entrada in
                    self._pedir("GetInputList",
                                parada=parada).get("inputs", ())}
        if nombre not in entradas:
            self._pedir("CreateInput", {
                "sceneName": escena_guyrapu.ESCENA, "inputName": nombre,
                "inputKind": clase, "inputSettings": {}}, parada)
        elif self._item(nombre, parada) is None:
            self._pedir("CreateSceneItem", {
                "sceneName": escena_guyrapu.ESCENA, "sourceName": nombre},
                parada)
        return self._item(nombre, parada)

    def _ajustar(self, item, ancho, alto, parada) -> None:
        self._pedir("SetSceneItemTransform", {
            "sceneName": escena_guyrapu.ESCENA,
            "sceneItemId": item["sceneItemId"],
            "sceneItemTransform": {
                "positionX": 0, "positionY": 0, "alignment": 5,
                "boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsAlignment": 0,
                "boundsWidth": ancho, "boundsHeight": alto}}, parada)

    def _debajo(self, item, indice, parada) -> None:
        self._pedir("SetSceneItemIndex", {
            "sceneName": escena_guyrapu.ESCENA,
            "sceneItemId": item["sceneItemId"],
            "sceneItemIndex": indice}, parada)

    def _habilitar(self, item, visible, parada) -> None:
        self._pedir("SetSceneItemEnabled", {
            "sceneName": escena_guyrapu.ESCENA,
            "sceneItemId": item["sceneItemId"],
            "sceneItemEnabled": visible}, parada)

    def armar(self, ruta, tipo, ganancia_db=None, parada=None) -> None:
        """Deja el medio listo y habilitado, debajo de la tarjeta."""
        if tipo not in medios.CLAVES:
            raise ValueError(f"tipo de medio desconocido: {tipo!r}")
        lienzo = self._pedir("GetVideoSettings", parada=parada)
        ancho = int(lienzo.get("baseWidth") or 0)
        alto = int(lienzo.get("baseHeight") or 0)
        imagen = self._asegurar(IMAGEN, "image_source", parada)
        medio = self._asegurar(MEDIO, "ffmpeg_source", parada)
        if tipo == "imagen":
            self._pedir("SetInputSettings", {
                "inputName": IMAGEN,
                "inputSettings": {"file": str(ruta)}}, parada)
            activo, inactivo = imagen, medio
        else:
            self._pedir("SetInputSettings", {
                "inputName": MEDIO,
                "inputSettings": {
                    "is_local_file": True, "local_file": str(ruta),
                    "restart_on_activate": True,
                    "close_when_inactive": True}}, parada)
            activo, inactivo = medio, imagen
        self._pedir("SetInputVolume", {
            "inputName": MEDIO,
            "inputVolumeDb": 0 if ganancia_db is None else ganancia_db},
            parada)
        self._ajustar(activo, ancho, alto, parada)
        self._debajo(imagen, 0, parada)
        self._debajo(medio, 1, parada)
        self._habilitar(activo, True, parada)
        self._habilitar(inactivo, False, parada)
        if tipo != "imagen":
            self._pedir("SetInputAudioMonitorType", {
                "inputName": MEDIO, "monitorType": MONITOR_Y_SALIDA}, parada)
            self._pedir("TriggerMediaInputAction", {
                "inputName": MEDIO, "mediaAction": REINICIAR}, parada)

    def soltar(self, parada=None) -> None:
        """Detiene el medio y apaga las dos entradas, sin borrarlas."""
        medio = self._item(MEDIO, parada)
        if medio is not None:
            self._pedir("TriggerMediaInputAction", {
                "inputName": MEDIO, "mediaAction": DETENER}, parada)
            self._habilitar(medio, False, parada)
        imagen = self._item(IMAGEN, parada)
        if imagen is not None:
            self._habilitar(imagen, False, parada)

    def quitar_todo(self, parada=None) -> None:
        """Borra las dos entradas del medio, aunque no existan.

        Medido el 18/11/2026: OBS no limpia la escena que no se dibuja hasta
        que pasa por un cuadro; borrar la escena, como hace
        `EscenaGuyrapu.quitar_todo`, la deja en cero.
        """
        for nombre in (IMAGEN, MEDIO):
            try:
                self._pedir("RemoveInput", {"inputName": nombre}, parada)
            except obs_cliente.ObsError as error:
                if not _no_existe(error):
                    raise
