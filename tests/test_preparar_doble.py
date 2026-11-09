# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la preparación doble de Restream, sin OBS ni YouTube reales.

El archivo del plugin, el cliente de OBS y los módulos de la capa vertical
entran como dobles para poder mirar el orden y los efectos.
"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from guyrapu.core.idioma import _
from guyrapu.obs import obs_cliente, obs_destinos
from guyrapu.restream import ganchos, preparar_doble
from guyrapu.restream.api import Canal
from guyrapu.restream.perfiles import Perfil
from guyrapu.youtube.emision import EmisionError


LIENZO = {"canvasUuid": "uuid-vertical", "canvasName": "Aitum Vertical",
          "ancho": 1080, "alto": 1920}


def _perfil(canales=(1, 2), youtube=True, directo=None):
    return Perfil(nombre="Doble", canales=canales, orientacion="ambas",
                  youtube=youtube, chat="",
                  directo=directo if directo is not None else {
                      "titulo": "Un título", "descripcion": "Una descripción"})


def _canal(identificador, plataforma, activo=True, plataforma_id=0):
    return Canal(id=identificador, plataforma_id=plataforma_id,
                 plataforma=plataforma, nombre=f"canal {identificador}",
                 url="", activo=activo)


class CuentaFalsa:

    def __init__(self, canales, servidor="rtmp://restream",
                 clave="clave-restream"):
        self._canales = list(canales)
        self._servidor = servidor
        self._clave = clave
        self.llamadas = []

    def canales(self):
        return list(self._canales)

    def clave_cuenta(self):
        self.llamadas.append(("clave",))
        return SimpleNamespace(servidor=self._servidor, clave=self._clave)

    def activar_canal(self, identificador, activo):
        self.llamadas.append(("activar", identificador, activo))

    def cambiar_meta(self, identificador, titulo, descripcion):
        self.llamadas.append(("meta", identificador, titulo, descripcion))

    def eliminar_canal(self, identificador):
        self.llamadas.append(("eliminar", identificador))

    def agregar_canal_manual(self, plataforma_id, nombre, servidor, clave):
        self.llamadas.append(("manual", plataforma_id, nombre, servidor,
                              clave))
        return _canal(90, "Custom RTMP", activo=False)


class ClienteObsFalso:

    def __init__(self, activo=False, escena="Juego"):
        self.activo = activo
        self.escena = escena
        self.llamadas = []

    def conectar(self, parada=None):
        self.llamadas.append("conectar")

    def cerrar(self):
        self.llamadas.append("cerrar")

    def pedir(self, tipo, datos=None, parada=None):
        self.llamadas.append((tipo, datos))
        if tipo == "GetCurrentProgramScene":
            return {"responseData": {
                "currentProgramSceneName": self.escena}}
        return {"responseData": {"outputActive": self.activo}}


def _preparados():
    return {"cliente": object(), "cuerpo": {"snippet": {}}, "extras": {},
            "guardar_token": None, "esperar": mock.Mock(),
            "finalizar": mock.Mock()}


