# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las decisiones del botón directo, sin ventana ni OBS."""

from types import SimpleNamespace
import unittest
from unittest import mock

from tests.pseudo_prueba import con_pseudo
from guyrapu.obs import transmision_directa
from guyrapu.obs.transmision_directa import (
    ALTERNAR, DETENER_SUPERVISADA, ESPERAR_DETENCION, FALTA_DESTINO,
    FALTA_USUARIO, REVISAR, FalloCierreYoutube, Preparacion, boton_visible,
    cuenta_restream_conectada, decidir_transmision, es_directo_propio,
    etiqueta, finalizar, preparar, resolver_revision)


class EsDirectoPropioTest(unittest.TestCase):
    def test_conexion_pedida_por_la_transmision_en_youtube(self):
        self.assertTrue(es_directo_propio(False, "", "", True))

    def test_conexion_pedida_por_la_transmision_en_tiktok(self):
        self.assertTrue(es_directo_propio(True, "otro", "mio", True))

    def test_tiktok_mismo_usuario_sin_importar_mayusculas(self):
        self.assertTrue(es_directo_propio(True, "Amigo", "amigo", False))

    def test_tiktok_con_arroba_coincide_con_el_guardado(self):
        self.assertTrue(es_directo_propio(True, "@amigo", "amigo", False))

    def test_tiktok_directo_de_otro(self):
        self.assertFalse(es_directo_propio(True, "otro", "mio", False))

    def test_tiktok_sin_usuario_en_la_sesion(self):
        self.assertFalse(es_directo_propio(True, "", "mio", False))

    def test_tiktok_sin_usuario_guardado(self):
        self.assertFalse(es_directo_propio(True, "mio", "", False))

    def test_youtube_sin_conexion_pedida_aunque_coincida(self):
        self.assertFalse(es_directo_propio(False, "mio", "mio", False))

    def test_video_grabado_de_youtube_sin_conexion_pedida(self):
        self.assertFalse(es_directo_propio(False, "", "", False))


class BotonVisibleTest(unittest.TestCase):
    def test_pantalla_de_inicio_visible(self):
        self.assertTrue(boton_visible(False, False, False, False))

    def test_pantalla_de_inicio_visible_aunque_se_transmita(self):
        self.assertTrue(boton_visible(False, False, False, True))

    def test_conectando_oculto(self):
        self.assertFalse(boton_visible(False, True, False, False))
        self.assertFalse(boton_visible(False, True, False, True))

    def test_conectando_al_propio_visible(self):
        self.assertTrue(boton_visible(False, True, True, False))

    def test_directo_de_otro_oculto(self):
        self.assertFalse(boton_visible(True, False, False, False))

    def test_directo_de_otro_oculto_mientras_se_transmite(self):
        self.assertFalse(boton_visible(True, False, False, True))

    def test_directo_propio_visible(self):
        self.assertTrue(boton_visible(True, False, True, False))

    def test_directo_propio_visible_mientras_se_transmite(self):
        self.assertTrue(boton_visible(True, False, True, True))


class EtiquetaTest(unittest.TestCase):
    def test_sin_transmitir_invita_a_transmitir(self):
        self.assertEqual(etiqueta(False),
                         ("Transm&itir en directo", "Transmitir en directo"))

    def test_transmitiendo_invita_a_finalizar(self):
        self.assertEqual(etiqueta(True),
                         ("&Finalizar directo", "Finalizar directo"))

    def test_deteniendo_avisa_que_se_espera_a_obs(self):
        self.assertEqual(
            etiqueta(True, deteniendo=True),
            ("Finalizando el directo",
             "Finalizando el directo, esperando a OBS"))

    def test_deteniendo_manda_aunque_no_transmita(self):
        self.assertEqual(
            etiqueta(False, deteniendo=True),
            ("Finalizando el directo",
             "Finalizando el directo, esperando a OBS"))


