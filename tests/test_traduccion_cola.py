# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La cola que junta lo que llega en el mismo medio segundo y respeta el orden.

Puro: el instante llega como argumento y lo avanza cada prueba.
"""

import random
import unittest

from guyrapu.translation.cola import Cola
from guyrapu.translation.memoria import Memoria
from guyrapu.translation.proveedores.base import Traduccion


class TestCola(unittest.TestCase):

    def test_junta_lo_del_mismo_medio_segundo_en_un_lote(self):
        cola = Cola("es")
        cola.agregar("uno", 0.0)
        cola.agregar("dos", 0.4)
        self.assertEqual(cola.lote_listo(0.2), [])
        self.assertEqual(cola.lote_listo(0.5), ["uno", "dos"])
        cola.recibir([Traduccion("ONE", "en"), Traduccion("TWO", "fr")])
        self.assertEqual(cola.entregables(0.6),
                         [Traduccion("ONE", "en"), Traduccion("TWO", "fr")])

    def test_el_lote_se_cierra_medio_segundo_despues_del_primero(self):
        cola = Cola("es")
        cola.agregar("uno", 0.0)
        self.assertEqual(cola.lote_listo(0.5), ["uno"])
        cola.agregar("dos", 0.6)
        self.assertEqual(cola.lote_listo(0.9), [])
        cola.recibir([Traduccion("ONE", "en")])
        self.assertEqual(cola.lote_listo(1.1), ["dos"])

    def test_a_los_dos_segundos_se_entrega_el_original(self):
        cola = Cola("es")
        cola.agregar("hola", 10.0)
        self.assertEqual(cola.lote_listo(10.5), ["hola"])
        self.assertEqual(cola.entregables(11.99), [])
        self.assertEqual(cola.entregables(12.0), [Traduccion("hola", None)])

    def test_no_adelanta_un_texto_si_el_anterior_espera(self):
        memoria = Memoria()
        memoria.guardar("nuevo", "es", Traduccion("NEW", "en"))
        cola = Cola("es", memoria)
        cola.agregar("viejo", 0.0)
        cola.agregar("nuevo", 0.1)
        self.assertEqual(cola.lote_listo(0.5), ["viejo"])
        self.assertEqual(cola.entregables(1.0), [])
        self.assertEqual(cola.entregables(2.0),
                         [Traduccion("viejo", None), Traduccion("NEW", "en")])

    def test_lo_que_la_memoria_tiene_sale_traducido_sin_entrar_al_lote(self):
        memoria = Memoria()
        memoria.guardar("hola", "es", Traduccion("HELLO", "en"))
        cola = Cola("es", memoria)
        cola.agregar("hola", 0.0)
        self.assertEqual(cola.lote_listo(0.5), [])
        self.assertEqual(cola.entregables(0.0), [Traduccion("HELLO", "en")])

    def test_lo_recibido_queda_en_la_memoria(self):
        cola = Cola("es")
        cola.agregar("hola", 0.0)
        self.assertEqual(cola.lote_listo(0.5), ["hola"])
        cola.recibir([Traduccion("HELLO", "en")])
        self.assertEqual(cola.entregables(0.6), [Traduccion("HELLO", "en")])
        cola.agregar("hola", 1.0)
        self.assertEqual(cola.lote_listo(2.0), [])
        self.assertEqual(cola.entregables(2.0), [Traduccion("HELLO", "en")])

    def test_un_lote_que_falla_no_cruza_la_respuesta_del_siguiente(self):
        cola = Cola("es")
        cola.agregar("viejo", 0.0)
        self.assertEqual(cola.lote_listo(0.5), ["viejo"])
        cola.agregar("nuevo", 0.6)
        cola.fallo()
        self.assertEqual(cola.lote_listo(1.1), ["nuevo"])
        cola.recibir([Traduccion("NUEVO", "en")])
        self.assertEqual(cola.entregables(1.2), [])
        self.assertEqual(cola.entregables(2.0),
                         [Traduccion("viejo", None), Traduccion("NUEVO", "en")])

    def test_entregables_nunca_adelanta_el_orden_de_llegada(self):
        for semilla in range(8):
            with self.subTest(semilla=semilla):
                self._revisar_orden(random.Random(semilla))

    def _revisar_orden(self, azar):
        cola = Cola("es")
        llegadas = []
        entregadas = []
        en_vuelo = []
        for paso in range(40):
            ahora = paso * 0.1
            if azar.random() < 0.4:
                texto = f"texto{len(llegadas)}"
                cola.agregar(texto, ahora)
                llegadas.append(texto)
            lote = cola.lote_listo(ahora)
            if lote:
                entrega = ahora + azar.choice((0.2, 0.7, 3.0))
                en_vuelo.append((entrega, lote))
            while en_vuelo and en_vuelo[0][0] <= ahora:
                _cuando, lote = en_vuelo.pop(0)
                cola.recibir([Traduccion(f"TRADUCIDO {texto}", "en")
                              for texto in lote])
            entregadas.extend(cola.entregables(ahora))
            originales = [self._original(entrega.texto)
                          for entrega in entregadas]
            self.assertEqual(originales, llegadas[:len(originales)],
                             f"paso {paso}")

    def _original(self, texto):
        if texto.startswith("TRADUCIDO "):
            return texto.split(" ", 1)[1]
        return texto


if __name__ == "__main__":
    unittest.main()
