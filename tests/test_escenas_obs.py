# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las peticiones de escenas a OBS, con un doble."""

import unittest

from guyrapu.obs import escenas_obs, obs_cliente
from guyrapu.ui import escena_menu_escena
from tests.letras_acceso import _letra_de_acceso


class PedirFalso:

    def __init__(self, respuestas=None, fallo=None, fallos=None):
        self.llamadas = []
        self._respuestas = respuestas or {}
        self._fallo = fallo
        self._fallos = fallos or {}

    def __call__(self, tipo, datos=None, parada=None):
        self.llamadas.append((tipo, datos or {}, parada))
        if self._fallo is not None:
            raise self._fallo
        if tipo in self._fallos:
            raise self._fallos[tipo]
        respuesta = self._respuestas.get(tipo, {})
        return respuesta(datos or {}) if callable(respuesta) else respuesta


class GestorFalso:

    def __init__(self, elementos=None):
        self._elementos = elementos or {}
        self.llamadas = []

    def elementos(self, escena, parada=None):
        self.llamadas.append((escena, parada))
        return list(self._elementos.get(escena, ()))


def _elemento(identificador, indice, nombre, visible=True):
    return {
        "sceneItemId": identificador,
        "sceneItemIndex": indice,
        "sourceName": nombre,
        "sceneItemEnabled": visible,
        "sceneItemTransform": {
            "positionX": 10 * indice, "positionY": 5 * indice,
            "alignment": 5, "scaleX": 1.5, "scaleY": 1.5},
    }


class TestPeticiones(unittest.TestCase):

    def test_crear_una_escena(self):
        pedir = PedirFalso()
        escenas_obs.crear(pedir, "Charla")
        self.assertEqual(
            pedir.llamadas,
            [("CreateScene", {"sceneName": "Charla"}, None)])

    def test_cambiar_el_nombre(self):
        pedir = PedirFalso()
        escenas_obs.renombrar(pedir, "Juego", "Charla")
        self.assertEqual(
            pedir.llamadas,
            [("SetSceneName", {"sceneName": "Juego",
                               "newSceneName": "Charla"}, None)])

    def test_eliminar_una_escena(self):
        pedir = PedirFalso()
        escenas_obs.eliminar(pedir, "Juego")
        self.assertEqual(
            pedir.llamadas,
            [("RemoveScene", {"sceneName": "Juego"}, None)])

    def test_contar_las_fuentes_de_una_escena(self):
        gestor = GestorFalso({"Juego": [object(), object(), object()]})
        self.assertEqual(escenas_obs.contar_fuentes(gestor, "Juego"), 3)
        self.assertEqual(gestor.llamadas, [("Juego", None)])

    def test_el_inventario_conserva_el_orden_de_las_escenas(self):
        gestor = GestorFalso({
            "Juego": [object()],
            "Vacía": [],
        })
        self.assertEqual(
            escenas_obs.inventario(gestor, ("Juego", "Vacía")),
            (("Juego", 1), ("Vacía", 0)))