class GestorFalso:
    def __init__(self, transmitiendo=False, perfil="TikTok", fallo=None,
                 resultado_preparar=None):
        self.transmitiendo = transmitiendo
        self.perfil = perfil
        self.fallo = fallo
        self.resultado_preparar = resultado_preparar
        self.llamadas = []
        self.cierres = 0

    def conectar(self, *args, **kwargs):
        self.llamadas.append("conectar")

    def estado_transmision(self, *args, **kwargs):
        self.llamadas.append("estado")
        return {"outputActive": self.transmitiendo}

    def perfil_actual(self, *args, **kwargs):
        self.llamadas.append("perfil")
        return self.perfil

    def preparar_destino(self, destino, *args, **kwargs):
        self.llamadas.append(("preparar", destino))
        if self.fallo == "preparar":
            raise RuntimeError("boom al preparar")
        return self.resultado_preparar

    def revisar(self, destino, *args, **kwargs):
        self.llamadas.append(("revisar", destino))
        return ("revision", destino)

    def detener_transmision(self, *args, **kwargs):
        self.llamadas.append("detener")

    def cerrar(self, *args, **kwargs):
        self.llamadas.append("cerrar")
        self.cierres += 1


def _asegurar(registro, conectar, al_anunciar=None, parada=None):
    registro.append(("asegurar", conectar, al_anunciar, parada))


class PrepararTest(unittest.TestCase):
    def setUp(self):
        # El perfil elegido sale de config.ini, que cambia de una PC a otra.
        parche = mock.patch(
            "guyrapu.obs.perfil_por_uso.perfil_elegido",
            side_effect=lambda plataforma: plataforma)
        parche.start()
        self.addCleanup(parche.stop)

    def _preparar(self, gestor, destino="TikTok", parada=None):
        registro = []
        anuncios = []
        resultado = preparar(
            gestor, destino,
            lambda conectar, al_anunciar=None, parada=None: _asegurar(
                registro, conectar, al_anunciar, parada),
            anuncios.append, parada=parada)
        return resultado, registro, anuncios

    def test_orden_exacta_de_llamadas(self):
        gestor = GestorFalso(transmitiendo=False, perfil="TikTok")
        resultado, registro, anuncios = self._preparar(gestor)
        self.assertFalse(resultado.ya_transmitiendo)
        self.assertEqual(resultado.revision, ("revision", "TikTok"))
        self.assertEqual(len(registro), 1)
        _nombre, conectar, al_anunciar, parada = registro[0]
        self.assertTrue(callable(conectar))
        self.assertTrue(callable(al_anunciar))
        self.assertIsNone(parada)
        self.assertEqual(
            gestor.llamadas,
            ["conectar", "estado", "perfil", ("preparar", "TikTok"),
             ("revisar", "TikTok"), "cerrar"])
        self.assertEqual(anuncios, [])

    def test_ya_transmitiendo_no_prepara_ni_revisa(self):
        gestor = GestorFalso(transmitiendo=True, perfil="YouTube")
        resultado, _registro, anuncios = self._preparar(gestor, "TikTok")
        self.assertTrue(resultado.ya_transmitiendo)
        self.assertIsNone(resultado.revision)
        self.assertEqual(gestor.llamadas, ["conectar", "estado", "cerrar"])
        self.assertEqual(anuncios, [])

    def test_anuncia_solo_cuando_el_perfil_es_otro(self):
        gestor = GestorFalso(transmitiendo=False, perfil="YouTube")
        _resultado, _registro, anuncios = self._preparar(gestor, "TikTok")
        self.assertEqual(anuncios, ["Preparando OBS para TikTok."])

    def test_cierra_aunque_preparar_levante(self):
        gestor = GestorFalso(transmitiendo=False, perfil="TikTok",
                             fallo="preparar")
        with self.assertRaises(RuntimeError):
            self._preparar(gestor)
        self.assertEqual(gestor.llamadas[-1], "cerrar")

    def test_la_parada_llega_a_asegurar(self):
        gestor = GestorFalso()
        parada = object()
        _resultado, registro, _anuncios = self._preparar(
            gestor, parada=parada)
        self.assertIs(registro[0][3], parada)

    def test_perfil_creado_se_anuncia(self):
        gestor = GestorFalso(transmitiendo=False, perfil="Sin Título",
                             resultado_preparar={"perfil_creado": True})
        _resultado, _registro, anuncios = self._preparar(gestor, "YouTube")
        self.assertIn("Se creó en OBS el perfil YouTube.", anuncios)

    def test_anuncia_el_perfil_real_que_va_a_usar(self):
        gestor = GestorFalso(transmitiendo=False, perfil="Otro",
                             resultado_preparar={"perfil_creado": True,
                                                 "perfil": "Mi horizontal"})
        with mock.patch("guyrapu.obs.perfil_por_uso.perfil_elegido",
                        return_value="Mi horizontal"):
            _resultado, _registro, anuncios = self._preparar(
                gestor, "YouTube")
        self.assertEqual(anuncios, [
            "Preparando OBS para Mi horizontal.",
            "Se creó en OBS el perfil Mi horizontal."])

    def test_sin_perfil_creado_no_hay_anuncio_extra(self):
        with self.subTest(caso="None"):
            gestor = GestorFalso(transmitiendo=False, perfil="YouTube",
                                 resultado_preparar=None)
            _resultado, _registro, anuncios = self._preparar(gestor, "YouTube")
            self.assertNotIn("Se creó en OBS el perfil YouTube.", anuncios)
        with self.subTest(caso="False"):
            gestor = GestorFalso(transmitiendo=False, perfil="YouTube",
                                 resultado_preparar={"perfil_creado": False})
            _resultado, _registro, anuncios = self._preparar(gestor, "YouTube")
            self.assertNotIn("Se creó en OBS el perfil YouTube.", anuncios)


