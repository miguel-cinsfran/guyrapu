# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del espejo de escenas verticales, con un doble de OBS.

Sin ventanas y sin OBS real: el cliente falso guarda escenas, fuentes y
respuestas como lo haría el websocket con el plugin cargado.
"""

import unittest

from guyrapu.obs import espejo_vertical


def _elemento(identificador, indice, fuente, visible=True, bloqueada=False,
              grupo=False):
    return {
        "sceneItemId": identificador,
        "sceneItemIndex": indice,
        "sourceName": fuente,
        "sceneItemEnabled": visible,
        "sceneItemLocked": bloqueada,
        "isGroup": grupo,
        "sceneItemTransform": {
            "positionX": 10 * indice, "positionY": 5 * indice,
            "alignment": 5, "scaleX": 1.5, "scaleY": 1.5,
            "cropLeft": 1, "cropRight": 2, "cropTop": 3, "cropBottom": 4,
            "sourceWidth": 640, "sourceHeight": 360,
            "width": 960, "height": 540,
        },
    }


class ClienteFalso:

    def __init__(self, principales, items_principal, verticales,
                 items_vertical):
        self.principales = list(principales)
        self.items_principal = {nombre: list(items) for nombre, items
                                in items_principal.items()}
        self.verticales = dict(verticales)
        self.items_vertical = {uuid: list(items) for uuid, items
                               in items_vertical.items()}
        self.llamadas = []
        self._uuid = iter(("uuid-nueva",))
        self._item = iter(range(100, 200))

    def pedir(self, tipo, datos=None, parada=None):
        datos = datos or {}
        self.llamadas.append((tipo, dict(datos), parada))
        if tipo == "GetSceneList":
            if "canvasUuid" in datos:
                return {"responseData": {"scenes": [
                    {"sceneName": nombre, "sceneUuid": uuid}
                    for nombre, uuid in self.verticales.items()]}}
            return {"responseData": {"scenes": [
                {"sceneName": nombre} for nombre in self.principales]}}
        if tipo == "GetSceneItemList":
            if "sceneUuid" in datos:
                return {"responseData": {"sceneItems": list(
                    self.items_vertical.get(datos["sceneUuid"], ()))}}
            return {"responseData": {"sceneItems": list(
                self.items_principal.get(datos.get("sceneName"), ()))}}
        if tipo == "CreateScene":
            uuid = next(self._uuid)
            self.verticales[datos["sceneName"]] = uuid
            self.items_vertical[uuid] = []
            return {"responseData": {"sceneUuid": uuid}}
        if tipo == "CreateSceneItem":
            identificador = next(self._item)
            self.items_vertical[datos["sceneUuid"]].append({
                "sceneItemId": identificador,
                "sourceName": datos["sourceName"]})
            return {"responseData": {"sceneItemId": identificador}}
        return {"responseData": {}}

    def de_tipo(self, tipo):
        return [datos for llamado, datos, _parada in self.llamadas
                if llamado == tipo]


class ParejasTest(unittest.TestCase):

    def test_parea_la_version_vertical_con_su_original(self):
        self.assertEqual(
            espejo_vertical.parejas(
                ["Principal", "Principal vertical", "Juego"]),
            [("Principal", "Principal vertical")])

    def test_una_vertical_sin_original_no_es_pareja(self):
        self.assertEqual(espejo_vertical.parejas(["Y vertical"]), [])

    def test_conserva_el_orden_del_principal(self):
        self.assertEqual(
            espejo_vertical.parejas(
                ["B vertical", "A", "A vertical", "B"]),
            [("B", "B vertical"), ("A", "A vertical")])


class EspejarTest(unittest.TestCase):

    def setUp(self):
        self.principal = _elemento(1, 0, "Fondo")
        self.camara = _elemento(2, 0, "Cámara")
        self.grupo = _elemento(3, 1, "Grupo", grupo=True)
        self.chat = _elemento(4, 2, "Chat", visible=False, bloqueada=True)
        self.cliente = ClienteFalso(
            principales=["Principal", "Principal vertical", "Juego",
                         "Juego vertical"],
            items_principal={
                "Principal": [self.principal],
                "Juego": [self.grupo, self.chat, self.camara],
            },
            verticales={"Juego vertical": "uuid-juego",
                        "Suelta vertical": "uuid-suelta"},
            items_vertical={
                "uuid-juego": [_elemento(31, 0, "Vieja"),
                              _elemento(32, 1, "Otra")],
                "uuid-suelta": [_elemento(41, 0, "Algo")],
            })
        self.resultado = espejo_vertical.espejar(
            self.cliente, {"canvasUuid": "uuid-vertical"})

    def test_crea_solo_la_copia_que_faltaba(self):
        self.assertEqual(
            self.cliente.de_tipo("CreateScene"),
            [{"canvasUuid": "uuid-vertical",
              "sceneName": "Principal vertical"}])

    def test_crea_cada_fuente_por_scene_uuid_y_en_orden(self):
        self.assertEqual(
            [(datos["sceneUuid"], datos["sourceName"])
             for datos in self.cliente.de_tipo("CreateSceneItem")],
            [("uuid-nueva", "Fondo"), ("uuid-juego", "Cámara"),
             ("uuid-juego", "Chat")])

    def test_rehacer_borra_las_fuentes_antes_de_crearlas(self):
        borradas = self.cliente.de_tipo("RemoveSceneItem")
        self.assertEqual([datos["sceneItemId"] for datos in borradas],
                         [31, 32])
        self.assertTrue(all(datos["sceneUuid"] == "uuid-juego"
                            for datos in borradas))
        ultima_borrada = max(
            indice for indice, (tipo, datos, _parada)
            in enumerate(self.cliente.llamadas)
            if tipo == "RemoveSceneItem"
            and datos.get("sceneUuid") == "uuid-juego")
        primera_creada = min(
            indice for indice, (tipo, datos, _parada)
            in enumerate(self.cliente.llamadas)
            if tipo == "CreateSceneItem"
            and datos.get("sceneUuid") == "uuid-juego")
        self.assertLess(ultima_borrada, primera_creada)

    def test_no_manda_los_campos_que_calcula_obs(self):
        for datos in self.cliente.de_tipo("SetSceneItemTransform"):
            for campo in ("sourceWidth", "sourceHeight", "width", "height"):
                self.assertNotIn(campo, datos["sceneItemTransform"])

    def test_copia_posicion_escala_y_recorte(self):
        transformaciones = [
            datos["sceneItemTransform"]
            for datos in self.cliente.de_tipo("SetSceneItemTransform")]
        self.assertEqual(transformaciones[0]["positionX"], 0)
        self.assertEqual(transformaciones[0]["scaleX"], 1.5)
        self.assertEqual(transformaciones[0]["cropLeft"], 1)
        self.assertEqual(transformaciones[2]["positionX"], 20)
        self.assertEqual(transformaciones[2]["cropBottom"], 4)

    def test_copia_visibilidad_y_bloqueo(self):
        self.assertEqual(
            [datos["sceneItemEnabled"]
             for datos in self.cliente.de_tipo("SetSceneItemEnabled")],
            [True, True, False])
        self.assertEqual(
            [datos["sceneItemLocked"]
             for datos in self.cliente.de_tipo("SetSceneItemLocked")],
            [False, False, True])

    def test_omite_los_grupos(self):
        fuentes = [datos["sourceName"]
                   for datos in self.cliente.de_tipo("CreateSceneItem")]
        self.assertNotIn("Grupo", fuentes)
        self.assertEqual(self.resultado[1],
                         (("Juego vertical", "Grupo"),))

    def test_no_toca_las_escenas_verticales_sin_pareja(self):
        for _tipo, datos, _parada in self.cliente.llamadas:
            self.assertNotEqual(datos.get("sceneUuid"), "uuid-suelta")
            self.assertNotEqual(datos.get("sceneName"), "Suelta vertical")

    def test_nunca_pide_duplicate_scene_item(self):
        tipos = [tipo for tipo, _datos, _parada in self.cliente.llamadas]
        self.assertNotIn("DuplicateSceneItem", tipos)

    def test_devuelve_las_escenas_copiadas(self):
        self.assertEqual(self.resultado[0],
                         ("Principal vertical", "Juego vertical"))


if __name__ == "__main__":
    unittest.main()
