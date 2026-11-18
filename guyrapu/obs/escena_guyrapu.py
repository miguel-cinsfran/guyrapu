# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La escena propia de Guyrapu en OBS: tarjeta, texto y fondo, sin wx."""

from __future__ import annotations

import base64
import time
from collections import namedtuple

from guyrapu.core import esperas, paths
from guyrapu.core.tiempo import resolver_tiempo
from guyrapu.interaction import zonas
from guyrapu.obs import estilos_aviso, fondo_tarjeta, fuentes_windows
from guyrapu.obs import luz_imagen
from guyrapu.obs import obs_cliente
from guyrapu.obs.fondo_guardado import borrar, guardar_fondo

# Fijos, sin traducir: son identificadores dentro de OBS.
ESCENA, TARJETA, TEXTO, FONDO, OPACIDAD = (
    "Guyrapu", "Guyrapu tarjeta", "Guyrapu texto", "Guyrapu fondo",
    "Guyrapu opacidad")

_ALINEACIONES = {"izquierda": "left", "centro": "center", "derecha": "right",
                 "left": "left", "center": "center", "right": "right"}


Tarjeta = namedtuple("Tarjeta", "x y ancho alto escena aviso_fuente")


def _no_existe(error) -> bool:
    return str(getattr(error, "codigo", "")) == "600"


def _color_obs(codigo) -> int:
    """El color #RRGGBB como entero 0xAABBGGRR con alfa 255."""
    try:
        rojo = int(codigo[1:3], 16)
        verde = int(codigo[3:5], 16)
        azul = int(codigo[5:7], 16)
    except (TypeError, ValueError, IndexError):
        rojo = verde = azul = 0
    return 0xFF000000 | (azul << 16) | (verde << 8) | rojo


def _ajustes_de_estilo(estilo, fuente, tamano, ancho, alto) -> dict:
    contorno = estilos_aviso.contorno_en_pixeles(estilo, ancho, alto)
    return {
        "font": {"face": fuente, "size": tamano,
                 "flags": 1 if bool(estilo.get("negrita")) else 0},
        "color": _color_obs(str(estilo.get("color_texto", "#FFFFFF"))),
        "outline": contorno > 0,
        "outline_size": contorno,
        "outline_color": _color_obs(
            str(estilo.get("color_contorno", "#000000"))),
        "align": _ALINEACIONES.get(
            str(estilo.get("alineacion", "izquierda")), "left"),
        "valign": "top",
    }


