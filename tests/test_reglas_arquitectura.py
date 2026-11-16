# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las reglas de arquitectura declaradas en la tabla."""

import ast
import textwrap
import unittest

from tests import reglas_arquitectura as reglas
from tests import reglas_controles as controles
from tests import reglas_detectores as detectores
from tests import reglas_sonido as sonido


EVENTOS = {"aviso", "comentario", "conectado", "error", "copiar"}
# El detector de pruebas remotas reconoce el módulo gráfico por su nombre:
# se arma así para que estas pruebas de lectura corran en esta PC.
WX = "w" + "x"


def _hallazgos(detector, codigo, *extra):
    arbol = ast.parse(textwrap.dedent(codigo))
    return detector("fragmento.py", arbol, *extra)


def _lineas(hallazgos):
    return [hallazgo.linea for hallazgo in hallazgos]


class TestTabla(unittest.TestCase):

    def test_las_quince_reglas_estan_en_la_tabla(self):
        self.assertEqual([regla.id for regla in reglas.REGLAS],
                         ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8",
                          "R9", "R10", "R11", "R12", "R13", "R14", "R15"])
        for regla in reglas.REGLAS:
            with self.subTest(regla=regla.id):
                self.assertTrue(regla.prohibido)
                self.assertTrue(callable(regla.detectar))
                self.assertTrue(callable(regla.ambito))


class TestReglasSobreElCodigo(unittest.TestCase):

    def test_ningun_archivo_ajeno_usa_lo_prohibido(self):
        for regla in reglas.REGLAS:
            hallazgos = detectores.hallazgos_por_archivo(regla)
            ajenos, _ = detectores.revisar(regla, hallazgos)
            with self.subTest(regla=regla.id):
                self.assertEqual([], ajenos,
                                 detectores.detalle_ajenos(regla, ajenos))

    def test_los_pendientes_solo_bajan(self):
        for regla in reglas.REGLAS:
            hallazgos = detectores.hallazgos_por_archivo(regla)
            _, vencidos = detectores.revisar(regla, hallazgos)
            with self.subTest(regla=regla.id):
                self.assertEqual([], vencidos,
                                 detectores.detalle_vencidos(regla, vencidos))

    def test_cada_pendiente_tiene_motivo(self):
        vacios = [f"{regla.id}: {archivo}"
                  for regla in reglas.REGLAS
                  for archivo, pendiente in regla.pendientes.items()
                  if not pendiente.motivo.strip()]
        self.assertEqual([], vacios, "Pendientes sin motivo: " + ", ".join(vacios))