class BaseAsegurar(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / "config.json"

    def escribir(self, salidas=()):
        self.ruta.write_text(json.dumps({
            "canvas": [{"canvasName": "Aitum Vertical",
                        "stream_outputs": list(salidas)}],
        }), encoding="utf-8")

    def leer(self):
        return json.loads(self.ruta.read_text(encoding="utf-8"))

    def asegurar(self, cuenta=None, en_ejecucion=lambda: False,
                 crear_cliente=None, cerrar=None, base=None, anuncios=None):
        cuenta = cuenta or CuentaFalsa([])
        llamadas = anuncios if anuncios is not None else []
        self.base = base or mock.Mock(return_value=True)
        self.cerrar = cerrar or mock.Mock(return_value=True)
        self.crear_cliente = crear_cliente or (lambda: ClienteObsFalso())
        funcion = preparar_doble.asegurar(
            cuenta, ruta=self.ruta, en_ejecucion=en_ejecucion,
            crear_cliente=self.crear_cliente, cerrar=self.cerrar,
            base=self.base)
        return lambda: funcion(
            lambda: None,
            al_anunciar=lambda frase: llamadas.append(frase),
            parada=None)


class AsegurarTest(BaseAsegurar):

    def test_salida_que_falta_con_obs_cerrado_escribe_sin_cerrar(self):
        self.escribir()

        self.asegurar()()

        salidas = self.leer()["canvas"][0]["stream_outputs"]
        self.assertEqual(salidas, [{
            "name": "Guyrapu", "stream_server": "rtmp://restream",
            "stream_key": "clave-restream", "enabled": True}])
        self.base.assert_called_once()
        self.cerrar.assert_not_called()

    def test_con_obs_abierto_cierra_relee_y_escribe(self):
        self.escribir()

        def cerrar():
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            datos["plugin_guardado"] = True
            self.ruta.write_text(json.dumps(datos), encoding="utf-8")
            return True

        anuncios = []
        self.asegurar(en_ejecucion=lambda: True, cerrar=cerrar,
                      anuncios=anuncios)()

        self.assertTrue(self.leer().get("plugin_guardado"))
        self.assertEqual(
            self.leer()["canvas"][0]["stream_outputs"][-1]["name"], "Guyrapu")
        self.assertIn(_(preparar_doble.MENSAJE_PREPARANDO_CIERRE), anuncios)
        self.base.assert_called_once()

    def test_con_salidas_en_marcha_no_cierra_ni_escribe(self):
        self.escribir()
        crear = mock.Mock(return_value=ClienteObsFalso(activo=True))

        with self.assertRaises(obs_cliente.ObsError) as contexto:
            self.asegurar(en_ejecucion=lambda: True,
                          crear_cliente=crear)()

        self.assertEqual(str(contexto.exception),
                         _(preparar_doble.MENSAJE_SALIDA_EN_MARCHA))
        self.cerrar.assert_not_called()
        self.base.assert_not_called()
        self.assertEqual(self.leer()["canvas"][0]["stream_outputs"], [])

    def test_si_no_se_cierra_no_escribe_ni_abre(self):
        self.escribir()

        with self.assertRaises(obs_cliente.ObsError) as contexto:
            self.asegurar(en_ejecucion=lambda: True,
                          cerrar=lambda: False)()

        self.assertEqual(str(contexto.exception),
                         _(preparar_doble.MENSAJE_NO_SE_CERRO))
        self.base.assert_not_called()
        self.assertEqual(self.leer()["canvas"][0]["stream_outputs"], [])

    def test_si_la_salida_ya_esta_no_cierra_ni_reescribe(self):
        self.escribir([{"name": "Guyrapu", "stream_server": "viejo",
                        "stream_key": "vieja", "enabled": True}])

        self.asegurar(en_ejecucion=lambda: True)()

        self.cerrar.assert_not_called()
        self.base.assert_called_once()
        self.assertEqual(
            self.leer()["canvas"][0]["stream_outputs"][0]["stream_server"],
            "viejo")


class PrepararTest(unittest.TestCase):

    def setUp(self):
        self.anuncios = []
        self.orden = []
        self.cliente = ClienteObsFalso(escena="Juego")
        self.cuenta = CuentaFalsa([_canal(1, "YouTube", activo=True,
                                          plataforma_id=5),
                                   _canal(2, "TikTok", activo=False)])
        self.preparados = _preparados()
        self.extras = {}
        self._parches = []

    def tearDown(self):
        for parche in self._parches:
            parche.stop()

    def parchear(self, objeto, nombre, **kwargs):
        parche = mock.patch.object(objeto, nombre, **kwargs)
        self._parches.append(parche)
        return parche.start()

    def preparar(self, perfil=None, **cambios):
        perfil = perfil or _perfil()
        datos = {"preparados": self.preparados}
        datos.update(cambios)
        preparar, _restaurar, extras = ganchos.armar(
            "restream:" + perfil.nombre, self.anunciar,
            list(self.cuenta.canales()), cuenta_mod=self.cuenta,
            perfiles=[perfil], perfil=perfil, **datos)
        self.extras = extras
        return preparar

    def anunciar(self, frase, sonido, importante=False):
        self.anuncios.append((frase, sonido))

    def patch_youtube(self, resultado="video1"):
        def preparar(cliente_yt, cliente_obs, cuerpo, **kwargs):
            self.orden.append("youtube")
            return resultado
        return self.parchear(ganchos.emision, "preparar_en_youtube",
                              side_effect=preparar)

    def patch_vertical(self, copiadas=("Juego vertical",), omitidas=()):
        self.parchear(preparar_doble.lienzo_vertical, "detectar",
                      return_value=LIENZO)
        self.parchear(preparar_doble.config_lienzo_vertical, "leer",
                      return_value={"canvas": [{"stream_outputs": [
                          {"name": "Guyrapu", "stream_server": "x",
                           "stream_key": "y", "enabled": True}]}]})
        self.servidor = self.parchear(
            preparar_doble.lienzo_vertical, "cambiar_servidor")
        self.clave = self.parchear(
            preparar_doble.lienzo_vertical, "cambiar_clave")

        def espejar(cliente, lienzo, parada=None):
            self.orden.append("espejo")
            return copiadas, omitidas
        self.espejo = self.parchear(
            preparar_doble.espejo_vertical, "espejar", side_effect=espejar)

        def cambiar(cliente, escena, parada=None):
            self.orden.append("escena")
            return {}
        self.escena = self.parchear(
            preparar_doble.lienzo_vertical, "cambiar_escena",
            side_effect=cambiar)
        self.servidor.side_effect = lambda *a, **k: self.orden.append("salida")
        self.clave.side_effect = lambda *a, **k: None

    def test_sin_plugin_no_deja_directo_ni_canales_cambiados(self):
        self.patch_youtube()
        self.parchear(preparar_doble.lienzo_vertical, "detectar",
                      return_value=None)
        finalizar = self.parchear(ganchos.emision,
                                  "finalizar_en_youtube")

        with self.assertRaises(EmisionError) as contexto:
            self.preparar()(self.cliente)

        self.assertIn("Vertical Canvas", str(contexto.exception))
        finalizar.assert_called_once_with(self.preparados["cliente"],
                                          "video1")
        self.assertIn(("activar", 1, True), self.cuenta.llamadas)
        self.assertIn(("activar", 2, False), self.cuenta.llamadas)
        self.assertNotIn("manual", [llamada[0] for llamada in
                                    self.cuenta.llamadas])

    def test_prepara_youtube_salida_espejo_y_escena_en_orden(self):
        self.patch_youtube()
        self.patch_vertical()
        preparar = self.preparar()

        resultado = preparar(self.cliente)

        self.assertEqual(resultado, "video1")
        self.assertEqual(self.orden,
                         ["youtube", "salida", "espejo", "escena"])
        self.servidor.assert_called_once_with(
            self.cliente, 0, "rtmp://restream", None)
        self.clave.assert_called_once_with(
            self.cliente, 0, "clave-restream", None)
        self.escena.assert_called_once_with(
            self.cliente, "Juego vertical", None)
        crear = self.extras["envolver_crear_gestor"]
        gestor = crear(lambda: mock.Mock())()
        self.assertEqual(gestor._estado,
                         {"lienzo": LIENZO, "escena": "Juego vertical"})

    def test_el_horizontal_usa_el_destino_de_youtube_sin_restream(self):
        youtube = self.patch_youtube()
        self.patch_vertical()

        self.preparar()(self.cliente)

        kwargs = youtube.call_args.kwargs
        self.assertIs(kwargs["preparar_destino"],
                      obs_destinos.preparar_destino)
        self.assertNotIn("manual", [llamada[0] for llamada in
                                    self.cuenta.llamadas])

    def test_avisa_las_fuentes_que_no_se_copiaron(self):
        self.patch_youtube()
        self.patch_vertical(
            omitidas=(("Juego vertical", "Grupo"), ("Juego vertical",
                                                    "Otra")))

        self.preparar()(self.cliente)

        self.assertIn((_("No se copiaron al vertical: {fuentes}.").format(
            fuentes="Grupo, Otra"), "aviso"), self.anuncios)

    def test_sin_fuentes_omitidas_no_avisa(self):
        self.patch_youtube()
        self.patch_vertical()

        self.preparar()(self.cliente)

        self.assertNotIn("aviso", [sonido for _frase, sonido
                                   in self.anuncios])

    def test_sin_youtube_falla_antes_de_tocar_la_cuenta_ni_obs(self):
        preparar = self.preparar(_perfil(youtube=False))

        with self.assertRaises(EmisionError) as contexto:
            preparar(self.cliente)

        self.assertEqual(str(contexto.exception),
                         _(preparar_doble.MENSAJE_AMBAS_SIN_YOUTUBE))
        self.assertEqual(self.cuenta.llamadas, [])
        self.assertEqual(self.cliente.llamadas, [])

    def test_sin_sesion_falla_antes_de_tocar_la_cuenta_ni_obs(self):
        preparar = self.preparar(preparados=None)

        with self.assertRaises(EmisionError) as contexto:
            preparar(self.cliente)

        self.assertEqual(str(contexto.exception),
                         _(preparar_doble.MENSAJE_AMBAS_SIN_SESION))
        self.assertEqual(self.cuenta.llamadas, [])
        self.assertEqual(self.cliente.llamadas, [])


if __name__ == "__main__":
    unittest.main()
