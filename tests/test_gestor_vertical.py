# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del gestor que acompaña al horizontal con el lienzo vertical.

Sin OBS ni ventanas: el gestor de base y el lienzo son dobles, y el reloj
entra inyectado para no esperar los 30 segundos del reintento.
"""

import unittest

from guyrapu.core.idioma import _
from guyrapu.obs import gestor_vertical, obs_cliente


class Reloj:
    def __init__(self, ahora=0.0):
        self.ahora = ahora

    def __call__(self):
        return self.ahora


class GestorFalso:

    def __init__(self, activo=True, escena="Juego"):
        self.activo = activo
        self.escena = escena
        self.escenas_verticales = {"Juego vertical"}
        self.llamadas = []
        self.orden = []

    def iniciar_transmision(self, parada=None):
        self.llamadas.append("iniciar")
        self.orden.append("horizontal_iniciar")

    def detener_transmision(self, parada=None):
        self.llamadas.append("detener")
        self.orden.append("horizontal_detener")

    def estado_transmision(self, parada=None):
        self.llamadas.append("estado")
        return {"outputActive": self.activo}

    def escena_al_aire(self, parada=None):
        self.llamadas.append("escena")
        return self.escena

    def pedir(self, tipo, datos=None, parada=None):
        self.llamadas.append((tipo, datos))
        if tipo == "GetSceneList":
            return {"responseData": {"scenes": [
                {"sceneName": nombre}
                for nombre in self.escenas_verticales]}}
        return {"responseData": {}}


class LienzoFalso:

    def __init__(self, activo=False, escena="Juego vertical", parejas=None,
                 orden=None):
        self.activo = activo
        self.actual = escena
        self.parejas = parejas
        self.llamadas = []
        self.orden = orden if orden is not None else []
        self.fallo_estado = None
        self.fallo_arrancar = None
        self.conecta_al_arrancar = True

    def estado(self, cliente, parada=None):
        self.llamadas.append("estado")
        if self.fallo_estado is not None:
            raise self.fallo_estado
        return {"transmitiendo": self.activo}

    def arrancar(self, cliente, parada=None):
        self.llamadas.append("arrancar")
        self.orden.append("vertical_arrancar")
        if self.fallo_arrancar is not None:
            raise self.fallo_arrancar
        if self.conecta_al_arrancar:
            self.activo = True

    def detener(self, cliente, parada=None):
        self.llamadas.append("detener")
        self.orden.append("vertical_detener")
        self.activo = False

    def escena_actual(self, cliente, parada=None):
        self.llamadas.append("escena_actual")
        return self.actual

    def cambiar_escena(self, cliente, escena, parada=None):
        self.llamadas.append(("cambiar", escena))
        if self.parejas is not None and escena not in self.parejas:
            return
        self.actual = escena


class BaseGestorVertical(unittest.TestCase):

    def armar(self, base=None, lienzo=None, reloj=None, escena="Juego vertical"):
        self.anuncios = []
        self.orden = []
        self.base = base or GestorFalso()
        self.base.orden = self.orden
        self.lienzo = lienzo or LienzoFalso(orden=self.orden)
        if self.lienzo.parejas is not None:
            self.base.escenas_verticales = set(self.lienzo.parejas)
        self.reloj = reloj or Reloj()
        gestor = gestor_vertical.GestorVertical(
            self.base,
            lambda frase, sonido: self.anuncios.append((frase, sonido)),
            lienzo={"canvasUuid": "uuid-vertical"},
            escena=escena, lienzo_mod=self.lienzo, reloj=self.reloj)
        return gestor

    def iniciar(self, gestor):
        gestor.iniciar_transmision(None)


class ArranqueTest(BaseGestorVertical):

    def test_arranca_el_horizontal_y_despues_el_vertical_y_avisa(self):
        gestor = self.armar()
        self.iniciar(gestor)

        self.assertEqual(self.base.llamadas[0], "iniciar")
        self.assertIn("arrancar", self.lienzo.llamadas)
        self.assertEqual(self.orden[:2],
                         ["horizontal_iniciar", "vertical_arrancar"])
        self.assertIn((_("El vertical también está transmitiendo."),
                       "conectado"), self.anuncios)

    def test_si_el_vertical_no_arranca_avisa_y_el_horizontal_sigue(self):
        lienzo = LienzoFalso()
        lienzo.fallo_arrancar = obs_cliente.ObsError("sin salida")
        gestor = self.armar(lienzo=lienzo)

        gestor.iniciar_transmision(None)

        self.assertEqual(self.base.llamadas[0], "iniciar")
        self.assertEqual(self.base.activo, True)
        self.assertIn((_("El vertical se interrumpió. El horizontal sigue y "
                         "Guyrapu lo vuelve a intentar cada 30 segundos."),
                       "transmision_problema"), self.anuncios)


class VigilanciaTest(BaseGestorVertical):

    def test_un_gestor_que_no_arranco_delega_y_no_vigila(self):
        gestor = self.armar()

        self.assertEqual(gestor.estado_transmision(None),
                         {"outputActive": True})
        self.assertEqual(self.lienzo.llamadas, [])
        self.assertEqual(self.anuncios, [])

    def test_un_corte_avisa_una_sola_vez_y_el_horizontal_sigue(self):
        gestor = self.armar()
        self.iniciar(gestor)
        self.lienzo.activo = False

        gestor.estado_transmision(None)
        gestor.estado_transmision(None)

        cortes = [aviso for aviso in self.anuncios
                  if aviso[0] == _(
                      "El vertical se interrumpió. El horizontal sigue y Guyrapu "
                      "lo vuelve a intentar cada 30 segundos.")]
        self.assertEqual(len(cortes), 1)
        self.assertEqual(cortes[0][1], "transmision_problema")
        self.assertNotIn("detener", self.base.llamadas)

    def test_reintenta_a_los_treinta_segundos_y_avisa_cuando_vuelve(self):
        gestor = self.armar()
        self.iniciar(gestor)
        self.lienzo.activo = False
        gestor.estado_transmision(None)
        arranques = self.lienzo.llamadas.count("arrancar")

        self.reloj.ahora = 29.0
        gestor.estado_transmision(None)
        self.assertEqual(self.lienzo.llamadas.count("arrancar"), arranques)

        self.lienzo.conecta_al_arrancar = False
        self.reloj.ahora = 30.0
        gestor.estado_transmision(None)
        self.assertEqual(self.lienzo.llamadas.count("arrancar"),
                         arranques + 1)
        self.assertNotIn((_("El vertical volvió."), "transmision_recuperada"),
                         self.anuncios)

        self.lienzo.activo = True
        gestor.estado_transmision(None)
        self.assertIn((_("El vertical volvió."), "transmision_recuperada"),
                      self.anuncios)

    def test_un_reintento_que_falla_no_repite_el_aviso_de_corte(self):
        gestor = self.armar()
        self.iniciar(gestor)
        self.lienzo.activo = False
        gestor.estado_transmision(None)
        self.lienzo.fallo_arrancar = obs_cliente.ObsError("sin salida")

        self.reloj.ahora = 30.0
        gestor.estado_transmision(None)
        self.reloj.ahora = 60.0
        gestor.estado_transmision(None)

        cortes = [aviso for aviso in self.anuncios
                  if aviso[0] == _(gestor_vertical.MENSAJE_CORTE)]
        self.assertEqual(len(cortes), 1)
        self.assertEqual(cortes[0][1], "transmision_problema")

    def test_un_fallo_del_lienzo_no_corta_la_vigilancia(self):
        gestor = self.armar()
        self.iniciar(gestor)
        self.lienzo.fallo_estado = obs_cliente.ObsError("sin respuesta")

        estado = gestor.estado_transmision(None)

        self.assertEqual(estado, {"outputActive": True})
        self.assertNotIn("detener", self.base.llamadas)


class EscenasTest(BaseGestorVertical):

    def test_cambia_el_vertical_a_la_pareja_de_la_escena(self):
        lienzo = LienzoFalso(parejas={"Juego vertical", "Charla vertical"})
        gestor = self.armar(lienzo=lienzo)
        self.iniciar(gestor)

        self.base.escena = "Charla"
        gestor.estado_transmision(None)

        self.assertIn(("cambiar", "Charla vertical"), lienzo.llamadas)
        self.assertEqual(lienzo.actual, "Charla vertical")

    def test_sin_pareja_avisa_una_vez_por_escena_y_queda_en_la_anterior(self):
        lienzo = LienzoFalso(parejas={"Juego vertical"})
        gestor = self.armar(lienzo=lienzo)
        self.iniciar(gestor)

        self.base.escena = "Charla"
        gestor.estado_transmision(None)
        gestor.estado_transmision(None)

        avisos = [aviso for aviso in self.anuncios
                  if aviso[1] == "aviso"]
        self.assertEqual(avisos, [(
            _("La escena {escena} no tiene versión vertical: el vertical "
              "sigue en {vertical}. Créala con Crear la versión vertical.")
            .format(escena="Charla", vertical="Juego vertical"), "aviso")])
        self.assertEqual(lienzo.actual, "Juego vertical")
        self.assertNotIn(("cambiar", "Charla vertical"), lienzo.llamadas)


class FinTest(BaseGestorVertical):

    def test_si_el_horizontal_termina_solo_detiene_el_vertical_y_lo_dice(self):
        gestor = self.armar()
        self.iniciar(gestor)
        self.base.activo = False

        gestor.estado_transmision(None)

        self.assertIn("detener", self.lienzo.llamadas)
        self.assertNotIn("detener", self.base.llamadas)
        self.assertIn((_("También se detuvo el vertical."),
                       "transmision_problema"), self.anuncios)

    def test_no_avisa_fin_si_el_vertical_ya_estaba_detenido(self):
        gestor = self.armar()
        self.iniciar(gestor)
        self.lienzo.activo = False
        self.base.activo = False

        gestor.estado_transmision(None)

        self.assertNotIn("detener", self.lienzo.llamadas)
        self.assertNotIn((_("También se detuvo el vertical."),
                          "transmision_problema"), self.anuncios)

    def test_no_lo_dice_cada_vuelta_despues_del_fin(self):
        gestor = self.armar()
        self.iniciar(gestor)
        self.base.activo = False
        gestor.estado_transmision(None)

        gestor.estado_transmision(None)

        avisos = [aviso for aviso in self.anuncios
                  if aviso[0] == _("También se detuvo el vertical.")]
        self.assertEqual(len(avisos), 1)


class DetenerTest(BaseGestorVertical):

    def test_detener_detiene_el_vertical_antes_que_el_horizontal(self):
        gestor = self.armar()
        self.iniciar(gestor)

        gestor.detener_transmision(None)

        self.assertEqual(self.orden[-2:],
                         ["vertical_detener", "horizontal_detener"])
        self.assertEqual(self.anuncios, [(
            _("El vertical también está transmitiendo."), "conectado")])

    def test_detener_no_anuncia_corte_aunque_el_vertical_se_apague(self):
        gestor = self.armar()
        self.iniciar(gestor)

        gestor.detener_transmision(None)
        gestor.estado_transmision(None)

        cortes = [aviso for aviso in self.anuncios
                  if aviso[0] == _(
                      "El vertical se interrumpió. El horizontal sigue y Guyrapu "
                      "lo vuelve a intentar cada 30 segundos.")]
        self.assertEqual(cortes, [])


if __name__ == "__main__":
    unittest.main()
