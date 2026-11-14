# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana Administrar voces: controles, filtros, acciones y vista previa."""

import json
import unittest
from unittest import mock

import wx

from guyrapu.core import idioma, paquetes_instalacion
from guyrapu.ui import preferencias_voz, voces_ventana
from tests.letras_acceso import ingles, letras_repetidas
from tests.ventanas_prueba import app_de_prueba, destruir

MEGA = 1024 * 1024
SHA = "a" * 64


def _voz(nombre, idioma, genero=None, muestra=None):
    return {"nombre": nombre, "idioma": idioma, "genero": genero,
            "muestra": muestra}


def _paquete(identificador, proveedor, nombre, idioma, voces, version=1):
    return {
        "id": identificador, "tipo": "voz", "proveedor": proveedor,
        "nombre": nombre, "idioma": idioma, "version": version,
        "guyrapu_minima": "0.0.1", "licencia": "CC BY 4.0",
        "licencia_url": "https://ejemplo.test/licencia",
        "origen": "prueba", "voces": voces,
        "archivos": [{"url": "https://ejemplo.test/voz.bin", "bytes": 10 * MEGA,
                      "sha256": SHA, "ruta": "voz.bin"}],
    }


def _catalogo(*paquetes):
    return json.dumps({"formato": 1, "paquetes": list(paquetes)})


class _Instalados:
    def __init__(self, fichas=()):
        self.fichas = list(fichas)

    def __call__(self, _tipo):
        return list(self.fichas)


class HiloInmediato:
    def __init__(self, target, nombre, **kwargs):
        self._target = target

    def start(self):
        self._target()


class HiloQuieto:
    def __init__(self, target, nombre, **kwargs):
        pass

    def start(self):
        pass


class EsperaFalsa:
    instancias = []

    def __init__(self, padre, titulo, texto, parada=None):
        self.titulo = titulo
        self.texto = texto
        self.parada = parada
        self.estados = []
        self.final = None
        self.error = None
        self.destruida = False
        EsperaFalsa.instancias.append(self)

    def ShowModal(self):
        return wx.ID_CANCEL

    def Destroy(self):
        self.destruida = True

    def estado(self, texto):
        self.estados.append(texto)

    def terminar(self, texto, error=False):
        self.final = texto
        self.error = error


