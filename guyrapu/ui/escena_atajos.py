# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué hacen los atajos de escena y de la IA y dónde valen.

Ctrl+F2 describe la escena de OBS y Ctrl+Mayús+F2 hace la consulta rápida a
la IA. Los dos atajos pueden valer en cualquier programa si la casilla de
Preferencias lo pide.
"""

from __future__ import annotations

import wx

from guyrapu.core import config, diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.music import anuncios
from guyrapu.ui import atajos_globales, ia_consulta_rapida
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.ui.atajos_globales import combinacion_funcion
from guyrapu.voice import sound_player as _snd


logger = diagnostico.obtener_logger(__name__)

# Traductores: confirmación de que los atajos de escena e IA valen fuera de la app.
TEXTO_ACTIVOS = N_("Atajos de escena e IA en cualquier aplicación")
# Traductores: confirmación de que los atajos de escena e IA valen solo en la app.
_TEXTO_SOLO = N_("Atajos de escena e IA solo en {app}")

# Acciones de escena e IA con atajo global, en orden: el índice da el id.
ORDEN = ("describir_escena", "consulta_rapida_ia")

# Base de los ids propios para `RegisterHotKey`, lejos de los de cámara.
BASE_IDS = 0xB300


class EscenaAtajos:
    """Los atajos de escena e IA dentro de la app o en todo el sistema.

    `frame` es la ventana principal: de ella salen los atajos configurados,
    la configuración y la ventana que registra las combinaciones. Nunca
    lanza: registrar o soltar puede fallar y se informa con el anuncio.
    """

    def __init__(self, frame) -> None:
        self._ventana = frame
        self._config = frame._config
        self._acciones = {
            "describir_escena": lambda: frame._describir_escena(),
            "consulta_rapida_ia":
                lambda: ia_consulta_rapida.consultar(frame),
        }
        self._globales = atajos_globales.AtajosGlobales(
            frame, self._acciones, orden=ORDEN, base_ids=BASE_IDS,
            traducir=combinacion_funcion)
        self._globales_atajos = None
        if bool(self._config.get("escena_atajos_globales", False)):
            # Después de que la ventana exista: el registro es del sistema
            # y pide el bucle de eventos.
            try:
                wx.CallAfter(self.activar_arranque)
            except Exception:
                logger.debug("No se pudieron activar los atajos de escena")

    def _textos(self) -> dict:
        """Los atajos efectivos de escena e IA, acción → texto guardado."""
        atajos = getattr(self._ventana, "_atajos", None) or {}
        textos = {}
        for accion in ORDEN:
            atajo = atajos.get(accion)
            texto = getattr(atajo, "texto", atajo)
            if texto:
                textos[accion] = texto
        return textos

    def activar_arranque(self) -> None:
        """Activa los globales al arrancar: calla salvo que algo falle."""
        try:
            textos = self._textos()
            fallidos = self._globales.activar(textos)
        except Exception:
            logger.exception("No se pudieron activar los atajos de escena")
            return
        self._globales_atajos = textos
        if fallidos:
            self._avisar(anuncios.aviso_atajos_globales_fallo(fallidos))

    def aplicar_preferencias(self) -> None:
        """Activa o desactiva los globales según la preferencia.

        Al activar desde Preferencias se anuncia (y el fallo, con el tono de
        ocupado); al desactivar, también. Nunca lanza.
        """
        try:
            if bool(self._config.get("escena_atajos_globales", False)):
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
                self._avisar(anuncios.Aviso(
                    _(_TEXTO_SOLO).format(app=config.APP_NAME)))
        except Exception:
            logger.exception("No se pudieron aplicar los atajos de escena")

    def _avisar(self, aviso) -> None:
        if aviso is None:
            return
        if aviso.sonido:
            try:
                _snd.reproducir(aviso.sonido)
            except Exception:
                logger.debug("No se pudo reproducir el sonido %s", aviso.sonido)
        if aviso.texto:
            anunciar(aviso.texto)
