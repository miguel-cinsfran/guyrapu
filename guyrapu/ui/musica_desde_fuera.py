# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Manejo de la música desde fuera de la ventana de Guyrapu.

Son los atajos globales y los controles de medios del sistema, que valen en
cualquier programa. El control de música la crea al arrancar y la suelta al
cerrarse.
"""

from __future__ import annotations

import wx

from guyrapu.core import config as cfg
from guyrapu.core import diagnostico
from guyrapu.music import anuncios
from guyrapu.ui import atajos_globales
from guyrapu.ui.controles_medios import ControlesMedios


logger = diagnostico.obtener_logger(__name__)


class DesdeFueraMusica:
    """Los atajos globales, los controles de medios y sus avisos."""

    def __init__(self, frame, config, acciones, avisar, estado,
                 ejecutar_atajo) -> None:
        self.globales = atajos_globales.AtajosGlobales(frame, acciones)
        self.medios = ControlesMedios(frame, ejecutar_atajo)
        self._config = config
        self._avisar = avisar
        self._estado = estado
        self._teclas = bool(config.get("musica_teclas_multimedia", True))
        self._atajos = None
        if bool(self._config.get("musica_atajos_globales", False)):
            # Después de que la ventana exista: el registro es del sistema
            # y pide el bucle de eventos.
            try:
                wx.CallAfter(self.activar_al_arrancar)
            except Exception:
                logger.debug("No se pudieron activar los atajos globales")

    def soltar(self) -> None:
        """Suelta los atajos globales y los controles de medios."""
        try:
            self.globales.desactivar()
        except Exception:
            logger.debug("No se pudieron soltar los atajos globales")
        self.medios.soltar()

    def poner_al_dia(self) -> None:
        """Pone al día los controles de medios con la cola y el tema."""
        self.medios.poner_al_dia(
            self._estado(),
            bool(self._config.get("musica_teclas_multimedia", True)))

    def _atajos_globales_textos(self) -> dict:
        """Los atajos efectivos de música, acción → texto guardado."""
        atajos = cfg.parsear_atajos(self._config.get("atajos_raw", {}))
        return {accion: atajos[accion].texto for accion in atajos_globales.ACCIONES
                if accion in atajos}

    def activar_al_arrancar(self) -> None:
        """Activa los globales al arrancar: calla salvo que algo falle."""
        try:
            textos = self._atajos_globales_textos()
            fallidos = self.globales.activar(textos)
        except Exception:
            logger.exception("No se pudieron activar los atajos globales")
            return
        self._atajos = textos
        if fallidos:
            self._avisar(anuncios.aviso_atajos_globales_fallo(fallidos))

    def aplicar_preferencias(self) -> None:
        """Activa o desactiva los globales según la preferencia.

        Reactiva si cambiaron los atajos. Al activar desde Preferencias se
        anuncia (y el fallo, con error); al desactivar, también. Nunca lanza.
        """
        activo = bool(self._config.get("musica_teclas_multimedia", True))
        if activo != self._teclas:
            self._teclas = activo
            self.poner_al_dia()
        try:
            if bool(self._config.get("musica_atajos_globales", False)):
                textos = self._atajos_globales_textos()
                if self.globales.activos and textos == self._atajos:
                    return
                fallidos = self.globales.activar(textos)
                self._atajos = dict(textos)
                if fallidos:
                    self._avisar(anuncios.aviso_atajos_globales_fallo(fallidos))
                else:
                    self._avisar(anuncios.aviso_atajos_globales_activos())
            elif self.globales.activos:
                self.globales.desactivar()
                self._atajos = None
                self._avisar(anuncios.aviso_atajos_globales_solo())
        except Exception:
            logger.exception("No se pudieron aplicar los atajos globales")