class BaseVentana(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        idioma.instalar("es")
        self.addCleanup(idioma._reiniciar)
        EsperaFalsa.instancias = []

    def _parchear(self, objeto, atributo, valor):
        parche = mock.patch.object(objeto, atributo, valor)
        parche.start()
        self.addCleanup(parche.stop)
        return valor

    def _dialogo(self, paquetes=(), instalados=(), fallo=None, hilo=HiloInmediato,
                 idioma="es"):
        self.instalados = _Instalados(instalados)
        self._parchear(voces_ventana.paquetes_instalacion, "instalados",
                       self.instalados)
        if fallo is None:
            pedir = mock.Mock(return_value=_catalogo(*paquetes))
        else:
            pedir = mock.Mock(side_effect=fallo)
        self._parchear(voces_ventana.red, "pedir_texto", pedir)
        self._parchear(voces_ventana.diagnostico, "crear_hilo", hilo)
        self._parchear(voces_ventana.wx, "CallAfter",
                       lambda funcion, *args: funcion(*args))
        self._parchear(voces_ventana.voces_disponibles, "idioma_actual",
                       lambda: idioma)
        self.avisar = self._parchear(voces_ventana.confirmar, "avisar",
                                     mock.Mock())
        self.sonido = self._parchear(voces_ventana._snd, "reproducir",
                                     mock.Mock())
        self.anuncios = self._parchear(voces_ventana, "anunciar", mock.Mock())
        dialogo = voces_ventana.VentanaVoces(None)
        self.addCleanup(destruir, dialogo)
        return dialogo


class TestControles(BaseVentana):

    def test_nombres_accesibles_y_orden_de_tab(self):
        paquete = _paquete("piper-davefx", "piper", "Piper Davefx", "es-ES",
                           [_voz("Davefx", "es-ES")])
        dialogo = self._dialogo(paquetes=(paquete,))
        for nombre, control in (
                ("Idioma", dialogo.cho_idioma),
                ("Motor de voz", dialogo.cho_motor),
                ("Paquetes de voces", dialogo.lista_paquetes),
                ("Detalles", dialogo.txt_detalles),
                ("Instalar", dialogo.btn_instalar),
                ("Actualizar", dialogo.btn_actualizar),
                ("Eliminar", dialogo.btn_eliminar),
                ("Voces del paquete", dialogo.lista_voces),
                ("Vista previa de voz", dialogo.btn_previa),
                ("Cerrar", dialogo.btn_cerrar)):
            self.assertEqual(control.GetName(), nombre)
        self.assertEqual(
            [control for control in dialogo.GetChildren()
             if isinstance(control, (wx.Choice, wx.ListBox, wx.TextCtrl,
                                     wx.Button))],
            [dialogo.cho_idioma, dialogo.cho_motor, dialogo.lista_paquetes,
             dialogo.txt_detalles, dialogo.btn_instalar,
             dialogo.btn_actualizar, dialogo.btn_eliminar,
             dialogo.lista_voces, dialogo.btn_previa, dialogo.btn_cerrar])
        dialogo.Show()
        try:
            self.assertIs(wx.Window.FindFocus(), dialogo.lista_paquetes)
        finally:
            dialogo.Hide()

    def test_letras_de_acceso_sin_repetir(self):
        paquete = _paquete("piper-davefx", "piper", "Piper Davefx", "es-ES",
                           [_voz("Davefx", "es-ES")])
        self.assertEqual(letras_repetidas(self._dialogo(paquetes=(paquete,))), {})

    def test_cargando_mientras_no_hay_instalado(self):
        dialogo = self._dialogo(hilo=HiloQuieto)
        self.assertEqual(dialogo.lista_paquetes.GetCount(), 1)
        self.assertEqual(dialogo.lista_paquetes.GetString(0),
                         "Cargando paquetes de voces…")


class TestListasYFiltros(BaseVentana):

    def _dos(self):
        piper = _paquete("piper-davefx", "piper", "Piper Davefx", "es-ES",
                         [_voz("Davefx", "es-ES")])
        phonon = _paquete("phonon-en", "phonon", "Phonon inglés", "en",
                          [_voz("Ana", "en-US")])
        return piper, phonon

    def test_la_fila_se_lee_entera(self):
        piper, _phonon = self._dos()
        instalado = dict(piper, instalado="2026-11-14T12:00:00-03:00")
        dialogo = self._dialogo(paquetes=(piper,), instalados=(instalado,))
        self.assertEqual(dialogo.lista_paquetes.GetString(0),
                         "Davefx, Piper, español (España), 10 MB, instalado")

    def test_elegir_un_paquete_llena_detalles_y_voces(self):
        paquete = _paquete(
            "phonon-es", "phonon", "Phonon español", "es",
            [_voz("Noa", "es-ES", "female"), _voz("Marc", "es-MX", "male")])
        dialogo = self._dialogo(paquetes=(paquete,))
        dialogo.lista_paquetes.SetSelection(0)
        dialogo._al_elegir_paquete(mock.Mock())
        detalles = dialogo.txt_detalles.GetValue()
        self.assertIn("Nombre: Phonon español", detalles)
        self.assertIn("Licencia: CC BY 4.0", detalles)
        self.assertEqual(
            [dialogo.lista_voces.GetString(i)
             for i in range(dialogo.lista_voces.GetCount())],
            ["Noa, femenina, español (España)",
             "Marc, masculina, español (México)"])

    def test_cambiar_un_filtro_rehace_la_lista(self):
        piper, phonon = self._dos()
        dialogo = self._dialogo(paquetes=(piper, phonon))
        self.assertEqual(dialogo.lista_paquetes.GetCount(), 1)
        self.assertIn("Davefx", dialogo.lista_paquetes.GetString(0))
        dialogo.cho_idioma.SetSelection(
            dialogo._valores_idioma.index("en"))
        dialogo._al_cambiar_filtro(True)
        self.assertEqual(dialogo.lista_paquetes.GetCount(), 1)
        self.assertIn("Phonon", dialogo.lista_paquetes.GetString(0))
        dialogo.cho_motor.SetSelection(
            dialogo._valores_motor.index("piper"))
        dialogo._al_cambiar_filtro(False)
        self.assertEqual(dialogo.lista_paquetes.GetString(0),
                         "No hay paquetes de voces con este filtro.")


class TestInstalarYActualizar(BaseVentana):

    def _paquete_base(self, version=1):
        return _paquete("piper-davefx", "piper", "Piper Davefx", "es-ES",
                        [_voz("Davefx", "es-ES")], version=version)

    def _preparar_instalacion(self, dialogo, resultado, actualizar=True):
        def instalar(paquete, aviso=None, cancelar=None):
            self.instalados.fichas = [dict(paquete, instalado=(
                "2026-11-14T12:00:00-03:00"))]
            if aviso is not None:
                aviso(10)
            return resultado
        self.instalar = self._parchear(
            voces_ventana.paquetes_instalacion, "instalar",
            mock.Mock(side_effect=instalar))
        self._parchear(voces_ventana, "VentanaEspera", EsperaFalsa)
        return dialogo

    def test_instalar_llama_y_al_terminar_la_fila_queda_instalada(self):
        paquete = self._paquete_base()
        dialogo = self._dialogo(paquetes=(paquete,))
        self._preparar_instalacion(
            dialogo, paquetes_instalacion.ResultadoInstalacion(
                True, "paquete instalado"))
        dialogo._paquetes.ejecutar("instalar")
        self.instalar.assert_called_once()
        self.assertEqual(self.instalar.call_args.args[0], paquete)
        self.assertIn("instalado", dialogo.lista_paquetes.GetString(0))
        self.assertEqual(EsperaFalsa.instancias[-1].final,
                         "Instalación completada: Piper Davefx.")
        self.assertEqual(self.sonido.call_args_list, [mock.call("listo")])

    def test_instalar_con_ya_instalado_no_llama(self):
        paquete = self._paquete_base()
        instalado = dict(paquete, instalado="2026-11-14T12:00:00-03:00")
        dialogo = self._dialogo(paquetes=(paquete,), instalados=(instalado,))
        self.instalar = self._parchear(
            voces_ventana.paquetes_instalacion, "instalar", mock.Mock())
        dialogo._paquetes.ejecutar("instalar")
        self.instalar.assert_not_called()
        self.anuncios.assert_called_with("Piper Davefx ya está instalado.")

    def test_actualizar_sin_actualizacion_no_llama(self):
        paquete = self._paquete_base()
        instalado = dict(paquete, instalado="2026-11-14T12:00:00-03:00")
        dialogo = self._dialogo(paquetes=(paquete,), instalados=(instalado,))
        self.instalar = self._parchear(
            voces_ventana.paquetes_instalacion, "instalar", mock.Mock())
        dialogo._paquetes.ejecutar("actualizar")
        self.instalar.assert_not_called()
        self.anuncios.assert_called_with(
            "No hay actualización disponible para Piper Davefx.")

    def test_actualizar_con_version_nueva_llama(self):
        instalado = self._paquete_base()
        nuevo = self._paquete_base(version=2)
        ficha = dict(instalado, instalado="2026-11-14T12:00:00-03:00")
        dialogo = self._dialogo(paquetes=(nuevo,), instalados=(ficha,))
        self._preparar_instalacion(
            dialogo, paquetes_instalacion.ResultadoInstalacion(
                True, "paquete instalado"))
        dialogo._paquetes.ejecutar("actualizar")
        self.instalar.assert_called_once()
        self.assertEqual(EsperaFalsa.instancias[-1].final,
                         "Actualización completada: Piper Davefx.")

    def test_cancelado_lo_dice_sin_error(self):
        paquete = self._paquete_base()
        dialogo = self._dialogo(paquetes=(paquete,))
        self._preparar_instalacion(
            dialogo, paquetes_instalacion.ResultadoInstalacion(
                False, "instalación cancelada", cancelada=True))
        dialogo._paquetes.ejecutar("instalar")
        self.assertEqual(EsperaFalsa.instancias[-1].final,
                         "Instalación cancelada.")
        self.assertFalse(EsperaFalsa.instancias[-1].error)

    def test_el_aviso_de_porcentaje_pasa_por_callafter(self):
        paquete = self._paquete_base()
        dialogo = self._dialogo(paquetes=(paquete,))

        def instalar(_paquete, aviso=None, cancelar=None):
            aviso(10)
            return paquetes_instalacion.ResultadoInstalacion(
                True, "paquete instalado")
        self._parchear(voces_ventana.paquetes_instalacion, "instalar",
                       mock.Mock(side_effect=instalar))
        self._parchear(voces_ventana, "VentanaEspera", EsperaFalsa)
        with mock.patch.object(voces_ventana.wx, "CallAfter") as diferido:
            dialogo._paquetes.ejecutar("instalar")
        self.assertTrue(diferido.called)
        self.assertTrue(any(
            llamada.args and llamada.args[0] == dialogo._aviso_porcentaje
            for llamada in diferido.call_args_list))
        self.assertEqual(EsperaFalsa.instancias[-1].estados, [])

    def test_el_texto_cambia_al_cruzar_una_decena(self):
        dialogo = self._dialogo()
        espera = EsperaFalsa(None, "t", "t")
        dialogo._espera = espera
        dialogo._ultimo_porcentaje = None
        dialogo._aviso_porcentaje(0, "Piper Davefx")
        espera.estados.clear()
        dialogo._aviso_porcentaje(9, "Piper Davefx")
        self.assertEqual(espera.estados, [])
        dialogo._aviso_porcentaje(10, "Piper Davefx")
        dialogo._aviso_porcentaje(15, "Piper Davefx")
        dialogo._aviso_porcentaje(20, "Piper Davefx")
        self.assertEqual(
            espera.estados,
            ["Descargando Piper Davefx: 10 por ciento",
             "Descargando Piper Davefx: 20 por ciento"])


class TestEliminar(BaseVentana):

    def _con_instalado(self, en_catalogo=True):
        paquete = _paquete("piper-davefx", "piper", "Piper Davefx", "es-ES",
                           [_voz("Davefx", "es-ES")])
        ficha = dict(paquete, instalado="2026-11-14T12:00:00-03:00")
        paquetes = (paquete,) if en_catalogo else ()
        return self._dialogo(paquetes=paquetes, instalados=(ficha,))

    def test_cancelar_no_llama_a_borrar(self):
        dialogo = self._con_instalado()
        preguntar = self._parchear(
            voces_ventana.confirmar, "preguntar", mock.Mock(return_value=False))
        borrar = self._parchear(
            voces_ventana.paquetes_instalacion, "borrar", mock.Mock())
        dialogo._eliminar()
        self.assertFalse(borrar.called)
        self.assertEqual(preguntar.call_args.kwargs["predeterminado_si"], False)

    def test_eliminar_llama_a_borrar_y_anuncia(self):
        dialogo = self._con_instalado(en_catalogo=False)
        self._parchear(voces_ventana.confirmar, "preguntar",
                       mock.Mock(return_value=True))

        def borrar(identificador, tipo):
            self.instalados.fichas = [
                ficha for ficha in self.instalados.fichas
                if ficha["id"] != identificador]
            return paquetes_instalacion.ResultadoInstalacion(
                True, "paquete borrado")
        self.borrar = self._parchear(
            voces_ventana.paquetes_instalacion, "borrar",
            mock.Mock(side_effect=borrar))
        dialogo._eliminar()
        self.borrar.assert_called_once_with("piper-davefx", "voz")
        self.anuncios.assert_called_with("Paquete eliminado: Piper Davefx.")
        self.assertEqual(dialogo.lista_paquetes.GetString(0),
                         "No hay paquetes de voces.")

    def test_si_sigue_en_el_catalogo_la_fila_queda_disponible(self):
        dialogo = self._con_instalado(en_catalogo=True)
        self._parchear(voces_ventana.confirmar, "preguntar",
                       mock.Mock(return_value=True))

        def borrar(_identificador, _tipo):
            self.instalados.fichas = []
            return paquetes_instalacion.ResultadoInstalacion(
                True, "paquete borrado")
        self._parchear(voces_ventana.paquetes_instalacion, "borrar",
                       mock.Mock(side_effect=borrar))
        dialogo._eliminar()
        self.assertIn("disponible", dialogo.lista_paquetes.GetString(0))


class TestFalloYVistaPrevia(BaseVentana):

    def test_catalogo_que_falla_muestra_lo_instalado(self):
        paquete = _paquete("piper-davefx", "piper", "Piper Davefx", "es-ES",
                           [_voz("Davefx", "es-ES")])
        ficha = dict(paquete, instalado="2026-11-14T12:00:00-03:00")
        dialogo = self._dialogo(instalados=(ficha,),
                                fallo=OSError("sin conexión"))
        self.assertEqual(dialogo.lista_paquetes.GetCount(), 1)
        self.assertIn("instalado", dialogo.lista_paquetes.GetString(0))
        self.avisar.assert_called_once()
        self.assertIn("sin conexión", self.avisar.call_args.args[1])
        self.sonido.assert_called_with("error")

    def test_vista_previa_reproduce_la_muestra(self):
        paquete = _paquete(
            "piper-davefx", "piper", "Piper Davefx", "es-ES",
            [_voz("Davefx", "es-ES", muestra="https://ejemplo.test/davefx.mp3")])
        dialogo = self._dialogo(paquetes=(paquete,))
        reproducir = self._parchear(
            voces_ventana.muestra_voz, "reproducir", mock.Mock())
        dialogo._vista_previa()
        reproducir.assert_called_once_with("https://ejemplo.test/davefx.mp3")

    def test_sin_muestra_lo_anuncia(self):
        paquete = _paquete("piper-davefx", "piper", "Piper Davefx", "es-ES",
                           [_voz("Davefx", "es-ES")])
        dialogo = self._dialogo(paquetes=(paquete,))
        dialogo._vista_previa()
        self.anuncios.assert_called_with("Esta voz no tiene vista previa.")

    def test_si_libvlc_falla_muestra_el_motivo(self):
        paquete = _paquete(
            "piper-davefx", "piper", "Piper Davefx", "es-ES",
            [_voz("Davefx", "es-ES", muestra="https://ejemplo.test/davefx.mp3")])
        dialogo = self._dialogo(paquetes=(paquete,))
        self._parchear(voces_ventana.muestra_voz, "reproducir",
                       mock.Mock(side_effect=RuntimeError("sin libVLC")))
        dialogo._vista_previa()
        self.avisar.assert_called_once()
        self.assertIn("sin libVLC", self.avisar.call_args.args[1])


class TestLetrasEnIngles(BaseVentana):

    def test_la_ventana_no_repite_letras_en_ingles(self):
        with ingles():
            paquete = _paquete("piper-davefx", "piper", "Piper Davefx",
                               "es-ES", [_voz("Davefx", "es-ES")])
            dialogo = self._dialogo(paquetes=(paquete,), idioma="en")
            self.assertEqual(letras_repetidas(dialogo), {})


class TestAbrirReal(BaseVentana):

    def test_abrir_llama_a_al_cerrar_despues_de_cerrar(self):
        self._parchear(voces_ventana.paquetes_instalacion, "instalados",
                       _Instalados())
        self._parchear(voces_ventana.red, "pedir_texto",
                       mock.Mock(return_value=_catalogo()))
        self._parchear(voces_ventana.diagnostico, "crear_hilo", HiloInmediato)
        self._parchear(voces_ventana.wx, "CallAfter",
                       lambda funcion, *args: funcion(*args))
        self._parchear(voces_ventana.voces_disponibles, "idioma_actual",
                       lambda: "es")
        self._parchear(voces_ventana.confirmar, "avisar", mock.Mock())
        self._parchear(voces_ventana._snd, "reproducir", mock.Mock())
        self._parchear(voces_ventana, "anunciar", mock.Mock())
        al_cerrar = mock.Mock()
        with mock.patch.object(voces_ventana.VentanaVoces, "ShowModal",
                               return_value=wx.ID_CANCEL):
            voces_ventana.abrir(None, al_cerrar=al_cerrar)
        al_cerrar.assert_called_once_with()


class TestDesdePreferencias(BaseVentana):

    def test_abrir_y_cerrar_recarga_las_voces_de_la_pagina(self):
        frame = wx.Frame(None)
        self.addCleanup(destruir, frame)
        self._parchear(preferencias_voz.credenciales, "cargar",
                       mock.Mock(return_value={}))
        with mock.patch("guyrapu.voice.motores.listar_voces",
                        return_value=[]):
            pagina = preferencias_voz.PaginaVoz(None, {})
            pagina.construir(frame)
        pagina._on_motor_cambiado = mock.Mock()
        with mock.patch.object(voces_ventana, "abrir") as abrir:
            evento = wx.CommandEvent(
                wx.EVT_BUTTON.typeId, pagina.btn_voces.GetId())
            pagina.btn_voces.GetEventHandler().ProcessEvent(evento)
        abrir.assert_called_once()
        abrir.call_args.kwargs["al_cerrar"]()
        pagina._on_motor_cambiado.assert_called_once_with(None)


if __name__ == "__main__":
    unittest.main()
