"""Pruebas del cifrado DPAPI atado a la cuenta de Windows."""

import unittest

from guyrapu.core import dpapi


class TestDpapi(unittest.TestCase):

    def test_id_y_vuelta_devuelve_lo_mismo(self):
        claro = b"hola"
        cifrado = dpapi.cifrar(claro)
        self.assertEqual(dpapi.descifrar(cifrado), claro)

    def test_el_cifrado_no_contiene_el_texto_claro(self):
        self.assertNotIn(b"hola", dpapi.cifrar(b"hola"))

    def test_basura_lanza_dpapi_error(self):
        with self.assertRaises(dpapi.DpapiError):
            dpapi.descifrar(b"basura")

    def test_dpapi_error_es_oserror(self):
        self.assertTrue(issubclass(dpapi.DpapiError, OSError))


if __name__ == "__main__":
    unittest.main()
