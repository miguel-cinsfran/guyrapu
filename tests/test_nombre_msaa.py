"""El nombre se anota en la ventana sin cambiar el rol ni el estado de MSAA.

Medido el 07/11/2026 con wx 4.3.1 sobre controles reales: el proxy de wx
convertía las casillas en botones y las filas de una lista con casillas
perdían su rol. La anotación dinámica de Windows solo cambia el nombre.
"""

import ctypes
import unittest
from ctypes import wintypes
from unittest import mock

import wx

from guyrapu.ui import accesibilidad
from tests.ventanas_prueba import app_de_prueba, destruir

OBJID_CLIENT = 0xFFFFFFFC
ROL_CASILLA = 0x2C
ESTADO_MARCADO = 0x10


def _accesible(hwnd):
    """Objeto MSAA del cliente de una ventana, leído con comtypes."""
    import comtypes.client
    from comtypes import GUID

    accessibility = comtypes.client.GetModule("oleacc.dll")
    puntero = ctypes.POINTER(accessibility.IAccessible)()
    funcion = ctypes.oledll.oleacc.AccessibleObjectFromWindow
    funcion.argtypes = [
        wintypes.HWND, wintypes.DWORD, ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.POINTER(accessibility.IAccessible))]
    funcion.restype = ctypes.HRESULT
    funcion(hwnd, OBJID_CLIENT,
            ctypes.byref(accessibility.IAccessible._iid_),
            ctypes.byref(puntero))
    return puntero


class TestNombreMsaa(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _ventana(self):
        ventana = wx.Frame(None)
        self.addCleanup(destruir, ventana)
        ventana.Show()
        wx.Yield()
        return ventana

    def test_casilla_con_color_conserva_rol_estado_y_nombre(self):
        ventana = self._ventana()
        casilla = wx.CheckBox(ventana, label="Creado para niños")
        casilla.SetForegroundColour(wx.Colour(200, 200, 200))
        casilla.SetValue(True)
        accesibilidad.nombre_accesible(casilla, "Nombre propio")

        accesible = _accesible(casilla.GetHandle())
        self.assertEqual(accesible.accName(0), "Nombre propio")
        self.assertEqual(accesible.accRole(0), ROL_CASILLA)
        self.assertTrue(accesible.accState(0) & ESTADO_MARCADO)

    def test_fila_de_checklistbox_conserva_rol_y_estado(self):
        ventana = self._ventana()
        lista = wx.CheckListBox(ventana, choices=["uno", "dos"])
        lista.Check(0)
        accesibilidad.nombre_accesible(lista, "Destinos")

        accesible = _accesible(lista.GetHandle())
        self.assertEqual(accesible.accRole(1), ROL_CASILLA)
        self.assertTrue(accesible.accState(1) & ESTADO_MARCADO)

    def test_textctrl_conserva_el_nombre_pedido(self):
        ventana = self._ventana()
        campo = wx.TextCtrl(ventana)
        accesibilidad.nombre_accesible(campo, "Texto propio")

        accesible = _accesible(campo.GetHandle())
        self.assertEqual(accesible.accName(0), "Texto propio")

    def test_al_destruir_se_quita_la_anotacion(self):
        from guyrapu.core import nombre_msaa

        ventana = self._ventana()
        casilla = wx.CheckBox(ventana, label="Algo")
        hwnd = casilla.GetHandle()
        accesibilidad.nombre_accesible(casilla, "Nombre propio")

        llamadas = []
        original = nombre_msaa.quitar

        def _quitar(hwnd_borrado):
            resultado = original(hwnd_borrado)
            llamadas.append((hwnd_borrado, resultado))
            return resultado

        with mock.patch.object(nombre_msaa, "quitar", _quitar):
            casilla.Destroy()
            wx.SafeYield()

        self.assertEqual(llamadas, [(hwnd, True)])

    def test_msaa_false_no_anota_y_deja_nombre_tooltip_y_ayuda(self):
        from guyrapu.core import nombre_msaa

        control = mock.Mock()
        control.GetToolTip.return_value = None

        with mock.patch.object(nombre_msaa, "poner") as poner:
            accesibilidad.nombre_accesible(control, "Otro nombre", msaa=False)

        poner.assert_not_called()
        control.SetName.assert_called_once_with("Otro nombre")
        control.SetToolTip.assert_called_once_with("Otro nombre")
        control.SetHelpText.assert_called_once_with("Otro nombre")

    def test_fallo_de_com_devuelve_false_y_no_lanza(self):
        from guyrapu.core import nombre_msaa

        with mock.patch.object(nombre_msaa, "_servicios", None), \
                mock.patch.object(
                    nombre_msaa, "_co_create_instance",
                    side_effect=OSError("COM sin inicializar")):
            with self.assertLogs(nombre_msaa.logger, "DEBUG") as registros:
                self.assertFalse(nombre_msaa.poner(1234, "Nombre"))

        self.assertIn("No se pudo anotar el nombre accesible",
                      "\n".join(registros.output))


if __name__ == "__main__":
    unittest.main()
