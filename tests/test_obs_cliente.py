# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import base64
import hashlib
import json
import logging
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

from websockets.exceptions import ConnectionClosed
from websockets.sync.server import serve

from guyrapu.core import paths
from guyrapu.core.idioma import _
from guyrapu.obs import obs_cliente
from tests.pseudo_prueba import con_pseudo


class AjustesObsTest(unittest.TestCase):
    def test_lee_configuracion(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False,
                                         encoding="utf-8") as archivo:
            json.dump({"server_enabled": True, "server_port": 4456,
                       "server_password": "secreto"}, archivo)
            ruta = archivo.name
        try:
            self.assertEqual(obs_cliente.leer_ajustes(ruta),
                             obs_cliente.AjustesObs(True, 4456, "secreto"))
        finally:
            os.unlink(ruta)

    def test_usa_valores_por_defecto_ausentes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False,
                                         encoding="utf-8") as archivo:
            archivo.write("{}")
            ruta = archivo.name
        try:
            self.assertEqual(obs_cliente.leer_ajustes(ruta), obs_cliente.AjustesObs())
        finally:
            os.unlink(ruta)

    def test_archivo_inexistente_no_revienta(self):
        self.assertEqual(obs_cliente.leer_ajustes("ruta-que-no-existe.json"),
                         obs_cliente.AjustesObs())

    def test_archivo_invalido_no_revienta(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False,
                                         encoding="utf-8") as archivo:
            archivo.write("no es json")
            ruta = archivo.name
        try:
            self.assertEqual(obs_cliente.leer_ajustes(ruta), obs_cliente.AjustesObs())
        finally:
            os.unlink(ruta)


class RutaConfigTest(unittest.TestCase):
    def test_la_ruta_del_config_sale_de_paths(self):
        self.assertEqual(obs_cliente.RUTA_CONFIG_OBS,
                         str(paths.carpeta_obs("config")))


class AutenticacionTest(unittest.TestCase):
    def test_respuesta_auth_hace_las_dos_pasadas(self):
        password, salt, challenge = "clave", "sal", "desafio"
        intermedio = base64.b64encode(
            hashlib.sha256((password + salt).encode()).digest()
        ).decode()
        esperado = base64.b64encode(
            hashlib.sha256((intermedio + challenge).encode()).digest()
        ).decode()
        self.assertEqual(obs_cliente.respuesta_auth(password, salt, challenge), esperado)

    def test_respuesta_auth_acepta_textos_vacios(self):
        resultado = obs_cliente.respuesta_auth("", "", "")
        self.assertIsInstance(resultado, str)
        self.assertEqual(len(resultado), 44)


class MensajesDeFalloTest(unittest.TestCase):
    def test_error_de_obs_conserva_su_texto(self):
        texto = ("No se pudo conectar con OBS. Comprueba que OBS esté abierto y "
                 "que su servidor WebSocket esté activado.")
        self.assertEqual(obs_cliente.mensaje_de_fallo_obs(obs_cliente.ObsError(texto)), texto)

    def test_traducir_dos_veces_conserva_el_mismo_texto(self):
        una_vez = obs_cliente.mensaje_de_fallo_obs(
            "Connection refused", obs_abierto=lambda: False)
        dos_veces = obs_cliente.mensaje_de_fallo_obs(obs_cliente.ObsError(una_vez))
        self.assertEqual(dos_veces, una_vez)

    def test_error_crudo_de_conexion_rechazada(self):
        self.assertEqual(obs_cliente.mensaje_de_fallo_obs(
            "Connection refused", obs_abierto=lambda: False),
                         "No se pudo conectar con OBS. Comprueba que OBS esté abierto y "
                         "que su servidor WebSocket esté activado.")

    def test_conexion_rechazada_con_obs_abierto_avisa_que_no_responde(self):
        self.assertEqual(
            obs_cliente.mensaje_de_fallo_obs(
                "Connection refused", obs_abierto=lambda: True),
            obs_cliente.TEXTO_ABIERTO_SIN_RESPUESTA)

    def test_conexion_rechazada_con_obs_cerrado_pide_comprobar(self):
        self.assertEqual(
            obs_cliente.mensaje_de_fallo_obs(
                "Connection refused", obs_abierto=lambda: False),
            "No se pudo conectar con OBS. Comprueba que OBS esté abierto y "
            "que su servidor WebSocket esté activado.")

    def test_conexion_rechazada_si_falla_la_comprobacion_cuenta_como_cerrado(self):
        def obs_abierto_que_falla():
            raise OSError("sin tasklist")
        with self.assertLogs(obs_cliente.logger, level="WARNING"):
            texto = obs_cliente.mensaje_de_fallo_obs(
                "Connection refused", obs_abierto=obs_abierto_que_falla)
        self.assertEqual(
            texto,
            "No se pudo conectar con OBS. Comprueba que OBS esté abierto y "
            "que su servidor WebSocket esté activado.")

    def test_fallo_de_autenticacion_no_consulta_si_obs_esta_abierto(self):
        def obs_abierto_que_falla():
            raise AssertionError("no debe consultarse")
        self.assertEqual(
            obs_cliente.mensaje_de_fallo_obs(
                "error 4009 unauthorized",
                obs_abierto=obs_abierto_que_falla),
            "OBS rechazó la contraseña guardada. Vuelve a conectar para leerla de nuevo.")

    def test_error_crudo_desconocido_conserva_el_generico(self):
        self.assertEqual(obs_cliente.mensaje_de_fallo_obs("fallo extraño"),
                         "OBS no pudo completar la operación. Vuelve a intentarlo.")

    def test_fallo_de_conexion(self):
        self.assertIn("No se pudo conectar", obs_cliente.mensaje_de_fallo_obs(
            "Connection refused", obs_abierto=lambda: False))

    def test_fallo_de_autenticacion(self):
        self.assertEqual(obs_cliente.mensaje_de_fallo_obs("error 4009 unauthorized"),
                         "OBS rechazó la contraseña guardada. Vuelve a conectar para leerla de nuevo.")

    def test_fuente_duplicada(self):
        self.assertEqual(obs_cliente.mensaje_de_fallo_obs("601"),
                         "Ya existe una fuente con ese nombre en OBS.")

    def test_escena_o_fuente_inexistente(self):
        self.assertEqual(obs_cliente.mensaje_de_fallo_obs("No scene"),
                         "OBS no encuentra la escena o la fuente indicada.")

    def test_fallo_desconocido(self):
        self.assertEqual(obs_cliente.mensaje_de_fallo_obs("fallo extraño"),
                         "OBS no pudo completar la operación. Vuelve a intentarlo.")

    def test_motivo_vacio(self):
        self.assertEqual(obs_cliente.mensaje_de_fallo_obs(None),
                         "OBS no pudo completar la operación. Vuelve a intentarlo.")


