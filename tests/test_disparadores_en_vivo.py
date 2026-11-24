# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La unión entre los disparadores de evento y la tarjeta del vídeo."""

import os
import tempfile
import unittest
from unittest import mock

from guyrapu.core import paths
from guyrapu.core.config import TIPO_MIEMBRO, TIPO_SUPERCHAT
from guyrapu.interaction import (
    disparadores_guardados, filtro_publico, informe_ensayo, medios_guardados)
from guyrapu.ui import comandos_en_vivo, disparadores_en_vivo, gui_envio_chat
from guyrapu.ui.lista_chat import MensajeChat
from tests.rutas_temporales import redirigir_rutas


def _datos(nombre="regalo", medio="", tarjeta="Ríe {usuario}",
             estilo="clasico", segundos=8, permiso="todos", nombres=(),
             espera_general=5.0, espera_persona=0.0, activo=True,
             evento="superchat", minimo=None, regalo="", destino="video",
             avisar=True):
    return {
        "nombre": nombre, "cuando": "evento", "evento": evento,
        "minimo": minimo, "regalo": regalo, "medio": medio,
        "destino": destino, "tarjeta": tarjeta, "estilo": estilo,
        "segundos": segundos,
        "permiso": permiso, "nombres": list(nombres),
        "espera_general": espera_general, "espera_persona": espera_persona,
        "activo": activo, "avisar": avisar,
    }


def _medio(nombre="fuegos", tipo="video", archivo="fuegos.mp4", duracion=12,
           ganancia_db=None):
    return {"nombre": nombre, "tipo": tipo, "archivo": archivo,
            "duracion": duracion, "ganancia_db": ganancia_db}


def _registro(texto="", autor="Ana", plataforma="youtube",
              tipo=TIPO_SUPERCHAT, monto="US$5.00"):
    return MensajeChat(plataforma=plataforma, autor=autor,
                       identificador="C1", texto=texto, hora="12:00",
                       tipo=tipo, monto=monto, rol="")


class _Frame:
    def __init__(self, conectado=True):
        self._conectado = conectado
        self._capa_video = mock.Mock()
        self.sesion = mock.Mock(
            chat_propio=True, conexion_propia=True, es_tiktok=False,
            live_chat_id="C1")
        self._sesion_api_disponible = mock.Mock(return_value=True)


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

    def test_un_evento_cumplido_agrega_su_tarjeta_con_estilo_segundos_y_nombre(
            self):
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


class TestAvisoEnElVideo(Base):

    def setUp(self):
        super().setUp()
        self.frame._avisar = mock.Mock()
        parche = mock.patch.object(
            disparadores_en_vivo, "anunciar_con_sonido", self.frame._avisar)
        parche.start()
        self.addCleanup(parche.stop)

    def test_la_alerta_en_el_video_anuncia_su_nombre_y_su_autor(self):
        self._guardar(_datos(nombre="Regalo grande"))
        self._atender(_registro(autor="Ana"))
        self.assertEqual(self.frame._avisar.call_args.args, (
            "Alerta Regalo grande en el vídeo, de Ana.", "alerta_en_video"))

    def test_la_alerta_que_va_solo_al_chat_no_anuncia(self):
        with mock.patch.object(gui_envio_chat, "enviar_respuesta_chat"):
            self._guardar(_datos(nombre="Gracias", destino="chat"))
            self._atender()
        self.frame._avisar.assert_not_called()

    def test_con_avisar_apagado_sigue_yendo_al_video_pero_no_anuncia(self):
        self._guardar(_datos(nombre="Regalo grande", avisar=False))
        self._atender()
        self.frame._avisar.assert_not_called()
        self.frame._capa_video.agregar_pieza.assert_called_once()

    def test_en_ensayo_tambien_anuncia_la_alerta(self):
        self.frame._conectado = False
        self.frame._ensayo = True
        self._guardar(_datos(nombre="Regalo grande"))
        self._atender()
        self.assertEqual(self.frame._avisar.call_args.args[1],
                         "alerta_en_video")


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
            nombre="regalo", minimo=5, tarjeta="Gracias",
            espera_general=0, espera_persona=0))
        self._atender(_registro(monto="US$4.99"), ahora=0)
        self.frame._capa_video.agregar_pieza.assert_not_called()
        self._atender(_registro(monto="US$5.00"), ahora=1)
        self.frame._capa_video.agregar_pieza.assert_called_once()

    def test_p3_un_regalo_de_tiktok_pone_el_regalo_y_la_cantidad(self):
        self._guardar(_datos(
            nombre="regalo", regalo="Rosa", tarjeta="{regalo}: {cantidad}",
            espera_general=0, espera_persona=0))
        self._atender(_registro(
            texto="Rosa x5", monto="500 diamantes", plataforma="tiktok"),
            ahora=0)
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
            "tipo": "video", "duracion": 12, "ganancia_db": None,
            "volumen": 100})

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

    def test_cambiar_el_archivo_entre_dos_eventos_cambia_lo_que_se_agrega(self):
        self._guardar(_datos(tarjeta="Uno", espera_general=0,
                             espera_persona=0))
        self._atender(ahora=0)
        self._guardar(_datos(tarjeta="Dos", espera_general=0,
                             espera_persona=0))
        self._adelantar(paths.disparadores())
        self._atender(ahora=1)
        self.assertEqual(self._textos(), ["Uno", "Dos"])

    def test_cambiar_las_palabras_entre_dos_eventos_cambia_la_tarjeta(self):
        self._guardar(_datos(tarjeta="Hola {usuario}", espera_general=0,
                             espera_persona=0))
        self._guardar_palabras(["tonto"])
        self._atender(_registro(autor="Tonto"), ahora=0)
        self._guardar_palabras([])
        self._adelantar(paths.palabras_bloqueadas())
        self._atender(_registro(autor="Tonto"), ahora=1)
        self.assertEqual(self._textos(), ["Hola ***", "Hola Tonto"])


