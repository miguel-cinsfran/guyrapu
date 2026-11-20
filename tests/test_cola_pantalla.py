# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La cola que decide qué se muestra en el vídeo y cuándo se oculta.

Puro: el instante llega como número y lo avanza cada prueba.
"""

import unittest

from guyrapu.interaction.cola_pantalla import ColaPantalla, Pieza


def _pieza(texto, segundos=10, tipo="aviso"):
    return Pieza(tipo=tipo, texto=texto, segundos=segundos, datos={})


class TestColaPantalla(unittest.TestCase):

    def test_salen_de_a_uno_en_orden_y_con_un_segundo_entre_medio(self):
        cola = ColaPantalla()
        primera = _pieza("Primera")
        segunda = _pieza("Segunda")
        self.assertTrue(cola.agregar(primera))
        self.assertTrue(cola.agregar(segunda))
        mostrar = cola.ordenes(0)
        self.assertEqual([orden.accion for orden in mostrar], ["mostrar"])
        self.assertIs(mostrar[0].pieza, primera)
        cola.mostrada(primera, 0)
        self.assertEqual(cola.ordenes(5), [])
        ocultar = cola.ordenes(10)
        self.assertEqual([orden.accion for orden in ocultar], ["ocultar"])
        self.assertIs(ocultar[0].pieza, primera)
        cola.oculta(primera, 10)
        self.assertEqual(cola.ordenes(10.99), [])
        otra = cola.ordenes(11)
        self.assertEqual([orden.accion for orden in otra], ["mostrar"])
        self.assertIs(otra[0].pieza, segunda)

    def test_los_segundos_cuentan_desde_la_confirmacion(self):
        cola = ColaPantalla()
        pieza = _pieza("Aviso")
        cola.agregar(pieza)
        cola.ordenes(0)
        cola.mostrada(pieza, 3)
        self.assertEqual(cola.ordenes(12.99), [])
        self.assertEqual([orden.accion for orden in cola.ordenes(13)],
                         ["ocultar"])

    def test_una_orden_no_se_repite_mientras_espera_confirmacion(self):
        cola = ColaPantalla()
        pieza = _pieza("Aviso")
        cola.agregar(pieza)
        self.assertEqual(len(cola.ordenes(0)), 1)
        self.assertEqual(cola.ordenes(1), [])
        self.assertEqual(cola.ordenes(2), [])
        cola.mostrada(pieza, 2)
        self.assertEqual(cola.ordenes(3), [])
        self.assertEqual(len(cola.ordenes(12)), 1)
        self.assertEqual(cola.ordenes(13), [])
        cola.oculta(pieza, 13)
        self.assertEqual(cola.ordenes(14), [])

    def test_un_fallo_al_mostrar_la_devuelve_primero_y_reintenta_a_los_cinco(self):
        cola = ColaPantalla()
        primera = _pieza("Primera")
        segunda = _pieza("Segunda")
        cola.agregar(primera)
        cola.agregar(segunda)
        cola.ordenes(0)
        cola.fallo(primera, 0)
        self.assertEqual(cola.ordenes(4), [])
        otra = cola.ordenes(5)
        self.assertEqual(len(otra), 1)
        self.assertIs(otra[0].pieza, primera)
        cola.fallo(primera, 5)
        self.assertEqual(cola.ordenes(9), [])
        self.assertIs(cola.ordenes(10)[0].pieza, primera)

    def test_un_fallo_al_mostrar_la_encuesta_se_reintenta_a_los_cinco(self):
        cola = ColaPantalla()
        encuesta = _pieza("¿Sí o no?")
        cola.fijar_encuesta(encuesta)
        cola.ordenes(0)
        cola.fallo(encuesta, 0)
        self.assertEqual(cola.ordenes(4), [])
        self.assertIs(cola.ordenes(5)[0].pieza, encuesta)
        cola.mostrada(encuesta, 5)
        self.assertEqual(cola.describir(),
                         "Encuesta en el vídeo: ¿Sí o no?.")

    def test_un_fallo_al_ocultar_la_da_por_oculta(self):
        cola = ColaPantalla()
        primera = _pieza("Primera")
        segunda = _pieza("Segunda")
        cola.agregar(primera)
        cola.agregar(segunda)
        cola.ordenes(0)
        cola.mostrada(primera, 0)
        cola.ordenes(10)
        cola.fallo(primera, 10)
        self.assertEqual(cola.ordenes(11)[0].pieza, segunda)

    def test_pausar_deja_terminar_la_pieza_y_no_muestra_la_siguiente(self):
        cola = ColaPantalla()
        primera = _pieza("Primera")
        segunda = _pieza("Segunda")
        cola.agregar(primera)
        cola.agregar(segunda)
        cola.ordenes(0)
        cola.mostrada(primera, 0)
        cola.pausar()
        self.assertEqual([orden.accion for orden in cola.ordenes(10)],
                         ["ocultar"])
        cola.oculta(primera, 10)
        self.assertEqual(cola.ordenes(11), [])
        self.assertEqual(cola.ordenes(100), [])
        cola.reanudar()
        self.assertIs(cola.ordenes(100)[0].pieza, segunda)

    def test_saltar_oculta_enseguida_la_que_se_ve(self):
        cola = ColaPantalla()
        primera = _pieza("Primera")
        segunda = _pieza("Segunda")
        cola.agregar(primera)
        cola.agregar(segunda)
        cola.ordenes(0)
        cola.mostrada(primera, 0)
        self.assertEqual(cola.ordenes(1), [])
        cola.saltar()
        self.assertEqual([orden.accion for orden in cola.ordenes(1)],
                         ["ocultar"])
        cola.oculta(primera, 1)
        self.assertEqual(cola.ordenes(1.99), [])
        self.assertIs(cola.ordenes(2)[0].pieza, segunda)

    def test_saltar_mientras_se_esta_mostrando_oculta_al_confirmarse(self):
        cola = ColaPantalla()
        primera = _pieza("Primera")
        cola.agregar(primera)
        cola.ordenes(0)
        cola.saltar()
        self.assertEqual(cola.ordenes(0), [])
        cola.mostrada(primera, 0)
        self.assertEqual([orden.accion for orden in cola.ordenes(0)],
                         ["ocultar"])

    def test_vaciar_descarta_lo_pendiente_sin_tocar_la_que_se_ve(self):
        cola = ColaPantalla()
        primera = _pieza("Primera")
        cola.agregar(primera)
        cola.agregar(_pieza("Segunda"))
        cola.agregar(_pieza("Tercera"))
        cola.ordenes(0)
        cola.mostrada(primera, 0)
        cola.vaciar()
        self.assertEqual([orden.accion for orden in cola.ordenes(10)],
                         ["ocultar"])
        cola.oculta(primera, 10)
        self.assertEqual(cola.ordenes(11), [])

    def test_el_silencio_quita_el_sonido_solo_a_mostrar(self):
        cola = ColaPantalla()
        pieza = _pieza("Aviso")
        cola.silenciar(True)
        cola.agregar(pieza)
        mostrar = cola.ordenes(0)
        self.assertTrue(mostrar[0].con_sonido is False)
        cola.mostrada(pieza, 0)
        cola.silenciar(False)
        ocultar = cola.ordenes(10)
        self.assertEqual(ocultar[0].accion, "ocultar")
        self.assertFalse(ocultar[0].con_sonido)
        cola.oculta(pieza, 10)
        cola.agregar(_pieza("Otra"))
        self.assertTrue(cola.ordenes(11)[0].con_sonido)

    def test_panico_vacia_oculta_y_rechaza_hasta_apagarlo(self):
        cola = ColaPantalla()
        primera = _pieza("Primera")
        segunda = _pieza("Segunda")
        encuesta = _pieza("¿Sí o no?")
        cola.agregar(primera)
        cola.agregar(segunda)
        cola.ordenes(0)
        cola.mostrada(primera, 0)
        cola.fijar_encuesta(encuesta)
        cola.ordenes(0)
        cola.mostrada(encuesta, 0)
        cola.panico(True)
        self.assertFalse(cola.agregar(_pieza("Tercera")))
        self.assertIs(cola.ordenes(1)[0].pieza, primera)
        cola.oculta(primera, 1)
        self.assertIs(cola.ordenes(1)[0].pieza, encuesta)
        cola.oculta(encuesta, 1)
        self.assertEqual(
            cola.describir(),
            "Pánico activado: no se muestra nada en el vídeo.")
        cola.panico(False)
        self.assertIs(cola.ordenes(2)[0].pieza, encuesta)
        cola.mostrada(encuesta, 2)
        self.assertEqual(cola.ordenes(3), [])

    def test_un_fallo_al_mostrar_con_panico_no_devuelve_la_pieza(self):
        cola = ColaPantalla()
        pieza = _pieza("Primera")
        cola.agregar(pieza)
        cola.ordenes(0)
        cola.panico(True)
        cola.fallo(pieza, 0)
        cola.panico(False)
        self.assertEqual(cola.ordenes(100), [])

    def test_la_encuesta_se_muestra_aparte_y_la_cola_sigue(self):
        cola = ColaPantalla()
        encuesta = _pieza("¿Sí o no?")
        primera = _pieza("Primera")
        cola.agregar(primera)
        cola.fijar_encuesta(encuesta)
        self.assertIs(cola.ordenes(0)[0].pieza, encuesta)
        cola.mostrada(encuesta, 0)
        self.assertIs(cola.ordenes(0)[0].pieza, primera)
        cola.mostrada(primera, 0)
        self.assertEqual(cola.describir(),
                         "Encuesta en el vídeo: ¿Sí o no?. "
                         "En el vídeo: Primera.")

    def test_poner_al_dia_la_encuesta_visible_no_la_oculta(self):
        cola = ColaPantalla()
        encuesta = _pieza("¿Sí o no?")
        cola.fijar_encuesta(encuesta)
        cola.ordenes(0)
        cola.mostrada(encuesta, 0)
        nueva = _pieza("¿Sí o no? 2 votos")
        self.assertTrue(cola.poner_al_dia_encuesta(nueva))
        orden = cola.ordenes(1)
        self.assertEqual([actual.accion for actual in orden],
                         ["actualizar"])
        self.assertIs(orden[0].pieza, nueva)
        cola.actualizada(nueva, 1)
        self.assertEqual(cola.ordenes(1), [])
        self.assertEqual(cola.describir(),
                         "Encuesta en el vídeo: ¿Sí o no? 2 votos.")

    def test_p6_la_pieza_fija_de_metas_se_describe_como_metas(self):
        cola = ColaPantalla()
        pieza = _pieza("Risa: 2 de 3", 0, "metas")
        cola.fijar_encuesta(pieza)
        cola.ordenes(0)
        cola.mostrada(pieza, 0)
        self.assertEqual(cola.describir(),
                         "Metas en el vídeo: Risa: 2 de 3.")

    def test_fijar_otra_encuesta_reemplaza_la_anterior(self):
        cola = ColaPantalla()
        primera = _pieza("¿Sí o no?")
        segunda = _pieza("¿Azul o rojo?")
        cola.fijar_encuesta(primera)
        cola.ordenes(0)
        cola.mostrada(primera, 0)
        cola.fijar_encuesta(segunda)
        ocultar = cola.ordenes(1)
        self.assertIs(ocultar[0].pieza, primera)
        self.assertEqual(ocultar[0].accion, "ocultar")
        cola.oculta(primera, 1)
        self.assertIs(cola.ordenes(1)[0].pieza, segunda)
        cola.mostrada(segunda, 1)
        cola.fijar_encuesta(None)
        ocultar = cola.ordenes(2)
        self.assertIs(ocultar[0].pieza, segunda)
        self.assertEqual(ocultar[0].accion, "ocultar")
        cola.oculta(segunda, 2)
        self.assertEqual(cola.describir(), "No hay nada en el vídeo.")

    def test_un_comando_va_delante_de_los_mensajes_y_detras_de_otro_comando(self):
        cola = ColaPantalla()
        cola.agregar(_pieza("Mensaje 1", 0, tipo="mensaje"))
        cola.agregar(_pieza("Mensaje 2", 0, tipo="mensaje"))
        cola.agregar(_pieza("Comando 1", 0, tipo="comando"))
        cola.agregar(_pieza("Comando 2", 0, tipo="comando"))
        vistos = []
        for instante in range(4):
            mostrar = cola.ordenes(instante)[0]
            self.assertEqual(mostrar.accion, "mostrar")
            vistos.append(mostrar.pieza.texto)
            cola.mostrada(mostrar.pieza, instante)
            ocultar = cola.ordenes(instante)[0]
            self.assertEqual(ocultar.accion, "ocultar")
            cola.oculta(ocultar.pieza, instante)
        self.assertEqual(vistos, ["Comando 1", "Comando 2",
                                  "Mensaje 1", "Mensaje 2"])

    def test_un_disparador_va_delante_de_los_mensajes_y_detras_de_lo_que_espera(self):
        cola = ColaPantalla()
        cola.agregar(_pieza("Mensaje 1", 0, tipo="mensaje"))
        cola.agregar(_pieza("Mensaje 2", 0, tipo="mensaje"))
        cola.agregar(_pieza("Comando", 0, tipo="comando"))
        cola.agregar(_pieza("Disparador 1", 0, tipo="disparador"))
        cola.agregar(_pieza("Disparador 2", 0, tipo="disparador"))
        vistos = []
        for instante in range(5):
            mostrar = cola.ordenes(instante)[0]
            self.assertEqual(mostrar.accion, "mostrar")
            vistos.append(mostrar.pieza.texto)
            cola.mostrada(mostrar.pieza, instante)
            ocultar = cola.ordenes(instante)[0]
            self.assertEqual(ocultar.accion, "ocultar")
            cola.oculta(ocultar.pieza, instante)
        self.assertEqual(vistos, ["Comando", "Disparador 1", "Disparador 2",
                                  "Mensaje 1", "Mensaje 2"])

    def test_una_meta_va_delante_de_los_mensajes_como_un_disparador(self):
        cola = ColaPantalla()
        cola.agregar(_pieza("Mensaje 1", 0, tipo="mensaje"))
        cola.agregar(_pieza("Mensaje 2", 0, tipo="mensaje"))
        cola.agregar(_pieza("Meta 1", 0, tipo="meta"))
        cola.agregar(_pieza("Meta 2", 0, tipo="meta"))
        vistos = []
        for instante in range(4):
            mostrar = cola.ordenes(instante)[0]
            self.assertEqual(mostrar.accion, "mostrar")
            vistos.append(mostrar.pieza.texto)
            cola.mostrada(mostrar.pieza, instante)
            ocultar = cola.ordenes(instante)[0]
            self.assertEqual(ocultar.accion, "ocultar")
            cola.oculta(ocultar.pieza, instante)
        self.assertEqual(vistos, ["Meta 1", "Meta 2",
                                  "Mensaje 1", "Mensaje 2"])

    def test_la_pieza_veintiuno_se_rechaza(self):
        cola = ColaPantalla()
        for numero in range(20):
            self.assertTrue(cola.agregar(_pieza(f"Pieza {numero + 1}")))
        self.assertFalse(cola.agregar(_pieza("Pieza 21")))
        self.assertIn("20 en cola.", cola.describir())

    def test_frase_con_encuesta_pieza_cola_y_pausa(self):
        cola = ColaPantalla()
        encuesta = _pieza("¿Sí o no?")
        primera = _pieza("Primera")
        cola.fijar_encuesta(encuesta)
        cola.agregar(primera)
        cola.agregar(_pieza("Segunda"))
        cola.agregar(_pieza("Tercera"))
        cola.ordenes(0)
        cola.mostrada(encuesta, 0)
        cola.ordenes(0)
        cola.mostrada(primera, 0)
        cola.pausar()
        self.assertEqual(
            cola.describir(),
            "Encuesta en el vídeo: ¿Sí o no?. En el vídeo: Primera. "
            "2 en cola. La cola está en pausa.")

    def test_frase_sin_nada_y_con_el_sonido_silenciado(self):
        cola = ColaPantalla()
        self.assertEqual(cola.describir(), "No hay nada en el vídeo.")
        cola.silenciar(True)
        self.assertEqual(cola.describir(),
                         "No hay nada en el vídeo. Sonido de los medios silenciado.")


class TestVideoLibre(unittest.TestCase):

    def test_p3_sin_nada_visible_el_video_esta_libre(self):
        self.assertTrue(ColaPantalla().libre())

    def test_p3_con_una_tarjeta_visible_no_esta_libre(self):
        cola = ColaPantalla()
        pieza = _pieza("Aviso")
        cola.agregar(pieza)
        cola.ordenes(0)
        cola.mostrada(pieza, 0)
        self.assertFalse(cola.libre())

    def test_p3_con_una_encuesta_visible_no_esta_libre(self):
        cola = ColaPantalla()
        encuesta = _pieza("¿Sí o no?", 0, "encuesta")
        cola.fijar_encuesta(encuesta)
        cola.ordenes(0)
        cola.mostrada(encuesta, 0)
        self.assertFalse(cola.libre())


if __name__ == "__main__":
    unittest.main()
