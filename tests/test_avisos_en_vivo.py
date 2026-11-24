# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuándo se avisa del avance de una encuesta o una meta en vivo."""

import unittest

from guyrapu.interaction import avisos_en_vivo


OPCIONES = ("Sí", "No", "Tal vez")


def _aviso(estado, votos, restante=60, ahora=0, opciones=OPCIONES):
    return estado.aviso(votos, opciones, restante, ahora)


def _frase(aviso):
    return None if aviso is None else aviso.frase


class TestEncuestaPorTerminar(unittest.TestCase):

    def test_a_diez_segundos_anuncia_una_sola_vez(self):
        estado = avisos_en_vivo.EstadoEncuesta()
        avisos = [_aviso(estado, [0, 0, 0], restante, indice)
                  for indice, restante in enumerate(
                      (20, 11, 10, 9, 10, 5))]
        self.assertEqual([_frase(aviso) for aviso in avisos], [
            None, None, "Quedan 10 segundos de la encuesta.",
            None, None, None])
        self.assertEqual(avisos[2].clave, "encuesta_por_terminar")

    def test_sin_tiempo_no_anuncia(self):
        estado = avisos_en_vivo.EstadoEncuesta()
        self.assertIsNone(_aviso(estado, [0, 0, 0], None, 0))

    def test_antes_de_los_diez_no_anuncia(self):
        estado = avisos_en_vivo.EstadoEncuesta()
        self.assertIsNone(_aviso(estado, [0, 0, 0], 11, 0))


class TestGanador(unittest.TestCase):

    def test_un_ganador_unico_anuncia_su_opcion_y_sus_votos(self):
        estado = avisos_en_vivo.EstadoEncuesta()
        aviso = _aviso(estado, [2, 1, 0], 60, 0)
        self.assertEqual(aviso.frase, "Va ganando Sí, con 2 votos.")
        self.assertEqual(aviso.clave, "encuesta_ganadora")

    def test_un_empate_no_se_anuncia(self):
        estado = avisos_en_vivo.EstadoEncuesta()
        self.assertIsNone(_aviso(estado, [2, 2, 0], 60, 0))
        self.assertIsNone(_aviso(estado, [0, 0, 0], 60, 1))

    def test_el_mismo_ganador_no_se_anuncia_dos_veces(self):
        estado = avisos_en_vivo.EstadoEncuesta()
        self.assertIsNotNone(_aviso(estado, [2, 1, 0], 60, 0))
        self.assertIsNone(_aviso(estado, [3, 1, 0], 60, 20))
        self.assertIsNone(_aviso(estado, [4, 1, 0], 60, 40))

    def test_la_espera_termina_con_el_ganador_vigente(self):
        estado = avisos_en_vivo.EstadoEncuesta()
        self.assertEqual(
            _frase(_aviso(estado, [2, 0, 0], 60, 0)),
            "Va ganando Sí, con 2 votos.")
        self.assertIsNone(_aviso(estado, [0, 1, 0], 55, 5))
        self.assertIsNone(_aviso(estado, [0, 1, 0], 46, 14))
        self.assertEqual(
            _frase(_aviso(estado, [0, 3, 0], 45, 15)),
            "Va ganando No, con 3 votos.")

    def test_si_el_ganador_vuelve_al_ultimo_anunciado_no_dice_nada(self):
        estado = avisos_en_vivo.EstadoEncuesta()
        self.assertIsNotNone(_aviso(estado, [2, 0, 0], 60, 0))
        self.assertIsNone(_aviso(estado, [0, 1, 0], 55, 5))
        self.assertIsNone(_aviso(estado, [2, 1, 0], 40, 20))

    def test_en_los_ultimos_diez_segundos_no_anuncia_ganador(self):
        estado = avisos_en_vivo.EstadoEncuesta()
        primero = _aviso(estado, [2, 0, 0], 10, 0)
        self.assertEqual(primero.clave, "encuesta_por_terminar")
        self.assertIsNone(_aviso(estado, [3, 0, 0], 9, 1))
        self.assertIsNone(_aviso(estado, [3, 0, 0], 8, 2))


