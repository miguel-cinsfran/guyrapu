# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Escenario del banco para la página de mensajes automáticos."""

from __future__ import annotations

from banco_app import Aplicacion, Resultado
from banco_auditoria import revisar_nombres

ACCIONES = ("Agregar", "Editar", "Cambiar nombre", "Duplicar", "Subir",
            "Bajar", "Pausar o reanudar", "Escuchar", "Eliminar",
            "Exportar", "Importar")


def escenario_mensajes_automaticos(app: Aplicacion, args, res: Resultado):
    """Abre la ventana Interacción en mensajes y audita controles y acciones."""
    app.pedir("frente")
    try:
        app.abrir_por_menu("&Mensajes automáticos…")
    except Exception as exc:
        res.fallo(f"mensajes_automaticos: no se pudo abrir por el menú, {exc}")
        return
    dlg = app.esperar_ventana("Interacción", segundos=15)
    if dlg is None:
        res.fallo("mensajes_automaticos: el menú no abrió la ventana")
        return
    res.nota(f"mensajes_automaticos: el menú abre «{dlg['titulo']}», "
             f"clase {dlg['clase']}")
    try:
        controles = app.arbol("Interacción")
        revisar_nombres(controles, res, "mensajes_automaticos")
        textos = " ".join((c.get("etiqueta") or "") + " "
                          + (c.get("nombre") or "") for c in controles)
        textos = " ".join(textos.split())
        for clave, que in (("5 minutos", "el intervalo mínimo"),
                           ("200 caracteres", "el límite de caracteres"),
                           ("enlaces", "el aviso sobre los enlaces")):
            if clave not in textos:
                res.fallo(f"mensajes_automaticos: la explicación no menciona {que}")
        esperados = ("ActivarProgramados", "Mensajes automáticos guardados")
        nombres = {c.get("nombre") or "" for c in controles}
        faltan = [nombre for nombre in esperados if nombre not in nombres]
        if faltan:
            res.fallo(f"mensajes_automaticos: no aparecen en el árbol: {faltan}")
        dichos = dict.fromkeys(
            (c.get("etiqueta") or "").replace("&", "").rstrip(":")
            for c in controles)
        acciones = [accion for accion in ACCIONES if accion not in dichos]
        if acciones:
            res.fallo(f"mensajes_automaticos: faltan acciones: {acciones}")
        else:
            res.nota(f"mensajes_automaticos: las {len(ACCIONES)} acciones están")
    finally:
        app.pedir("cerrar_ventana", ventana="Interacción")