class TransporteDoble:
    def __init__(self, mensajes):
        self.mensajes = list(mensajes)
        self.enviados = []
        self.cerrado = False

    def send(self, mensaje):
        datos = json.loads(mensaje)
        self.enviados.append(datos)
        if datos.get("op") == 6:
            self.mensajes.append(json.dumps({
                "op": 7,
                "d": {
                    "requestId": datos["d"]["requestId"],
                    "requestStatus": {"result": True},
                    "responseData": {"ok": True},
                },
            }))

    def recv(self, timeout=None):
        if not self.mensajes:
            raise TimeoutError()
        return self.mensajes.pop(0)

    def close(self):
        self.cerrado = True


class TransporteSinRespuesta(TransporteDoble):
    def send(self, mensaje):
        self.enviados.append(json.loads(mensaje))


class TransporteNoListo(TransporteDoble):
    """Responde con el código 207 las primeras veces y después acepta."""

    def __init__(self, veces=2):
        super().__init__([])
        self.veces = veces
        self.peticiones = 0

    def send(self, mensaje):
        datos = json.loads(mensaje)
        self.enviados.append(datos)
        if datos.get("op") != 6:
            return
        self.peticiones += 1
        if self.peticiones <= self.veces:
            estado = {"result": False, "code": 207, "comment": "not ready"}
        else:
            estado = {"result": True}
        self.mensajes.append(json.dumps({
            "op": 7,
            "d": {
                "requestId": datos["d"]["requestId"],
                "requestStatus": estado,
                "responseData": {"ok": True},
            },
        }))


class RelojFalso:
    def __init__(self):
        self.ahora = 0.0

    def reloj(self):
        return self.ahora

    def dormir(self, segundos):
        self.ahora += segundos


class ReintentoNoListoTest(unittest.TestCase):
    def cliente(self, transporte):
        cliente = obs_cliente.ClienteObs(
            obs_cliente.AjustesObs(True, 4455, ""), lambda uri: transporte)
        cliente._transporte = transporte
        return cliente

    def parchear_reloj(self, reloj):
        return (
            mock.patch.object(obs_cliente.time, "monotonic", reloj.reloj),
            mock.patch.object(obs_cliente.time, "sleep", reloj.dormir),
        )

    def test_pedir_reintenta_hasta_que_obs_esta_listo(self):
        transporte = TransporteNoListo(veces=2)
        cliente = self.cliente(transporte)
        reloj = RelojFalso()
        parches = self.parchear_reloj(reloj)
        with parches[0], parches[1]:
            resultado = cliente.pedir("GetVersion")
        self.assertEqual(resultado["responseData"], {"ok": True})
        self.assertEqual(transporte.peticiones, 3)

    def test_pedir_falla_al_pasar_el_plazo_si_sigue_sin_estar_listo(self):
        transporte = TransporteNoListo(veces=10 ** 6)
        cliente = self.cliente(transporte)
        reloj = RelojFalso()
        parches = self.parchear_reloj(reloj)
        with parches[0], parches[1], \
                self.assertRaises(obs_cliente.ObsError) as contexto:
            cliente.pedir("GetVersion")
        self.assertIn("no pudo completar", str(contexto.exception))
        self.assertGreaterEqual(reloj.ahora, 30.0)

    def test_la_parada_corta_la_espera(self):
        class ParadaFalsa:
            def __init__(self):
                self.puesta = False

            def is_set(self):
                return self.puesta

            def wait(self, segundos):
                self.puesta = True
                return True

        transporte = TransporteNoListo(veces=10 ** 6)
        cliente = self.cliente(transporte)
        reloj = RelojFalso()
        with mock.patch.object(obs_cliente.time, "monotonic", reloj.reloj), \
                self.assertRaises(obs_cliente.ObsError) as contexto:
            cliente.pedir("GetVersion", parada=ParadaFalsa())
        self.assertEqual(str(contexto.exception), "Operación cancelada.")
        self.assertLess(reloj.ahora, 30.0)


