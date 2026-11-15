# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de motivo_de_error: la causa en llano de un fallo de yt-dlp."""

import unittest

from guyrapu.downloads.motivo_error import motivo_de_error
from guyrapu.downloads.progreso_ytdlp import tratar_linea
from tests.pseudo_prueba import con_pseudo


EDAD = ("ERROR: [youtube] O2yixU7XjGU: Sign in to confirm your age. Use "
        "--cookies-from-browser or --cookies for the authentication.")

LINEA_ERROR = "ERROR:\n"
LINEA_DETALLE = ("[download] Got error: HTTPConnectionPool(host='127.0.0.1', "
                 "port=8765): Read timed out.. Giving up after 10 retries\n")


class TestMotivoDeError(unittest.TestCase):

    def test_edad_restringida(self):
        self.assertEqual(
            motivo_de_error(EDAD),
            "El vídeo tiene restricción de edad y YouTube pide iniciar sesión.")

    def test_edad_con_otras_mayusculas(self):
        self.assertEqual(
            motivo_de_error(EDAD.replace("Sign in to confirm your age",
                                         "SIGN IN TO CONFIRM YOUR AGE")),
            "El vídeo tiene restricción de edad y YouTube pide iniciar sesión.")

    def test_marca_age_restricted(self):
        self.assertEqual(
            motivo_de_error("ERROR: [youtube] abc: This video is age-restricted."),
            "El vídeo tiene restricción de edad y YouTube pide iniciar sesión.")

    def test_privado(self):
        self.assertEqual(
            motivo_de_error("ERROR: [youtube] abc: Private video. Sign in if "
                            "you've been granted access to this video."),
            "El vídeo es privado.")

    def test_solo_miembros(self):
        self.assertEqual(
            motivo_de_error("ERROR: [youtube] abc: Join this channel to get "
                            "access to members-only content like this video."),
            "El vídeo es solo para miembros del canal.")

    def test_solo_miembros_sin_invitacion(self):
        self.assertEqual(
            motivo_de_error("ERROR: [youtube] abc: This is a members-only video."),
            "El vídeo es solo para miembros del canal.")

    def test_no_robot(self):
        self.assertEqual(
            motivo_de_error("ERROR: [youtube] abc: Sign in to confirm you're "
                            "not a bot. Use --cookies-from-browser."),
            "YouTube pide confirmar que no eres un robot. Vuelve a "
            "intentarlo más tarde.")

    def test_no_disponible(self):
        self.assertEqual(
            motivo_de_error("ERROR: [youtube] abc: Video unavailable"),
            "El vídeo no está disponible.")

    def test_no_disponible_en_frase(self):
        self.assertEqual(
            motivo_de_error("ERROR: [youtube] abc: This video is not available."),
            "El vídeo no está disponible.")

    def test_pide_iniciar_sesion(self):
        self.assertEqual(
            motivo_de_error("ERROR: [vimeo] abc: This video is only available "
                            "for logged-in users."),
            "Esta plataforma pide iniciar sesión.")

    def test_pide_autenticacion(self):
        self.assertEqual(
            motivo_de_error("ERROR: [reddit] abc: authentication is required"),
            "Esta plataforma pide iniciar sesión.")

    def test_enlace_no_compatible(self):
        self.assertEqual(
            motivo_de_error("ERROR: Unsupported URL: https://example.com"),
            "Este enlace no es compatible con la descarga.")

    def test_edad_restringida_gana_sobre_las_cookies(self):
        self.assertEqual(
            motivo_de_error("ERROR: age-restricted, use --cookies"),
            "El vídeo tiene restricción de edad y YouTube pide iniciar sesión.")

    def test_video_sin_audio(self):
        self.assertEqual(
            motivo_de_error("ERROR: Postprocessing: WARNING: unable to "
                            "obtain file audio codec with ffprobe"),
            "El vídeo no tiene audio.")

    def test_perfil_de_tiktok_pide_enlace_de_video(self):
        self.assertEqual(
            motivo_de_error("ERROR: [tiktok:user] scout2015: Unable to "
                            "extract secondary user ID."),
            "No se pudo leer este perfil de TikTok. Pega el enlace de "
            "un vídeo.")

    def test_desconocido_da_none(self):
        self.assertIsNone(
            motivo_de_error("ERROR: [youtube] abc: Unable to download webpage"))

    def test_none_da_none(self):
        self.assertIsNone(motivo_de_error(None))

    def test_vacio_da_none(self):
        self.assertIsNone(motivo_de_error(""))


class TestErrorDeRed(unittest.TestCase):
    """El error de yt-dlp partido en dos líneas y la conexión perdida."""

    def _procesar(self, lineas):
        estado = {"ultimo_error": "", "rutas": [], "indice": 0, "total": 0,
                  "procesando": False, "ultimo_archivo": "", "ultimo_ts": None}
        for linea in lineas:
            tratar_linea(linea, estado, lambda *a: None, lambda *a: None)
        return estado

    def test_error_solo_junta_la_linea_siguiente_no_vacia(self):
        estado = self._procesar([LINEA_ERROR, "\n", LINEA_DETALLE])
        self.assertEqual(
            estado["ultimo_error"],
            "ERROR: [download] Got error: "
            "HTTPConnectionPool(host='127.0.0.1', port=8765): Read timed "
            "out.. Giving up after 10 retries")

    def test_conexion_perdida_por_tiempo_agotado(self):
        estado = self._procesar([LINEA_ERROR, LINEA_DETALLE])
        self.assertEqual(motivo_de_error(estado["ultimo_error"]),
                         "Se perdió la conexión. Vuelve a intentarlo.")

    def test_giving_up_y_timed_out_sin_mayusculas(self):
        for linea in ("ERROR: Giving up after 10 retries",
                      "ERROR: Read TIMED OUT"):
            with self.subTest(linea=linea):
                self.assertEqual(
                    motivo_de_error(linea),
                    "Se perdió la conexión. Vuelve a intentarlo.")

    def test_las_causas_conocidas_ganan_sobre_la_red(self):
        self.assertEqual(
            motivo_de_error("ERROR: Private video. Read timed out"),
            "El vídeo es privado.")


class TestPseudoMotivos(unittest.TestCase):
    """Pseudotraducción: cada motivo conocido sale marcado."""

    def test_todos_los_motivos_salen_marcados(self):
        lineas = [
            EDAD,
            "ERROR: [youtube] abc: This video is age-restricted.",
            "ERROR: [youtube] abc: Private video.",
            "ERROR: [youtube] abc: This is a members-only video.",
            "ERROR: [youtube] abc: Sign in to confirm you're not a bot.",
            "ERROR: [youtube] abc: Video unavailable.",
            "ERROR: [vimeo] abc: This video is only available for logged-in users.",
            "ERROR: Unsupported URL: https://example.com",
            "ERROR: Postprocessing: WARNING: unable to obtain file audio codec.",
            "ERROR: [tiktok:user] scout2015: Unable to extract secondary user ID.",
            "ERROR: Read timed out.. Giving up after 10 retries",
        ]
        with con_pseudo():
            motivos = [motivo_de_error(linea) for linea in lineas]
        self.assertEqual(len(motivos), len(lineas))
        for motivo in motivos:
            with self.subTest(motivo=motivo):
                self.assertTrue(motivo.startswith("[¡"), motivo)


if __name__ == "__main__":
    unittest.main()
