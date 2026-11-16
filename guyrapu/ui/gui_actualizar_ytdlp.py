# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana de actualización de yt-dlp.

El cuerpo de `abrir_ventana_actualizacion` es el antiguo
`VentanaPrincipal._on_actualizar_ytdlp`, movido sin cambios, igual que ya hace
`gui_actualizar_app.abrir_ventana_actualizacion(frame)` para la app. En la
clase queda un delegado de dos líneas porque lo enlazan el menú
Herramientas y las pruebas.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.downloads import ytdlp_actualizar


def abrir_ventana_actualizacion(frame) -> None:
    """Abre la ventana de actualización de yt-dlp o enfoca la ya abierta."""
    from guyrapu.ui.gui import diagnostico, logger
    from guyrapu.ui.gui_actualizacion import DialogoActualizacion
    abierta = getattr(frame, "_ventana_actualizar_ytdlp", None)
    if abierta is not None and not abierta.cerrado:
        try:
            abierta.Raise()
        except Exception as error:
            logger.debug("no se pudo traer al frente la ventana: %s", error)
        try:
            abierta.btn_cerrar.SetFocus()
        except Exception as error:
            logger.debug("no se pudo enfocar el cierre: %s", error)
        return
    ventana = DialogoActualizacion(frame, _("Actualizar yt-dlp"))
    frame._ventana_actualizar_ytdlp = ventana
    ventana.Show()
    ventana.estado(_("Buscando la última versión de yt-dlp."))
    actualizacion = _ActualizacionYtdlp(ventana)
    diagnostico.crear_hilo(actualizacion._run, "ActualizarYtdlp").start()


class _ActualizacionYtdlp:
    """Lleva el avance de la actualización a la ventana."""

    def __init__(self, ventana):
        self.ventana = ventana
        self.ultimo_texto = None

    def _avisar(self, version_nueva):
        self.ventana.en_hilo_principal(
            self._mostrar_descarga, version_nueva)

    def _mostrar_descarga(self, version_nueva):
        # Traductores: {version} es la versión nueva de yt-dlp.
        texto = _("Hay una versión nueva de yt-dlp, la {version}. "
                  "Descargando.")
        self.ventana.estado(texto.format(version=version_nueva))

    def _progreso(self, porcentaje):
        self.ventana.en_hilo_principal(self._actualizar_progreso, porcentaje)

    def _actualizar_progreso(self, porcentaje):
        self.ventana.progreso(porcentaje)
        if ytdlp_actualizar.debe_actualizar_texto_progreso(
                self.ultimo_texto, porcentaje):
            self.ultimo_texto = porcentaje
            # Traductores: {porcentaje} es el avance de 0 a 100.
            texto = _("Descargando yt-dlp: {porcentaje} por ciento")
            self.ventana.txt_estado.SetValue(texto.format(porcentaje=porcentaje))

    def _terminar(self, estado, texto):
        from guyrapu.ui.gui import logger
        fallo = ytdlp_actualizar.resultado_actualizacion_es_fallo(estado)
        self.ventana.terminar_espera("error" if fallo else "listo")
        if fallo:
            self.ventana.progreso(0)
        else:
            self.ventana.progreso(100)
        self.ventana.estado(texto)
        try:
            self.ventana.btn_cerrar.SetFocus()
        except Exception as error:
            logger.debug("no se pudo enfocar el cierre: %s", error)

    def _run(self):
        from guyrapu.ui.gui import logger
        try:
            estado, version_actual, version_nueva = ytdlp_actualizar.actualizar_ytdlp(
                self._avisar, self._progreso, self.ventana.cancelado.is_set)
            texto = ytdlp_actualizar.mensaje_de_actualizacion(
                estado, version_actual, version_nueva)
        except Exception as exc:
            logger.warning("actualización de yt-dlp: %s", exc)
            estado = "otro_fallo"
            texto = ytdlp_actualizar.mensaje_de_actualizacion(
                "otro_fallo", motivo=str(exc))
        self.ventana.en_hilo_principal(self._terminar, estado, texto)
