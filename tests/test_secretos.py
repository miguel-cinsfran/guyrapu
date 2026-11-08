"""Pruebas del tachado de secretos en los textos que escribe la app."""

import logging
import unittest

from guyrapu.core import secretos


class TestTacharCampos(unittest.TestCase):

    def test_campo_con_comillas_dobles(self):
        self.assertEqual(
            secretos.tachar('{"access_token": "ya29.x"}'),
            '{"access_token": "[tachado]"}')

    def test_campo_con_comillas_simples(self):
        self.assertEqual(
            secretos.tachar("{'refresh_token': '1//x'}"),
            "{'refresh_token': '[tachado]'}")

    def test_campo_en_forma_camel(self):
        self.assertEqual(
            secretos.tachar('{"clientSecret": "secreto"}'),
            '{"clientSecret": "[tachado]"}')


class TestTacharParametros(unittest.TestCase):

    def test_parametro_despues_de_interrogacion(self):
        self.assertEqual(
            secretos.tachar("?key=AIzaX&part=snippet"),
            "?key=[tachado]&part=snippet")

    def test_parametro_despues_de_ampersand(self):
        self.assertEqual(
            secretos.tachar("https://x.test/a?a=1&token=abc"),
            "https://x.test/a?a=1&token=[tachado]")


class TestTacharCabeceras(unittest.TestCase):

    def test_lo_que_sigue_a_bearer(self):
        self.assertEqual(
            secretos.tachar("Authorization: Bearer ya29.secreto"),
            "Authorization: Bearer [tachado]")

    def test_valor_de_xi_api_key(self):
        self.assertEqual(
            secretos.tachar("xi-api-key: sk-123"),
            "xi-api-key: [tachado]")


class TestTacharFormasConocidas(unittest.TestCase):

    def test_token_de_acceso_de_google(self):
        self.assertEqual(secretos.tachar("valor ya29.a0Af-1_.x fin"),
                         "valor [tachado] fin")

    def test_token_de_refresco(self):
        self.assertEqual(secretos.tachar("valor 1//0gAbC-d_E fin"),
                         "valor [tachado] fin")

    def test_clave_de_api_de_google(self):
        self.assertEqual(
            secretos.tachar("valor AIza" + "a" * 35 + " fin"),
            "valor [tachado] fin")

    def test_jwt(self):
        self.assertEqual(
            secretos.tachar(
                "valor eyJhbGciOi.eyJzdWIi.abc_def-123 fin"),
            "valor [tachado] fin")


class TestTacharRtmp(unittest.TestCase):

    def test_clave_de_transmision_en_rtmp(self):
        self.assertEqual(
            secretos.tachar("rtmp://a.rtmp.youtube.com/live2/clave-secreta"),
            "rtmp://a.rtmp.youtube.com/live2/[tachado]")

    def test_clave_de_transmision_en_rtmps(self):
        self.assertEqual(
            secretos.tachar("rtmps://host/live/clave"),
            "rtmps://host/live/[tachado]")


class TestNoTacha(unittest.TestCase):

    def test_textos_normales_quedan_iguales(self):
        textos = (
            "Iniciando la transmisión.",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "C:\\Users\\Manu\\Videos\\2026-11-07 21-30-00.mp4",
            "Tecla F5",
            "perfil TikTok 720x1280",
        )
        for texto in textos:
            with self.subTest(texto=texto):
                self.assertEqual(secretos.tachar(texto), texto)


class TestFormatoTachado(unittest.TestCase):

    def test_el_formato_tacha_el_mensaje(self):
        registro = logging.LogRecord(
            "guyrapu.prueba", logging.WARNING, "", 0,
            "guardado access_token=%s", ("ya29.secreto",), None)
        formato = secretos.FormatoTachado("%(message)s")
        self.assertEqual(formato.format(registro),
                         "guardado access_token=[tachado]")


if __name__ == "__main__":
    unittest.main()
