# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las ventanas de prueba del carril, construidas sin mostrar.

Abren wx, así que se corren en la PC que no usa nadie. No abren ninguna
ventana visible: solo se construyen los controles y se inspeccionan.
"""

import unittest
from unittest import mock

import wx

from guyrapu.core import nombre_msaa
from qa.nvda import reglas, trampas

TRAMPAS = [nombre for nombre, datos in trampas.VENTANAS.items()
           if datos["regla"]]
SONDAS = [nombre for nombre, datos in trampas.VENTANAS.items()
          if datos.get("sonda")]


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
        "nombre_repetido": ["Siguiente", "Volumen", "Volumen"],
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

    def test_la_trampa_tiene_al_menos_dos_paradas_de_tab(self):
        marco = self.construir("nombre_repetido")
        paradas = [control for control in _controles(marco)
                   if isinstance(control, wx.Control)
                   and not isinstance(control, wx.StaticBox)
                   and control.AcceptsFocusFromKeyboard()]
        self.assertGreaterEqual(len(paradas), 2)

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


class TestSondas(Base):
    TIPOS = {
        "sonda_lista_box": wx.ListBox,
        "sonda_lista_box_nombre": wx.ListBox,
        "sonda_lista_box_pieza": wx.ListBox,
        "sonda_lista_box_ayuda": wx.ListBox,
        "sonda_lista_box_msaa": wx.ListBox,
        "sonda_lista_vista": wx.ListCtrl,
        "sonda_categorias": wx.Listbook,
    }

    def test_hay_siete_sondas_de_una_clase_de_lista_cada_una(self):
        self.assertEqual(len(SONDAS), 7)
        self.assertEqual(sorted(SONDAS), sorted(self.TIPOS))
        for nombre in SONDAS:
            with self.subTest(ventana=nombre):
                datos = trampas.VENTANAS[nombre]
                self.assertTrue(datos["sonda"])
                self.assertIsNone(datos["regla"])
                self.assertEqual(datos["primero"], "Antes")
                marco = self.construir(nombre)
                self.assertTrue(any(
                    isinstance(control, self.TIPOS[nombre])
                    for control in _controles(marco)))

    def test_el_primer_control_de_cada_sonda_es_antes(self):
        for nombre in SONDAS:
            with self.subTest(ventana=nombre):
                self.assertTrue(_con_nombre(self.construir(nombre), "Antes"))

    def _control_de_lista(self, marco, nombre):
        if nombre == "sonda_categorias":
            libro = [control for control in _controles(marco)
                     if isinstance(control, wx.Listbook)][0]
            return libro.GetListView()
        clase = self.TIPOS[nombre]
        return [control for control in _controles(marco)
                if isinstance(control, clase)][0]

    def _elementos_y_elegido(self, control):
        if isinstance(control, wx.ListBox):
            textos = [control.GetString(i)
                      for i in range(control.GetCount())]
            return textos, control.GetSelection()
        textos = [control.GetItemText(i)
                  for i in range(control.GetItemCount())]
        return textos, control.GetFirstSelected()

    def test_cada_lista_tiene_tres_elementos_y_el_primero_elegido(self):
        for nombre in SONDAS:
            with self.subTest(ventana=nombre):
                control = self._control_de_lista(
                    self.construir(nombre), nombre)
                textos, elegido = self._elementos_y_elegido(control)
                self.assertEqual(textos, ["Uno", "Dos", "Tres"])
                self.assertEqual(elegido, 0)

    def test_las_listas_llevan_el_nombre_de_sonda(self):
        for nombre in SONDAS:
            with self.subTest(ventana=nombre):
                control = self._control_de_lista(
                    self.construir(nombre), nombre)
                self.assertEqual(control.GetName(), "Lista de sonda")

    def test_la_sonda_de_ayuda_pone_tooltip_sin_anotar(self):
        with mock.patch.object(nombre_msaa, "poner") as poner:
            marco = self.construir("sonda_lista_box_ayuda")
        lista = self._control_de_lista(marco, "sonda_lista_box_ayuda")
        self.assertEqual(lista.GetName(), "Lista de sonda")
        self.assertEqual(lista.GetToolTip().GetTip(), "Lista de sonda")
        self.assertNotIn(mock.call(lista.GetHandle(), "Lista de sonda"),
                         poner.call_args_list)

    def test_la_sonda_msaa_anota_el_nombre_sin_tooltip_ni_ayuda(self):
        with mock.patch.object(nombre_msaa, "poner",
                               return_value=True) as poner:
            marco = self.construir("sonda_lista_box_msaa")
        lista = self._control_de_lista(marco, "sonda_lista_box_msaa")
        self.assertEqual(lista.GetName(), "Lista de sonda")
        self.assertIsNone(lista.GetToolTip())
        self.assertEqual(lista.GetHelpText(), "")
        poner.assert_any_call(lista.GetHandle(), "Lista de sonda")

    def test_el_primer_elemento_de_la_vista_tiene_foco(self):
        lista = self._control_de_lista(
            self.construir("sonda_lista_vista"), "sonda_lista_vista")
        estado = lista.GetItemState(
            0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        self.assertTrue(estado & wx.LIST_STATE_SELECTED)
        self.assertTrue(estado & wx.LIST_STATE_FOCUSED)


if __name__ == "__main__":
    unittest.main()
