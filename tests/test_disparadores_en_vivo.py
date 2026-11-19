# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La unión entre los disparadores del directo y la tarjeta del vídeo."""

import os
import tempfile
import unittest
from unittest import mock

from guyrapu.core import paths
from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.interaction import (
    disparadores_guardados, filtro_publico, medios_guardados)
from guyrapu.ui import disparadores_en_vivo
from guyrapu.ui.lista_chat import MensajeChat
from tests.rutas_temporales import redirigir_rutas


def _datos(nombre="risa", cuando="comando", comandos=("risa",), evento="",
           minimo=None, medio="", tarjeta="Ríe {usuario}", estilo="clasico",
           segundos=8, permiso="todos", nombres=(), espera_general=5.0,
           espera_persona=0.0, activo=True, atajo=0):
    return {
        "nombre": nombre, "cuando": cuando, "comandos": list(comandos),
        "evento": evento, "minimo": minimo, "medio": medio,
        "tarjeta": tarjeta, "estilo": estilo, "segundos": segundos,
        "permiso": permiso, "nombres": list(nombres),
        "espera_general": espera_general, "espera_persona": espera_persona,
        "activo": activo, "atajo": atajo,
    }


def _medio(nombre="fuegos", tipo="video", archivo="fuegos.mp4", duracion=12,
           ganancia_db=None):
    return {"nombre": nombre, "tipo": tipo, "archivo": archivo,
            "duracion": duracion, "ganancia_db": ganancia_db}


def _registro(texto="!risa", autor="Ana", plataforma="youtube",
              tipo=TIPO_TEXTO, monto=""):
    return MensajeChat(plataforma=plataforma, autor=autor,
                       identificador="C1", texto=texto, hora="12:00",
                       tipo=tipo, monto=monto, rol="")


class _Frame:
    def __init__(self, conectado=True):
        self._conectado = conectado
        self._capa_video = mock.Mock()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        self.ahora = 0.0
        self.frame = _Frame()

    def _guardar(self, *disparadores):
        disparadores_guardados.guardar(paths.disparadores(),
                                       list(disparadores))

    def _guardar_palabras(self, palabras):
        filtro_publico.guardar(paths.palabras_bloqueadas(), palabras)

    def _guardar_medios(self, *medios):
        medios_guardados.guardar(paths.medios(), list(medios))
        carpeta = paths.carpeta_medios()
        carpeta.mkdir(parents=True, exist_ok=True)
        for medio in medios:
            (carpeta / medio["archivo"]).write_bytes(b"x")

    def _adelantar(self, ruta):
        futuro = ruta.stat().st_mtime + 10
        os.utime(ruta, (futuro, futuro))

    def _atender(self, registro=None, ahora=None):
        disparadores_en_vivo.atender(
            self.frame, registro or _registro(),
            self.ahora if ahora is None else ahora)

    def _textos(self):
        return [llamada.args[0].texto for llamada in
                self.frame._capa_video.agregar_pieza.call_args_list]


class TestPiezaDeDisparador(Base):

    def test_un_comando_cumplido_agrega_su_tarjeta_con_estilo_segundos_y_nombre(self):
        self._guardar(_datos(nombre="risa", tarjeta="Ríe {usuario}",
                             estilo="banda", segundos=12))
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_called_once()
        pieza = self.frame._capa_video.agregar_pieza.call_args.args[0]
        self.assertEqual((pieza.tipo, pieza.texto, pieza.segundos),
                         ("disparador", "Ríe Ana", 12))
        self.assertEqual(pieza.datos,
                         {"estilo": "banda", "nombre": "risa"})

    def test_repetido_antes_de_la_espera_general_no_agrega_otra(self):
        self._guardar(_datos(espera_general=5, espera_persona=0))
        self._atender(ahora=0)
        self._atender(ahora=3)
        self.frame._capa_video.agregar_pieza.assert_called_once()
        self._atender(ahora=5)
        self.assertEqual(
            self.frame._capa_video.agregar_pieza.call_count, 2)


class TestContador(Base):

    def test_p5_dos_veces_el_mismo_disparador_ponen_uno_y_dos(self):
        self._guardar(_datos(tarjeta="Va {contador}", espera_general=0,
                             espera_persona=0))
        self._atender(ahora=0)
        self._atender(ahora=1)
        self.assertEqual(self._textos(), ["Va 1", "Va 2"])