class ClienteConCodigos:
    """Falla con los códigos pedidos y después acepta el pedido."""

    def __init__(self, codigos):
        self.codigos = list(codigos)
        self.pedidos = 0

    def pedir(self, tipo, datos=None, parada=None):
        self.pedidos += 1
        if self.pedidos <= len(self.codigos):
            codigo = self.codigos[self.pedidos - 1]
            raise obs_cliente.ObsError("fallo de OBS", codigo=codigo)
        return {"responseData": {"ok": True}}


class ReintentoDeVideoTest(unittest.TestCase):
    def parchear_reloj(self, reloj):
        return (
            mock.patch.object(obs_cliente.time, "monotonic", reloj.reloj),
            mock.patch.object(obs_cliente.time, "sleep", reloj.dormir),
        )

    def test_reintenta_cada_medio_segundo_hasta_que_obs_acepta(self):
        cliente = ClienteConCodigos([500, 500])
        reloj = RelojFalso()
        parches = self.parchear_reloj(reloj)
        with parches[0], parches[1]:
            resultado = obs_cliente.pedir_reintentando(
                cliente, "SetVideoSettings")
        self.assertEqual(resultado["responseData"], {"ok": True})
        self.assertEqual(cliente.pedidos, 3)
        self.assertEqual(reloj.ahora, 1.0)

    def test_otro_codigo_falla_al_primer_intento(self):
        cliente = ClienteConCodigos([601])
        reloj = RelojFalso()
        parches = self.parchear_reloj(reloj)
        with parches[0], parches[1], \
                self.assertRaises(obs_cliente.ObsError) as contexto:
            obs_cliente.pedir_reintentando(cliente, "SetVideoSettings")
        self.assertEqual(cliente.pedidos, 1)
        self.assertEqual(reloj.ahora, 0.0)
        self.assertEqual(contexto.exception.codigo, 601)

    def test_con_500_siempre_falla_al_pasar_el_limite(self):
        cliente = ClienteConCodigos([500] * 1000)
        reloj = RelojFalso()
        parches = self.parchear_reloj(reloj)
        with parches[0], parches[1], \
                self.assertRaises(obs_cliente.ObsError) as contexto:
            obs_cliente.pedir_reintentando(cliente, "SetVideoSettings")
        self.assertEqual(contexto.exception.codigo, 500)
        self.assertGreaterEqual(reloj.ahora, 10.0)
        self.assertEqual(cliente.pedidos, 21)