class TestMeta(unittest.TestCase):

    def test_al_pasar_la_mitad_anuncia(self):
        dichos = set()
        self.assertEqual(
            avisos_en_vivo.aviso_meta("Risa", 0, 60, 100, dichos),
            "Meta Risa: a la mitad, 60 de 100.")

    def test_llegar_a_la_mitad_anuncia_con_el_valor_exacto(self):
        dichos = set()
        self.assertEqual(
            avisos_en_vivo.aviso_meta("Risa", 4, 5, 10, dichos),
            "Meta Risa: a la mitad, 5 de 10.")

    def test_llegar_al_noventa_anuncia_cerca_con_el_valor_exacto(self):
        dichos = set()
        self.assertEqual(
            avisos_en_vivo.aviso_meta("Risa", 8, 9, 10, dichos),
            "Meta Risa: cerca del objetivo, 9 de 10.")

    def test_al_pasar_el_noventa_anuncia_cerca_del_objetivo(self):
        dichos = set()
        self.assertEqual(
            avisos_en_vivo.aviso_meta("Risa", 60, 91, 100, dichos),
            "Meta Risa: cerca del objetivo, 91 de 100.")

    def test_un_salto_que_cruza_los_dos_dice_solo_el_de_noventa(self):
        dichos = set()
        frase = avisos_en_vivo.aviso_meta("Risa", 10, 95, 100, dichos)
        self.assertEqual(frase,
                         "Meta Risa: cerca del objetivo, 95 de 100.")
        self.assertIsNone(
            avisos_en_vivo.aviso_meta("Risa", 95, 96, 100, dichos))

    def test_un_salto_al_cien_no_dice_ninguno_de_los_dos(self):
        dichos = set()
        self.assertIsNone(
            avisos_en_vivo.aviso_meta("Risa", 40, 100, 100, dichos))
        self.assertIsNone(
            avisos_en_vivo.aviso_meta("Risa", 100, 120, 100, dichos))

    def test_cada_umbral_una_sola_vez(self):
        dichos = set()
        frases = [avisos_en_vivo.aviso_meta("Risa", anterior, nuevo,
                                            100, dichos)
                  for anterior, nuevo in ((0, 60), (60, 70), (70, 92),
                                          (92, 95))]
        self.assertEqual(frases, [
            "Meta Risa: a la mitad, 60 de 100.",
            None,
            "Meta Risa: cerca del objetivo, 92 de 100.",
            None])


class TestPropiedades(unittest.TestCase):
    """Las reglas valen recorriendo secuencias, no en un solo ejemplo."""

    SECUENCIAS = (
        (10, 30, 50, 60, 80, 91, 95, 100),
        (0, 49, 51, 89, 90, 100),
        (60, 70, 100),
        (100, 100),
    )

    def test_un_umbral_nunca_se_dice_dos_veces(self):
        for valores in self.SECUENCIAS:
            with self.subTest(valores=valores):
                dichos = set()
                frases = [avisos_en_vivo.aviso_meta(
                    "Risa", anterior, nuevo, 100, dichos)
                    for anterior, nuevo in zip((0,) + valores, valores)]
                dichas = [frase for frase in frases if frase]
                self.assertLessEqual(
                    sum("a la mitad" in frase for frase in dichas), 1)
                self.assertLessEqual(
                    sum("cerca del objetivo" in frase
                        for frase in dichas), 1)

    def test_nunca_se_dice_un_umbral_mas_bajo_despues_de_uno_mas_alto(self):
        for valores in self.SECUENCIAS:
            with self.subTest(valores=valores):
                dichos = set()
                vio_cerca = False
                for anterior, nuevo in zip((0,) + valores, valores):
                    frase = avisos_en_vivo.aviso_meta(
                        "Risa", anterior, nuevo, 100, dichos)
                    if frase and "cerca del objetivo" in frase:
                        vio_cerca = True
                    self.assertFalse(vio_cerca and frase
                                     and "a la mitad" in frase)

    def test_entre_dos_avisos_de_ganador_pasan_quince_segundos(self):
        secuencias = (
            (((2, 0, 0), 0), ((2, 1, 0), 5), ((3, 1, 0), 14),
             ((3, 5, 0), 15), ((3, 6, 0), 29), ((3, 7, 0), 30)),
            (((1, 0, 0), 3), ((1, 2, 0), 4), ((1, 3, 0), 18),
             ((2, 3, 0), 19), ((4, 3, 0), 40)),
        )
        for pasos in secuencias:
            with self.subTest(pasos=pasos):
                estado = avisos_en_vivo.EstadoEncuesta()
                anunciados = []
                for votos, momento in pasos:
                    aviso = _aviso(estado, votos, 60, momento)
                    if aviso is not None:
                        self.assertEqual(aviso.clave, "encuesta_ganadora")
                        anunciados.append(momento)
                self.assertGreaterEqual(len(anunciados), 2)
                for anterior, posterior in zip(anunciados, anunciados[1:]):
                    self.assertGreaterEqual(posterior - anterior, 15)


if __name__ == "__main__":
    unittest.main()
