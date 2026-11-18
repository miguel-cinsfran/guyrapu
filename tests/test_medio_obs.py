# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del medio de la escena de Guyrapu, con un cliente falso de OBS."""

import unittest

from guyrapu.obs import escena_guyrapu, medio_obs
from guyrapu.obs.obs_cliente import ObsError

ESCENA = escena_guyrapu.ESCENA
TARJETA = escena_guyrapu.TARJETA
IMAGEN = medio_obs.IMAGEN
MEDIO = medio_obs.MEDIO


class ClienteFalso:
    """Guarda cada pedido y responde como OBS, con la tarjeta ya en escena."""

    def __init__(self, ancho=1280, alto=720):
        self.ancho = ancho
        self.alto = alto
        self.escenas = {ESCENA: []}
        self.entradas = {}
        self.llamadas = []
        self.paradas = []
        self._siguiente = 1
        self._agregar(TARJETA)

    def pedir(self, tipo, datos=None, parada=None):
        datos = dict(datos or {})
        self.llamadas.append((tipo, datos))
        self.paradas.append((tipo, parada))
        manejador = getattr(self, "_" + tipo, None)
        return {"responseData": manejador(datos) if manejador else {}}

    def pedidos(self, tipo):
        return [datos for llamado, datos in self.llamadas if llamado == tipo]

    def item(self, nombre):
        return next(item for item in self.escenas[ESCENA]
                    if item["sourceName"] == nombre)

    def indice(self, nombre):
        return self.item(nombre)["sceneItemIndex"]

    def habilitada(self, nombre):
        return self.item(nombre)["sceneItemEnabled"]

    def _agregar(self, nombre):
        item = {
            "sceneItemId": self._siguiente,
            "sceneItemIndex": len(self.escenas[ESCENA]),
            "sourceName": nombre,
            "sceneItemEnabled": True,
            "sceneItemTransform": {},
        }
        self._siguiente += 1
        self.escenas[ESCENA].append(item)
        return item

    def _renumerar(self):
        for indice, item in enumerate(self.escenas[ESCENA]):
            item["sceneItemIndex"] = indice

    def _buscar(self, datos):
        for item in self.escenas[ESCENA]:
            if item["sceneItemId"] == datos.get("sceneItemId"):
                return item
        raise ObsError("no existe", 600)

    def _GetVideoSettings(self, datos):
        return {"baseWidth": self.ancho, "baseHeight": self.alto}

    def _GetInputList(self, datos):
        return {"inputs": [{"inputName": nombre,
                            "inputKind": entrada["inputKind"]}
                           for nombre, entrada in self.entradas.items()]}

    def _GetSceneItemList(self, datos):
        items = sorted(self.escenas[ESCENA],
                       key=lambda item: item["sceneItemIndex"])
        return {"sceneItems": [dict(item) for item in items]}

    def _CreateInput(self, datos):
        nombre = datos["inputName"]
        if nombre in self.entradas:
            raise ObsError("ya existe", 601)
        self.entradas[nombre] = {
            "inputKind": datos.get("inputKind", ""),
            "inputSettings": dict(datos.get("inputSettings") or {}),
        }
        item = self._agregar(nombre)
        return {"sceneItemId": item["sceneItemId"]}

    def _CreateSceneItem(self, datos):
        item = self._agregar(datos["sourceName"])
        return {"sceneItemId": item["sceneItemId"]}

    def _SetInputSettings(self, datos):
        entrada = self.entradas.get(datos["inputName"])
        if entrada is None:
            raise ObsError("no existe", 600)
        entrada["inputSettings"].update(datos["inputSettings"])
        return {}

    def _SetInputVolume(self, datos):
        entrada = self.entradas.get(datos["inputName"])
        if entrada is None:
            raise ObsError("no existe", 600)
        entrada["inputVolumeDb"] = datos["inputVolumeDb"]
        return {}

    def _SetSceneItemTransform(self, datos):
        self._buscar(datos)["sceneItemTransform"].update(
            datos["sceneItemTransform"])
        return {}

    def _SetSceneItemIndex(self, datos):
        item = self._buscar(datos)
        self.escenas[ESCENA].remove(item)
        self.escenas[ESCENA].insert(datos["sceneItemIndex"], item)
        self._renumerar()
        return {}

    def _SetSceneItemEnabled(self, datos):
        self._buscar(datos)["sceneItemEnabled"] = datos["sceneItemEnabled"]
        return {}

    def _RemoveInput(self, datos):
        nombre = datos["inputName"]
        if nombre not in self.entradas:
            raise ObsError("no existe", 600)
        del self.entradas[nombre]
        self.escenas[ESCENA][:] = [
            item for item in self.escenas[ESCENA]
            if item["sourceName"] != nombre]
        self._renumerar()
        return {}