class ClienteObsTest(unittest.TestCase):
    def cliente(self, transporte, password=""):
        return obs_cliente.ClienteObs(
            obs_cliente.AjustesObs(True, 4455, password),
            lambda uri: transporte,
        )

    def test_conectar_sin_autenticacion(self):
        transporte = TransporteDoble([
            json.dumps({"op": 0, "d": {"rpcVersion": 1}}),
            json.dumps({"op": 2, "d": {}}),
        ])
        cliente = self.cliente(transporte)
        cliente.conectar()
        self.assertTrue(cliente.conectado)
        self.assertEqual(transporte.enviados[0],
                         {"op": 1, "d": {"rpcVersion": 1, "eventSubscriptions": 0}})

    def test_conectar_de_nuevo_cierra_el_transporte_anterior(self):
        def transporte_nuevo():
            return TransporteDoble([
                json.dumps({"op": 0, "d": {"rpcVersion": 1}}),
                json.dumps({"op": 2, "d": {}}),
            ])
        transportes = [transporte_nuevo(), transporte_nuevo()]
        cliente = obs_cliente.ClienteObs(
            obs_cliente.AjustesObs(True, 4455, ""),
            lambda uri: transportes.pop(0))
        cliente.conectar()
        primero = cliente._transporte
        cliente.conectar()
        self.assertTrue(primero.cerrado)
        self.assertIsNot(cliente._transporte, primero)
        self.assertTrue(cliente.conectado)

    def test_obs_cierra_la_conexion_y_el_cliente_deja_de_estar_conectado(self):
        from websockets.exceptions import ConnectionClosed
        transporte = TransporteDoble([])
        transporte.recv = mock.Mock(side_effect=ConnectionClosed(None, None))
        cliente = self.cliente(transporte)
        cliente._transporte = transporte
        with self.assertRaisesRegex(obs_cliente.ObsError, "Se perdió la conexión"):
            cliente.pedir("GetVersion")
        self.assertFalse(cliente.conectado)
        self.assertTrue(transporte.cerrado)

    def test_peticiones_concurrentes_no_se_pisan(self):
        # Sin cerrojo, dos hilos hacían send/recv a la vez sobre el mismo socket.
        class TransporteLento(TransporteDoble):
            def __init__(self):
                super().__init__([])
                self.ocupado = False
                self.solapes = 0

            def send(self, mensaje):
                if self.ocupado:
                    self.solapes += 1
                self.ocupado = True
                time.sleep(0.01)
                super().send(mensaje)

            def recv(self, timeout=None):
                mensaje = super().recv(timeout)
                self.ocupado = False
                return mensaje

        transporte = TransporteLento()
        cliente = self.cliente(transporte)
        cliente._transporte = transporte
        hilos = [threading.Thread(target=cliente.pedir, args=("GetVersion",))
                 for _ in range(4)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(2)
        self.assertEqual(transporte.solapes, 0)
        self.assertEqual(len(transporte.enviados), 4)

    def test_conectar_con_autenticacion(self):
        transporte = TransporteDoble([
            json.dumps({"op": 0, "d": {"rpcVersion": 1,
                                         "authentication": {"salt": "sal",
                                                             "challenge": "reto"}}}),
            json.dumps({"op": 2, "d": {}}),
        ])
        cliente = self.cliente(transporte, "clave")
        cliente.conectar()
        enviado = transporte.enviados[0]["d"]
        self.assertEqual(enviado["rpcVersion"], 1)
        self.assertEqual(enviado["authentication"],
                         obs_cliente.respuesta_auth("clave", "sal", "reto"))

    def test_salta_eventos_y_devuelve_respuesta(self):
        transporte = TransporteDoble([
            json.dumps({"op": 5, "d": {"eventType": "CurrentProgramSceneChanged"}}),
            json.dumps({"op": 7, "d": {"requestId": "otro",
                                         "requestStatus": {"result": True}}}),
        ])
        cliente = self.cliente(transporte)
        cliente._transporte = transporte
        resultado = cliente.pedir("GetVersion", {"campo": 1})
        self.assertEqual(resultado["responseData"], {"ok": True})
        pedido = transporte.enviados[0]
        self.assertEqual(pedido["d"]["requestType"], "GetVersion")
        self.assertEqual(pedido["d"]["requestData"], {"campo": 1})

    def test_cerrar_libera_el_transporte(self):
        transporte = TransporteDoble([])
        cliente = self.cliente(transporte)
        cliente._transporte = transporte
        cliente.cerrar()
        self.assertFalse(cliente.conectado)
        self.assertTrue(transporte.cerrado)

    def test_pedir_traduce_error_de_obs(self):
        transporte = TransporteDoble([])
        cliente = self.cliente(transporte)
        cliente._transporte = transporte
        transporte.recv = lambda timeout=None: json.dumps({
            "op": 7,
            "d": {"requestId": transporte.enviados[0]["d"]["requestId"],
                  "requestStatus": {"result": False, "code": 601,
                                     "comment": "A source already exists"}},
        })
        with self.assertRaisesRegex(obs_cliente.ObsError,
                                    "Ya existe una fuente"):
            cliente.pedir("CreateInput")

    def test_pedir_sin_conexion_falla(self):
        with self.assertRaisesRegex(obs_cliente.ObsError, "no pudo completar"):
            self.cliente(TransporteDoble([])).pedir("GetVersion")


class CancelacionYTiempoTest(unittest.TestCase):
    def cliente_sin_respuesta(self):
        transporte = TransporteSinRespuesta([])
        cliente = obs_cliente.ClienteObs(
            obs_cliente.AjustesObs(True, 4455, ""), lambda uri: transporte
        )
        cliente._transporte = transporte
        return cliente

    def test_pedir_se_cancela_mientras_recv_espera(self):
        cliente = self.cliente_sin_respuesta()
        parada = threading.Event()
        resultado = []

        def ejecutar():
            try:
                cliente.pedir("GetVersion", parada=parada)
            except obs_cliente.ObsError as error:
                resultado.append(str(error))

        hilo = threading.Thread(target=ejecutar)
        hilo.start()
        parada.set()
        hilo.join(1.5)
        self.assertFalse(hilo.is_alive())
        self.assertEqual(resultado, ["Operación cancelada."])

    def test_pedir_respeta_el_tiempo_total(self):
        cliente = self.cliente_sin_respuesta()
        original = cliente._TIEMPO_LIMITE
        cliente._TIEMPO_LIMITE = 0.02
        try:
            with mock.patch.object(obs_cliente.obs_activacion,
                                   "obs_esta_en_ejecucion",
                                   return_value=False), \
                    self.assertRaisesRegex(obs_cliente.ObsError,
                                           "No se pudo conectar"):
                cliente.pedir("GetVersion")
        finally:
            cliente._TIEMPO_LIMITE = original


class EscuchaTest(unittest.TestCase):
    def cliente(self, transporte, suscripciones=0):
        return obs_cliente.ClienteObs(
            obs_cliente.AjustesObs(True, 4455, ""), lambda uri: transporte,
            suscripciones=suscripciones)

    def evento(self, tipo="InputVolumeMeters", datos=None):
        return json.dumps({"op": 5, "d": {"eventType": tipo,
                                           "eventData": datos or {}}})

    def test_identificacion_lleva_la_suscripcion_pedida(self):
        transporte = TransporteDoble([
            json.dumps({"op": 0, "d": {"rpcVersion": 1}}),
            json.dumps({"op": 2, "d": {}}),
        ])
        cliente = self.cliente(transporte, suscripciones=65536)
        cliente.conectar()
        self.assertEqual(transporte.enviados[0]["d"]["eventSubscriptions"],
                         65536)

    def test_devuelve_solo_los_eventos_del_tipo_pedido(self):
        datos = {"inputs": [{"inputName": "Mic/Aux"}]}
        transporte = TransporteDoble([
            self.evento(datos=datos),
            json.dumps({"op": 7, "d": {"requestId": "otro",
                                        "requestStatus": {"result": True}}}),
            self.evento(tipo="SceneChanged", datos={"lo": "otro"}),
            self.evento(datos={"inputs": []}),
        ])
        cliente = self.cliente(transporte)
        cliente._transporte = transporte
        resultado = cliente.escuchar("InputVolumeMeters", 0.10)
        self.assertEqual(resultado, [datos, {"inputs": []}])

    def test_sin_conexion_lanza_obs_error_como_pedir(self):
        with self.assertRaisesRegex(obs_cliente.ObsError, "no pudo completar"):
            self.cliente(TransporteDoble([])).escuchar("InputVolumeMeters", 0.1)

    def test_sin_nada_que_recibir_termina_al_agotar_el_tiempo(self):
        transporte = TransporteDoble([])
        cliente = self.cliente(transporte)
        cliente._transporte = transporte
        comienzo = time.monotonic()
        self.assertEqual(cliente.escuchar("InputVolumeMeters", 0.05), [])
        self.assertLess(time.monotonic() - comienzo, 2.0)

    def test_el_fin_del_tiempo_no_registra_ningun_fallo(self):
        transporte = TransporteSinRespuesta([])
        cliente = self.cliente(transporte)
        cliente._transporte = transporte
        with self.assertNoLogs(obs_cliente.logger, level="WARNING"):
            self.assertEqual(cliente.escuchar("InputVolumeMeters", 0.02), [])

    def test_la_parada_termina_la_escucha_sin_lanzar_nada(self):
        transporte = TransporteDoble([])
        cliente = self.cliente(transporte)
        cliente._transporte = transporte
        parada = threading.Event()
        parada.set()
        comienzo = time.monotonic()
        self.assertEqual(cliente.escuchar("InputVolumeMeters", 1.0, parada), [])
        self.assertLess(time.monotonic() - comienzo, 2.0)


class RegistroDeFalloTest(unittest.TestCase):
    def test_excepcion_cruda_deja_warning_con_tipo_y_traza(self):
        with self.assertLogs(obs_cliente.logger, level="WARNING") as registro:
            texto = obs_cliente.mensaje_de_fallo_obs(RuntimeError("algo raro"))
        self.assertEqual(texto, "OBS no pudo completar la operación. Vuelve a intentarlo.")
        self.assertIn("RuntimeError", registro.output[0])
        self.assertIn("algo raro", registro.output[0])
        self.assertIsNotNone(registro.records[0].exc_info)

    def test_texto_crudo_deja_warning_sin_traza(self):
        with self.assertLogs(obs_cliente.logger, level="WARNING") as registro:
            texto = obs_cliente.mensaje_de_fallo_obs(
                "timed out", obs_abierto=lambda: False)
        self.assertEqual(texto, "No se pudo conectar con OBS. Comprueba que OBS esté "
                                "abierto y que su servidor WebSocket esté activado.")
        self.assertIn("timed out", registro.output[0])
        self.assertIsNone(registro.records[0].exc_info)

    def test_error_de_obs_no_registra_nada(self):
        texto_esperado = "OBS no pudo completar la operación. Vuelve a intentarlo."
        with self.assertNoLogs(obs_cliente.logger, level="WARNING"):
            texto = obs_cliente.mensaje_de_fallo_obs(
                obs_cliente.ObsError(texto_esperado))
        self.assertEqual(texto, texto_esperado)

    def test_conexion_rechazada_registra_en_debug_y_no_en_warning(self):
        motivo = ConnectionRefusedError(10061, "conexion rechazada")
        with self.assertNoLogs(obs_cliente.logger, level="WARNING"):
            texto = obs_cliente.mensaje_de_fallo_obs(
                motivo, obs_abierto=lambda: False)
        self.assertIn("No se pudo conectar", texto)
        with self.assertLogs(obs_cliente.logger, level="DEBUG") as registros:
            obs_cliente.mensaje_de_fallo_obs(motivo, obs_abierto=lambda: False)
        self.assertEqual(1, len(registros.records))


class TransporteConError(TransporteDoble):
    """Responde siempre con el código de error pedido."""

    def __init__(self, code, comment=""):
        super().__init__([])
        self.code = code
        self.comment = comment

    def send(self, mensaje):
        datos = json.loads(mensaje)
        self.enviados.append(datos)
        if datos.get("op") != 6:
            return
        self.mensajes.append(json.dumps({
            "op": 7,
            "d": {
                "requestId": datos["d"]["requestId"],
                "requestStatus": {"result": False, "code": self.code,
                                  "comment": self.comment},
            },
        }))


class RespuestaConErrorTest(unittest.TestCase):

    def test_el_codigo_de_error_va_a_debug_y_no_a_warning(self):
        transporte = TransporteConError(604, "No source")
        cliente = obs_cliente.ClienteObs(
            obs_cliente.AjustesObs(True, 4455, ""), lambda uri: transporte)
        cliente._transporte = transporte
        with self.assertLogs(obs_cliente.logger, level="DEBUG") as registros:
            with self.assertRaises(obs_cliente.ObsError) as contexto:
                cliente.pedir("GetReplayBufferStatus")
        self.assertEqual(
            str(contexto.exception),
            "OBS no pudo completar la operación. Vuelve a intentarlo.")
        self.assertEqual([registro.levelno for registro in registros.records],
                         [logging.DEBUG])
        self.assertIn("GetReplayBufferStatus", registros.output[0])
        self.assertIn("604", registros.output[0])


class TestPseudoMensajesCliente(unittest.TestCase):
    """Pseudotraducción de los mensajes que muestra `obs_cliente`.

    Sin ventanas: llama a la traducción de fallos y a la cancelación bajo
    `con_pseudo()`. Los motivos técnicos son datos y no se envuelven.
    """

    def test_todos_los_mensajes_de_fallo_salen_marcados(self):
        casos = (
            ("Connection refused", False),
            ("Connection refused", True),
            ("authentication", False),
            ("4009 unauthorized", False),
            ("601", False),
            ("not found", False),
            ("fallo extraño", False),
        )
        with con_pseudo():
            for motivo, abierto in casos:
                with self.subTest(motivo=motivo, abierto=abierto):
                    frase = obs_cliente.mensaje_de_fallo_obs(
                        motivo, obs_abierto=lambda: abierto)
                    self.assertTrue(frase.startswith("[¡"), frase)

    def test_constantes_marcadas_se_traducen_al_usarse(self):
        with con_pseudo():
            self.assertTrue(
                _(obs_cliente.MENSAJE_CONEXION_PERDIDA).startswith("[¡"))
            self.assertTrue(
                _(obs_cliente.TEXTO_ABIERTO_SIN_RESPUESTA).startswith("[¡"))

    def test_operacion_cancelada_sale_marcada(self):
        parada = threading.Event()
        parada.set()
        with con_pseudo():
            with self.assertRaises(obs_cliente.ObsError) as contexto:
                obs_cliente.ClienteObs._recibir(None, parada, 0.0)
        self.assertTrue(str(contexto.exception).startswith("[¡"), contexto.exception)


class CoordinadorObs:
    """Estado que comparten los transportes falsos de una prueba."""

    def __init__(self):
        self.demoras = {}
        self.pedidos = []
        self.cerrojo = threading.Lock()
        self.perfil_nuevo_visible = threading.Event()
        self.creado_sin_cambiar = False

    def registrar(self, tipo):
        with self.cerrojo:
            self.pedidos.append(tipo)

    def espero(self, tipo):
        with self.cerrojo:
            return tipo in self.pedidos

    def respuesta(self, tipo):
        if tipo == "GetProfileList":
            if self.creado_sin_cambiar:
                return {"profiles": ["anterior", "nuevo"],
                        "currentProfileName": "anterior"}
            if self.perfil_nuevo_visible.is_set():
                return {"profiles": ["anterior", "nuevo"],
                        "currentProfileName": "nuevo"}
            return {"profiles": ["anterior"],
                    "currentProfileName": "anterior"}
        return {}


class TransporteCoordinado:
    """Responde al instante salvo los pedidos que la prueba demora."""

    def __init__(self, coordinador):
        self.coordinador = coordinador
        self.pendiente = None
        self.enviados = []
        self.cerrado = False

    def send(self, mensaje):
        datos = json.loads(mensaje)
        if datos.get("op") != 6:
            return
        self.enviados.append(datos)
        self.coordinador.registrar(datos["d"]["requestType"])
        self.pendiente = datos

    def recv(self, timeout=None):
        datos = self.pendiente
        tipo = datos["d"]["requestType"]
        demora = self.coordinador.demoras.get(tipo)
        if demora is not None and not demora.is_set():
            raise TimeoutError()
        self.pendiente = None
        return json.dumps({
            "op": 7,
            "d": {
                "requestId": datos["d"]["requestId"],
                "requestStatus": {"result": True},
                "responseData": self.coordinador.respuesta(tipo),
            },
        })

    def close(self):
        self.cerrado = True


def esperar_a(condicion, limite=2.0):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.01)
    return False


