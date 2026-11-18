# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Atajos del chat que valen en cualquier programa.

`Ctrl+Mayús+1` a `Ctrl+Mayús+0` leen con el lector los diez últimos mensajes
de la lista del chat: 1 el último, 0 el décimo desde el final. `Ctrl+Mayús`
con las dos teclas a la derecha del cero pasan al filtro anterior o
siguiente. De fábrica valen solo dentro de la app; la casilla de
Preferencias, Lectura, los hace valer en cualquier programa, como los
atajos de música. No lee atributos privados de nadie: la lista se recorre
con `GetCount` y `GetString`.
"""

from __future__ import annotations

import wx

from guyrapu.core import atajos as _atajos_fijos
from guyrapu.core import config, diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.music import anuncios
from guyrapu.ui import atajos_globales
from guyrapu.ui.atajos_globales import combinacion_ctrl_mayus
from guyrapu.ui.lista_chat import texto_reciente
from guyrapu.voice import sound_player as _snd


logger = diagnostico.obtener_logger(__name__)

# Acciones fijas de recientes, en orden: el índice da el id desde BASE_IDS.
ORDEN = (
    "chat_reciente_1",
    "chat_reciente_2",
    "chat_reciente_3",
    "chat_reciente_4",
    "chat_reciente_5",
    "chat_reciente_6",
    "chat_reciente_7",
    "chat_reciente_8",
    "chat_reciente_9",
    "chat_reciente_10",
)

# Filtro anterior y siguiente, en el orden del menú. Van después de los
# recientes para que sus ids no cambien.
ORDEN_FILTRO = (
    "chat_filtro_anterior",
    "chat_filtro_siguiente",
)
ORDEN_GLOBALES = ORDEN + ORDEN_FILTRO

# Base de los ids propios para `RegisterHotKey`, lejos de los de música.
BASE_IDS = 0xB100

TEXTO_ACTIVOS = N_("Mensajes recientes del chat en cualquier aplicación")
TEXTO_SOLO = N_("Mensajes recientes del chat solo en {app}")


class LecturaRecientes:
    """Lee un mensaje reciente por su posición y maneja sus atajos globales.

    `ventana` es el frame, `lista` es `lb_chat` y `config` el dict de
    configuración. `cola` es la cola de la voz; con la preferencia en «voz»
    el mensaje se adelanta ahí en vez de anunciarse. Nunca lanza: registrar
    o soltar puede fallar (otro programa tiene la combinación, la ventana
    se cerró) y se informa con el anuncio de fallo, no con excepciones.
    """

    def __init__(self, ventana, lista, config, cola=None, acciones=None) -> None:
        self._ventana = ventana
        self._lista = lista
        self._config = config
        self._cola = cola
        self._acciones_chat = acciones
        self._acciones = {accion: (lambda n=n: self.leer(n))
                          for n, accion in enumerate(ORDEN, start=1)}
        self._acciones["chat_filtro_anterior"] = (
            lambda: self.cambiar_filtro(-1))
        self._acciones["chat_filtro_siguiente"] = (
            lambda: self.cambiar_filtro(1))
        self._globales = atajos_globales.AtajosGlobales(
            ventana, self._acciones, orden=ORDEN_GLOBALES, base_ids=BASE_IDS,
            traducir=combinacion_ctrl_mayus)
        self._globales_atajos = None
        if bool(config.get("lectura_atajos_globales", False)):
            # Después de que la ventana exista: el registro es del sistema
            # y pide el bucle de eventos.
            try:
                wx.CallAfter(self.activar_arranque)
            except Exception:
                logger.debug("No se pudieron activar los atajos de recientes")

    def leer(self, n: int) -> None:
        """Anuncia el mensaje `n` desde el final de la lista del chat."""
        from guyrapu.ui import gui as _gui
        filas = [self._lista.GetString(i)
                 for i in range(self._lista.GetCount())]
        texto = texto_reciente(filas, n)
        if (self._config.get("lectura_recientes") == "voz"
                and self._cola is not None):
            self._cola.adelantar({"texto_tts": texto, "autor": ""})
        else:
            _gui.anunciar(texto)

    def cambiar_filtro(self, paso: int) -> None:
        """Pasa el filtro del chat al anterior o al siguiente."""
        if self._acciones_chat is not None:
            self._acciones_chat.cambiar_filtro(paso)

    def _textos(self) -> dict:
        """Los atajos efectivos del chat, acción → texto guardado."""
        return {accion: _atajos_fijos.ATAJOS_FIJOS_DEFAULTS[accion]
                for accion in ORDEN_GLOBALES}

    def activar_arranque(self) -> None:
        """Activa los globales al arrancar: calla salvo que algo falle."""
        try:
            textos = self._textos()
            fallidos = self._globales.activar(textos)
        except Exception:
            logger.exception("No se pudieron activar los atajos de recientes")
            return
        self._globales_atajos = textos
        if fallidos:
            self._avisar(anuncios.aviso_atajos_globales_fallo(fallidos))

    def aplicar_preferencias(self) -> None:
        """Activa o desactiva los globales según la preferencia.

        Al activar desde Preferencias se anuncia (y el fallo, con error);
        al desactivar, también. Nunca lanza.
        """
        try:
            if bool(self._config.get("lectura_atajos_globales", False)):
                textos = self._textos()
                if self._globales.activos and textos == self._globales_atajos:
                    return
                fallidos = self._globales.activar(textos)
                self._globales_atajos = dict(textos)
                if fallidos:
                    self._avisar(anuncios.aviso_atajos_globales_fallo(fallidos))
                else:
                    self._avisar(anuncios.Aviso(_(TEXTO_ACTIVOS)))
            elif self._globales.activos:
                self._globales.desactivar()
                self._globales_atajos = None
                self._avisar(anuncios.Aviso(_(TEXTO_SOLO).format(app=config.APP_NAME)))
        except Exception:
            logger.exception("No se pudieron aplicar los atajos de recientes")

    def cerrar(self) -> None:
        """Suelta los atajos. Nunca lanza."""
        try:
            self._globales.desactivar()
        except Exception:
            logger.debug("No se pudieron soltar los atajos de recientes")

    def _avisar(self, aviso) -> None:
        if aviso is None:
            return
        if aviso.sonido:
            try:
                _snd.reproducir(aviso.sonido)
            except Exception:
                logger.debug("No se pudo reproducir el sonido %s", aviso.sonido)
        if aviso.texto:
            from guyrapu.ui import gui as _gui
            _gui.anunciar(aviso.texto)
