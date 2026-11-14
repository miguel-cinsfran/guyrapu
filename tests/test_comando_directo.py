# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del comando de transmitir y finalizar el directo.

Sin ventana: los cuadros, los hilos y el supervisor van con dobles, así se
corren acá.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.ui import comando_directo
from tests.pseudo_prueba import con_pseudo


def _avisar_de(anunciar, sonar):
    def _avisar(texto, sonido=None, *, error=False):
        anunciar(texto)
        if sonido:
            sonar(sonido)
    return _avisar


class TestTransmitirSinVentana(unittest.TestCase):
    # Sin ventana: pedir_destino y la revisión de OBS van con dobles.

    def _comando(self, **config):
        comando = comando_directo.ComandoDirecto(mock.Mock())
        marco = comando._marco
        marco._alive = True
        marco._config = {"transmision_destino": "TikTok",
                         "tiktok_usuario": "guardado"}
        marco._config.update(config)
        marco._guardar_destino_transmision = mock.Mock(
            side_effect=lambda d: marco._config.update(
                {"transmision_destino": d}) or d)
        marco._guardar_usuario_tiktok = mock.Mock(
            side_effect=lambda u: marco._config.update(
                {"tiktok_usuario": u}) or u)
        marco._supervisar_transmision = mock.Mock()
        marco._actualizar_boton_directo = mock.Mock()
        comando._boton = mock.Mock()
        return comando, marco

    def test_cancelar_anuncia_y_no_revisa(self):
        comando, marco = self._comando()
        with mock.patch(
                "guyrapu.ui.gui_elegir_destino.pedir_destino",
                return_value=None) as pedir, \
                mock.patch.object(comando_directo.diagnostico,
                                  "crear_hilo") as hilos, \
                mock.patch.object(comando_directo, "anunciar") as anunciar:
            comando._transmitir(marco)
        pedir.assert_called_once_with(marco, "TikTok", "guardado")
        anunciar.assert_called_once_with("No se transmitió.")
        hilos.assert_not_called()
        marco._guardar_destino_transmision.assert_not_called()

    def test_youtube_guarda_y_revisa_aunque_el_guardado_decia_tiktok(self):
        comando, marco = self._comando(transmision_destino="TikTok",
                                       tiktok_usuario="guardado")
        hilos = []
        revision = mock.sentinel.revision
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=revision)

        class Hilo:
            def __init__(self, target, *args, **kwargs):
                self.target = target

            def start(self):
                hilos.append(self.target)
                self.target()

        with mock.patch(
                "guyrapu.ui.gui_elegir_destino.pedir_destino",
                return_value=("YouTube", "")), \
                mock.patch.object(comando_directo.diagnostico,
                                  "crear_hilo",
                                  side_effect=lambda f, n: Hilo(f)), \
                mock.patch.object(comando_directo.transmision_directa,
                                  "preparar",
                                  return_value=preparacion) as preparar, \
                mock.patch.object(comando_directo, "anunciar"), \
                mock.patch.object(comando_directo._snd, "reproducir"), \
                mock.patch.object(comando_directo.wx,
                                  "CallAfter",
                                  side_effect=lambda f, *a: f(*a)):
            comando._transmitir(marco)
        marco._guardar_destino_transmision.assert_called_once_with(
            "YouTube")
        preparar.assert_called_once()
        args, _ = preparar.call_args
        self.assertEqual(args[1], "YouTube")
        marco._supervisar_transmision.assert_called_once_with(
            "iniciar", "YouTube", "", revision=revision)

    def test_restream_sin_cuenta_avisa_y_no_revisa(self):
        comando, marco = self._comando()
        with mock.patch(
                "guyrapu.ui.gui_elegir_destino.pedir_destino",
                return_value=("restream:Uno", "")), \
                mock.patch.object(comando_directo.ganchos,
                                  "cuenta_conectada",
                                  return_value=False), \
                mock.patch.object(comando_directo, "anunciar") as anunciar, \
                mock.patch.object(comando_directo._snd,
                                  "reproducir") as sonido, \
                mock.patch.object(comando_directo, "avisar",
                                  _avisar_de(anunciar, sonido)), \
                mock.patch.object(comando_directo.diagnostico,
                                  "crear_hilo") as hilos:
            comando._transmitir(marco)
        anunciar.assert_called_once_with(
            "Para transmitir con un perfil de Restream hace falta conectar "
            "la cuenta, en el cuadro Restream, pestaña Cuenta.")
        sonido.assert_called_once_with("error")
        hilos.assert_not_called()
        marco._guardar_destino_transmision.assert_called_once_with(
            "restream:Uno")

    def test_restream_prepara_obs_y_supervisa_la_opcion(self):
        from guyrapu.restream.perfiles import Perfil
        comando, marco = self._comando()
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        perfil = Perfil(nombre="Vertical", canales=(1,),
                        orientacion="vertical")

        class Hilo:
            def __init__(self, target, *args, **kwargs):
                self.target = target

            def start(self):
                self.target()

        with mock.patch(
                "guyrapu.ui.gui_elegir_destino.pedir_destino",
                return_value=("restream:Vertical", "")), \
                mock.patch.object(comando_directo.ganchos,
                                  "cuenta_conectada", return_value=True), \
                mock.patch.object(comando_directo.ganchos,
                                  "cargar_perfiles",
                                  return_value=[perfil]), \
                mock.patch.object(comando_directo.diagnostico,
                                  "crear_hilo",
                                  side_effect=lambda f, n: Hilo(f)), \
                mock.patch.object(comando_directo.transmision_directa,
                                  "preparar",
                                  return_value=preparacion) as preparar, \
                mock.patch.object(comando_directo, "anunciar"), \
                mock.patch.object(comando_directo._snd, "reproducir"), \
                mock.patch.object(comando_directo.wx, "CallAfter",
                                  side_effect=lambda f, *a: f(*a)):
            comando._transmitir(marco)
        args, kwargs = preparar.call_args
        self.assertEqual(args[1], "TikTok")
        self.assertEqual(kwargs.get("opcion"), "restream:Vertical")
        marco._guardar_destino_transmision.assert_called_once_with(
            "restream:Vertical")
        marco._guardar_usuario_tiktok.assert_not_called()
        marco._supervisar_transmision.assert_called_once_with(
            "iniciar", "restream:Vertical", "")

    def test_tiktok_guarda_usuario_y_revisa(self):
        comando, marco = self._comando()
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)

        class Hilo:
            def __init__(self, target, *args, **kwargs):
                self.target = target

            def start(self):
                self.target()

        with mock.patch(
                "guyrapu.ui.gui_elegir_destino.pedir_destino",
                return_value=("TikTok", "nuevo")), \
                mock.patch.object(comando_directo.diagnostico,
                                  "crear_hilo",
                                  side_effect=lambda f, n: Hilo(f)), \
                mock.patch.object(comando_directo.transmision_directa,
                                  "preparar",
                                  return_value=preparacion), \
                mock.patch.object(comando_directo, "anunciar"), \
                mock.patch.object(comando_directo._snd, "reproducir"), \
                mock.patch.object(
                    comando_directo, "confirmar_transmision",
                    return_value=True), \
                mock.patch.object(comando_directo.wx,
                                  "CallAfter",
                                  side_effect=lambda f, *a: f(*a)):
            comando._transmitir(marco)
        marco._guardar_destino_transmision.assert_called_once_with(
            "TikTok")
        marco._guardar_usuario_tiktok.assert_called_once_with("nuevo")