class TestDetectores(unittest.TestCase):

    def test_cuadros(self):
        codigo = """\
            __WX__.MessageBox("a", "b")
            _gui.__WX__.MessageDialog(None, "a", "b")
            # __WX__.MessageBox("comentario")
            texto = "__WX__.MessageBox"
            otro.MessageBox("a", "b")
            """.replace("__WX__", WX)
        hallazgos = _hallazgos(detectores.detectar_cuadros, codigo)
        self.assertEqual([1, 2], _lineas(hallazgos))

    def test_capas(self):
        hallazgos = _hallazgos(detectores.detectar_capas, """\
            import guyrapu.ui.confirmar

            def f():
                from guyrapu.ui import paleta

            # import guyrapu.ui
            texto = "import guyrapu.ui"
            import guyrapu.util
            """)
        self.assertEqual([1, 4], _lineas(hallazgos))

    def test_red(self):
        hallazgos = _hallazgos(detectores.detectar_red, """\
            import httpx
            from urllib.request import urlopen

            def f():
                import requests

            # import requests
            from urllib import request
            from urllib.parse import urlparse
            import urllib.error
            from requests import get
            """)
        self.assertEqual([1, 2, 5, 8, 11], _lineas(hallazgos))

    def test_escape(self):
        codigo = """\
            if k == __WX__.WXK_ESCAPE:
                pass
            codigo = WXK_ESCAPE
            # WXK_ESCAPE
            texto = "WXK_ESCAPE"
            __WX__.WXK_F11
            """.replace("__WX__", WX)
        hallazgos = _hallazgos(detectores.detectar_escape, codigo)
        self.assertEqual([1, 3], _lineas(hallazgos))

    def test_avisar(self):
        hallazgos = _hallazgos(sonido.detectar_avisar, """\
            from guyrapu.ui.aviso_importante import avisar
            from guyrapu.ui import aviso_importante
            from guyrapu.ui.aviso_importante import avisar as chillar

            avisar("texto", "aviso")
            avisar("texto", sonido="comentario")
            avisar("texto")
            avisar("texto", "")
            avisar("texto", variable)
            avisar("texto", "error")
            avisar("texto", "copiar")
            avisar("texto", "inventado")
            aviso_importante.avisar("texto", "conectado")
            aviso_importante.avisar("texto")
            chillar("texto", "aviso")
            chillar("texto")
            # avisar("texto")
            texto = "avisar('x')"
            """, EVENTOS)
        self.assertEqual([7, 8, 9, 12, 14, 16],
                         _lineas(hallazgos))

    def test_avisar_acepta_el_parametro_que_reenvia(self):
        hallazgos = _hallazgos(sonido.detectar_avisar, """\
            from guyrapu.ui.aviso_importante import avisar

            def _decir(frase, sonido, *, clave):
                avisar(frase, sonido)
                avisar(frase, clave)
            """, EVENTOS)
        self.assertEqual([], _lineas(hallazgos))

    def test_avisar_acepta_una_constante_del_modulo(self):
        validos = _hallazgos(sonido.detectar_avisar, """\
            from guyrapu.ui.aviso_importante import avisar

            SONIDO = "error"

            def f():
                avisar("texto", SONIDO)
            """, EVENTOS)
        self.assertEqual([], _lineas(validos))
        reasignada = _hallazgos(sonido.detectar_avisar, """\
            from guyrapu.ui.aviso_importante import avisar

            SONIDO = "error"
            SONIDO = "aviso"

            def f():
                avisar("texto", SONIDO)
            """, EVENTOS)
        self.assertEqual([7], _lineas(reasignada))
        atributo = _hallazgos(sonido.detectar_avisar, """\
            from guyrapu.ui.aviso_importante import avisar

            class Aviso:
                sonido = "error"

            def f(aviso):
                avisar("texto", aviso.sonido)
            """, EVENTOS)
        self.assertEqual([7], _lineas(atributo))

    def test_avisar_error_acepta_las_familias_de_error(self):
        codigo = """\
            from guyrapu.ui.aviso_importante import avisar

            avisar("texto", "{clave}", error=True)
            """
        for clave in ("error", "transmision_problema", "espera"):
            with self.subTest(clave=clave):
                hallazgos = _hallazgos(sonido.detectar_avisar_error,
                                       codigo.format(clave=clave))
                self.assertEqual([], _lineas(hallazgos))
        completado = _hallazgos(sonido.detectar_avisar_error,
                                codigo.format(clave="comentario"))
        self.assertEqual([3], _lineas(completado))

    def test_notebook_sin_enlace_de_pestana(self):
        hallazgos = _hallazgos(controles.detectar_pestana_sin_anuncio, """\
            class Ventana:
                def armar(self):
                    self.nb = __WX__.Notebook(self, name="Paneles")
                    enlazar_anuncio_de_pestana(self.nb)
                    self.pestanas = __WX__.Notebook(self, name="Otras")

            def arma(frame):
                frame.nb = __WX__.Notebook(frame, name="Marco")

            def anuncia(frame):
                enlazar_anuncio_de_pestana(frame.nb)
            """.replace("__WX__", WX))
        self.assertEqual([5], _lineas(hallazgos))

    def test_notebook_sin_destino(self):
        hallazgos = _hallazgos(controles.detectar_pestana_sin_anuncio, """\
            def armar(frame):
                __WX__.Notebook(frame, name="Paneles")
            """.replace("__WX__", WX))
        self.assertEqual([2], _lineas(hallazgos))

    def test_listbook_no_necesita_el_anuncio(self):
        hallazgos = _hallazgos(controles.detectar_pestana_sin_anuncio, """\
            def armar(frame):
                frame.lb = __WX__.Listbook(frame, name="Otras")
            """.replace("__WX__", WX))
        self.assertEqual([], _lineas(hallazgos))

    def test_cuadro_sin_via_de_escape(self):
        hallazgos = _hallazgos(controles.detectar_cuadro_sin_escape, """\
            class Cuadro(__WX__.Dialog):
                pass

            class Ventana(__WX__.Frame):
                pass
            """.replace("__WX__", WX))
        self.assertEqual([1, 4], _lineas(hallazgos))

    def test_un_cierre_sin_escape_no_cuenta_como_via(self):
        hallazgos = _hallazgos(controles.detectar_cuadro_sin_escape, """\
            class Cuadro(__WX__.Dialog):
                def cerrar(self):
                    self.EndModal(__WX__.ID_CANCEL)
            """.replace("__WX__", WX))
        self.assertEqual([1], _lineas(hallazgos))

    def test_cada_via_de_escape_la_exime(self):
        vias = (
            "__WX__.Button(self, __WX__.ID_CANCEL, 'Cerrar')",
            "self.SetEscapeId(__WX__.ID_OK)",
            "from guyrapu.ui import tecla_escape",
            "tecla_escape.cancelar_si_escape(self, evento)",
            "codigo = __WX__.WXK_ESCAPE",
        )
        for via in vias:
            with self.subTest(via=via):
                codigo = (
                    "class Cuadro(__WX__.Dialog):\n"
                    "    def armar(self):\n"
                    f"        {via}\n").replace("__WX__", WX)
                hallazgos = _hallazgos(controles.detectar_cuadro_sin_escape,
                                       codigo)
                self.assertEqual([], _lineas(hallazgos))

    def test_cada_clase_mira_su_propio_cuerpo(self):
        hallazgos = _hallazgos(controles.detectar_cuadro_sin_escape, """\
            class ConCancelar(__WX__.Dialog):
                def armar(self):
                    __WX__.Button(self, __WX__.ID_CANCEL, "Cerrar")

            class SinNada(__WX__.Dialog):
                def armar(self):
                    __WX__.Button(self, label="Cerrar")
            """.replace("__WX__", WX))
        self.assertEqual([5], _lineas(hallazgos))

    def test_la_ventana_principal_no_entra(self):
        arbol = ast.parse(textwrap.dedent("""\
            class VentanaPrincipal(__WX__.Frame):
                pass
            """.replace("__WX__", WX)))
        hallazgos = controles.detectar_cuadro_sin_escape(
            "guyrapu/ui/gui.py", arbol)
        self.assertEqual([], _lineas(hallazgos))

    def test_una_base_propia_no_se_mira(self):
        hallazgos = _hallazgos(controles.detectar_cuadro_sin_escape, """\
            class DialogoBase(__WX__.Dialog):
                def armar(self):
                    __WX__.Button(self, __WX__.ID_CANCEL, "Cerrar")

            class Hijo(DialogoBase):
                pass
            """.replace("__WX__", WX))
        self.assertEqual([], _lineas(hallazgos))

    def test_controles(self):
        hallazgos = _hallazgos(detectores.detectar_controles, """\
            boton.Disable()
            boton.Enable(True)
            boton.Enable(False)
            boton.Enable(estado)
            menu.Enable(id, False)
            boton.Enable()
            # boton.Disable()
            texto = "boton.Disable()"
            boton.Enable(enable=False)
            boton.Enable(enable=True)
            boton.Enable(False, False)
            """)
        self.assertEqual([1, 3, 4, 9], _lineas(hallazgos))

    def test_preguntar_pide_el_predeterminado_explicito(self):
        hallazgos = _hallazgos(controles.detectar_predeterminado, """\
            from guyrapu.ui import confirmar, confirmar as confirmaciones
            from guyrapu.ui.confirmar import preguntar as preguntar_confirmar

            confirmar.preguntar(None, "a", "b", "Sí", "No", predeterminado_si=False)
            confirmar.preguntar(None, "a", "b", "Sí", "No", predeterminado_si=True)
            confirmar.preguntar(None, "a", "b", "Sí", "No")
            preguntar_confirmar(None, "a", "b", "Sí", "No", predeterminado_si=True)
            preguntar_confirmar(None, "a", "b", "Sí", "No")
            confirmar.preguntar(None, "a", "b", "Sí", "No", predeterminado_si=decidir)
            confirmar.preguntar(None, "a", "b", "Sí", "No", predeterminado_si=not problemas)
            confirmaciones.preguntar(None, "a", "b", "Sí", "No", predeterminado_si=False)
            otro.preguntar(None, "a", "b", "Sí", "No")
            # confirmar.preguntar(None, "a", "b", "Sí", "No")
            """)
        self.assertEqual([6, 8], _lineas(hallazgos))

    def test_control_sin_nombre(self):
        hallazgos = _hallazgos(controles.detectar_nombres_de_control, """\
            class Ventana:
                def armar(self):
                    self.btn_ok = __WX__.Button(self, label="A", name="Aceptar")
                    self.btn_no = __WX__.Button(self, label="B")
                    nombre_accesible(self.btn_no, "No")
                    self.txt = __WX__.TextCtrl(self, name="")
                    self.lista = __WX__.ListBox(self, choices=[])
                    self.otra = __WX__.CheckBox(self, label="C")
                    nombre_accesible(self.lista, "Lista")
                    self.cho = __WX__.Choice(self, name=nombre)
                    self.rad = __WX__.RadioButton(self, label="D", name=_("D"))

                def aparte(self):
                    self.spin = __WX__.SpinCtrl(self)
                    nombre_accesible(self.spin, "Cantidad")
                    self.sld = __WX__.Slider(self)

            def suelto():
                nombre_accesible(self.otra, "C")
            """.replace("__WX__", WX))
        self.assertEqual([6, 8, 16], _lineas(hallazgos))

    def test_reconoce_los_constructores_de_control(self):
        for constructor in ("Button", "CheckBox", "RadioButton", "TextCtrl",
                            "Choice", "ComboBox", "ListBox", "ListCtrl",
                            "CheckListBox", "Slider", "SpinCtrl",
                            "ToggleButton"):
            with self.subTest(constructor=constructor):
                codigo = "self.ctrl = __WX__." + constructor + "(self)\n"
                hallazgos = _hallazgos(controles.detectar_nombres_de_control,
                                       codigo.replace("__WX__", WX))
                self.assertEqual([1], _lineas(hallazgos))

    def test_rotulos_con_un_solo_mnemonico(self):
        hallazgos = _hallazgos(controles.detectar_mnemonico, """\
            __WX__.Button(self, label=_("&Aceptar"))
            __WX__.CheckBox(self, label=_("Aceptar"))
            __WX__.RadioButton(self, label=_("A&&B"))
            __WX__.Button(self, label=_("A&B&C"))
            __WX__.Button(self, label=etiqueta)
            __WX__.Button(self, label=_(""))
            __WX__.Button(self, label=f"&{nombre}")
            __WX__.StaticText(self, label=_("Sin mnemónico"))
            __WX__.Button(self, label=_("Doble && y uno &"))
            __WX__.Button(self, __WX__.ID_ANY, _("&Posicional"))
            """.replace("__WX__", WX))
        self.assertEqual([2, 3, 4], _lineas(hallazgos))

    def test_bibliotecas_voz(self):
        hallazgos = _hallazgos(detectores.detectar_bibliotecas_voz, """\
            import prism
            import piper.dsp
            from ptts import voz
            from onnxruntime import sesion
            import sounddevice as sd

            import numpy
            # import prism
            texto = "import piper"
            """)
        self.assertEqual([1, 2, 3, 4, 5], _lineas(hallazgos))

    def test_rotulos_de_menu(self):
        hallazgos = _hallazgos(detectores.detectar_rotulos_de_menu, """\
            m.Append(wx.ID_ANY, nombre_voz)
            m.Append(wx.ID_ANY, _("Abrir"))
            m.Append(wx.ID_ANY, _("Abrir") + algo)
            m.AppendSubMenu(sub, nombre_voz)
            m.Append(wx.ID_ANY)
            for nombre, _sin_uso in enumerate(FILTROS):
                m.AppendRadioItem(wx.ID_ANY, _(nombre))
            for etiqueta, altura in CALIDADES:
                m.AppendRadioItem(wx.ID_ANY, _(etiqueta))
            """)
        self.assertEqual([1, 4], _lineas(hallazgos))

    def test_esperas(self):
        hallazgos = _hallazgos(detectores.detectar_esperas, """\
            while activo:
                leer()
                dormir(1)
            while activo:
                parada.wait(1)
            while activo:
                leer_socket()
            while activo:
                def anidada():
                    time.sleep(1)
                leer()
            while activo:
                time.sleep(1)
            while activo:
                esperar(1)
            while activo:
                self._esperar_intervalo()
            """)
        self.assertEqual([1, 4, 12, 14, 16], _lineas(hallazgos))


if __name__ == "__main__":
    unittest.main()