class DestinosDeMasTest(unittest.TestCase):
    def _preparar(self, opcion, canales=None, conectada=True, fallo=None):
        gestor = GestorFalso(transmitiendo=False, perfil="TikTok")
        with mock.patch(
                "guyrapu.restream.ganchos.cuenta_conectada",
                return_value=conectada) as cuenta, \
                mock.patch(
                    "guyrapu.restream.cuenta.canales",
                    return_value=canales,
                    side_effect=fallo) as leer:
            resultado = preparar(
                gestor, "TikTok", lambda *a, **k: None, lambda frase: None,
                opcion=opcion)
        return resultado, cuenta, leer

    def test_tiktok_con_cuenta_y_youtube_encendido_trae_ese_destino(self):
        canales = [
            SimpleNamespace(plataforma="YouTube", nombre="Canal", activo=True),
            SimpleNamespace(plataforma="TikTok", nombre="Cuenta", activo=True),
        ]
        resultado, cuenta, leer = self._preparar("TikTok", canales=canales)
        self.assertEqual(
            [canal.nombre for canal in resultado.destinos_de_mas], ["Canal"])
        cuenta.assert_called_once_with()
        leer.assert_called_once_with()

    def test_sin_destinos_de_mas_la_revision_trae_vacio(self):
        canales = [
            SimpleNamespace(plataforma="TikTok", nombre="Cuenta", activo=True),
        ]
        resultado, _cuenta, leer = self._preparar("TikTok", canales=canales)
        self.assertEqual(resultado.destinos_de_mas, ())
        leer.assert_called_once_with()

    def test_sin_tiktok_o_sin_cuenta_no_lee_canales(self):
        for opcion, conectada in (("YouTube", True),
                                  ("restream:Uno", True),
                                  ("TikTok", False)):
            with self.subTest(opcion=opcion, conectada=conectada):
                resultado, cuenta, leer = self._preparar(
                    opcion, canales=[], conectada=conectada)
                self.assertEqual(resultado.destinos_de_mas, ())
                leer.assert_not_called()
                if opcion != "TikTok":
                    cuenta.assert_not_called()

    def test_si_la_lectura_falla_no_hay_destinos_y_deja_advertencia(self):
        with self.assertLogs(
                "guyrapu.transmision_directa",
                level="WARNING") as registro:
            resultado, _cuenta, _leer = self._preparar(
                "TikTok", fallo=RuntimeError("sin red"))
        self.assertEqual(resultado.destinos_de_mas, ())
        self.assertTrue(any("destinos" in mensaje.lower()
                            for mensaje in registro.output), registro.output)