class TestRevisionListaSinVentana(unittest.TestCase):
    # Sin ventana: confirmar y supervisar van con dobles.

    def _comando(self):
        comando = comando_directo.ComandoDirecto(mock.Mock())
        marco = comando._marco
        marco._alive = True
        marco._supervisar_transmision = mock.Mock()
        marco._actualizar_boton_directo = mock.Mock()
        comando._boton = mock.Mock()
        return comando, marco

    def test_youtube_no_confirma_y_pasa_la_revision(self):
        comando, marco = self._comando()
        revision = mock.sentinel.revision
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=revision)
        with mock.patch.object(
                comando_directo, "confirmar_transmision") as confirmar:
            comando._revision_lista(marco, preparacion, "YouTube", "YouTube", "")
        confirmar.assert_not_called()
        marco._supervisar_transmision.assert_called_once_with(
            "iniciar", "YouTube", "", revision=revision)

    def test_tiktok_confirma_como_hoy(self):
        comando, marco = self._comando()
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        with mock.patch.object(
                comando_directo, "confirmar_transmision",
                return_value=True) as confirmar, \
                mock.patch(
                    "guyrapu.obs.perfil_previo.volver_sin_directo") as volver:
            comando._revision_lista(
                marco, preparacion, "TikTok", "TikTok", "usuario")
        confirmar.assert_called_once_with(marco, preparacion.revision, ())
        volver.assert_not_called()
        marco._supervisar_transmision.assert_called_once_with(
            "iniciar", "TikTok", "usuario")

    def test_tiktok_cancelar_anuncia_y_no_inicia(self):
        comando, marco = self._comando()
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        with mock.patch.object(
                comando_directo, "confirmar_transmision",
                return_value=False), \
                mock.patch.object(comando_directo, "anunciar") as anunciar, \
                mock.patch(
                    "guyrapu.obs.perfil_previo.volver_sin_directo") as volver:
            comando._revision_lista(
                marco, preparacion, "TikTok", "TikTok", "usuario")
        anunciar.assert_called_once_with("No se transmitió.")
        volver.assert_called_once_with()
        marco._supervisar_transmision.assert_not_called()

    def _con_destinos(self):
        destino = SimpleNamespace(plataforma="YouTube", nombre="Canal",
                                  activo=True)
        return (destino,)

    def test_con_destinos_de_mas_los_pasa_a_confirmar(self):
        comando, marco = self._comando()
        destinos = self._con_destinos()
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision,
                                      destinos_de_mas=destinos)
        with mock.patch.object(
                comando_directo, "confirmar_transmision",
                return_value=True) as confirmar:
            comando._revision_lista(
                marco, preparacion, "TikTok", "TikTok", "usuario")
        confirmar.assert_called_once_with(
            marco, preparacion.revision, destinos)
        marco._supervisar_transmision.assert_called_once_with(
            "iniciar", "TikTok", "usuario")

    def test_con_destinos_y_cancelar_no_inicia(self):
        comando, marco = self._comando()
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision,
                                      destinos_de_mas=self._con_destinos())
        with mock.patch.object(
                comando_directo, "confirmar_transmision",
                return_value=False), \
                mock.patch.object(comando_directo, "anunciar") as anunciar, \
                mock.patch(
                    "guyrapu.obs.perfil_previo.volver_sin_directo") as volver:
            comando._revision_lista(
                marco, preparacion, "TikTok", "TikTok", "usuario")
        marco._supervisar_transmision.assert_not_called()
        anunciar.assert_called_once_with("No se transmitió.")
        volver.assert_called_once_with()

    def test_sin_destinos_de_mas_confirma_vacio(self):
        comando, marco = self._comando()
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        with mock.patch.object(
                comando_directo, "confirmar_transmision",
                return_value=True) as confirmar:
            comando._revision_lista(
                marco, preparacion, "TikTok", "TikTok", "usuario")
        confirmar.assert_called_once_with(
            marco, preparacion.revision, ())
        marco._supervisar_transmision.assert_called_once_with(
            "iniciar", "TikTok", "usuario")