class Base(unittest.TestCase):
    def setUp(self):
        self.cliente = ClienteFalso()
        self.medio = medio_obs.MedioObs(self.cliente)


class TestArmar(Base):

    def test_p1_la_imagen_va_a_su_entrada_y_apaga_la_de_multimedia(self):
        self.medio.armar("C:/medios/foto.png", "imagen")
        clases = {datos["inputName"]: datos["inputKind"]
                  for datos in self.cliente.pedidos("CreateInput")}
        self.assertEqual(clases, {IMAGEN: "image_source",
                                  MEDIO: "ffmpeg_source"})
        ajustes = self.cliente.pedidos("SetInputSettings")
        self.assertEqual(ajustes, [{"inputName": IMAGEN, "inputSettings": {
            "file": "C:/medios/foto.png"}}])
        self.assertTrue(self.cliente.habilitada(IMAGEN))
        self.assertFalse(self.cliente.habilitada(MEDIO))
        transformacion = self.cliente.item(IMAGEN)["sceneItemTransform"]
        self.assertEqual(transformacion["boundsType"],
                         "OBS_BOUNDS_SCALE_INNER")
        self.assertEqual(transformacion["boundsAlignment"], 0)
        self.assertEqual((transformacion["boundsWidth"],
                          transformacion["boundsHeight"]), (1280, 720))
        self.assertLess(self.cliente.indice(IMAGEN),
                        self.cliente.indice(TARJETA))

    def test_p1_el_medio_se_ancla_arriba_a_la_izquierda_y_se_centra(self):
        self.medio.armar("C:/medios/foto.png", "imagen")
        transformacion = self.cliente.item(IMAGEN)["sceneItemTransform"]
        self.assertEqual(transformacion["alignment"], 5)
        self.assertEqual(transformacion["boundsAlignment"], 0)

    def test_p1_las_dos_entradas_del_medio_quedan_debajo_de_la_tarjeta(self):
        for tipo, ruta in (("imagen", "C:/medios/foto.png"),
                           ("sonido", "C:/medios/tono.wav")):
            with self.subTest(tipo=tipo):
                self.setUp()
                self.medio.armar(ruta, tipo)
                self.assertLess(self.cliente.indice(IMAGEN),
                                self.cliente.indice(TARJETA))
                self.assertLess(self.cliente.indice(MEDIO),
                                self.cliente.indice(TARJETA))

    def test_p1_video_y_sonido_van_a_la_entrada_de_multimedia(self):
        for tipo, ruta in (("video", "C:/medios/clip.mp4"),
                           ("sonido", "C:/medios/tono.wav")):
            with self.subTest(tipo=tipo):
                self.setUp()
                self.medio.armar(ruta, tipo)
                ajustes = self.cliente.pedidos("SetInputSettings")
                self.assertEqual(ajustes, [{
                    "inputName": MEDIO,
                    "inputSettings": {
                        "is_local_file": True,
                        "local_file": ruta,
                        "restart_on_activate": True,
                        "close_when_inactive": True}}])
                self.assertTrue(self.cliente.habilitada(MEDIO))
                self.assertFalse(self.cliente.habilitada(IMAGEN))
                transformacion = self.cliente.item(MEDIO)["sceneItemTransform"]
                self.assertEqual(transformacion["boundsType"],
                                 "OBS_BOUNDS_SCALE_INNER")
                self.assertEqual(transformacion["boundsAlignment"], 0)
                self.assertEqual((transformacion["boundsWidth"],
                                  transformacion["boundsHeight"]), (1280, 720))
                self.assertLess(self.cliente.indice(MEDIO),
                                self.cliente.indice(TARJETA))


