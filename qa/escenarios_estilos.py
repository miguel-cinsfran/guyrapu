# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Escenario del banco para la ventana de estilos del vídeo."""

from __future__ import annotations

from banco_app import Aplicacion, Resultado
from banco_auditoria import revisar_nombres

ACCIONES = (
    "Agregar",
    "Editar",
    "Cambiar nombre",
    "Duplicar",
    "Escuchar",
    "Eliminar",
    "Exportar",
    "Importar",
)


def escenario_estilos(app: Aplicacion, args, res: Resultado):
    """Abre la ventana Interacción en estilos y audita controles y acciones."""
    app.pedir("frente")
    try:
        app.abrir_por_menu("Es&tilos del vídeo…")
    except Exception as exc:
        res.fallo(f"estilos: no se pudo abrir por el menú, {exc}")
        return
    dlg = app.esperar_ventana("Interacción", segundos=15)
    if dlg is None:
        res.fallo("estilos: el menú no abrió la ventana")
        return
    res.nota(f"estilos: el menú abre «{dlg['titulo']}», "
             f"clase {dlg['clase']}")
    try:
        controles = app.arbol("Interacción")
        revisar_nombres(controles, res, "estilos")
        esperados = ("ListaEstilosVideo", "Estilos del vídeo guardados")
        nombres = {c.get("nombre") or "" for c in controles}
        faltan = [nombre for nombre in esperados if nombre not in nombres]
        if faltan:
            res.fallo(f"estilos: no aparecen en el árbol: {faltan}")
        dichos = dict.fromkeys(
            (c.get("etiqueta") or "").replace("&", "").rstrip(":")
            for c in controles)
        acciones = [accion for accion in ACCIONES if accion not in dichos]
        if acciones:
            res.fallo(f"estilos: faltan acciones: {acciones}")
        else:
            res.nota(f"estilos: las {len(ACCIONES)} acciones están")
    finally:
        app.pedir("cerrar_ventana", ventana="Interacción")