class TestDuplicar(unittest.TestCase):

    def setUp(self):
        self.fuentes = [
            _elemento(1, 0, "Cámara"),
            _elemento(2, 1, "Juego"),
            _elemento(3, 2, "Chat en el vídeo", visible=False),
        ]
        self.nuevos = iter((11, 12, 13))
        self.pedir = PedirFalso({
            "GetSceneItemList": {"sceneItems": [
                self.fuentes[2], self.fuentes[0], self.fuentes[1]]},
            "DuplicateSceneItem": lambda _datos: {
                "sceneItemId": next(self.nuevos)},
        })
        escenas_obs.duplicar(self.pedir, "Principal", "Principal - copia")

    def _de_tipo(self, tipo):
        return [datos for llamado, datos, _parada in self.pedir.llamadas
                if llamado == tipo]

    def test_crea_la_escena_de_destino(self):
        self.assertEqual(
            self._de_tipo("CreateScene"),
            [{"sceneName": "Principal - copia"}])

    def test_duplica_cada_fuente_en_el_orden_de_la_escena(self):
        self.assertEqual(
            [datos["sceneItemId"] for datos in self._de_tipo(
                "DuplicateSceneItem")],
            [1, 2, 3])

    def test_cada_duplicado_lleva_la_escena_de_destino(self):
        for datos in self._de_tipo("DuplicateSceneItem"):
            self.assertEqual(datos["sceneName"], "Principal")
            self.assertEqual(datos["destinationSceneName"],
                             "Principal - copia")

    def test_no_crea_fuentes_nuevas(self):
        self.assertEqual(self._de_tipo("CreateInput"), [])
        self.assertEqual(self._de_tipo("CreateSceneItem"), [])

    def test_conserva_el_indice(self):
        self.assertEqual(
            [datos["sceneItemIndex"] for datos in self._de_tipo(
                "SetSceneItemIndex")],
            [0, 1, 2])

    def test_no_manda_la_transformacion(self):
        self.assertEqual(self._de_tipo("SetSceneItemTransform"), [])

    def test_conserva_la_visibilidad(self):
        self.assertEqual(
            [datos["sceneItemEnabled"] for datos in self._de_tipo(
                "SetSceneItemEnabled")], [True, True, False])

    def test_si_falla_el_duplicado_quita_la_copia_y_propaga(self):
        pedir = PedirFalso(
            {"GetSceneItemList": {"sceneItems": [self.fuentes[0]]}},
            fallos={"DuplicateSceneItem": obs_cliente.ObsError("sin cupo")})
        with self.assertRaises(obs_cliente.ObsError) as contexto:
            escenas_obs.duplicar(pedir, "Principal", "Principal - copia")
        self.assertEqual(str(contexto.exception), "sin cupo")
        self.assertEqual(
            pedir.llamadas[-1],
            ("RemoveScene", {"sceneName": "Principal - copia"}, None))

    def test_una_escena_vacia_solo_se_crea(self):
        pedir = PedirFalso({"GetSceneItemList": {"sceneItems": []}})
        escenas_obs.duplicar(pedir, "Vacía", "Vacía - copia")
        self.assertEqual(
            [tipo for tipo, _datos, _parada in pedir.llamadas],
            ["CreateScene", "GetSceneItemList"])


class TestAccionesDeEscena(unittest.TestCase):

    def _acciones(self, llamadas, motivo=None, version_vertical=True):
        return escena_menu_escena.acciones_de_escena(
            lambda: llamadas.append("cambiar"),
            lambda: llamadas.append("renombrar"),
            lambda: llamadas.append("duplicar"),
            lambda: llamadas.append("eliminar"),
            lambda: llamadas.append("guardar"),
            (lambda: llamadas.append("vertical")) if version_vertical else None,
            motivo)

    def test_las_acciones_van_en_su_orden_y_con_su_tecla(self):
        acciones = self._acciones([])
        self.assertEqual(
            [accion.etiqueta for accion in acciones],
            ["&Cambiar escena", "Cambiar &nombre…", "&Duplicar",
             "Crear versión &vertical", "E&liminar", "&Guardar imagen…"])
        self.assertEqual(
            [accion.tecla for accion in acciones],
            ["intro", "f2", "ctrl+d", None, "suprimir", None])

    def test_sin_version_vertical_no_aparece(self):
        self.assertEqual(
            [accion.clave for accion in self._acciones(
                [], version_vertical=False)],
            ["cambiar", "renombrar", "duplicar", "eliminar", "guardar"])

    def test_las_letras_de_acceso_no_se_repiten(self):
        letras = {}
        for accion in self._acciones([]):
            letra = _letra_de_acceso(accion.etiqueta)
            self.assertIsNotNone(letra, accion.etiqueta)
            self.assertNotIn(letra, letras, accion.etiqueta)
            letras[letra] = accion.etiqueta

    def test_cada_accion_lleva_el_motivo(self):
        acciones = self._acciones([], motivo=lambda: "Sin conexión con OBS")
        self.assertEqual(
            {accion.motivo() for accion in acciones},
            {"Sin conexión con OBS"})

    def test_cada_accion_llama_a_la_suya(self):
        for indice, esperada in enumerate(
                ("cambiar", "renombrar", "duplicar", "vertical", "eliminar",
                 "guardar")):
            llamadas = []
            self._acciones(llamadas)[indice].manejador()
            self.assertEqual(llamadas, [esperada])


if __name__ == "__main__":
    unittest.main()