class FinalizarTest(unittest.TestCase):
    def test_transmitiendo_detiene_y_cierra(self):
        gestor = GestorFalso(transmitiendo=True)
        finalizar(gestor)
        self.assertEqual(gestor.llamadas, ["conectar", "estado", "detener",
                                           "cerrar"])

    def test_sin_transmision_solo_cierra(self):
        gestor = GestorFalso(transmitiendo=False)
        finalizar(gestor)
        self.assertEqual(gestor.llamadas, ["conectar", "estado", "cerrar"])

    def test_cierra_aunque_detener_levante(self):
        gestor = GestorFalso(transmitiendo=True)

        def _romper(*args, **kwargs):
            raise RuntimeError("boom al detener")
        gestor.detener_transmision = _romper
        with self.assertRaises(RuntimeError):
            finalizar(gestor)
        self.assertEqual(gestor.llamadas[-1], "cerrar")

    def test_con_perfil_youtube_llama_despues_de_detener(self):
        gestor = GestorFalso(transmitiendo=True, perfil="YouTube")
        llamadas = []
        finalizar(gestor,
                  finalizar_youtube=lambda: llamadas.append("youtube"))
        self.assertEqual(llamadas, ["youtube"])
        self.assertLess(gestor.llamadas.index("detener"),
                        len(gestor.llamadas) - 1)
        self.assertEqual(gestor.llamadas[-1], "cerrar")
        self.assertIn("perfil", gestor.llamadas)
        self.assertLess(gestor.llamadas.index("perfil"),
                        gestor.llamadas.index("detener"))

    def test_con_otro_perfil_no_toca_youtube(self):
        gestor = GestorFalso(transmitiendo=True, perfil="TikTok")
        llamadas = []
        finalizar(gestor,
                  finalizar_youtube=lambda: llamadas.append("youtube"))
        self.assertEqual(llamadas, [])
        self.assertIn("detener", gestor.llamadas)

    def test_cierra_youtube_con_el_horizontal_elegido(self):
        gestor = GestorFalso(transmitiendo=True, perfil="Mi horizontal")
        llamadas = []
        with mock.patch("guyrapu.obs.perfil_por_uso.perfil_elegido",
                        return_value="Mi horizontal"):
            finalizar(gestor,
                      finalizar_youtube=lambda: llamadas.append("youtube"))
        self.assertEqual(llamadas, ["youtube"])

    def test_con_otro_perfil_y_horizontal_elegido_no_cierra(self):
        gestor = GestorFalso(transmitiendo=True, perfil="Otro")
        llamadas = []
        with mock.patch("guyrapu.obs.perfil_por_uso.perfil_elegido",
                        return_value="Mi horizontal"):
            finalizar(gestor,
                      finalizar_youtube=lambda: llamadas.append("youtube"))
        self.assertEqual(llamadas, [])

    def test_con_el_horizontal_vacio_cierra_siempre(self):
        gestor = GestorFalso(transmitiendo=True, perfil="Otro")
        llamadas = []
        with mock.patch("guyrapu.obs.perfil_por_uso.perfil_elegido",
                        return_value=""):
            finalizar(gestor,
                      finalizar_youtube=lambda: llamadas.append("youtube"))
        self.assertEqual(llamadas, ["youtube"])

    def test_sin_callable_no_lee_el_perfil(self):
        gestor = GestorFalso(transmitiendo=True, perfil="YouTube")
        finalizar(gestor)
        self.assertNotIn("perfil", gestor.llamadas)

    def test_fallo_en_youtube_sale_como_fallo_de_cierre(self):
        gestor = GestorFalso(transmitiendo=True, perfil="YouTube")

        def _romper():
            raise RuntimeError("cuota agotada")
        with self.assertRaises(FalloCierreYoutube) as contexto:
            finalizar(gestor, finalizar_youtube=_romper)
        self.assertIn("YouTube no confirmó", str(contexto.exception))
        self.assertEqual(gestor.llamadas[-1], "cerrar")


