# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Escenario del banco para la ventana de comandos del chat."""

from __future__ import annotations

from banco_app import Aplicacion, Resultado
from banco_auditoria import auditar_dialogo

ACCIONES = ("Agregar", "Editar", "Cambiar palabra", "Duplicar",
            "Pausar o reanudar", "Escuchar", "Eliminar", "Exportar",
            "Importar")


def escenario_comandos(app: Aplicacion, args, res: Resultado):
    """Abre la ventana Interacción en comandos y audita controles y acciones."""
    auditar_dialogo(
        app, res, "&Comandos del chat…", "Interacción", vueltas_tab=14,
        esperados=("Comandos del chat guardados",) + ACCIONES,
        esperados_en_tab=("Comandos del chat guardados",) + ACCIONES)