class CandadoDeConsultasTest(unittest.TestCase):
    def crear(self, coordinador):
        transporte = TransporteCoordinado(coordinador)
        cliente = obs_cliente.ClienteObs(
            obs_cliente.AjustesObs(True, 4455, ""), lambda uri: transporte)
        cliente._transporte = transporte
        return cliente, transporte

    def correr_en_hilo(self, cliente, tipo, datos=None, parada=None):
        resultado = {}

        def ejecutar():
            try:
                resultado["valor"] = cliente.pedir(tipo, datos, parada)
            except obs_cliente.ObsError as error:
                resultado["error"] = str(error)

        hilo = threading.Thread(target=ejecutar)
        hilo.start()
        return hilo, resultado

    def tipos_enviados(self, transporte):
        return [pedido["d"]["requestType"] for pedido in transporte.enviados]

    def test_get_stream_status_espera_al_cambio_de_perfil(self):
        coordinador = CoordinadorObs()
        coordinador.demoras["GetProfileList"] = coordinador.perfil_nuevo_visible
        cambio, _transporte_cambio = self.crear(coordinador)
        consulta, transporte_consulta = self.crear(coordinador)
        hilo_cambio, _ = self.correr_en_hilo(
            cambio, "SetCurrentProfile", {"profileName": "nuevo"})
        self.assertTrue(esperar_a(
            lambda: coordinador.espero("GetProfileList")))
        hilo_consulta, resultado = self.correr_en_hilo(
            consulta, "GetStreamStatus")
        time.sleep(0.2)
        self.assertEqual(transporte_consulta.enviados, [])
        self.assertTrue(hilo_consulta.is_alive())
        coordinador.perfil_nuevo_visible.set()
        hilo_cambio.join(2)
        hilo_consulta.join(2)
        self.assertFalse(hilo_cambio.is_alive())
        self.assertFalse(hilo_consulta.is_alive())
        self.assertEqual(self.tipos_enviados(transporte_consulta),
                         ["GetStreamStatus"])
        self.assertIn("valor", resultado)

    def test_get_stats_espera_a_la_creacion_de_perfil(self):
        coordinador = CoordinadorObs()
        coordinador.demoras["GetProfileList"] = coordinador.perfil_nuevo_visible
        cambio, _ = self.crear(coordinador)
        consulta, transporte_consulta = self.crear(coordinador)
        hilo_cambio, _ = self.correr_en_hilo(
            cambio, "CreateProfile", {"profileName": "nuevo"})
        self.assertTrue(esperar_a(
            lambda: coordinador.espero("GetProfileList")))
        hilo_consulta, resultado = self.correr_en_hilo(consulta, "GetStats")
        time.sleep(0.2)
        self.assertEqual(transporte_consulta.enviados, [])
        coordinador.perfil_nuevo_visible.set()
        hilo_cambio.join(2)
        hilo_consulta.join(2)
        self.assertFalse(hilo_cambio.is_alive())
        self.assertEqual(self.tipos_enviados(transporte_consulta),
                         ["GetStats"])
        self.assertIn("valor", resultado)

    def test_crear_en_otra_version_no_espera_a_que_sea_actual(self):
        coordinador = CoordinadorObs()
        coordinador.creado_sin_cambiar = True
        cambio, _ = self.crear(coordinador)
        consulta, transporte_consulta = self.crear(coordinador)
        comienzo = time.monotonic()
        hilo_cambio, _ = self.correr_en_hilo(
            cambio, "CreateProfile", {"profileName": "nuevo"})
        hilo_cambio.join(1)
        self.assertFalse(hilo_cambio.is_alive())
        self.assertLess(time.monotonic() - comienzo, 1.0)
        self.assertIn("GetProfileList", coordinador.pedidos)
        hilo_consulta, resultado = self.correr_en_hilo(consulta, "GetStats")
        hilo_consulta.join(2)
        self.assertIn("valor", resultado)
        self.assertEqual(self.tipos_enviados(transporte_consulta),
                         ["GetStats"])


    def test_get_stats_espera_al_cambio_de_video(self):
        coordinador = CoordinadorObs()
        permitir = threading.Event()
        coordinador.demoras["SetVideoSettings"] = permitir
        cambio, _ = self.crear(coordinador)
        consulta, transporte_consulta = self.crear(coordinador)
        hilo_cambio, _ = self.correr_en_hilo(
            cambio, "SetVideoSettings", {"baseWidth": 1280, "baseHeight": 720})
        self.assertTrue(esperar_a(
            lambda: coordinador.espero("SetVideoSettings")))
        hilo_consulta, resultado = self.correr_en_hilo(consulta, "GetStats")
        time.sleep(0.2)
        self.assertEqual(transporte_consulta.enviados, [])
        permitir.set()
        hilo_cambio.join(2)
        hilo_consulta.join(2)
        self.assertFalse(hilo_cambio.is_alive())
        self.assertFalse(hilo_consulta.is_alive())
        self.assertEqual(self.tipos_enviados(transporte_consulta),
                         ["GetStats"])
        self.assertIn("valor", resultado)

    def test_una_consulta_que_no_se_vigila_no_espera(self):
        coordinador = CoordinadorObs()
        permitir = threading.Event()
        coordinador.demoras["SetVideoSettings"] = permitir
        cambio, _ = self.crear(coordinador)
        consulta, _transporte_consulta = self.crear(coordinador)
        hilo_cambio, _ = self.correr_en_hilo(
            cambio, "SetVideoSettings", {"baseWidth": 1280, "baseHeight": 720})
        self.assertTrue(esperar_a(
            lambda: coordinador.espero("SetVideoSettings")))
        hilo_consulta, resultado = self.correr_en_hilo(
            consulta, "GetSceneItemList", {"sceneName": "Escena"})
        hilo_consulta.join(2)
        self.assertFalse(hilo_consulta.is_alive())
        self.assertIn("valor", resultado)
        self.assertTrue(hilo_cambio.is_alive())
        permitir.set()
        hilo_cambio.join(2)

    def test_la_parada_corta_la_espera_del_candado(self):
        coordinador = CoordinadorObs()
        permitir = threading.Event()
        coordinador.demoras["SetVideoSettings"] = permitir
        cambio, _ = self.crear(coordinador)
        consulta, transporte_consulta = self.crear(coordinador)
        hilo_cambio, _ = self.correr_en_hilo(
            cambio, "SetVideoSettings", {"baseWidth": 1280, "baseHeight": 720})
        self.assertTrue(esperar_a(
            lambda: coordinador.espero("SetVideoSettings")))
        parada = threading.Event()
        hilo_consulta, resultado = self.correr_en_hilo(
            consulta, "GetStats", parada=parada)
        time.sleep(0.15)
        parada.set()
        hilo_consulta.join(2)
        self.assertFalse(hilo_consulta.is_alive())
        self.assertEqual(resultado.get("error"), "Operación cancelada.")
        self.assertEqual(transporte_consulta.enviados, [])
        permitir.set()
        hilo_cambio.join(2)

    def test_el_limite_del_cambio_no_traba_la_consulta(self):
        coordinador = CoordinadorObs()
        cambio, _ = self.crear(coordinador)
        consulta, transporte_consulta = self.crear(coordinador)
        cambio._TIEMPO_LIMITE = 0.3
        hilo_cambio, _ = self.correr_en_hilo(
            cambio, "SetCurrentProfile", {"profileName": "nuevo"})
        self.assertTrue(esperar_a(
            lambda: coordinador.espero("GetProfileList")))
        hilo_consulta, resultado = self.correr_en_hilo(consulta, "GetStats")
        time.sleep(0.1)
        self.assertEqual(transporte_consulta.enviados, [])
        hilo_cambio.join(2)
        hilo_consulta.join(2)
        self.assertFalse(hilo_cambio.is_alive())
        self.assertFalse(hilo_consulta.is_alive())
        self.assertEqual(self.tipos_enviados(transporte_consulta),
                         ["GetStats"])
        self.assertIn("valor", resultado)