class DecidirTransmisionTest(unittest.TestCase):
    def test_sin_supervisor_alterna_sin_preguntar_nada(self):
        llamadas = []
        decision = decidir_transmision(
            hay_supervisor=False,
            deteniendo=lambda: llamadas.append("deteniendo") or False,
            con_supervisor=lambda: llamadas.append("activa") or False,
            transmitiendo=False, destino="",
            usuario_tiktok=lambda: llamadas.append("usuario") or "")
        self.assertEqual(decision, ALTERNAR)
        self.assertEqual(llamadas, [])

    def test_deteniendo_avisa_que_hay_que_esperar(self):
        llamadas = []
        decision = decidir_transmision(
            hay_supervisor=True, deteniendo=lambda: True,
            con_supervisor=lambda: llamadas.append("activa") or False,
            transmitiendo=False, destino="YouTube",
            usuario_tiktok=lambda: llamadas.append("usuario") or "")
        self.assertEqual(decision, ESPERAR_DETENCION)
        self.assertEqual(llamadas, [])

    def test_con_supervisor_detiene_lo_supervisado(self):
        decision = decidir_transmision(
            hay_supervisor=True, deteniendo=lambda: False,
            con_supervisor=lambda: True,
            transmitiendo=False, destino="YouTube",
            usuario_tiktok=lambda: (_ for _ in ()).throw(
                AssertionError("no se normaliza")))
        self.assertEqual(decision, DETENER_SUPERVISADA)

    def test_boton_que_dice_detener_alterna(self):
        decision = decidir_transmision(
            hay_supervisor=True, deteniendo=lambda: False,
            con_supervisor=lambda: False,
            transmitiendo=True, destino="",
            usuario_tiktok=lambda: (_ for _ in ()).throw(
                AssertionError("no se normaliza")))
        self.assertEqual(decision, ALTERNAR)

    def test_sin_destino_pide_elegir_destino(self):
        decision = decidir_transmision(
            hay_supervisor=True, deteniendo=lambda: False,
            con_supervisor=lambda: False,
            transmitiendo=False, destino="",
            usuario_tiktok=lambda: (_ for _ in ()).throw(
                AssertionError("no se normaliza")))
        self.assertEqual(decision, FALTA_DESTINO)

    def test_tiktok_sin_usuario_pide_el_usuario(self):
        decision = decidir_transmision(
            hay_supervisor=True, deteniendo=lambda: False,
            con_supervisor=lambda: False,
            transmitiendo=False, destino="TikTok",
            usuario_tiktok=lambda: "")
        self.assertEqual(decision, FALTA_USUARIO)

    def test_tiktok_con_usuario_pasa_a_revisar(self):
        decision = decidir_transmision(
            hay_supervisor=True, deteniendo=lambda: False,
            con_supervisor=lambda: False,
            transmitiendo=False, destino="TikTok",
            usuario_tiktok=lambda: "usuario")
        self.assertEqual(decision, REVISAR)

    def test_youtube_pasa_a_revisar_sin_normalizar(self):
        llamadas = []
        decision = decidir_transmision(
            hay_supervisor=True, deteniendo=lambda: False,
            con_supervisor=lambda: False,
            transmitiendo=False, destino="YouTube",
            usuario_tiktok=lambda: llamadas.append("usuario") or "usuario")
        self.assertEqual(decision, REVISAR)
        self.assertEqual(llamadas, [])