class TestPulsarSinVentana(unittest.TestCase):
    # Sin ventana: pulsar es el único camino que comparten los botones.

    def _comando(self, transmitiendo=False, deteniendo=False):
        comando = comando_directo.ComandoDirecto(mock.Mock())
        comando._transmitiendo = transmitiendo
        comando._deteniendo = deteniendo
        comando._boton = mock.Mock()
        return comando, comando._marco

    def test_pulsar_sin_directo_transmite(self):
        comando, marco = self._comando()
        with mock.patch.object(comando, "_transmitir") as transmitir:
            comando.pulsar(marco)
        transmitir.assert_called_once_with(marco)

    def test_pulsar_transmitiendo_finaliza(self):
        comando, marco = self._comando(transmitiendo=True)
        with mock.patch.object(comando, "_finalizar") as finalizar:
            comando.pulsar(marco)
        finalizar.assert_called_once_with(marco)

    def test_pulsar_deteniendo_solo_avisa(self):
        comando, marco = self._comando(transmitiendo=True, deteniendo=True)
        with (
                mock.patch.object(comando, "_finalizar") as finalizar,
                mock.patch.object(comando, "_transmitir") as transmitir,
                mock.patch.object(comando_directo, "anunciar") as anunciar,
        ):
            comando.pulsar(marco)
        finalizar.assert_not_called()
        transmitir.assert_not_called()
        anunciar.assert_called_once_with(
            "Deteniendo la transmisión. Esperando a que OBS confirme.")


class TestPulsarDeteniendoSinVentana(unittest.TestCase):
    # Sin ventana: se comprueba que pulsar mientras se detiene solo avisa.

    def _comando(self):
        comando = comando_directo.ComandoDirecto(mock.Mock())
        comando._transmitiendo = True
        comando._deteniendo = True
        comando._marco._alive = True
        comando._boton = mock.Mock()
        return comando, comando._marco

    def test_pulsar_deteniendo_anuncia_y_no_dialoga_ni_detiene(self):
        comando, marco = self._comando()
        with mock.patch.object(comando_directo.wx, "MessageDialog") as dialogo, \
                mock.patch.object(comando_directo, "anunciar") as anunciar, \
                mock.patch.object(comando_directo.diagnostico,
                                  "crear_hilo") as hilos:
            comando.pulsar(marco)
        dialogo.assert_not_called()
        hilos.assert_not_called()
        marco._supervisar_transmision.assert_not_called()
        anunciar.assert_called_once_with(
            "Deteniendo la transmisión. Esperando a que OBS confirme.")


