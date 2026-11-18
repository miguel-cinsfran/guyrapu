# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del ControladorChat, sin ventana: lista falsa y parches locales."""

import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.core.config import (
    TIPO_ENTRADA, TIPO_ME_GUSTA, TIPO_SUPERCHAT, TIPO_TEXTO,
)
from guyrapu.core.avisos_tiktok import TIPOS_AVISO
from guyrapu.ui import chat_vivo
from guyrapu.translation.proveedores.base import Traduccion
from guyrapu.ui.chat_vivo import ControladorChat
from guyrapu.ui.lista_chat import MensajeChat


def _registro(tipo=TIPO_TEXTO, autor="Ana", texto="hola", monto="",
              plataforma="youtube"):
    return MensajeChat(plataforma=plataforma, autor=autor, identificador="C",
                       texto=texto, hora="12:00", tipo=tipo, monto=monto,
                       rol="")


def _controlador(lista=None, maximo=500, activo=True, filtro="__filtro__",
                 oculto=False, config=None):
    if lista is None:
        lista = mock.Mock()
        lista.GetCount.return_value = 1
    control = ControladorChat(
        lista, maximo,
        activo=(lambda: activo) if isinstance(activo, bool) else activo,
        autor_oculto=lambda autor: oculto,
        formatear=lambda autor, texto, hora, tipo, monto: f"{autor}: {texto}, {hora}",
        al_superchat=mock.Mock(), config=config)
    if filtro != "__filtro__":
        control.filtro = filtro
    return control


class TestRecibidos(unittest.TestCase):
    """Cuentan los de texto de cualquier plataforma, aunque se oculten."""

    def test_cuenta_los_de_texto_aunque_el_filtro_los_oculte(self):
        control = _controlador(filtro=TIPO_SUPERCHAT)
        with mock.patch.object(chat_vivo.wx, "CallLater",
                               return_value=mock.Mock()),                 mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                  return_value=None),                 mock.patch.object(chat_vivo._snd, "reproducir"):
            control.encolar(_registro(plataforma="tiktok"))
            control.encolar(_registro(tipo=TIPO_SUPERCHAT))
            control.volcar()
        self.assertEqual(control.recibidos, 1)

    def test_cuenta_al_autor_oculto_si_es_de_texto(self):
        control = _controlador(oculto=True)
        with mock.patch.object(chat_vivo.wx, "CallLater",
                               return_value=mock.Mock()):
            control.encolar(_registro(texto="tapado"))
            control.encolar(_registro(tipo=TIPO_ME_GUSTA, monto="3"))
            control.volcar()
        self.assertEqual(control.recibidos, 1)


