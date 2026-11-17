# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Escenario del banco para la ventana de mensajes automáticos."""

from __future__ import annotations

from banco_app import Aplicacion, Resultado
from banco_auditoria import revisar_nombres

ACCIONES = ("Agregar", "Editar", "Cambiar nombre", "Duplicar", "Subir",
            "Bajar", "Pausar o reanudar", "Escuchar", "Eliminar",
            "Exportar", "Importar")


def _paso_del_atajo():
    from guyrapu.core import config_predeterminada
    texto = config_predeterminada.obtener(
        "atajos", "mensajes_automaticos", "ctrl+shift+a")
    partes = (texto or "").strip().lower().replace(" ", "").split("+")
    tecla = partes[-1] if partes and partes[-1] else "a"
    mods = [parte for parte in partes[:-1] if parte] or ["ctrl", "shift"]
    return tecla, mods


def escenario_mensajes_automaticos(app: Aplicacion, args, res: Resultado):
    """Abre la ventana con su atajo y audita controles, textos y acciones."""
    tecla, mods = _paso_del_atajo()
    app.pedir("frente")
    try:
        app.pedir("foco", nombre="Enlace del directo o vídeo")
    except Exception as exc:
        res.nota(f"mensajes_automaticos: no se pudo poner el foco, {exc}")
    app.teclas((tecla, mods))
    dlg = app.esperar_ventana("Mensajes automáticos", segundos=15)
    if dlg is None:
        res.fallo("mensajes_automaticos: el atajo no abrió la ventana")
        return
    res.nota(f"mensajes_automaticos: el atajo abre «{dlg['titulo']}», "
             f"clase {dlg['clase']}")
    try:
        controles = app.arbol("Mensajes automáticos")
        revisar_nombres(controles, res, "mensajes_automaticos")
        textos = " ".join((c.get("etiqueta") or "") + " "
                          + (c.get("nombre") or "") for c in controles)
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
        app.pedir("cerrar_ventana", ventana="Mensajes automáticos")