class TestPseudoAnunciosComandoDirecto(unittest.TestCase):
    # Sin ventana: controles y marco con dobles, así se corre acá. Los
    # textos que arman otros módulos (`mensaje_de_fallo_obs` y el error
    # del cierre en YouTube) no entran.

    def setUp(self):
        self.modulo = comando_directo
        self.captados = []
        parches = [
            mock.patch.object(comando_directo, "anunciar",
                              self.captados.append),
            mock.patch.object(comando_directo, "avisar",
                              lambda texto, sonido=None, **k:
                              self.captados.append(texto)),
            mock.patch.object(comando_directo._snd, "reproducir"),
        ]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        pseudo = con_pseudo()
        pseudo.__enter__()
        self.addCleanup(pseudo.__exit__, None, None, None)

    def _exigir_marcados(self, cantidad):
        self.assertEqual(len(self.captados), cantidad)
        for frase in self.captados:
            self.assertTrue(frase.startswith("[¡"), frase)
        del self.captados[:]

    def _comando(self, **config):
        comando = comando_directo.ComandoDirecto(mock.Mock())
        marco = comando._marco
        marco._alive = True
        marco._config = {"transmision_destino": "TikTok",
                         "tiktok_usuario": "guardado"}
        marco._config.update(config)
        marco._guardar_destino_transmision = mock.Mock(
            side_effect=lambda d: marco._config.update(
                {"transmision_destino": d}) or d)
        marco._guardar_usuario_tiktok = mock.Mock(
            side_effect=lambda u: marco._config.update(
                {"tiktok_usuario": u}) or u)
        marco._supervisar_transmision = mock.Mock()
        marco._actualizar_boton_directo = mock.Mock()
        comando._boton = mock.Mock()
        comando._transmitiendo = False
        comando._deteniendo = False
        return comando, marco

    def test_pulsar_deteniendo_avisa_marcado(self):
        comando, marco = self._comando()
        comando._transmitiendo = True
        comando._deteniendo = True
        with mock.patch.object(self.modulo.diagnostico,
                               "crear_hilo") as hilos:
            comando.pulsar(marco)
        hilos.assert_not_called()
        marco._supervisar_transmision.assert_not_called()
        self._exigir_marcados(1)

    def test_transmitir_cancelado_avisa_marcado(self):
        comando, marco = self._comando()
        with mock.patch(
                "guyrapu.ui.gui_elegir_destino.pedir_destino",
                return_value=None), \
                mock.patch.object(self.modulo.diagnostico,
                                  "crear_hilo") as hilos:
            comando._transmitir(marco)
        hilos.assert_not_called()
        self._exigir_marcados(1)

    def test_transmitir_revisa_marcado(self):
        comando, marco = self._comando()
        with mock.patch(
                "guyrapu.ui.gui_elegir_destino.pedir_destino",
                return_value=("TikTok", "nuevo")), \
                mock.patch.object(self.modulo.diagnostico, "crear_hilo"):
            comando._transmitir(marco)
        marco._guardar_usuario_tiktok.assert_called_once_with("nuevo")
        self._exigir_marcados(1)

    def test_revision_ya_transmitiendo_avisa_marcado(self):
        comando, marco = self._comando()
        preparacion = SimpleNamespace(ya_transmitiendo=True,
                                      revision=mock.sentinel.revision)
        comando._revision_lista(marco, preparacion, "YouTube", "YouTube", "")
        self._exigir_marcados(1)

    def test_revision_tiktok_cancelado_avisa_marcado(self):
        comando, marco = self._comando()
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        with mock.patch.object(
                comando_directo, "confirmar_transmision",
                return_value=False):
            comando._revision_lista(
                marco, preparacion, "TikTok", "TikTok", "usuario")
        marco._supervisar_transmision.assert_not_called()
        self._exigir_marcados(1)

    def test_finalizar_pide_confirmacion_y_sigue_marcado(self):
        comando, marco = self._comando()
        comando._transmitiendo = True
        with mock.patch.object(self.modulo, "confirmar_finalizar",
                               return_value=False) as confirmar:
            comando._finalizar(marco)
        confirmar.assert_called_once_with(marco)
        marco._supervisar_transmision.assert_not_called()
        self._exigir_marcados(1)

    def test_finalizada_avisa_marcado(self):
        comando, _marco = self._comando()
        comando._finalizada()
        self._exigir_marcados(1)


if __name__ == "__main__":
    unittest.main()