class TestControladorChat(unittest.TestCase):
    def test_encolar_dos_veces_pide_un_solo_temporizador(self):
        control = _controlador()
        with mock.patch.object(chat_vivo.wx, "CallLater",
                               return_value=mock.Mock()) as diferir:
            control.encolar(_registro(texto="uno"))
            control.encolar(_registro(texto="dos"))
        diferir.assert_called_once_with(chat_vivo.MS_VOLCADO_CHAT,
                                        control.volcar)
        control.lista.Append.assert_not_called()
        control.lista.Delete.assert_not_called()
        self.assertEqual(len(control._pendientes), 2)

    def test_volcar_dos_pendientes_congela_y_agrega_dos(self):
        control = _controlador()
        control._pendientes = [_registro(texto="uno"), _registro(texto="dos")]
        with mock.patch.object(chat_vivo._snd, "reproducir"), \
                mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                   return_value=None):
            control.volcar()
        control.lista.Freeze.assert_called_once_with()
        control.lista.Thaw.assert_called_once_with()
        self.assertEqual(control.lista.Append.call_count, 2)

    def test_volcar_un_pendiente_no_congela(self):
        control = _controlador()
        control._pendientes = [_registro(texto="uno")]
        with mock.patch.object(chat_vivo._snd, "reproducir"), \
                mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                   return_value=None):
            control.volcar()
        control.lista.Freeze.assert_not_called()
        control.lista.Thaw.assert_not_called()
        control.lista.Append.assert_called_once()

    def test_volcar_solo_mueve_al_final_sin_foco_en_la_lista(self):
        control = _controlador()
        control._pendientes = [_registro(texto="uno")]
        control.lista.GetCount.return_value = 3
        with mock.patch.object(chat_vivo._snd, "reproducir"), \
                mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                   return_value=mock.Mock()):
            control.volcar()
        control.lista.SetFirstItem.assert_called_once_with(2)
        with mock.patch.object(chat_vivo._snd, "reproducir"), \
                mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                   return_value=control.lista):
            control.lista.SetFirstItem.reset_mock()
            control._pendientes = [_registro(texto="dos")]
            control.volcar()
        control.lista.SetFirstItem.assert_not_called()

    def test_volcar_sin_nada_visible_no_mueve_la_vista(self):
        control = _controlador()
        with mock.patch.object(chat_vivo._snd, "reproducir"), \
                mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                   return_value=None):
            control.volcar()
        control.lista.SetFirstItem.assert_not_called()
        control.lista.Append.assert_not_called()

    def test_volcar_desconectado_tira_la_cola_sin_tocar_la_lista(self):
        control = _controlador(activo=False)
        control._pendientes = [_registro(texto="uno")]
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            control.volcar()
        self.assertEqual(control._pendientes, [])
        control.lista.Append.assert_not_called()
        control.lista.Freeze.assert_not_called()
        reproducir.assert_not_called()

    def test_filtro_de_otro_tipo_no_agrega_pero_suena(self):
        control = _controlador(filtro=TIPO_SUPERCHAT)
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir, \
                mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                   return_value=None):
            control._pendientes = [_registro(tipo=TIPO_TEXTO, texto="hola")]
            control.volcar()
        control.lista.Append.assert_not_called()
        reproducir.assert_called_once()
        self.assertEqual(len(control.modelo.todos), 1)
        self.assertEqual(control.modelo.visibles, [])

    def test_me_gusta_entra_al_modelo_y_a_la_lista(self):
        control = _controlador()
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            visible = control._procesar(
                _registro(tipo=TIPO_ME_GUSTA, monto="3"))
        self.assertTrue(visible)
        reproducir.assert_called_once_with("me_gusta")
        self.assertEqual(len(control.modelo.todos), 1)
        control.lista.Append.assert_called_once()

    def test_dos_me_gusta_seguidos_suenan_una_vez(self):
        control = _controlador()
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir, \
                mock.patch.object(chat_vivo.time, "monotonic",
                                  side_effect=[100.0, 101.0]):
            control._procesar(_registro(tipo=TIPO_ME_GUSTA, monto="3"))
            control._procesar(_registro(tipo=TIPO_ME_GUSTA, monto="5"))
        self.assertEqual(reproducir.call_count, 1)
        self.assertEqual(len(control.modelo.todos), 2)
        self.assertEqual(control.lista.Append.call_count, 2)

    def test_autor_oculto_no_suena_ni_entra(self):
        control = _controlador(oculto=True)
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            visible = control._procesar(_registro(texto="hola"))
        self.assertFalse(visible)
        reproducir.assert_not_called()
        self.assertEqual(control.modelo.todos, [])
        control.lista.Append.assert_not_called()

    def test_al_pasar_el_maximo_borra_la_fila_cero(self):
        control = _controlador(maximo=2)
        with mock.patch.object(chat_vivo._snd, "reproducir"), \
                mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                   return_value=None):
            control._procesar(_registro(texto="uno"))
            control._procesar(_registro(texto="dos"))
            control.lista.Delete.reset_mock()
            control._procesar(_registro(texto="tres"))
        control.lista.Delete.assert_called_once_with(0)
        self.assertEqual(len(control.modelo.todos), 2)

    def test_la_participacion_cuenta_todo_aunque_el_historial_recorte(self):
        control = _controlador(maximo=2)
        with mock.patch.object(chat_vivo._snd, "reproducir"):
            for texto in ("uno", "dos", "tres"):
                control._procesar(_registro(texto=texto))
        self.assertEqual(len(control.modelo.todos), 2)
        self.assertEqual(control.participacion.lineas(), ["Ana: 3 mensajes"])

    def test_autor_oculto_no_suma_a_la_participacion(self):
        control = _controlador(oculto=True)
        with mock.patch.object(chat_vivo._snd, "reproducir"):
            control._procesar(_registro(texto="hola"))
        self.assertTrue(control.participacion.vacia())

    def test_vaciar_limpia_participacion_y_modelo(self):
        control = _controlador()
        with mock.patch.object(chat_vivo._snd, "reproducir"):
            control._procesar(_registro(texto="hola"))
        control._pendientes = [_registro(texto="pendiente")]
        control.vaciar()
        self.assertTrue(control.participacion.vacia())
        self.assertEqual(control.modelo.todos, [])
        self.assertEqual(control._pendientes, [])

    def test_descartar_para_el_temporizador_y_vacia_la_cola(self):
        control = _controlador()
        temporizador = mock.Mock()
        control._timer = temporizador
        control._pendientes = [_registro(texto="uno")]
        control.descartar()
        temporizador.Stop.assert_called_once_with()
        self.assertIsNone(control._timer)
        self.assertEqual(control._pendientes, [])

    def test_reconstruir_vacia_y_repone_solo_lo_visible(self):
        control = _controlador(filtro=TIPO_TEXTO)
        with mock.patch.object(chat_vivo._snd, "reproducir"):
            control._procesar(_registro(tipo=TIPO_TEXTO, texto="visto"))
            control._procesar(_registro(tipo=TIPO_SUPERCHAT, texto="tapado",
                                        monto="$5"))
        control.lista.Append.reset_mock()
        with mock.patch.object(chat_vivo._snd, "reproducir"):
            control.reconstruir()
        control.lista.Clear.assert_called_once_with()
        control.lista.Append.assert_called_once_with("Ana: visto, 12:00")

    def test_evento_en_lista_entra_a_la_lista_sin_sonar(self):
        control = _controlador(config={"evento_entrada": "lista"})
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            visible = control._procesar(_registro(tipo=TIPO_ENTRADA))
        self.assertTrue(visible)
        reproducir.assert_not_called()
        control.lista.Append.assert_called_once()

    def test_evento_en_mostrar_suena(self):
        control = _controlador(config={"evento_entrada": "mostrar"})
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            control._procesar(_registro(tipo=TIPO_ENTRADA))
        reproducir.assert_called_once_with("entrada")

    def test_evento_en_principal_sin_sonido_entra_a_la_lista_sin_sonar(self):
        control = _controlador(config={"evento_entrada": "principal_sin_sonido"})
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            visible = control._procesar(_registro(tipo=TIPO_ENTRADA))
        self.assertTrue(visible)
        reproducir.assert_not_called()
        control.lista.Append.assert_called_once()

    def test_evento_en_secundaria_sin_sonido_entra_a_la_lista_sin_sonar(self):
        for modo in ("secundaria_sin_sonido", "secundaria"):
            with self.subTest(modo=modo):
                control = _controlador(config={"evento_entrada": modo})
                with mock.patch.object(chat_vivo._snd,
                                       "reproducir") as reproducir:
                    visible = control._procesar(_registro(tipo=TIPO_ENTRADA))
                self.assertTrue(visible)
                control.lista.Append.assert_called_once()
                if modo == "secundaria":
                    self.assertEqual(reproducir.call_count, 1)
                else:
                    reproducir.assert_not_called()

    def test_evento_en_principal_sigue_sonando(self):
        control = _controlador(config={"evento_entrada": "principal"})
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            control._procesar(_registro(tipo=TIPO_ENTRADA))
        reproducir.assert_called_once_with("entrada")

    def test_regalo_en_lista_suma_al_total_sin_sonar(self):
        control = _controlador(config={"evento_superchat": "lista"})
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            control._procesar(_registro(tipo=TIPO_SUPERCHAT, monto="$5"))
        reproducir.assert_not_called()
        control._al_superchat.assert_called_once_with("$5")

    def test_un_comando_de_fabrica_entra_a_la_lista_sin_sonar(self):
        control = _controlador(config={})
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            visible = control._procesar(_registro(texto="!1"))
        self.assertTrue(visible)
        reproducir.assert_not_called()
        control.lista.Append.assert_called_once()

    def test_un_mensaje_comun_suena_aunque_el_comando_este_en_la_lista(self):
        control = _controlador(config={})
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            control._procesar(_registro(texto="hola"))
        reproducir.assert_called_once()

    def test_un_comando_en_voz_principal_suena(self):
        control = _controlador(config={"evento_comando": "principal"})
        with mock.patch.object(chat_vivo._snd, "reproducir") as reproducir:
            control._procesar(_registro(texto="!1"))
        reproducir.assert_called_once()

    def test_un_comando_en_desactivado_se_atiende_y_no_entra(self):
        control = _controlador(config={"evento_comando": "ocultar"})
        with mock.patch.object(chat_vivo.wx, "CallLater",
                               return_value=mock.Mock()), \
                mock.patch.object(chat_vivo.comandos_en_vivo,
                                  "atender") as atender, \
                mock.patch.object(chat_vivo._snd,
                                  "reproducir") as reproducir:
            control.encolar(_registro(texto="!1"))
            control.volcar()
        atender.assert_called_once()
        reproducir.assert_not_called()
        control.lista.Append.assert_not_called()
        self.assertEqual(control.modelo.todos, [])

    def test_filtro_avisos_deja_solo_los_avisos_en_la_lista(self):
        control = _controlador(filtro=TIPOS_AVISO)
        with mock.patch.object(chat_vivo._snd, "reproducir"):
            control._procesar(_registro(tipo=TIPO_TEXTO, texto="comun"))
            control._procesar(_registro(tipo=TIPO_ENTRADA, texto="nuevo"))
        control.lista.Append.assert_called_once_with("Ana: nuevo, 12:00")
        self.assertEqual(len(control.modelo.todos), 2)
        self.assertEqual(len(control.modelo.visibles), 1)


