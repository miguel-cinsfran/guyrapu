# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las ventanas de prueba del carril, construidas sin mostrar.

Abren wx, así que se corren en la PC que no usa nadie. No abren ninguna
ventana visible: solo se construyen los controles y se inspeccionan.
"""

import unittest
from unittest import mock

import wx

from qa.nvda import reglas, trampas

TRAMPAS = [nombre for nombre, datos in trampas.VENTANAS.items()
           if datos["regla"]]


def setUpModule():
    global _APP
    _APP = wx.App(False)


def tearDownModule():
    global _APP
    _APP = None


def _controles(marco):
    salida = []
    pendientes = list(marco.GetChildren())
    while pendientes:
        actual = pendientes.pop()
        salida.append(actual)
        pendientes.extend(actual.GetChildren())
    return salida


def _con_nombre(marco, nombre):
    return [control for control in _controles(marco)
            if control.GetName() == nombre]


def _etiquetas(marco):
    salida = []
    for control in _controles(marco):
        if hasattr(control, "GetLabel"):
            etiqueta = control.GetLabel()
            if etiqueta:
                salida.append(etiqueta)
    return salida


def _letras_de_acceso(marco):
    letras = []
    for etiqueta in _etiquetas(marco):
        if "&" in etiqueta:
            posicion = etiqueta.index("&")
            if posicion + 1 < len(etiqueta):
                letras.append(etiqueta[posicion + 1].casefold())
    return letras


class Base(unittest.TestCase):

    def construir(self, nombre):
        marco = trampas.construir(nombre)
        self.addCleanup(marco.Destroy)
        return marco


class TestTabla(Base):

    def test_cada_ventana_declara_su_comando_y_su_primer_control(self):
        for nombre, datos in trampas.VENTANAS.items():
            with self.subTest(ventana=nombre):
                self.assertEqual(datos["nombre"], nombre)
                self.assertIn("--ventana", datos["comando"])
                self.assertIn(nombre, datos["comando"])
                self.assertTrue(datos["primero"])

    def test_cada_trampa_declara_su_regla_y_la_limpia_ninguna(self):
        self.assertEqual(sorted(TRAMPAS), sorted([
            "sin_nombre", "rol_contenedor", "nombre_repetido", "ingles",
            "atajo_repetido", "paso_mudo", "foco_perdido", "recorrido"]))
        self.assertIsNone(trampas.VENTANAS["limpia"]["regla"])

    def test_todas_se_construyen_sin_mostrarse(self):
        for nombre in trampas.VENTANAS:
            with self.subTest(ventana=nombre):
                marco = self.construir(nombre)
                self.assertFalse(marco.IsShown())
                self.assertTrue(
                    _con_nombre(marco, trampas.VENTANAS[nombre]["primero"]))


class TestNombreAccesible(Base):

    ESPERADOS = {
        "limpia": ["Nombre completo", "Imagen", "Audio", "Nivel",
                   "Activar", "Mostrar", "Anunciar", "Mover foco",
                   "Destino", "Campo libre"],
        "sin_nombre": ["Antes"],
        "rol_contenedor": ["Zona de prueba", "Siguiente"],
        "nombre_repetido": ["Volumen", "Volumen"],
        "ingles": ["Cancel"],
        "atajo_repetido": ["Activar", "Aplicar"],
        "paso_mudo": ["Mudo"],
        "foco_perdido": ["Deshabilitar"],
        "recorrido": ["Entrada", "Campo con Tab"],
    }

    def test_cada_control_nombrado_pasa_por_nombre_accesible(self):
        for nombre, esperados in self.ESPERADOS.items():
            with self.subTest(ventana=nombre):
                with mock.patch.object(
                        trampas, "nombre_accesible") as nombrar:
                    self.construir(nombre)
                    llamados = [llamada.args[1]
                                for llamada in nombrar.call_args_list]
                self.assertEqual(llamados, esperados)

    def test_el_boton_sin_nombre_no_se_nombra(self):
        with mock.patch.object(trampas, "nombre_accesible") as nombrar:
            marco = self.construir("sin_nombre")
            botones = [control for control in _controles(marco)
                       if isinstance(control, wx.BitmapButton)]
            llamados = [llamada.args[0]
                        for llamada in nombrar.call_args_list]
        self.assertTrue(botones)
        self.assertFalse(any(boton in llamados for boton in botones))


class TestSinNombre(Base):

    def test_la_trampa_tiene_un_boton_con_imagen_y_sin_nombre(self):
        marco = self.construir("sin_nombre")
        botones = [control for control in _controles(marco)
                   if isinstance(control, wx.BitmapButton)]
        self.assertTrue(any(not boton.GetName() for boton in botones))

    def test_la_limpia_tiene_el_boton_con_imagen_y_nombre(self):
        marco = self.construir("limpia")
        botones = _con_nombre(marco, "Imagen")
        self.assertTrue(botones)
        self.assertTrue(all(isinstance(boton, wx.BitmapButton)
                            for boton in botones))


class TestRolContenedor(Base):

    def _focos_propios(self, marco):
        return [control for control in _con_nombre(marco, "Zona de prueba")
                if not isinstance(control, wx.Control)
                and control.AcceptsFocusFromKeyboard()]

    def test_la_trampa_tiene_una_ventana_propia_que_toma_el_foco(self):
        self.assertTrue(self._focos_propios(
            self.construir("rol_contenedor")))

    def test_la_limpia_no_tiene_ninguna(self):
        self.assertEqual(self._focos_propios(self.construir("limpia")), [])


class TestNombreRepetido(Base):

    def _grupo_y_deslizador(self, marco):
        grupo = [control for control in _controles(marco)
                 if isinstance(control, wx.StaticBox)
                 and control.GetLabel()]
        deslizador = [control for control in _controles(marco)
                      if isinstance(control, wx.Slider)]
        return grupo, deslizador

    def test_la_trampa_repite_el_nombre_del_grupo_y_del_deslizador(self):
        grupo, deslizador = self._grupo_y_deslizador(
            self.construir("nombre_repetido"))
        self.assertEqual([c.GetLabel() for c in grupo], ["Volumen"])
        self.assertEqual([c.GetName() for c in deslizador], ["Volumen"])

    def test_la_limpia_usa_nombres_distintos(self):
        grupo, deslizador = self._grupo_y_deslizador(
            self.construir("limpia"))
        self.assertEqual([c.GetLabel() for c in grupo], ["Audio"])
        self.assertEqual([c.GetName() for c in deslizador], ["Nivel"])


class TestIngles(Base):

    def test_la_trampa_usa_un_texto_del_catalogo_ingles(self):
        catalogo = reglas.leer_catalogo_ingles()
        textos = _etiquetas(self.construir("ingles"))
        self.assertTrue(any(reglas.normalizar(texto) in catalogo
                            for texto in textos))

    def test_la_limpia_no_usa_ninguno(self):
        catalogo = reglas.leer_catalogo_ingles()
        textos = _etiquetas(self.construir("limpia"))
        usados = [texto for texto in textos
                  if reglas.normalizar(texto) in catalogo]
        self.assertEqual(usados, [])


class TestAtajoRepetido(Base):

    def test_la_trampa_repite_la_letra_de_acceso(self):
        letras = _letras_de_acceso(self.construir("atajo_repetido"))
        self.assertEqual(len(letras), 2)
        self.assertEqual(len(set(letras)), 1)

    def test_la_limpia_usa_letras_distintas(self):
        letras = _letras_de_acceso(self.construir("limpia"))
        self.assertEqual(len(letras), 2)
        self.assertEqual(len(set(letras)), 2)


class TestPasoMudo(Base):

    def test_la_trampa_declara_la_accion_que_no_hace_nada(self):
        datos = trampas.VENTANAS["paso_mudo"]
        self.assertEqual(datos["acciones"],
                         [{"control": "Mudo", "gesto": "space"}])
        self.assertTrue(_con_nombre(self.construir("paso_mudo"), "Mudo"))

    def test_la_limpia_declara_acciones_que_hablan(self):
        datos = trampas.VENTANAS["limpia"]
        controles = [accion["control"] for accion in datos["acciones"]]
        self.assertEqual(controles, ["Anunciar", "Mover foco"])
        marco = self.construir("limpia")
        for control in controles:
            self.assertTrue(_con_nombre(marco, control))


class TestFocoPerdido(Base):

    def test_la_trampa_deshabilita_el_boton_al_pulsarlo(self):
        marco = self.construir("foco_perdido")
        boton = _con_nombre(marco, "Deshabilitar")[0]
        evento = wx.CommandEvent(wx.EVT_BUTTON.typeId, boton.GetId())
        boton.GetEventHandler().ProcessEvent(evento)
        self.assertFalse(boton.IsEnabled())

    def test_la_limpia_lleva_el_foco_a_otro_control_antes(self):
        marco = self.construir("limpia")
        self.assertTrue(_con_nombre(marco, "Mover foco"))
        self.assertTrue(_con_nombre(marco, "Destino"))
        self.assertTrue(_con_nombre(marco, "Destino")[0].IsEnabled())


class TestRecorrido(Base):

    def _campos(self, marco):
        return [control for control in _controles(marco)
                if isinstance(control, wx.TextCtrl)]

    def test_la_trampa_tiene_un_campo_que_se_queda_con_el_tab(self):
        campos = self._campos(self.construir("recorrido"))
        self.assertTrue(any(
            campo.GetWindowStyle() & wx.TE_MULTILINE
            and campo.GetWindowStyle() & wx.TE_PROCESS_TAB
            for campo in campos))

    def test_la_limpia_tiene_un_campo_multilinea_sin_quedarse_el_tab(self):
        campos = self._campos(self.construir("limpia"))
        libres = [campo for campo in campos
                  if campo.GetWindowStyle() & wx.TE_MULTILINE
                  and not campo.GetWindowStyle() & wx.TE_PROCESS_TAB]
        self.assertTrue(libres)


if __name__ == "__main__":
    unittest.main()