class TestVolumen(Base):

    def test_p4_el_volumen_usa_la_ganancia_del_medio(self):
        self.medio.armar("C:/medios/tono.wav", "sonido", -6.5)
        self.assertEqual(self.cliente.pedidos("SetInputVolume"), [
            {"inputName": MEDIO, "inputVolumeDb": -6.5}])

    def test_p4_sin_ganancia_el_volumen_queda_en_cero(self):
        self.medio.armar("C:/medios/tono.wav", "sonido")
        self.assertEqual(self.cliente.pedidos("SetInputVolume"), [
            {"inputName": MEDIO, "inputVolumeDb": 0}])

    def test_p4_todos_los_pedidos_llevan_la_parada(self):
        parada = object()
        self.medio.armar("C:/medios/tono.wav", "sonido", 3.0, parada=parada)
        self.assertTrue(self.cliente.paradas)
        self.assertEqual({recibida for _tipo, recibida
                          in self.cliente.paradas}, {parada})

    def test_p4_el_volumen_va_en_un_pedido_aparte_del_archivo(self):
        self.medio.armar("C:/medios/tono.wav", "sonido", -6.5)
        self.assertEqual(
            [datos["inputName"]
             for datos in self.cliente.pedidos("SetInputSettings")],
            [MEDIO])
        self.assertEqual(
            [datos["inputName"]
             for datos in self.cliente.pedidos("SetInputVolume")],
            [MEDIO])


class TestReproducir(Base):

    def test_p2_arma_dos_veces_el_mismo_sonido_y_lo_reinicia(self):
        self.medio.armar("C:/medios/tono.wav", "sonido")
        self.medio.armar("C:/medios/tono.wav", "sonido")
        reinicios = self.cliente.pedidos("TriggerMediaInputAction")
        self.assertEqual(
            [datos["mediaAction"] for datos in reinicios],
            [medio_obs.REINICIAR, medio_obs.REINICIAR])
        self.assertEqual([datos["inputName"] for datos in reinicios],
                         [MEDIO, MEDIO])

    def test_p3_el_sonido_sale_al_aire_y_por_el_monitoreo(self):
        self.medio.armar("C:/medios/tono.wav", "sonido")
        self.assertEqual(
            self.cliente.pedidos("SetInputAudioMonitorType"),
            [{"inputName": MEDIO,
              "monitorType": "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT"}])


class TestSoltarYQuitar(Base):

    def test_p4_soltar_detiene_y_deshabilita_sin_borrar(self):
        self.medio.armar("C:/medios/tono.wav", "sonido")
        self.cliente.llamadas = []
        self.medio.soltar()
        detenciones = self.cliente.pedidos("TriggerMediaInputAction")
        self.assertEqual([datos["mediaAction"] for datos in detenciones],
                         [medio_obs.DETENER])
        self.assertFalse(self.cliente.habilitada(IMAGEN))
        self.assertFalse(self.cliente.habilitada(MEDIO))
        self.assertEqual(self.cliente.pedidos("RemoveInput"), [])
        self.assertIn(IMAGEN, self.cliente.entradas)
        self.assertIn(MEDIO, self.cliente.entradas)

    def test_p5_quitar_todo_borra_las_dos_entradas(self):
        self.medio.armar("C:/medios/foto.png", "imagen")
        self.medio.quitar_todo()
        self.assertNotIn(IMAGEN, self.cliente.entradas)
        self.assertNotIn(MEDIO, self.cliente.entradas)

    def test_p5_quitar_todo_no_falla_si_no_existen(self):
        self.medio.quitar_todo()


class TestTipo(Base):

    def test_p6_un_tipo_desconocido_es_value_error_antes_de_obs(self):
        for tipo in ("otro", "", None):
            with self.subTest(tipo=tipo):
                self.cliente.llamadas = []
                with self.assertRaises(ValueError):
                    self.medio.armar("C:/medios/foto.png", tipo)
                self.assertEqual(self.cliente.llamadas, [])


if __name__ == "__main__":
    unittest.main()