class TestComandosDelChat(unittest.TestCase):

    def test_un_fallo_al_atender_los_comandos_no_corta_la_lectura(self):
        control = _controlador()
        with mock.patch.object(chat_vivo.comandos_en_vivo, "atender",
                               side_effect=RuntimeError("x")), \
                mock.patch.object(chat_vivo.logger, "debug") as debug, \
                mock.patch.object(chat_vivo.wx, "CallLater",
                                  return_value=mock.Mock()):
            control.encolar(_registro(texto="!hola"))
        self.assertEqual(len(control._pendientes), 1)
        debug.assert_called_once()


class TestClipDelChat(unittest.TestCase):
    def _control(self, *, activo=True, minutos=1, guardar=None, reloj=None):
        lista = mock.Mock()
        lista.GetCount.return_value = 1
        return ControladorChat(
            lista, 500, activo=lambda: True,
            autor_oculto=lambda autor: False,
            formatear=lambda autor, texto, hora, tipo, monto: texto,
            al_superchat=mock.Mock(),
            ajustes_clip=lambda: SimpleNamespace(
                activo=activo, minutos=minutos),
            guardar_clip=guardar or mock.Mock(),
            reloj=reloj or (lambda: 0.0))

    def _encolar(self, control, texto):
        with mock.patch.object(chat_vivo.wx, "CallLater",
                               return_value=mock.Mock()):
            control.encolar(_registro(texto=texto))

    def test_un_mensaje_clip_pide_guardarlo(self):
        guardar = mock.Mock()
        control = self._control(guardar=guardar)
        self._encolar(control, "!clip")
        guardar.assert_called_once()
        self.assertEqual(guardar.call_args.args[0], "Ana")
        self.assertEqual(len(control._pendientes), 1)

    def test_un_mensaje_normal_no_pide_guardarlo(self):
        guardar = mock.Mock()
        control = self._control(guardar=guardar)
        self._encolar(control, "hola")
        guardar.assert_not_called()

    def test_un_clip_en_desactivado_se_atiende_igual(self):
        guardar = mock.Mock()
        lista = mock.Mock()
        lista.GetCount.return_value = 1
        control = ControladorChat(
            lista, 500, activo=lambda: True,
            autor_oculto=lambda autor: False,
            formatear=lambda autor, texto, hora, tipo, monto: texto,
            al_superchat=mock.Mock(), config={"evento_comando": "ocultar"},
            ajustes_clip=lambda: SimpleNamespace(activo=True, minutos=1),
            guardar_clip=guardar)
        self._encolar(control, "!clip")
        guardar.assert_called_once()
        self.assertEqual(control._pendientes, [])

    def test_otro_clip_durante_la_espera_no_guarda(self):
        ahora = [0.0]
        guardar = mock.Mock()
        control = self._control(guardar=guardar, reloj=lambda: ahora[0])
        self._encolar(control, "!clip")
        al_terminar = guardar.call_args.args[1]
        al_terminar(True)
        ahora[0] = 30.0
        self._encolar(control, "!clip")
        self.assertEqual(guardar.call_count, 1)

    def test_en_el_borde_de_la_espera_vuelve_a_guardar(self):
        ahora = [0.0]
        guardar = mock.Mock()
        control = self._control(guardar=guardar, reloj=lambda: ahora[0])
        self._encolar(control, "!clip")
        guardar.call_args.args[1](True)
        ahora[0] = 60.0
        self._encolar(control, "!clip")
        self.assertEqual(guardar.call_count, 2)

    def test_con_la_opcion_apagada_no_pide_guardarlo(self):
        guardar = mock.Mock()
        control = self._control(activo=False, guardar=guardar)
        self._encolar(control, "!clip")
        guardar.assert_not_called()


