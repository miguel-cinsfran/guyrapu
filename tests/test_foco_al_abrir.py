# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El foco al abrir termina en el control principal de cada ventana.

Control principal: la lista de la página abierta si la tiene; si no, el primer
campo editable de su contenido, nunca un botón ni la tira de pestañas.
"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import wx

from guyrapu.obs import ajustes_perfil
from guyrapu.ui import dialogo_ajustes_perfil
from guyrapu.ui import gui_historial
from guyrapu.ui import obs_ventana
from guyrapu.ui import restream_perfil
from guyrapu.ui import restream_ventana
from tests.test_gui_transmision import GestorFalso
from tests.ventanas_prueba import app_de_prueba, destruir

_EDITABLES = (wx.TextCtrl, wx.Choice, wx.CheckBox, wx.RadioBox, wx.SpinCtrl)


def _buscar(raiz, tipos):
    """El primer control de esos tipos, en orden de recorrido, que se ve."""
    for hijo in raiz.GetChildren():
        if hijo.IsShown() and isinstance(hijo, tipos):
            return hijo
        if isinstance(hijo, wx.Notebook):
            pagina = hijo.GetCurrentPage()
            encontrado = _buscar(pagina, tipos) if pagina is not None else None
        elif isinstance(hijo, (wx.Panel, wx.ScrolledWindow, wx.StaticBox)):
            encontrado = _buscar(hijo, tipos)
        else:
            encontrado = None
        if encontrado is not None:
            return encontrado
    return None


def _tiene_foco(control):
    """El foco está en ese control o en un botón interno suyo, como el de un
    RadioBox."""
    foco = wx.Window.FindFocus()
    while foco is not None:
        if foco is control:
            return True
        foco = foco.GetParent()
    return False


def control_principal(ventana):
    """La lista de la página abierta o, si no hay, su primer campo editable."""
    notebook = _buscar(ventana, (wx.Notebook,))
    if notebook is None:
        return _buscar(ventana, _EDITABLES)
    pagina = notebook.GetCurrentPage()
    lista = _buscar(pagina, (wx.ListBox,))
    return lista if lista is not None else _buscar(pagina, _EDITABLES)


class CuentaFalsa:

    def conectada(self):
        return False


def _entrada(plataforma, clave):
    return {
        "plataforma": plataforma,
        "clave": clave,
        "url": f"https://{plataforma}.com/{clave}",
        "titulo": f"Título {clave}",
        "canal": f"Canal {clave}",
        "fecha": "2026-08-28T12:00:00",
        "directo": False,
    }


class TestFocoAlAbrir(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

    def _abrir(self, ventana):
        self.addCleanup(destruir, ventana)
        ventana.Show()
        self.addCleanup(ventana.Hide)
        wx.Yield()
        return ventana

    def test_ajustes_de_perfil_abren_en_la_orientacion(self):
        ventana = self._abrir(dialogo_ajustes_perfil.DialogoAjustesPerfil(
            None, ajustes_perfil.valores_iniciales(False, "nvenc"), "Prueba"))

        self.assertIs(control_principal(ventana), ventana.rad_orientacion)
        self.assertTrue(_tiene_foco(ventana.rad_orientacion))

    def test_historial_abre_en_la_lista_de_la_pestana_abierta(self):
        ruta = Path(self.temporal.name) / "historial.json"
        ruta.write_text(json.dumps([
            _entrada("youtube", "yt"), _entrada("tiktok", "tk")]),
            encoding="utf-8")
        ventana = self._abrir(gui_historial.HistorialDialog(
            None, ruta, lambda url: None))
        lista = ventana._listas["youtube"]

        self.assertIs(control_principal(ventana), lista)
        self.assertTrue(_tiene_foco(lista))

    def test_obs_abre_en_la_lista_de_escenas(self):
        principal = SimpleNamespace(_config={"obs_microfono": "Mic/Aux"})
        with mock.patch.object(obs_ventana.VentanaObs, "_en_hilo") as en_hilo, \
                mock.patch.object(
                    obs_ventana.obs_lanzador, "asegurar_obs",
                    lambda probar, al_anunciar=None, parada=None: probar()), \
                mock.patch.object(obs_ventana, "anunciar"):
            ventana = obs_ventana.VentanaObs(
                None, principal, gestor=GestorFalso())
            self.addCleanup(destruir, ventana)
            ventana.Show()
            self.addCleanup(ventana.Hide)
            wx.Yield()
            funcion, al_terminar = en_hilo.call_args.args
            al_terminar(funcion())
        lista = ventana._pagina_escena.lst_escenas

        self.assertIs(control_principal(ventana), lista)
        self.assertTrue(_tiene_foco(lista))

    def test_restream_abre_en_el_estado_de_la_cuenta(self):
        ruta = Path(self.temporal.name) / "perfiles_restream.json"
        ventana = self._abrir(restream_ventana.VentanaRestream(
            None, CuentaFalsa(), lambda: [], ruta, id_canal=lambda: ""))
        estado = ventana._pagina_cuenta.txt_estado

        self.assertIs(control_principal(ventana), estado)
        self.assertTrue(_tiene_foco(estado))

    def test_perfil_de_restream_abre_en_el_nombre(self):
        ventana = self._abrir(restream_perfil.DialogoPerfilRestream(
            None, None, [(1, "TikTok: uno")], []))

        self.assertIs(control_principal(ventana), ventana.txt_nombre)
        self.assertTrue(_tiene_foco(ventana.txt_nombre))


if __name__ == "__main__":
    unittest.main()
