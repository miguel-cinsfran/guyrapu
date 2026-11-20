# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro del disparador: campos, nombres accesibles, validación y datos.

Abre ventanas.
"""

import tempfile
import unittest
from unittest import mock

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import _
from guyrapu.interaction import disparadores, medios_guardados
from guyrapu.obs import estilos_aviso
from guyrapu.ui import disparador_cuadro
from guyrapu.ui.accesibilidad import ContadorAccesible
from tests.letras_acceso import letras_repetidas
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir

NOMBRES_ACCESIBLES = (
    "Nombre", "Cuándo", "Número del atajo, Ctrl+Alt+Mayús",
    "Comandos del chat", "Palabras o emojis del chat", "Evento",
    "Cantidad mínima",
    "Nombre del regalo. Vacío para cualquier regalo. Escribe el nombre "
    "como lo lee Guyrapu",
    "Medio", "Texto de la tarjeta. Puedes usar {usuario}, {cantidad}, "
    "{regalo}, {texto} y {contador}.", "Estilo", "Segundos en pantalla",
    "Permiso", "Nombres permitidos", "Espera general (segundos)",
    "Espera por persona (segundos)", "Aceptar", "Cancelar")

ETIQUETAS = (
    "&Nombre:", "C&uándo:", "Número del ata&jo, Ctrl+Alt+Mayús:",
    "Co&mandos del chat:", "Palabras o emojis del c&hat:", "&Evento:",
    "Cantidad mín&ima:", "Nom&bre del regalo:", "Me&dio:",
    "&Texto de la tarjeta:", "Esti&lo:", "&Segundos en pantalla:",
    "Pe&rmiso:", "Nombres &permitidos:", "Espera &general (segundos):",
    "Espera por pers&ona (segundos):")


class BaseCuadro(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        medios_guardados.guardar(paths.medios(), [{
            "nombre": "aplauso.gif", "tipo": "imagen",
            "archivo": "aplauso.gif"}])

    def _cuadro(self, datos=None, otros=()):
        cuadro = disparador_cuadro.DialogoDisparador(
            None, datos or {}, otros)
        self.addCleanup(destruir, cuadro)
        return cuadro

    def _aceptar_con_error(self, cuadro):
        with mock.patch.object(disparador_cuadro, "anunciar") as decir, \
                mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_not_called()
        return decir


class TestCampos(BaseCuadro):

    def test_los_campos_van_en_el_orden_pedido(self):
        panel = self._cuadro().GetChildren()[0]
        etiquetas = [hijo.GetLabel() for hijo in panel.GetChildren()
                     if isinstance(hijo, wx.StaticText)]
        self.assertEqual(tuple(etiquetas), ETIQUETAS)

    def test_cada_control_tiene_el_nombre_accesible_de_su_rotulo(self):
        cuadro = self._cuadro()
        controles = (
            cuadro.txt_nombre, cuadro.cho_cuando, cuadro.sp_atajo,
            cuadro.txt_comandos, cuadro.txt_palabras, cuadro.cho_evento,
            cuadro.txt_minimo, cuadro.txt_regalo,
            cuadro.cho_medio, cuadro.txt_tarjeta, cuadro.cho_estilo,
            cuadro.sp_segundos, cuadro.cho_permiso, cuadro.txt_nombres,
            cuadro.sp_espera, cuadro.sp_persona, cuadro.btn_aceptar,
            cuadro.btn_cancelar)
        self.assertEqual(
            tuple(control.GetName() for control in controles),
            NOMBRES_ACCESIBLES)

    def test_los_rotulos_se_nombran_igual_que_el_control_siguiente(self):
        cuadro = self._cuadro()
        hijos = list(cuadro.GetChildren()[0].GetChildren())
        pares = 0
        for indice, hijo in enumerate(hijos[:-1]):
            if (isinstance(hijo, wx.StaticText)
                    and not isinstance(hijos[indice + 1], wx.Button)):
                pares += 1
                self.assertEqual(hijo.GetName(), hijos[indice + 1].GetName())
        self.assertGreaterEqual(pares, 12)

    def test_cada_contador_tiene_su_rotulo_inmediatamente_antes(self):
        cuadro = self._cuadro()
        hijos = cuadro.GetChildren()[0].GetChildren()
        contadores = [hijo for hijo in hijos
                      if isinstance(hijo, ContadorAccesible)]
        self.assertEqual(len(contadores), 4)
        for control in contadores:
            with self.subTest(control=control.GetName()):
                anterior = hijos[hijos.index(control) - 1]
                self.assertIsInstance(anterior, wx.StaticText)
                self.assertEqual(
                    anterior.GetLabel().replace("&", "").rstrip(":"),
                    control.GetName())

    def test_p4_el_campo_del_atajo_va_despues_del_cuando_en_el_tab(self):
        cuadro = self._cuadro()
        hijos = cuadro.GetChildren()[0].GetChildren()
        self.assertEqual(hijos.index(cuadro.sp_atajo),
                         hijos.index(cuadro.cho_cuando) + 2)

    def test_p4_el_campo_de_palabras_va_despues_de_los_comandos_en_el_tab(self):
        cuadro = self._cuadro()
        hijos = cuadro.GetChildren()[0].GetChildren()
        self.assertEqual(hijos.index(cuadro.txt_palabras),
                         hijos.index(cuadro.txt_comandos) + 2)

    def test_p4_el_campo_del_atajo_pide_del_uno_al_nueve_y_nunca_se_deshabilita(
            self):
        cuadro = self._cuadro()
        self.assertEqual(
            (cuadro.sp_atajo.GetMin(), cuadro.sp_atajo.GetMax()), (1, 9))
        self.assertEqual(cuadro.sp_atajo.GetName(),
                         "Número del atajo, Ctrl+Alt+Mayús")
        cuadro.cho_cuando.SetSelection(1)
        self.assertTrue(cuadro.sp_atajo.IsEnabled())

    def test_p3_el_regalo_va_despues_del_minimo_en_el_tab(self):
        cuadro = self._cuadro()
        hijos = cuadro.GetChildren()[0].GetChildren()
        self.assertEqual(hijos.index(cuadro.txt_regalo),
                         hijos.index(cuadro.txt_minimo) + 2)

    def test_p3_el_regalo_nunca_se_deshabilita(self):
        cuadro = self._cuadro()
        cuadro.cho_cuando.SetSelection(1)
        cuadro.cho_evento.SetSelection(
            disparadores.EVENTOS_DEL_DIRECTO.index("cofre"))
        self.assertTrue(cuadro.txt_regalo.IsEnabled())

    def test_p3_la_eleccion_empieza_por_el_predeterminado(self):
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_estilo.GetString(0),
                         "Predeterminado (Clásico)")
        self.assertEqual(cuadro.cho_estilo.GetSelection(), 0)
        self.assertEqual(cuadro.datos()["estilo"], "")

    def test_p3_el_predeterminado_lleva_el_nombre_del_estilo_del_tipo(self):
        estilos_aviso.guardar_por_tipo(
            paths.estilos_avisos(), {"disparador": "banda"})
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_estilo.GetString(0),
                         "Predeterminado (Banda)")

    def test_p3_elegir_predeterminado_guarda_el_estilo_vacio(self):
        cuadro = self._cuadro(
            {"nombre": "regalo", "estilo": "banda", "tarjeta": "Gracias"})
        self.assertEqual(cuadro.cho_estilo.GetSelection(), 2)
        cuadro.cho_estilo.SetSelection(0)
        self.assertEqual(cuadro.datos()["estilo"], "")

    def test_las_letras_de_acceso_no_se_repiten_en_el_cuadro(self):
        self.assertEqual(letras_repetidas(self._cuadro()), {})

    def test_el_foco_nace_en_el_nombre(self):
        cuadro = self._cuadro()
        cuadro.Show()
        try:
            self.assertIs(wx.Window.FindFocus(), cuadro.txt_nombre)
        finally:
            cuadro.Hide()

    def test_las_opciones_del_cuando_y_del_evento(self):
        cuadro = self._cuadro()
        self.assertEqual(
            cuadro.cho_cuando.GetStrings(),
            ["Comando del chat", "Evento del directo", "Atajo del teclado",
             "Palabra o emoji en el chat"])
        self.assertEqual(
            cuadro.cho_evento.GetStrings(),
            [_(disparadores.NOMBRES_EVENTOS[clave])
             for clave in disparadores.EVENTOS_DEL_DIRECTO])

    def test_el_medio_trae_la_biblioteca_y_ninguno(self):
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_medio.GetStrings(),
                         ["Ninguno", "aplauso.gif"])

    def test_los_segundos_y_las_esperas_tienen_sus_topes(self):
        cuadro = self._cuadro()
        self.assertEqual(
            (cuadro.sp_segundos.GetMin(), cuadro.sp_segundos.GetMax()),
            (3, 60))
        self.assertEqual(
            (cuadro.sp_espera.GetMin(), cuadro.sp_espera.GetMax()),
            (0, 3600))
        self.assertEqual(
            (cuadro.sp_persona.GetMin(), cuadro.sp_persona.GetMax()),
            (0, 3600))

    def test_p7_el_campo_de_la_tarjeta_dice_las_variables(self):
        nombre = self._cuadro().txt_tarjeta.GetName()
        for variable in ("{usuario}", "{cantidad}", "{regalo}",
                         "{texto}", "{contador}"):
            self.assertIn(variable, nombre)

    def test_escape_cierra_el_cuadro(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        cuadro = self._cuadro()
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)


class TestDatos(BaseCuadro):

    def test_guarda_cada_campo_con_el_minimo_en_numero(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("regalo")
        cuadro.cho_cuando.SetSelection(1)
        cuadro.txt_comandos.SetValue("aplauso, festejar")
        cuadro.cho_evento.SetSelection(
            disparadores.EVENTOS_DEL_DIRECTO.index("superchat"))
        cuadro.txt_minimo.SetValue("5")
        cuadro.cho_medio.SetSelection(1)
        cuadro.txt_tarjeta.SetValue("Gracias")
        cuadro._elegir_estilo("banda")
        cuadro.sp_segundos.SetValue(15)
        cuadro.cho_permiso.SetSelection(2)
        cuadro.txt_nombres.SetValue("Ana, Beto")
        cuadro.sp_espera.SetValue(10)
        cuadro.sp_persona.SetValue(40)
        cuadro.sp_atajo.SetValue(3)
        self.assertEqual(cuadro.datos(), {
            "nombre": "regalo", "cuando": "evento",
            "comandos": [], "palabras": [], "evento": "superchat",
            "minimo": 5.0,
            "regalo": "", "atajo": 3, "medio": "aplauso.gif",
            "tarjeta": "Gracias",
            "estilo": "banda", "segundos": 15, "permiso": "lista",
            "nombres": ["Ana", "Beto"], "espera_general": 10.0,
            "espera_persona": 40.0, "activo": True})

    def test_p4_el_cuadro_carga_y_guarda_el_atajo(self):
        cuadro = self._cuadro({
            "nombre": "botonera", "cuando": "atajo", "atajo": 4,
            "tarjeta": "Gracias"})
        self.assertEqual(cuadro.sp_atajo.GetValue(), 4)
        datos = cuadro.datos()
        self.assertEqual((datos["cuando"], datos["atajo"]), ("atajo", 4))

    def test_p4_el_cuadro_carga_y_guarda_las_palabras(self):
        cuadro = self._cuadro({
            "nombre": "saludo", "cuando": "palabra",
            "palabras": ["hola", "🔥"], "tarjeta": "Gracias"})
        self.assertEqual(cuadro.txt_palabras.GetValue(), "hola, 🔥")
        datos = cuadro.datos()
        self.assertEqual((datos["cuando"], datos["palabras"]),
                         ("palabra", ["hola", "🔥"]))

    def test_p4_un_numero_que_usa_otro_activo_no_guarda(self):
        otro = {"nombre": "otro", "cuando": "atajo", "atajo": 2,
                "tarjeta": "Gracias", "activo": True}
        cuadro = self._cuadro({}, [otro])
        cuadro.txt_nombre.SetValue("botonera")
        cuadro.cho_cuando.SetSelection(
            disparadores.CUANDOS.index("atajo"))
        cuadro.sp_atajo.SetValue(2)
        cuadro.txt_tarjeta.SetValue("Gracias")
        with mock.patch.object(cuadro.sp_atajo, "SetFocus") as foco:
            decir = self._aceptar_con_error(cuadro)
        foco.assert_called_once()
        self.assertEqual(decir.call_args.args[0],
                         "Ese número ya lo usa el disparador otro")

    def test_p4_un_numero_de_otro_pausado_se_puede_usar(self):
        otro = {"nombre": "otro", "cuando": "atajo", "atajo": 2,
                "tarjeta": "Gracias", "activo": False}
        cuadro = self._cuadro({}, [otro])
        cuadro.txt_nombre.SetValue("botonera")
        cuadro.cho_cuando.SetSelection(
            disparadores.CUANDOS.index("atajo"))
        cuadro.sp_atajo.SetValue(2)
        cuadro.txt_tarjeta.SetValue("Gracias")
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_called_once_with(wx.ID_OK)

    def test_p3_el_cuadro_carga_y_guarda_el_regalo(self):
        cuadro = self._cuadro({
            "nombre": "leon", "cuando": "evento", "evento": "superchat",
            "regalo": "Lion", "medio": "aplauso.gif"})
        self.assertEqual(cuadro.txt_regalo.GetValue(), "Lion")
        self.assertEqual(cuadro.datos()["regalo"], "Lion")

    def test_p3_con_otro_evento_guarda_el_regalo_vacio(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("regalo")
        cuadro.cho_cuando.SetSelection(1)
        cuadro.cho_evento.SetSelection(
            disparadores.EVENTOS_DEL_DIRECTO.index("cofre"))
        cuadro.txt_regalo.SetValue("Lion")
        cuadro.txt_tarjeta.SetValue("Gracias")
        self.assertEqual(cuadro.datos()["regalo"], "")

    def test_una_cantidad_vacia_es_sin_minimo(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("regalo")
        cuadro.txt_tarjeta.SetValue("Gracias")
        self.assertIsNone(cuadro.datos()["minimo"])

    def test_un_comando_ignora_el_evento_y_el_minimo(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("aplauso")
        cuadro.txt_comandos.SetValue("aplauso")
        cuadro.cho_evento.SetSelection(
            disparadores.EVENTOS_DEL_DIRECTO.index("superchat"))
        cuadro.txt_minimo.SetValue("5")
        cuadro.txt_tarjeta.SetValue("Gracias")
        datos = cuadro.datos()
        self.assertEqual(datos["evento"], "")
        self.assertIsNone(datos["minimo"])
        self.assertEqual(datos["comandos"], ["aplauso"])

    def test_un_evento_ignora_los_comandos(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("regalo")
        cuadro.cho_cuando.SetSelection(1)
        cuadro.txt_comandos.SetValue("aplauso")
        cuadro.cho_evento.SetSelection(
            disparadores.EVENTOS_DEL_DIRECTO.index("cofre"))
        cuadro.txt_minimo.SetValue("5")
        cuadro.txt_tarjeta.SetValue("Gracias")
        datos = cuadro.datos()
        self.assertEqual(datos["comandos"], [])
        self.assertEqual(datos["evento"], "cofre")
        self.assertEqual(datos["minimo"], 5.0)

    def test_conserva_el_estado_de_pausa_al_editar(self):
        cuadro = self._cuadro({
            "nombre": "regalo", "cuando": "evento", "evento": "cofre",
            "minimo": 5, "medio": "aplauso.gif", "activo": False})
        self.assertFalse(cuadro.datos()["activo"])


class TestValidacion(BaseCuadro):

    def test_un_nombre_vacio_manda_el_foco_al_nombre(self):
        cuadro = self._cuadro()
        cuadro.txt_comandos.SetValue("aplauso")
        cuadro.txt_tarjeta.SetValue("Gracias")
        with mock.patch.object(cuadro.txt_nombre, "SetFocus") as foco:
            decir = self._aceptar_con_error(cuadro)
        foco.assert_called_once()
        self.assertIn("nombre", decir.call_args.args[0])

    def test_un_nombre_repetido_manda_el_foco_al_nombre(self):
        otro = {"nombre": "regalo", "cuando": "evento",
                "evento": "cofre", "medio": "aplauso.gif"}
        cuadro = self._cuadro({}, [otro])
        cuadro.txt_nombre.SetValue("REGALO")
        cuadro.txt_comandos.SetValue("aplauso")
        cuadro.txt_tarjeta.SetValue("Gracias")
        with mock.patch.object(cuadro.txt_nombre, "SetFocus") as foco:
            self._aceptar_con_error(cuadro)
        foco.assert_called_once()

    def test_un_comando_sin_nombres_manda_el_foco_a_los_comandos(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("aplauso")
        cuadro.txt_tarjeta.SetValue("Gracias")
        with mock.patch.object(cuadro.txt_comandos, "SetFocus") as foco:
            self._aceptar_con_error(cuadro)
        foco.assert_called_once()

    def test_un_comando_repetido_manda_el_foco_a_los_comandos(self):
        otro = {"nombre": "otro", "cuando": "comando",
                "comandos": ("APLAUSO",), "medio": "aplauso.gif"}
        cuadro = self._cuadro({}, [otro])
        cuadro.txt_nombre.SetValue("aplauso")
        cuadro.txt_comandos.SetValue("aplauso")
        cuadro.txt_tarjeta.SetValue("Gracias")
        with mock.patch.object(cuadro.txt_comandos, "SetFocus") as foco:
            self._aceptar_con_error(cuadro)
        foco.assert_called_once()

    def test_p4_una_lista_de_palabras_vacia_manda_el_foco_a_las_palabras(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("saludo")
        cuadro.cho_cuando.SetSelection(
            disparadores.CUANDOS.index("palabra"))
        cuadro.txt_tarjeta.SetValue("Gracias")
        with mock.patch.object(cuadro.txt_palabras, "SetFocus") as foco:
            decir = self._aceptar_con_error(cuadro)
        foco.assert_called_once()
        self.assertIn("palabra", decir.call_args.args[0])

    def test_un_minimo_negativo_manda_el_foco_al_minimo(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("regalo")
        cuadro.cho_cuando.SetSelection(1)
        cuadro.cho_evento.SetSelection(
            disparadores.EVENTOS_DEL_DIRECTO.index("superchat"))
        cuadro.txt_minimo.SetValue("-1")
        cuadro.txt_tarjeta.SetValue("Gracias")
        with mock.patch.object(cuadro.txt_minimo, "SetFocus") as foco:
            self._aceptar_con_error(cuadro)
        foco.assert_called_once()

    def test_sin_medio_ni_tarjeta_manda_el_foco_a_la_tarjeta(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("aplauso")
        cuadro.txt_comandos.SetValue("aplauso")
        with mock.patch.object(cuadro.txt_tarjeta, "SetFocus") as foco:
            self._aceptar_con_error(cuadro)
        foco.assert_called_once()

    def test_p6_una_variable_que_no_existe_muestra_su_error(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("aplauso")
        cuadro.txt_comandos.SetValue("aplauso")
        cuadro.txt_tarjeta.SetValue("Hola {nada}")
        decir = self._aceptar_con_error(cuadro)
        self.assertEqual(
            decir.call_args.args[0],
            "La variable {nada} no existe. Puedes usar {usuario}, "
            "{cantidad}, {regalo}, {texto} y {contador}.")

    def test_p6_una_variable_que_no_existe_deja_el_foco_en_la_tarjeta(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("aplauso")
        cuadro.txt_comandos.SetValue("aplauso")
        cuadro.txt_tarjeta.SetValue("Hola {nada}")
        with mock.patch.object(cuadro.txt_tarjeta, "SetFocus") as foco:
            self._aceptar_con_error(cuadro)
        foco.assert_called_once()

    def test_un_error_de_validacion_no_cierra_el_cuadro(self):
        cuadro = self._cuadro()
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            self._aceptar_con_error(cuadro)
        cerrar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
