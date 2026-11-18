# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Entradas y despliegue de los menús contextuales de la ventana de música.

Las entradas se arman con funciones puras que devuelven pares
(etiqueta, acción), para poder comprobarlas sin mostrar el menú. Una acción
que es una lista de entradas se despliega como submenú. El despliegue es lo
único que toca wx.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_

ACCION_AHORA = "ahora"
ACCION_CONTINUACION = "continuacion"
ACCION_AGREGAR = "agregar"
ACCION_TODO_DESDE_AQUI = "todo_desde_aqui"
ACCION_AGREGAR_A_LISTA = "agregar_a_lista"
ACCION_QUITAR_DE_LISTA = "quitar_de_lista"
ACCION_RENOMBRAR_LISTA = "renombrar_lista"
ACCION_BORRAR_LISTA = "borrar_lista"
ACCION_EDITAR_LISTA = "editar_lista"
ACCION_REPRODUCIR_COLECCION = "reproducir_coleccion"
ACCION_AGREGAR_COLECCION = "agregar_coleccion"
ACCION_NUEVA_LISTA = "nueva_lista"

ACCION_REPRODUCIR = "reproducir"
ACCION_QUITAR = "quitar"
ACCION_SUBIR = "subir"
ACCION_BAJAR = "bajar"
ACCION_IR_AL_QUE_SUENA = "ir_al_que_suena"
ACCION_MEZCLAR = "mezclar"
ACCION_VACIAR = "vaciar"
ACCION_GUARDAR_COLA = "guardar_cola"


def entradas_canciones() -> list:
    """Las entradas del menú de la lista de canciones de la biblioteca."""
    return [
        (N_("Reproducir &ahora"), ACCION_AHORA),
        (N_("Reproducir a &continuación"), ACCION_CONTINUACION),
        (N_("A&gregar a la cola"), ACCION_AGREGAR),
        (N_("Reproducir &todo desde aquí"), ACCION_TODO_DESDE_AQUI),
        (N_("Agregar a una &lista"), ACCION_AGREGAR_A_LISTA),
        (N_("&Eliminar de esta lista"), ACCION_QUITAR_DE_LISTA),
    ]


def entradas_colecciones(es_lista: bool) -> list:
    """Las entradas del menú de «Colecciones», según lo elegido."""
    entradas = [
        (N_("&Reproducir"), ACCION_REPRODUCIR_COLECCION),
        (N_("A&gregar a la cola"), ACCION_AGREGAR_COLECCION),
    ]
    if es_lista:
        entradas += [
            (N_("&Editar la lista…"), ACCION_EDITAR_LISTA),
            (N_("&Cambiar nombre de la lista…"), ACCION_RENOMBRAR_LISTA),
            (N_("&Borrar la lista…"), ACCION_BORRAR_LISTA),
        ]
    entradas.append((N_("&Nueva lista…"), ACCION_NUEVA_LISTA))
    return entradas


def entradas_cola() -> list:
    """Las entradas del menú de la Cola."""
    return [
        (N_("&Reproducir"), ACCION_REPRODUCIR),
        (N_("&Eliminar"), ACCION_QUITAR),
        (N_("&Subir"), ACCION_SUBIR),
        (N_("&Bajar"), ACCION_BAJAR),
        (N_("&Ir al que suena"), ACCION_IR_AL_QUE_SUENA),
        (N_("&Mezclar la cola"), ACCION_MEZCLAR),
        (N_("&Vaciar la cola"), ACCION_VACIAR),
        (N_("&Guardar la cola como lista…"), ACCION_GUARDAR_COLA),
    ]


def entradas_lista_editada() -> list:
    """Las entradas del menú de las canciones de la lista que se edita."""
    return [
        (N_("&Reproducir"), ACCION_REPRODUCIR),
        (N_("&Eliminar"), ACCION_QUITAR),
        (N_("&Subir"), ACCION_SUBIR),
        (N_("&Bajar"), ACCION_BAJAR),
    ]


def _agregar_entradas(menu, entradas, al_elegir) -> None:
    """Engancha cada entrada en el menú que la contiene."""
    for etiqueta, accion in entradas:
        if isinstance(accion, list):
            submenu = wx.Menu()
            menu.AppendSubMenu(submenu, etiqueta)
            _agregar_entradas(submenu, accion, al_elegir)
            continue
        ident = wx.NewIdRef()
        menu.Append(ident, etiqueta)
        menu.Bind(
            wx.EVT_MENU, lambda _evento, accion=accion: al_elegir(accion),
            id=ident)


def mostrar_menu(ventana, entradas, al_elegir) -> None:
    """Muestra las entradas y despacha la acción elegida."""
    menu = wx.Menu()
    try:
        _agregar_entradas(menu, entradas, al_elegir)
        ventana.PopupMenu(menu)
    finally:
        menu.Destroy()
