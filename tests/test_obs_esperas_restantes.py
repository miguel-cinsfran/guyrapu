# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Esperas de OBS, del relevo y del fin del directo que ya usan la común.

Cubre lo que las pruebas de cada módulo no miraban: el aviso importante al
vencer la espera a OBS, la consulta que falla, el perfil que nunca llega a
actual sin error y el registro de cada fallo del reintento del fin.
"""

import json
import unittest
from unittest import mock

from guyrapu.obs import detener_obs, obs_cliente
from guyrapu.youtube import fin_pendiente


class RelojFalso:
    def __init__(self):
        self.ahora = 0.0

    def reloj(self):
        return self.ahora

    def dormir(self, segundos):
        self.ahora += segundos


class PruebasEsperaDetenerObs(unittest.TestCase):
    def test_avisa_el_plazo_con_error_e_importante(self):
        class GestorActivo:
            def estado_transmision(self):
                return {"outputActive": True}

        anuncios = []
        reloj = RelojFalso()
        detener_obs._esperar_a_obs(
            GestorActivo(),
            lambda frase, sonido, importante=False: anuncios.append(
                (frase, sonido, importante)),
            reloj.reloj, reloj.dormir, lambda: "", lambda: True)
        self.assertEqual(anuncios, [
            ("Deteniendo la transmisión. Esperando a que OBS confirme.",
             None, False),
            ("OBS sigue transmitiendo. Detén la transmisión en OBS.",
             "error", True),
        ])

    def test_consulta_que_falla_anuncia_sin_respuesta(self):
        class GestorQueFalla:
            def estado_transmision(self):
                raise RuntimeError("sin respuesta")

        anuncios = []
        reloj = RelojFalso()
        detener_obs._esperar_a_obs(
            GestorQueFalla(),
            lambda frase, sonido, importante=False: anuncios.append(
                (frase, sonido, importante)),
            reloj.reloj, reloj.dormir, lambda: "", lambda: True)
        self.assertEqual(anuncios, [(
            "No se pudo conectar con OBS para detener la transmisión.",
            "error", True)])


class TransportePerfil:
    """Responde a cada pedido con el perfil anterior como actual."""

    def __init__(self):
        self.pendiente = None
        self.peticiones = 0

    def send(self, mensaje):
        self.pendiente = json.loads(mensaje)
        self.peticiones += 1

    def recv(self, timeout=None):
        datos = self.pendiente
        return json.dumps({
            "op": 7,
            "d": {
                "requestId": datos["d"]["requestId"],
                "requestStatus": {"result": True},
                "responseData": {"profiles": ["anterior"],
                                 "currentProfileName": "anterior"},
            },
        })

    def close(self):
        pass


class PruebasEsperaPerfil(unittest.TestCase):
    def test_el_perfil_que_no_es_actual_vence_en_silencio(self):
        cliente = obs_cliente.ClienteObs(
            obs_cliente.AjustesObs(True, 4455, ""), lambda uri: None)
        transporte = TransportePerfil()
        cliente._transporte = transporte
        cliente._TIEMPO_LIMITE = 0.3
        cliente._INTERVALO_PERFIL = 0.1
        reloj = RelojFalso()
        with mock.patch.object(obs_cliente.time, "monotonic", reloj.reloj), \
                mock.patch.object(obs_cliente.time, "sleep", reloj.dormir):
            cliente._esperar_perfil(
                transporte, "SetCurrentProfile", {"profileName": "nuevo"},
                None)
        self.assertGreaterEqual(reloj.ahora, 0.3)
        self.assertGreater(transporte.peticiones, 1)


class PruebasReintentoFinPendiente(unittest.TestCase):
    def test_registra_cada_fallo_del_reintento(self):
        reloj = RelojFalso()
        intentos = []

        def intento():
            intentos.append(1)
            raise RuntimeError("sigue caída")

        with self.assertLogs(fin_pendiente.logger, level="INFO") as registro:
            self.assertFalse(fin_pendiente.reintentar(
                intento, reloj.dormir, reloj.reloj, intervalo=1.0,
                limite=2.0))
        self.assertEqual(len(registro.records), len(intentos))
        for anotado in registro.records:
            self.assertIn("reintento del fin del directo falló",
                          anotado.message)


if __name__ == "__main__":
    unittest.main()