class ResolverRevisionTest(unittest.TestCase):
    def _resolver(self, preparacion, opcion="TikTok", destino_obs="TikTok",
                  usuario="usuario", confirmacion=True):
        llamadas = []
        anuncios = []

        def confirmar(revision):
            llamadas.append(("confirmar", revision))
            return confirmacion

        def supervisar(accion, destino, usuario_sup, **kwargs):
            llamadas.append(
                ("supervisar", accion, destino, usuario_sup, kwargs))

        resolver_revision(
            preparacion, opcion, destino_obs, usuario,
            confirmar=confirmar, supervisar=supervisar,
            anunciar=anuncios.append,
            ya_transmitiendo=lambda: llamadas.append("ya"),
            iniciar=lambda: llamadas.append("iniciar"),
            recordar_destino=lambda: llamadas.append("recordar"),
            guardar_usuario=lambda: llamadas.append("guardar"))
        return llamadas, anuncios

    def test_ya_transmitiendo_avisa_y_no_inicia(self):
        preparacion = SimpleNamespace(ya_transmitiendo=True, revision=None)
        llamadas, anuncios = self._resolver(
            preparacion, opcion="YouTube", destino_obs="YouTube")
        self.assertEqual(llamadas, ["ya"])
        self.assertEqual(
            anuncios,
            ["OBS ya está transmitiendo. Con este mismo botón puedes "
             "finalizar el directo."])

    def test_ya_transmitiendo_marca_avisa_y_despues_actualiza(self):
        preparacion = SimpleNamespace(ya_transmitiendo=True, revision=None)
        orden = []
        resolver_revision(
            preparacion, "YouTube", "YouTube", "",
            confirmar=lambda revision: True,
            supervisar=lambda *args, **kwargs: None,
            anunciar=lambda texto: orden.append("anunciar"),
            ya_transmitiendo=lambda: orden.append("ya"),
            iniciar=lambda: orden.append("iniciar"),
            recordar_destino=lambda: None,
            guardar_usuario=lambda: None,
            tras_anunciar=lambda: orden.append("tras_anunciar"))
        self.assertEqual(orden, ["ya", "anunciar", "tras_anunciar"])

    def test_restream_inicia_sin_confirmar_ni_usuario(self):
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        llamadas, anuncios = self._resolver(
            preparacion, opcion="restream:Uno", destino_obs="TikTok",
            usuario="ignorado")
        self.assertEqual(
            llamadas,
            ["recordar",
             ("supervisar", "iniciar", "restream:Uno", "", {}),
             "iniciar"])
        self.assertEqual(anuncios, [])

    def test_youtube_inicia_con_la_revision(self):
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        llamadas, anuncios = self._resolver(
            preparacion, opcion="YouTube", destino_obs="YouTube",
            usuario="")
        self.assertEqual(
            llamadas,
            ["recordar",
             ("supervisar", "iniciar", "YouTube", "",
              {"revision": mock.sentinel.revision}),
             "iniciar"])
        self.assertEqual(anuncios, [])

    def test_tiktok_confirmado_guarda_usuario_y_destino(self):
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        llamadas, anuncios = self._resolver(preparacion)
        self.assertEqual(
            llamadas,
            [("confirmar", mock.sentinel.revision), "guardar", "recordar",
             ("supervisar", "iniciar", "TikTok", "usuario", {}),
             "iniciar"])
        self.assertEqual(anuncios, [])

    def test_tiktok_cancelado_vuelve_al_perfil_y_avisa(self):
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        with mock.patch(
                "guyrapu.obs.perfil_previo.volver_sin_directo") as volver:
            llamadas, anuncios = self._resolver(
                preparacion, confirmacion=False)
        volver.assert_called_once_with()
        self.assertEqual(llamadas, [("confirmar", mock.sentinel.revision)])
        self.assertEqual(anuncios, ["No se transmitió."])

    def test_tiktok_cancelado_no_supervisa_ni_marca(self):
        preparacion = SimpleNamespace(ya_transmitiendo=False,
                                      revision=mock.sentinel.revision)
        with mock.patch("guyrapu.obs.perfil_previo.volver_sin_directo"):
            llamadas, _anuncios = self._resolver(
                preparacion, confirmacion=False)
        self.assertNotIn("iniciar", llamadas)
        self.assertNotIn("recordar", llamadas)
        self.assertNotIn("guardar", llamadas)