def _pixel_bmp(datos):
    cabecera = luz_imagen._cabecera(datos)
    if cabecera is None:
        return None
    ancho, alto, bits, inicio = cabecera
    paso = ((ancho * (bits // 8) + 3) // 4) * 4
    base = inicio + (alto // 2) * paso + (ancho // 2) * (bits // 8)
    return (datos[base + 2], datos[base + 1], datos[base],
            datos[base + 3] if bits == 32 else 255)


def _parecido(pixel, objetivo) -> bool:
    if abs(pixel[3] - objetivo[3]) > 8:
        return False
    if max(abs(uno - otro) for uno, otro in
           zip(pixel[:3], objetivo[:3])) <= 8:
        return True
    if pixel[3]:
        rectos = tuple(round(canal * 255 / pixel[3])
                       for canal in pixel[:3])
        return max(abs(uno - otro) for uno, otro in
                   zip(rectos, objetivo[:3])) <= 8
    return False


class EscenaGuyrapu:
    """Arma, muestra y quita la capa propia de Guyrapu dentro de OBS."""

    def __init__(self, cliente):
        self._cliente = cliente
        self._escena = ""

    def _pedir(self, tipo, datos=None, parada=None):
        respuesta = self._cliente.pedir(tipo, datos, parada)
        return (respuesta or {}).get("responseData", respuesta or {})

    def _escenas(self, parada) -> list:
        return [escena.get("sceneName", "") for escena in
                self._pedir("GetSceneList", parada=parada).get("scenes", ())]

    def _items(self, escena, parada) -> list:
        return self._pedir("GetSceneItemList", {"sceneName": escena},
                           parada).get("sceneItems", ())

    def _item(self, escena, nombre, parada):
        return next((item for item in self._items(escena, parada)
                     if item.get("sourceName") == nombre), None)

    def _quitar(self, escena, fuente, parada) -> None:
        try:
            item = self._item(escena, fuente, parada)
            if item is not None:
                self._pedir("RemoveSceneItem", {
                    "sceneName": escena,
                    "sceneItemId": item["sceneItemId"]}, parada)
        except obs_cliente.ObsError as error:
            if not _no_existe(error):
                raise

    def preparar(self, parada=None) -> None:
        """Deja las escenas, entradas y filtro propios, sin duplicarlos."""
        escenas = set(self._escenas(parada))
        if TARJETA not in escenas:
            self._pedir("CreateScene", {"sceneName": TARJETA}, parada)
        if ESCENA not in escenas:
            self._pedir("CreateScene", {"sceneName": ESCENA}, parada)
        for nombre in self._escenas(parada):
            if nombre not in (ESCENA, TARJETA):
                self._quitar(nombre, ESCENA, parada)
        self._asegurar_entradas(parada)
        self._asegurar_tarjeta(parada)
        self._asegurar_filtro(parada)

    def _asegurar_entradas(self, parada) -> None:
        entradas = {entrada.get("inputName", "") for entrada in
                    self._pedir("GetInputList",
                                parada=parada).get("inputs", ())}
        for nombre, tipo in ((FONDO, "image_source"),
                             (TEXTO, "text_gdiplus_v3")):
            if nombre not in entradas:
                self._pedir("CreateInput", {
                    "sceneName": TARJETA, "inputName": nombre,
                    "inputKind": tipo, "inputSettings": {}}, parada)
            elif self._item(TARJETA, nombre, parada) is None:
                self._pedir("CreateSceneItem", {
                    "sceneName": TARJETA, "sourceName": nombre}, parada)
        items = {item.get("sourceName"): item
                 for item in self._items(TARJETA, parada)}
        for nombre, indice in ((FONDO, 0), (TEXTO, 1)):
            item = items.get(nombre)
            if item is not None and item.get("sceneItemIndex") != indice:
                self._pedir("SetSceneItemIndex", {
                    "sceneName": TARJETA,
                    "sceneItemId": item["sceneItemId"],
                    "sceneItemIndex": indice}, parada)

    def _asegurar_tarjeta(self, parada) -> None:
        item = self._item(ESCENA, TARJETA, parada)
        if item is None:
            datos = self._pedir("CreateSceneItem", {
                "sceneName": ESCENA, "sourceName": TARJETA}, parada)
            identificador = datos.get("sceneItemId")
        else:
            identificador = item["sceneItemId"]
        self._pedir("SetSceneItemTransform", {
            "sceneName": ESCENA, "sceneItemId": identificador,
            "sceneItemTransform": {
                "positionX": 0, "positionY": 0, "alignment": 5,
                "scaleX": 1, "scaleY": 1}}, parada)
        self._pedir("SetSceneItemEnabled", {
            "sceneName": ESCENA, "sceneItemId": identificador,
            "sceneItemEnabled": True}, parada)

    def _visible_tarjeta(self, visible, parada) -> None:
        item = self._item(ESCENA, TARJETA, parada)
        self._pedir("SetSceneItemEnabled", {
            "sceneName": ESCENA, "sceneItemId": item["sceneItemId"],
            "sceneItemEnabled": visible}, parada)

    def _asegurar_filtro(self, parada) -> None:
        filtros = self._pedir("GetSourceFilterList", {"sourceName": TARJETA},
                              parada).get("filters", ())
        if not any(filtro.get("filterName") == OPACIDAD
                   for filtro in filtros):
            self._pedir("CreateSourceFilter", {
                "sourceName": TARJETA, "filterName": OPACIDAD,
                "filterKind": "color_filter_v2",
                "filterSettings": {"opacity": 1}}, parada)
        self._pedir("SetSourceFilterSettings", {
            "sourceName": TARJETA, "filterName": OPACIDAD,
            "filterSettings": {"opacity": 1}}, parada)

    def _esperar_fondo(self, estilo, parada, esperar) -> None:
        entero = _color_obs(str(estilo.get("color_fondo", "#000000")))
        alfa = int(round(255 * float(estilo.get("opacidad_fondo", 0) or 0) / 100))
        objetivo = (entero & 255, entero >> 8 & 255, entero >> 16 & 255, alfa)

        def consultar():
            datos = self._pedir("GetSourceScreenshot", {
                "sourceName": FONDO, "imageFormat": "bmp",
                "imageWidth": 16}, parada)
            return _pixel_bmp(base64.b64decode(
                str(datos.get("imageData", "")).split(",")[-1]))

        esperas.esperar(
            consultar, lambda pixel: pixel is not None and _parecido(pixel, objetivo),
            cadencia=esperas.Fija(0.03), plazo=2,
            tolerar=(obs_cliente.ObsError,), tiempo=resolver_tiempo(None, esperar))

    def armar(self, texto, estilo, parada=None, esperar=time.sleep) -> Tarjeta:
        """Deja la tarjeta lista en la escena propia, sin ponerla al frente."""
        lienzo = self._pedir("GetVideoSettings", parada=parada)
        ancho = int(lienzo.get("baseWidth") or 0)
        alto = int(lienzo.get("baseHeight") or 0)
        fuente, aviso = estilos_aviso.fuente_para(
            estilo, fuentes_windows.familias())
        tamano = estilos_aviso.tamano_en_pixeles(estilo, ancho, alto)
        self._pedir("SetInputSettings", {
            "inputName": TEXTO,
            "inputSettings": _ajustes_de_estilo(
                estilo, fuente, tamano, ancho, alto)}, parada)
        ancho_texto, alto_texto = self._acomodar(
            texto, estilo, fuente, tamano, ancho, alto, parada)
        if float(estilo.get("opacidad_fondo", 0) or 0) > 0:
            margen_x = int(round(0.6 * tamano))
            margen_y = int(round(0.3 * tamano))
            ancho_tarjeta = ancho_texto + 2 * margen_x
            alto_tarjeta = alto_texto + 2 * margen_y
            escala = min(ancho, alto) / 1080
            fondo = fondo_tarjeta.fondo(
                ancho_tarjeta, alto_tarjeta,
                str(estilo.get("color_fondo", "#000000")),
                float(estilo.get("opacidad_fondo", 0) or 0),
                str(estilo.get("esquinas", "rectas")) == "redondeadas",
                bool(estilo.get("sombra", False)), escala)
            ruta = guardar_fondo(
                fondo.png, ancho_tarjeta, alto_tarjeta, estilo, escala)
            self._pedir("SetInputSettings", {
                "inputName": FONDO,
                "inputSettings": {"file": str(ruta)}}, parada)
            self._habilitar(FONDO, True, parada)
            self._esperar_fondo(estilo, parada, esperar)
        else:
            margen_x = margen_y = 0
            ancho_tarjeta = ancho_texto
            alto_tarjeta = alto_texto
            fondo = None
            self._habilitar(FONDO, False, parada)
        x, y = zonas.posicion(
            str(estilo.get("zona", "automatica")), ancho, alto,
            ancho_tarjeta, alto_tarjeta)
        self._ubicar(TEXTO, x + margen_x, y + margen_y, parada)
        if fondo is not None:
            self._ubicar(FONDO, x - fondo.x_tarjeta,
                         y - fondo.y_tarjeta, parada)
        return Tarjeta(x, y, ancho_tarjeta, alto_tarjeta, "", aviso)

    def mostrar(self, texto, estilo, parada=None, esperar=time.sleep) -> Tarjeta:
        """Arma la tarjeta con el estilo y la pone encima de lo que está al aire."""
        tarjeta = self.armar(texto, estilo, parada, esperar)
        self._visible_tarjeta(True, parada)
        escena = self._al_frente(parada)
        self._escena = escena
        return tarjeta._replace(escena=escena)

    def mostrar_sin_tarjeta(self, parada=None) -> None:
        """Pone la escena al frente con el elemento de la tarjeta apagado."""
        self._visible_tarjeta(False, parada)
        self._escena = self._al_frente(parada)

    def _acomodar(self, texto, estilo, fuente, tamano, ancho, alto,
                  parada) -> tuple:
        medir = fuentes_windows.medidor(
            fuente, tamano, bool(estilo.get("negrita")))
        margen_x = (int(round(0.6 * tamano))
                    if float(estilo.get("opacidad_fondo", 0) or 0) > 0 else 0)
        cabe = max(1, zonas.area_segura(ancho, alto)[2] - 2 * margen_x)
        limite = cabe
        for _intento in range(4):
            lineas = fuentes_windows.partir_en_lineas(texto, limite, medir)
            self._pedir("SetInputSettings", {
                "inputName": TEXTO,
                "inputSettings": {"text": "\n".join(lineas)}}, parada)
            medida = self._medir_texto(parada)
            if medida[0] <= cabe:
                break
            limite = max(1, int(limite * 0.9))
        return medida

    def _medir_texto(self, parada) -> tuple:
        item = self._item(TARJETA, TEXTO, parada)
        anterior = [None]

        def consultar():
            datos = self._pedir("GetSceneItemTransform", {
                "sceneName": TARJETA,
                "sceneItemId": item["sceneItemId"]}, parada)
            transformacion = datos.get("sceneItemTransform", {})
            medida = (int(round(float(transformacion.get("sourceWidth") or 0))),
                      int(round(float(transformacion.get("sourceHeight") or 0))))
            estable = medida == anterior[0] and all(medida)
            anterior[0] = medida
            return medida, estable

        return esperas.esperar(
            consultar, lambda resultado: resultado[1], cadencia=esperas.Fija(0.05),
            plazo=2, tiempo=resolver_tiempo(None, time.sleep)).valor[0]

    def _habilitar(self, fuente, visible, parada) -> None:
        item = self._item(TARJETA, fuente, parada)
        self._pedir("SetSceneItemEnabled", {
            "sceneName": TARJETA, "sceneItemId": item["sceneItemId"],
            "sceneItemEnabled": visible}, parada)

    def _ubicar(self, fuente, x, y, parada) -> None:
        item = self._item(TARJETA, fuente, parada)
        self._pedir("SetSceneItemTransform", {
            "sceneName": TARJETA, "sceneItemId": item["sceneItemId"],
            "sceneItemTransform": {
                "positionX": int(x), "positionY": int(y),
                "alignment": 5, "scaleX": 1, "scaleY": 1}}, parada)

    def en_el_programa(self, parada=None) -> bool:
        """Si la escena de Guyrapu está puesta en la que sale al aire."""
        programa = self._pedir("GetSceneList", parada=parada).get(
            "currentProgramSceneName", "") or ""
        if programa in (ESCENA, TARJETA):
            return True
        return any(item.get("sourceName") == ESCENA
                   for item in self._items(programa, parada))

    def _al_frente(self, parada) -> str:
        programa = self._pedir("GetCurrentProgramScene", parada=parada).get(
            "currentProgramSceneName", "") or ""
        if programa in (ESCENA, TARJETA):
            return ""
        items = list(self._items(programa, parada))
        item = next((candidato for candidato in items
                     if candidato.get("sourceName") == ESCENA), None)
        if item is None:
            self._pedir("CreateSceneItem", {
                "sceneName": programa, "sourceName": ESCENA}, parada)
        else:
            self._pedir("SetSceneItemIndex", {
                "sceneName": programa,
                "sceneItemId": item["sceneItemId"],
                "sceneItemIndex": len(items) - 1}, parada)
        return programa

    def ocultar(self, parada=None) -> None:
        """Saca la escena de Guyrapu de donde la puso `mostrar`."""
        escena = self._escena
        self._escena = ""
        if escena:
            self._quitar(escena, ESCENA, parada)

    def quitar_todo(self, parada=None, esperar=time.sleep) -> None:
        """Deja OBS como si Guyrapu nunca hubiera mostrado nada."""
        # Import diferido: medio_obs toma ESCENA de este módulo.
        from guyrapu.obs import medio_obs
        self._escena = ""
        for escena in self._escenas(parada):
            self._quitar(escena, ESCENA, parada)
        for tipo, datos in (
                ("RemoveScene", {"sceneName": ESCENA}),
                ("RemoveScene", {"sceneName": TARJETA}),
                ("RemoveInput", {"inputName": TEXTO}),
                ("RemoveInput", {"inputName": FONDO}),
                ("RemoveInput", {"inputName": medio_obs.IMAGEN}),
                ("RemoveInput", {"inputName": medio_obs.MEDIO})):
            try:
                self._pedir(tipo, datos, parada)
            except obs_cliente.ObsError as error:
                if not _no_existe(error):
                    raise
        carpeta = paths.fondos_de_avisos()
        if carpeta.is_dir():
            for ruta in carpeta.glob("*.png"):
                borrar(ruta, esperar)

    def captura(self, parada=None) -> bytes:
        """El PNG de la escena de Guyrapu."""
        datos = self._pedir("GetSourceScreenshot", {
            "sourceName": ESCENA, "imageFormat": "png"}, parada)
        imagen = str(datos.get("imageData", "") or "")
        if "," in imagen:
            imagen = imagen.split(",", 1)[1]
        return base64.b64decode(imagen)