class PedidoLista:
    def __init__(self):
        self.destino = "es"
        self.resultado = None
        self._callbacks = []

    def al_terminar(self, funcion):
        self._callbacks.append(funcion)

    def terminar(self, resultado):
        self.resultado = resultado
        for funcion in self._callbacks:
            funcion()


class TestTraduccionEnLaLista(unittest.TestCase):

    def _control(self, **config):
        base = {"traducir_chat": True, "traducir_que": "voz_lista",
                "traducir_idioma_original": "completo",
                "limpiar_emojis": True}
        base.update(config)
        return _controlador(config=base)

    def _encolar(self, control, texto="hola"):
        with mock.patch.object(chat_vivo.traduccion_chat, "traduce_lista",
                               return_value=True), \
                mock.patch.object(chat_vivo.traduccion_chat, "pedir",
                                  return_value=self.pedido), \
                mock.patch.object(chat_vivo.wx, "CallLater",
                                  return_value=mock.Mock()), \
                mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                  return_value=None), \
                mock.patch.object(chat_vivo._snd, "reproducir"):
            control.encolar(_registro(texto=texto))
            control.volcar()

    def _terminar(self, control, resultado):
        with mock.patch.object(chat_vivo.wx, "CallAfter",
                               side_effect=lambda funcion, *args: funcion(*args)):
            self.pedido.terminar(resultado)

    def test_la_fila_sale_con_el_original_y_cambia_al_llegar(self):
        control = self._control()
        self.pedido = PedidoLista()
        self._encolar(control)
        control.lista.Append.assert_called_once_with("Ana: hola, 12:00")
        control.lista.SetString.assert_not_called()
        self._terminar(control, Traduccion("HELLO", "en"))
        control.lista.SetString.assert_called_once_with(
            0, "Ana: HELLO (del inglés), 12:00")

    def test_la_fila_que_cambia_no_mueve_el_foco_ni_la_seleccion(self):
        control = self._control()
        self.pedido = PedidoLista()
        self._encolar(control)
        control.lista.SetFirstItem.reset_mock()
        self._terminar(control, Traduccion("HELLO", "en"))
        control.lista.SetSelection.assert_not_called()
        control.lista.SetFocus.assert_not_called()
        control.lista.SetFirstItem.assert_not_called()

    def test_abreviado_y_no_decirlo(self):
        esperados = {"abreviado": "Ana: HELLO (EN), 12:00",
                     "no": "Ana: HELLO, 12:00"}
        for forma, esperado in esperados.items():
            with self.subTest(forma=forma):
                control = self._control(traducir_idioma_original=forma)
                self.pedido = PedidoLista()
                self._encolar(control)
                self._terminar(control, Traduccion("HELLO", "en"))
                control.lista.SetString.assert_called_once_with(0, esperado)

    def test_un_codigo_desconocido_se_dice_abreviado(self):
        control = self._control()
        self.pedido = PedidoLista()
        self._encolar(control)
        self._terminar(control, Traduccion("HELLO", "xx"))
        control.lista.SetString.assert_called_once_with(
            0, "Ana: HELLO (XX), 12:00")

    def test_si_el_origen_es_el_destino_no_cambia_la_fila(self):
        control = self._control()
        self.pedido = PedidoLista()
        self._encolar(control)
        self._terminar(control, Traduccion("hola", "es"))
        control.lista.SetString.assert_not_called()

    def test_con_solo_voz_la_lista_no_pide_traduccion(self):
        control = self._control(traducir_que="solo_voz")
        self.pedido = PedidoLista()
        with mock.patch.object(chat_vivo.traduccion_chat, "traduce_lista",
                               return_value=False), \
                mock.patch.object(chat_vivo.traduccion_chat, "pedir") as pedir, \
                mock.patch.object(chat_vivo.wx, "CallLater",
                                  return_value=mock.Mock()), \
                mock.patch.object(chat_vivo.wx.Window, "FindFocus",
                                  return_value=None), \
                mock.patch.object(chat_vivo._snd, "reproducir"):
            control.encolar(_registro(texto="hola"))
            control.volcar()
        pedir.assert_not_called()
        control.lista.Append.assert_called_once_with("Ana: hola, 12:00")


if __name__ == "__main__":
    unittest.main()