class TestEventoDelDirecto(Base):

    def test_el_superchat_solo_cumple_desde_el_minimo(self):
        self._guardar(_datos(
            nombre="regalo", cuando="evento", comandos=(),
            evento="superchat", minimo=5, tarjeta="Gracias",
            espera_general=0, espera_persona=0))
        self._atender(_registro(texto="", tipo=TIPO_SUPERCHAT,
                                monto="US$4.99"), ahora=0)
        self.frame._capa_video.agregar_pieza.assert_not_called()
        self._atender(_registro(texto="", tipo=TIPO_SUPERCHAT,
                                monto="US$5.00"), ahora=1)
        self.frame._capa_video.agregar_pieza.assert_called_once()

    def test_p3_un_regalo_de_tiktok_pone_el_regalo_y_la_cantidad(self):
        self._guardar(_datos(
            nombre="regalo", cuando="evento", comandos=(),
            evento="superchat", tarjeta="{regalo}: {cantidad}",
            espera_general=0, espera_persona=0))
        self._atender(_registro(
            texto="Rosa x5", tipo=TIPO_SUPERCHAT,
            monto="500 diamantes", plataforma="tiktok"), ahora=0)
        self.assertEqual(self._textos(), ["Rosa: 500 diamantes"])


class TestUsuario(Base):

    def test_el_usuario_sale_con_las_palabras_bloqueadas_tapadas(self):
        self._guardar(_datos(tarjeta="Hola {usuario}", espera_general=0,
                             espera_persona=0))
        self._guardar_palabras(["tonto"])
        self._atender(_registro(autor="Tonto"))
        self.assertEqual(self._textos(), ["Hola ***"])


class TestPiezaConMedio(Base):

    def _pieza(self):
        self.frame._capa_video.agregar_pieza.assert_called_once()
        return self.frame._capa_video.agregar_pieza.call_args.args[0]

    def test_p1_un_medio_solo_agrega_la_pieza_con_su_ruta_tipo_y_duracion(self):
        self._guardar_medios(_medio())
        self._guardar(_datos(tarjeta="", medio="fuegos", espera_general=0,
                             espera_persona=0))
        self._atender()
        pieza = self._pieza()
        self.assertEqual((pieza.tipo, pieza.texto), ("disparador", ""))
        self.assertEqual(pieza.datos["medio"], {
            "ruta": str(paths.carpeta_medios() / "fuegos.mp4"),
            "tipo": "video", "duracion": 12, "ganancia_db": None})

    def test_p1_el_medio_lleva_su_ganancia_guardada(self):
        self._guardar_medios(_medio(ganancia_db=-6.0))
        self._guardar(_datos(tarjeta="", medio="fuegos", espera_general=0,
                             espera_persona=0))
        self._atender()
        self.assertEqual(self._pieza().datos["medio"]["ganancia_db"], -6.0)

    def test_p1_un_medio_sin_ganancia_lleva_none(self):
        self._guardar_medios(_medio())
        self._guardar(_datos(tarjeta="", medio="fuegos", espera_general=0,
                             espera_persona=0))
        self._atender()
        self.assertIsNone(self._pieza().datos["medio"]["ganancia_db"])

    def test_p1_con_tarjeta_la_misma_pieza_lleva_el_medio_y_el_texto(self):
        self._guardar_medios(_medio(tipo="imagen", archivo="fuegos.gif",
                                    duracion=0))
        self._guardar(_datos(tarjeta="Ríe {usuario}", medio="fuegos",
                             espera_general=0, espera_persona=0))
        self._atender()
        pieza = self._pieza()
        self.assertEqual(pieza.texto, "Ríe Ana")
        self.assertEqual(pieza.datos["medio"]["tipo"], "imagen")
        self.assertEqual(pieza.datos["medio"]["ruta"],
                         str(paths.carpeta_medios() / "fuegos.gif"))

    def test_p1_sin_tarjeta_ni_medio_en_la_biblioteca_no_agrega(self):
        self._guardar(_datos(tarjeta="", medio="fuegos", espera_general=0,
                             espera_persona=0))
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_not_called()


class TestSegundosDeLaPieza(Base):

    def _segundos(self, tipo, duracion, segundos=8):
        self._guardar_medios(_medio(tipo=tipo, archivo="x.mp4",
                                    duracion=duracion))
        self._guardar(_datos(tarjeta="", medio="fuegos", segundos=segundos,
                             espera_general=0, espera_persona=0))
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_called_once()
        return self.frame._capa_video.agregar_pieza.call_args.args[0].segundos

    def test_p2_un_video_dura_lo_que_su_archivo(self):
        self.assertEqual(self._segundos("video", 12), 12)

    def test_p2_un_sonido_dura_lo_que_su_archivo(self):
        self.assertEqual(self._segundos("sonido", 4), 4)

    def test_p2_un_sonido_sin_duracion_usa_los_segundos_del_disparador(self):
        self.assertEqual(self._segundos("sonido", 0), 8)

    def test_p2_una_imagen_usa_los_segundos_del_disparador(self):
        self.assertEqual(self._segundos("imagen", 20), 8)