class ServidorObs:
    """OBS mínimo que solo cambia de perfil cuando la prueba lo permite."""

    def __init__(self):
        self.pedidos = []
        self.cerrojo = threading.Lock()
        self.actual = "anterior"
        self.pendiente = None
        self.permitir = threading.Event()

    def atender(self, conexion):
        conexion.send(json.dumps({"op": 0, "d": {"rpcVersion": 1}}))
        conexion.recv()
        conexion.send(json.dumps({"op": 2, "d": {}}))
        while True:
            try:
                mensaje = conexion.recv()
            except ConnectionClosed:
                return
            datos = json.loads(mensaje)
            if datos.get("op") != 6:
                continue
            tipo = datos["d"]["requestType"]
            with self.cerrojo:
                self.pedidos.append(tipo)
            cuerpo = self.responder(tipo, datos["d"].get("requestData", {}))
            conexion.send(json.dumps({
                "op": 7,
                "d": {"requestId": datos["d"]["requestId"],
                      "requestStatus": {"result": True},
                      "responseData": cuerpo},
            }))

    def responder(self, tipo, datos):
        with self.cerrojo:
            if tipo == "SetCurrentProfile":
                self.pendiente = datos.get("profileName")
            elif (tipo == "GetProfileList" and self.pendiente
                    and self.permitir.is_set()):
                self.actual = self.pendiente
                self.pendiente = None
            actual = self.actual
        if tipo == "GetProfileList":
            return {"profiles": ["anterior", "nuevo"],
                    "currentProfileName": actual}
        return {}

    def espero(self, tipo):
        with self.cerrojo:
            return tipo in self.pedidos


