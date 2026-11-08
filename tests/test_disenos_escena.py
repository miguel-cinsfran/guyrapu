# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import unittest

from guyrapu.obs import disenos_escena as disenos


class DisenosEscenaTest(unittest.TestCase):
    def test_pantalla_completa_ajusta(self):
        fuente = disenos.Fuente("Captura", "otra", 1280, 720)
        diseno = disenos.Diseno(clase="pantalla_completa", principal="Captura")
        [resultado] = disenos.calcular(1920, 1080, [fuente], diseno)
        self.assertEqual(resultado["nombre"], "Captura")
        self.assertEqual((resultado["positionX"], resultado["positionY"]),
                         (0, 0))
        self.assertEqual((resultado["boundsWidth"], resultado["boundsHeight"]),
                         (1920, 1080))
        self.assertEqual(resultado["alignment"], 5)
        self.assertEqual(resultado["boundsType"], "OBS_BOUNDS_SCALE_INNER")
        self.assertEqual(resultado["boundsAlignment"], 0)
        self.assertEqual(
            (resultado["cropLeft"], resultado["cropRight"],
             resultado["cropTop"], resultado["cropBottom"]),
            (0, 0, 0, 0))
        self.assertEqual(resultado["estado"], disenos.ESTADO_AJUSTA)

    def test_imagen_en_imagen_mediana_abajo_derecha(self):
        camara = disenos.Fuente("Cámara", "camara", 1280, 720)
        juego = disenos.Fuente("Juego", "otra", 1920, 1080)
        diseno = disenos.Diseno(
            clase="imagen_en_imagen", principal="Juego", secundaria="Cámara",
            esquina="inferior-derecha", tamano="mediana",
            modos={"Cámara": "ajustar", "Juego": "ajustar"})
        resultados = disenos.calcular(1920, 1080, [juego, camara], diseno)
        self.assertEqual([resultado["nombre"] for resultado in resultados],
                         ["Cámara", "Juego"])
        camara_res, juego_res = resultados
        self.assertEqual(
            (camara_res["boundsWidth"], camara_res["boundsHeight"]), (480, 270))
        self.assertEqual(
            1920 - (camara_res["positionX"] + camara_res["boundsWidth"]), 38)
        self.assertEqual(
            1080 - (camara_res["positionY"] + camara_res["boundsHeight"]), 22)
        self.assertEqual(camara_res["estado"], disenos.ESTADO_AJUSTA)
        self.assertEqual(juego_res["positionX"], 0)
        self.assertEqual(juego_res["boundsWidth"], 1920)
        self.assertEqual(juego_res["estado"], disenos.ESTADO_AJUSTA)

    def test_dividida_mitades(self):
        camara = disenos.Fuente("Cámara", "camara", 1920, 1080)
        captura = disenos.Fuente("Captura", "otra", 1280, 720)
        diseno = disenos.Diseno(clase="dividida", izquierda="Cámara",
                                derecha="Captura", proporcion="mitades",
                                modos={"Cámara": "ajustar",
                                       "Captura": "ajustar"})
        resultados = disenos.calcular(1920, 1080, [camara, captura], diseno)
        self.assertEqual([resultado["nombre"] for resultado in resultados],
                         ["Cámara", "Captura"])
        izquierda, derecha = resultados
        self.assertEqual(
            (izquierda["positionX"], izquierda["positionY"],
             izquierda["boundsWidth"], izquierda["boundsHeight"]),
            (0, 0, 960, 1080))
        self.assertEqual(
            (izquierda["cropLeft"], izquierda["cropRight"],
             izquierda["cropTop"], izquierda["cropBottom"]),
            (0, 0, 0, 0))
        self.assertEqual(izquierda["estado"], disenos.ESTADO_AJUSTA)
        self.assertEqual((derecha["positionX"], derecha["boundsWidth"]),
                         (960, 960))
        self.assertEqual(
            (derecha["cropLeft"], derecha["cropRight"],
             derecha["cropTop"], derecha["cropBottom"]),
            (0, 0, 0, 0))
        self.assertEqual(derecha["estado"], disenos.ESTADO_AJUSTA)

    def test_dividida_dos_tercios_y_modos(self):
        camara = disenos.Fuente("Cámara", "camara", 640, 480)
        captura = disenos.Fuente("Captura", "otra", 1280, 720)
        diseno = disenos.Diseno(
            clase="dividida", izquierda="Cámara", derecha="Captura",
            proporcion="dos_tercios",
            modos={"Cámara": "ajustar", "Captura": "llenar"})
        izquierda, derecha = disenos.calcular(
            1920, 1080, [camara, captura], diseno)
        self.assertEqual(izquierda["boundsWidth"], 1280)
        self.assertEqual((derecha["positionX"], derecha["boundsWidth"]),
                         (1280, 640))
        self.assertEqual(izquierda["estado"], disenos.ESTADO_AJUSTA)
        self.assertEqual(
            (izquierda["cropLeft"], izquierda["cropRight"],
             izquierda["cropTop"], izquierda["cropBottom"]),
            (0, 0, 0, 0))
        self.assertEqual((derecha["cropLeft"], derecha["cropRight"]),
                         (426, 427))
        self.assertEqual(derecha["estado"], disenos.ESTADO_LLENA)

    def test_chat_en_franja(self):
        chat = disenos.Fuente("Chat", "chat", 460, 620)
        juego = disenos.Fuente("Juego", "otra", 1920, 1080)
        diseno = disenos.Diseno(clase="pantalla_completa", principal="Juego",
                                chat="franja")
        resultados = disenos.calcular(1920, 1080, [juego, chat], diseno)
        self.assertEqual([resultado["nombre"] for resultado in resultados],
                         ["Chat", "Juego"])
        chat_res, juego_res = resultados
        self.assertEqual((chat_res["positionX"], chat_res["positionY"]),
                         (1440, 0))
        self.assertEqual((chat_res["ancho"], chat_res["alto"]), (480, 1080))
        self.assertEqual(chat_res["alignment"], 5)
        self.assertEqual(juego_res["boundsWidth"], 1440)
        self.assertEqual(juego_res["boundsHeight"], 1080)

    def test_chat_en_franja_vertical_va_abajo(self):
        chat = disenos.Fuente("Chat", "chat", 460, 620)
        juego = disenos.Fuente("Juego", "otra", 1920, 1080)
        diseno = disenos.Diseno(clase="pantalla_completa", principal="Juego",
                                chat="franja")
        chat_res, juego_res = disenos.calcular(1080, 1920, [juego, chat],
                                               diseno)
        self.assertEqual((chat_res["positionX"], chat_res["positionY"]),
                         (0, 1440))
        self.assertEqual((chat_res["ancho"], chat_res["alto"]), (1080, 480))
        self.assertEqual((juego_res["boundsWidth"], juego_res["boundsHeight"]),
                         (1080, 1440))

    def test_dividida_vertical_apila_arriba_y_abajo(self):
        camara = disenos.Fuente("Cámara", "camara", 640, 480)
        captura = disenos.Fuente("Captura", "otra", 1280, 720)
        diseno = disenos.Diseno(clase="dividida", izquierda="Captura",
                                derecha="Cámara", proporcion="mitades")
        arriba, abajo = disenos.calcular(1080, 1920, [captura, camara], diseno)
        self.assertEqual(
            (arriba["positionX"], arriba["positionY"],
             arriba["boundsWidth"], arriba["boundsHeight"]),
            (0, 0, 1080, 960))
        self.assertEqual(
            (abajo["positionX"], abajo["positionY"],
             abajo["boundsWidth"], abajo["boundsHeight"]),
            (0, 960, 1080, 960))

    def test_a_la_medida_con_los_numeros_del_ejemplo(self):
        camara = disenos.Fuente("Cámara", "camara", 640, 480)
        captura = disenos.Fuente("Captura", "otra", 1600, 900)
        diseno = disenos.Diseno(clase="dividida", izquierda="Captura",
                                derecha="Cámara", proporcion="a_la_medida")
        arriba, abajo = disenos.calcular(1080, 1920, [captura, camara], diseno)
        self.assertEqual(
            (arriba["positionX"], arriba["positionY"],
             arriba["boundsWidth"], arriba["boundsHeight"]),
            (0, 0, 1080, 608))
        self.assertEqual(
            (abajo["positionX"], abajo["positionY"],
             abajo["boundsWidth"], abajo["boundsHeight"]),
            (0, 608, 1080, 1312))
        izquierda, derecha = disenos.calcular(1920, 1080, [captura, camara],
                                              diseno)
        self.assertEqual(
            (izquierda["positionX"], izquierda["boundsWidth"],
             izquierda["boundsHeight"]), (0, 1440, 1080))
        self.assertEqual(
            (derecha["positionX"], derecha["boundsWidth"]),
            (1440, 480))

    def test_a_la_medida_sin_tamano_de_fuente_usa_mitad(self):
        rara = disenos.Fuente("Rara", "camara", 0, 0)
        otra = disenos.Fuente("Otra", "otra", 640, 480)
        diseno = disenos.Diseno(clase="dividida", izquierda="Rara",
                                derecha="Otra", proporcion="a_la_medida")
        arriba, abajo = disenos.calcular(1080, 1920, [rara, otra], diseno)
        self.assertEqual(arriba["boundsHeight"], 960)
        self.assertEqual(abajo["boundsHeight"], 960)

    def test_automatico_llena_la_camara_y_ajusta_las_demas(self):
        camara = disenos.Fuente("Cámara", "camara", 640, 480)
        captura = disenos.Fuente("Captura", "otra", 1600, 900)
        for lienzo in ((1080, 1920), (1920, 1080)):
            with self.subTest(lienzo=lienzo):
                diseno = disenos.Diseno(clase="dividida",
                                        izquierda="Captura",
                                        derecha="Cámara")
                izquierda, derecha = disenos.calcular(
                    lienzo[0], lienzo[1], [captura, camara], diseno)
                self.assertEqual(izquierda["estado"], disenos.ESTADO_AJUSTA)
                self.assertEqual(derecha["estado"], disenos.ESTADO_LLENA)
                self.assertTrue(
                    derecha["cropLeft"] or derecha["cropTop"])

    def test_dividida_reparte_el_area_sin_huecos(self):
        fuente = disenos.Fuente("Cámara", "camara", 1600, 900)
        otra = disenos.Fuente("Otra", "otra", 640, 480)
        for lienzo in ((1920, 1080), (1280, 720), (1080, 1920), (720, 1280)):
            for proporcion in disenos.PROPORCIONES:
                with self.subTest(lienzo=lienzo, proporcion=proporcion):
                    diseno = disenos.Diseno(
                        clase="dividida", izquierda="Cámara",
                        derecha="Otra", proporcion=proporcion)
                    primero, segundo = disenos.calcular(
                        lienzo[0], lienzo[1], [fuente, otra], diseno)
                    self._comprobar_teselado(lienzo, primero, segundo)

    def _comprobar_teselado(self, lienzo, primero, segundo):
        ancho, alto = lienzo
        if alto > ancho:
            self.assertEqual(
                (primero["positionX"], primero["boundsWidth"],
                 segundo["positionX"], segundo["boundsWidth"]),
                (0, ancho, 0, ancho))
            self.assertEqual(primero["positionY"], 0)
            self.assertEqual(
                primero["positionY"] + primero["boundsHeight"],
                segundo["positionY"])
            self.assertEqual(
                segundo["positionY"] + segundo["boundsHeight"], alto)
        else:
            self.assertEqual(
                (primero["positionY"], primero["boundsHeight"],
                 segundo["positionY"], segundo["boundsHeight"]),
                (0, alto, 0, alto))
            self.assertEqual(primero["positionX"], 0)
            self.assertEqual(
                primero["positionX"] + primero["boundsWidth"],
                segundo["positionX"])
            self.assertEqual(
                segundo["positionX"] + segundo["boundsWidth"], ancho)

    def test_chat_superpuesto_conserva_tamano(self):
        chat = disenos.Fuente("Chat", "chat", 460, 620)
        juego = disenos.Fuente("Juego", "otra", 1920, 1080)
        diseno = disenos.Diseno(
            clase="pantalla_completa", principal="Juego", chat="superpuesto",
            esquina_chat="superior-izquierda")
        chat_res, juego_res = disenos.calcular(
            1920, 1080, [juego, chat], diseno)
        self.assertEqual(set(chat_res),
                         {"nombre", "positionX", "positionY", "alignment"})
        self.assertAlmostEqual(chat_res["positionX"], 38.4)
        self.assertAlmostEqual(chat_res["positionY"], 21.6)
        self.assertEqual(chat_res["alignment"], 5)
        self.assertEqual(juego_res["boundsWidth"], 1920)

    def test_llenar_sin_origen_ajusta_y_marca(self):
        camara = disenos.Fuente("Cámara", "camara", 0, 0)
        diseno = disenos.Diseno(clase="pantalla_completa", principal="Cámara",
                                modos={"Cámara": "llenar"})
        [resultado] = disenos.calcular(1920, 1080, [camara], diseno)
        self.assertEqual(resultado["estado"],
                         disenos.ESTADO_AJUSTA_SIN_ORIGEN)
        self.assertEqual(
            (resultado["cropLeft"], resultado["cropRight"],
             resultado["cropTop"], resultado["cropBottom"]),
            (0, 0, 0, 0))
        self.assertEqual((resultado["boundsWidth"], resultado["boundsHeight"]),
                         (1920, 1080))

    def test_errores(self):
        fuente = disenos.Fuente("A", "otra", 640, 480)
        otra = disenos.Fuente("B", "otra", 640, 480)
        casos = [
            (1920, 1080, [fuente], disenos.Diseno(
                clase="dividida", izquierda="A", derecha="A")),
            (1920, 1080, [fuente, otra], disenos.Diseno(
                clase="dividida", izquierda="", derecha="B")),
            (1920, 1080, [fuente], disenos.Diseno(
                clase="pantalla_completa", principal="NoExiste")),
            (1920, 1080, [fuente, otra], disenos.Diseno(
                clase="imagen_en_imagen", principal="A", secundaria="B",
                esquina="centro")),
            (1920, 1080, [fuente, otra], disenos.Diseno(
                clase="imagen_en_imagen", principal="A", secundaria="B",
                tamano="enorme")),
            (0, 1080, [fuente], disenos.Diseno(
                clase="pantalla_completa", principal="A")),
            (1920, -1, [fuente], disenos.Diseno(
                clase="pantalla_completa", principal="A")),
        ]
        for caso in casos:
            with self.subTest(caso=caso):
                with self.assertRaises(ValueError):
                    disenos.calcular(*caso)

    def test_propiedades_de_todas_las_combinaciones(self):
        lienzos = [(1920, 1080), (1280, 720), (1080, 1920)]
        origenes = [(1280, 720), (640, 480), (720, 1280)]
        for lienzo_ancho, lienzo_alto in lienzos:
            for origen in origenes:
                for clase in disenos.CLASES:
                    for esquina in disenos.ESQUINAS:
                        for tamano in disenos.TAMANOS:
                            for proporcion in disenos.PROPORCIONES:
                                for chat in disenos.CHATS:
                                    for modo in ("", "ajustar", "llenar"):
                                        self._comprobar_combinacion(
                                            lienzo_ancho, lienzo_alto, origen,
                                            clase, esquina, tamano,
                                            proporcion, chat, modo)

    def _comprobar_combinacion(self, lienzo_ancho, lienzo_alto, origen,
                               clase, esquina, tamano, proporcion, chat, modo):
        ancho_origen, alto_origen = origen
        fuentes = [
            disenos.Fuente("Principal", "camara", ancho_origen, alto_origen),
            disenos.Fuente("Secundaria", "otra", ancho_origen, alto_origen),
            disenos.Fuente("Izquierda", "camara", ancho_origen, alto_origen),
            disenos.Fuente("Derecha", "otra", ancho_origen, alto_origen),
            disenos.Fuente("Chat", "chat", 460, 620),
        ]
        modos = {}
        if modo:
            modos = {fuente.nombre: modo for fuente in fuentes[:4]}
        diseno = disenos.Diseno(
            clase=clase, principal="Principal", secundaria="Secundaria",
            izquierda="Izquierda", derecha="Derecha", esquina=esquina,
            tamano=tamano, proporcion=proporcion, chat=chat,
            esquina_chat=esquina, modos=modos)
        resultados = disenos.calcular(
            lienzo_ancho, lienzo_alto, fuentes, diseno)
        for resultado in resultados:
            if resultado["nombre"] == "Chat":
                if chat == "franja":
                    self.assertLessEqual(
                        resultado["positionX"] + resultado["ancho"],
                        lienzo_ancho)
                    self.assertLessEqual(
                        resultado["positionY"] + resultado["alto"],
                        lienzo_alto)
                continue
            self.assertGreaterEqual(resultado["positionX"], 0)
            self.assertGreaterEqual(resultado["positionY"], 0)
            self.assertLessEqual(
                resultado["positionX"] + resultado["boundsWidth"],
                lienzo_ancho)
            self.assertLessEqual(
                resultado["positionY"] + resultado["boundsHeight"],
                lienzo_alto)
            for clave in ("cropLeft", "cropRight", "cropTop", "cropBottom"):
                self.assertGreaterEqual(resultado[clave], 0)
            if resultado["estado"] == disenos.ESTADO_LLENA:
                restante_ancho = (
                    ancho_origen - resultado["cropLeft"]
                    - resultado["cropRight"])
                restante_alto = (
                    alto_origen - resultado["cropTop"]
                    - resultado["cropBottom"])
                proporcion_lugar = (resultado["boundsWidth"]
                                    / resultado["boundsHeight"])
                self.assertLessEqual(
                    abs(restante_ancho - restante_alto * proporcion_lugar), 1)
            else:
                self.assertEqual(
                    (resultado["cropLeft"], resultado["cropRight"],
                     resultado["cropTop"], resultado["cropBottom"]),
                    (0, 0, 0, 0))
        if clase == "dividida":
            por_nombre = {resultado["nombre"]: resultado
                          for resultado in resultados}
            izquierda = por_nombre["Izquierda"]
            derecha = por_nombre["Derecha"]
            if lienzo_alto > lienzo_ancho:
                self.assertLessEqual(
                    izquierda["positionY"] + izquierda["boundsHeight"],
                    derecha["positionY"])
            else:
                self.assertLessEqual(
                    izquierda["positionX"] + izquierda["boundsWidth"],
                    derecha["positionX"])


if __name__ == "__main__":
    unittest.main()