class CuentaRestreamConectadaTest(unittest.TestCase):
    def _avisar_en(self, avisos):
        def avisar(texto, sonido=None, *, error=False):
            avisos.append((texto, sonido, error))
        return avisar

    def test_sin_cuenta_avisa_y_con_cuenta_deja_seguir(self):
        avisos = []
        avisar = self._avisar_en(avisos)
        with mock.patch(
                "guyrapu.restream.ganchos.cuenta_conectada",
                return_value=True) as cuenta:
            self.assertTrue(
                cuenta_restream_conectada("restream:Uno", avisar))
        cuenta.assert_called_once_with()
        self.assertEqual(avisos, [])

        with mock.patch(
                "guyrapu.restream.ganchos.cuenta_conectada",
                return_value=False) as cuenta:
            self.assertFalse(
                cuenta_restream_conectada("restream:Uno", avisar))
        cuenta.assert_called_once_with()
        self.assertEqual(
            avisos,
            [("Para transmitir con un perfil de Restream hace falta conectar "
              "la cuenta, en el cuadro Restream, pestaña Cuenta.",
              "transmision_problema", True)])

    def test_sin_restream_no_consulta_la_cuenta(self):
        avisos = []
        with mock.patch(
                "guyrapu.restream.ganchos.cuenta_conectada") as cuenta:
            self.assertTrue(
                cuenta_restream_conectada("YouTube", self._avisar_en(avisos)))
        cuenta.assert_not_called()
        self.assertEqual(avisos, [])


class TestPseudoTransmisionDirecta(unittest.TestCase):
    """Pseudotraducción de las frases de `transmision_directa`.

    Sin ventana ni OBS: recorre la etiqueta, los anuncios de `preparar` y
    el error del cierre en YouTube bajo `con_pseudo()`.
    """

    def test_etiqueta_marca_rotulo_y_nombre_accesible(self):
        with con_pseudo():
            for transmitiendo, deteniendo in ((False, False), (True, False),
                                              (True, True), (False, True)):
                with self.subTest(transmitiendo=transmitiendo,
                                  deteniendo=deteniendo):
                    rotulo, nombre = etiqueta(transmitiendo, deteniendo)
                    self.assertTrue(rotulo.startswith("[¡"), rotulo)
                    self.assertTrue(nombre.startswith("[¡"), nombre)

    def test_anuncios_de_preparar_salen_marcados(self):
        anuncios = []
        gestor = GestorFalso(transmitiendo=False, perfil="Sin Título",
                             resultado_preparar={"perfil_creado": True})
        with con_pseudo():
            preparar(gestor, "YouTube",
                     lambda conectar, al_anunciar=None, parada=None: None,
                     anuncios.append)
        self.assertEqual(len(anuncios), 2)
        for frase in anuncios:
            self.assertTrue(frase.startswith("[¡"), frase)

    def test_fallo_de_cierre_en_youtube_sale_marcado(self):
        gestor = GestorFalso(transmitiendo=True, perfil="YouTube")

        def _romper():
            raise RuntimeError("cuota agotada")

        with con_pseudo():
            with self.assertRaises(FalloCierreYoutube) as contexto:
                finalizar(gestor, finalizar_youtube=_romper)
        self.assertTrue(str(contexto.exception).startswith("[¡"),
                        contexto.exception)


if __name__ == "__main__":
    unittest.main()