class CandadoPuntaAPuntaTest(unittest.TestCase):
    def test_dos_clientes_reales_esperan_el_cambio_por_websocket(self):
        servidor = ServidorObs()
        with serve(servidor.atender, "127.0.0.1", 0) as escucha:
            puerto = escucha.socket.getsockname()[1]
            hilo_servidor = threading.Thread(target=escucha.serve_forever)
            hilo_servidor.start()
            ajustes = obs_cliente.AjustesObs(True, puerto, "")
            cambio = obs_cliente.ClienteObs(ajustes)
            consulta = obs_cliente.ClienteObs(ajustes)
            try:
                cambio.conectar()
                consulta.conectar()
                hilo_cambio, _ = self.correr(cambio, "SetCurrentProfile",
                                             {"profileName": "nuevo"})
                self.assertTrue(esperar_a(
                    lambda: servidor.espero("GetProfileList")))
                hilo_consulta, resultado = self.correr(
                    consulta, "GetStreamStatus")
                time.sleep(0.3)
                self.assertTrue(hilo_consulta.is_alive())
                self.assertFalse(servidor.espero("GetStreamStatus"))
                servidor.permitir.set()
                hilo_cambio.join(2)
                hilo_consulta.join(2)
                self.assertFalse(hilo_cambio.is_alive())
                self.assertFalse(hilo_consulta.is_alive())
                self.assertIn("valor", resultado)
                self.assertTrue(servidor.espero("GetStreamStatus"))
            finally:
                cambio.cerrar()
                consulta.cerrar()
                escucha.shutdown()
                hilo_servidor.join(2)

    def correr(self, cliente, tipo, datos=None):
        resultado = {}

        def ejecutar():
            try:
                resultado["valor"] = cliente.pedir(tipo, datos)
            except obs_cliente.ObsError as error:
                resultado["error"] = str(error)

        hilo = threading.Thread(target=ejecutar)
        hilo.start()
        return hilo, resultado