class TestDesconectado(Base):

    def test_sin_chat_conectado_no_agrega_nada(self):
        self._guardar(_datos())
        self.frame._conectado = False
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_not_called()


class TestEnsayo(Base):
    """El disparador del ensayo pone su tarjeta sin un directo conectado."""

    def setUp(self):
        super().setUp()
        self.frame._conectado = False
        self.frame._ensayo = True

    def test_el_disparador_en_ensayo_pone_su_tarjeta(self):
        self._guardar(_datos())
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_called_once()

    def test_sin_ensayo_ni_conexion_no_pone_tarjeta(self):
        self.frame._ensayo = False
        self._guardar(_datos())
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_not_called()

    def test_la_alerta_se_anota_en_el_informe(self):
        self._guardar(_datos(nombre="Regalo grande"))
        self.frame._informe_ensayo = informe_ensayo.InformeEnsayo()
        self._atender()
        self.assertEqual(self.frame._informe_ensayo.texto(),
                         "Respondió la alerta Regalo grande.")

    def test_sin_alerta_anota_el_motivo_del_evento(self):
        self.frame._informe_ensayo = informe_ensayo.InformeEnsayo()
        self._atender()
        self.assertEqual(
            self.frame._informe_ensayo.texto("ninguna alerta usa ese evento."),
            "Nada respondió: ninguna alerta usa ese evento.")


class TestAlertaAlChat(Base):
    """La alerta con «Mostrar en» chat reparte como el comando."""

    def setUp(self):
        super().setUp()
        cuota = mock.patch.object(comandos_en_vivo, "_cuota_baja",
                                  return_value=False)
        cuota.start()
        self.addCleanup(cuota.stop)
        enviar = mock.patch.object(gui_envio_chat, "enviar_respuesta_chat")
        self.enviar = enviar.start()
        self.addCleanup(enviar.stop)

    def _alerta(self, **cambios):
        datos = {"nombre": "gracias", "destino": "chat",
                 "tarjeta": "Gracias {usuario}", "espera_general": 0,
                 "espera_persona": 0}
        datos.update(cambios)
        self._guardar(_datos(**datos))

    def test_p2_con_chat_disponible_escribe_el_texto_con_las_variables(self):
        self._alerta()
        self._atender(ahora=0)
        self.enviar.assert_called_once_with(self.frame, "Gracias Ana")
        self.frame._capa_video.agregar_pieza.assert_not_called()

    def test_p2_sin_chat_disponible_lo_muestra_en_el_video(self):
        self._alerta()
        self.frame.sesion.es_tiktok = True
        self._atender(ahora=0)
        self.enviar.assert_not_called()
        self.assertEqual(self._textos(), ["Gracias Ana"])

    def test_p2_con_la_cuota_baja_lo_muestra_en_el_video(self):
        self._alerta()
        with mock.patch.object(comandos_en_vivo, "_cuota_baja",
                               return_value=True):
            self._atender(ahora=0)
        self.enviar.assert_not_called()
        self.assertEqual(self._textos(), ["Gracias Ana"])

    def test_p2_dos_alertas_al_chat_con_menos_de_treinta_segundos(self):
        self._guardar(
            _datos(nombre="uno", destino="chat", tarjeta="Uno {contador}",
                   espera_general=0, evento="superchat"),
            _datos(nombre="dos", destino="chat", tarjeta="Dos {contador}",
                   espera_general=0, evento="miembro"))
        self._atender(ahora=0)
        self._atender(_registro(tipo=TIPO_MIEMBRO), ahora=10)
        self.enviar.assert_called_once_with(self.frame, "Uno 1")
        self.assertEqual(self._textos(), ["Dos 1"])

    def test_p7_en_ensayo_no_escribe_en_el_chat_real(self):
        self._alerta()
        self.frame._conectado = False
        self.frame._ensayo = True
        self._atender(ahora=0)
        self.enviar.assert_not_called()
        self.assertEqual(self._textos(), ["Gracias Ana"])


if __name__ == "__main__":
    unittest.main()