class TestMedioQueYaNoEsta(Base):

    def test_p6_con_tarjeta_sale_solo_la_tarjeta_sin_medio(self):
        self._guardar_medios(_medio(nombre="otro", archivo="otro.mp4"))
        self._guardar(_datos(tarjeta="Ríe", medio="fuegos", espera_general=0,
                             espera_persona=0))
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_called_once()
        pieza = self.frame._capa_video.agregar_pieza.call_args.args[0]
        self.assertEqual(pieza.texto, "Ríe")
        self.assertNotIn("medio", pieza.datos)

    def test_p6_sin_tarjeta_no_sale(self):
        self._guardar_medios(_medio(nombre="otro", archivo="otro.mp4"))
        self._guardar(_datos(tarjeta="", medio="fuegos", espera_general=0,
                             espera_persona=0))
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_not_called()


class TestSinTarjeta(Base):

    def test_sin_tarjeta_no_agrega_pero_su_uso_cuenta_para_la_espera(self):
        self._guardar(_datos(tarjeta="", medio="fuegos", espera_general=5))
        self._atender(ahora=0)
        self.frame._capa_video.agregar_pieza.assert_not_called()
        self._guardar(_datos(tarjeta="Ríe", medio="fuegos",
                             espera_general=5))
        self._adelantar(paths.disparadores())
        self._atender(ahora=3)
        self.frame._capa_video.agregar_pieza.assert_not_called()
        self._atender(ahora=5)
        self.frame._capa_video.agregar_pieza.assert_called_once()


class TestRecarga(Base):

    def test_cambiar_el_archivo_entre_dos_mensajes_cambia_lo_que_se_agrega(self):
        self._guardar(_datos(tarjeta="Uno", espera_general=0,
                             espera_persona=0))
        self._atender(ahora=0)
        self._guardar(_datos(tarjeta="Dos", espera_general=0,
                             espera_persona=0))
        self._adelantar(paths.disparadores())
        self._atender(ahora=1)
        self.assertEqual(self._textos(), ["Uno", "Dos"])

    def test_cambiar_las_palabras_entre_dos_mensajes_cambia_la_tarjeta(self):
        self._guardar(_datos(tarjeta="Hola {usuario}", espera_general=0,
                             espera_persona=0))
        self._guardar_palabras(["tonto"])
        self._atender(_registro(autor="Tonto"), ahora=0)
        self._guardar_palabras([])
        self._adelantar(paths.palabras_bloqueadas())
        self._atender(_registro(autor="Tonto"), ahora=1)
        self.assertEqual(self._textos(), ["Hola ***", "Hola Tonto"])


class TestAtajoGlobal(Base):

    def _disparar(self, numero, ahora=None):
        disparadores_en_vivo.disparar(self.frame, numero, ahora)

    def test_p2_dispara_los_activos_con_ese_numero_en_el_orden_de_la_lista(
            self):
        self._guardar(
            _datos(nombre="uno", cuando="atajo", comandos=(), atajo=3,
                   tarjeta="Uno", permiso="moderadores"),
            _datos(nombre="dos", cuando="atajo", comandos=(), atajo=4,
                   tarjeta="Dos"),
            _datos(nombre="tres", cuando="atajo", comandos=(), atajo=3,
                   tarjeta="Tres"),
            _datos(nombre="pausado", cuando="atajo", comandos=(), atajo=3,
                   tarjeta="Pausado", activo=False))
        self._disparar(3, ahora=0)
        self.assertEqual(self._textos(), ["Uno", "Tres"])

    def test_p2_dos_veces_seguidas_con_espera_general_las_dos_disparan(self):
        self._guardar(_datos(
            nombre="risa", cuando="atajo", comandos=(), atajo=1,
            tarjeta="Ríe", espera_general=5, espera_persona=0))
        self._disparar(1, ahora=10)
        self._disparar(1, ahora=11)
        self.assertEqual(self._textos(), ["Ríe", "Ríe"])

    def test_p3_sin_disparador_con_ese_numero_avisa_con_el_sonido_de_error(
            self):
        self._guardar(_datos(
            nombre="risa", cuando="atajo", comandos=(), atajo=1))
        with mock.patch.object(
                disparadores_en_vivo, "anunciar_con_sonido") as avisar:
            self._disparar(2, ahora=0)
        avisar.assert_called_once_with(
            "Ningún disparador usa Ctrl+Alt+Mayús+2", "error")
        self.frame._capa_video.agregar_pieza.assert_not_called()

    def test_p3_sin_directo_conectado_avisa_y_no_hace_nada_mas(self):
        self._guardar(_datos(
            nombre="risa", cuando="atajo", comandos=(), atajo=1,
            tarjeta="Ríe"))
        self.frame._conectado = False
        with mock.patch.object(
                disparadores_en_vivo, "anunciar_con_sonido") as avisar:
            self._disparar(1, ahora=0)
        avisar.assert_called_once_with(
            "Conecta un directo para usar los disparadores", "error")
        self.frame._capa_video.agregar_pieza.assert_not_called()


class TestDesconectado(Base):

    def test_sin_chat_conectado_no_agrega_nada(self):
        self._guardar(_datos())
        self.frame._conectado = False
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_not_called()


if __name__ == "__main__":
    unittest.main()
