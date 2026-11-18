# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las ventanas de la aplicación que recorre el carril de NVDA.

Cada entrada dice cómo abrirla por el menú, el título que se espera y el
primer control que toma el foco. Sumar otra ventana es agregar una entrada.
"""

from __future__ import annotations

# En una lista, el primero es el elemento seleccionado, no la lista.
VENTANAS = (
    {
        "nombre": "preferencias",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "General",
    },
    {
        "nombre": "interaccion",
        "menu": "Interacción > Mensajes automáticos",
        "titulo": "Interacción",
        "primero": "No hay mensajes automáticos. Usa Agregar para crear uno.",
    },
    {
        "nombre": "comandos",
        "menu": "Interacción > Comandos del chat…",
        "titulo": "Interacción",
        "primero": "No hay comandos. Usa Agregar para crear uno.",
    },
    {
        "nombre": "estilos",
        "menu": "Interacción > Estilos del vídeo…",
        "titulo": "Interacción",
        "primero": "Clásico (de fábrica)",
    },
    {
        "nombre": "historial",
        "menu": "Archivo > Historial de directos…",
        "titulo": "Historial de directos",
        "primero": "No hay entradas de YouTube.",
    },
    {
        "nombre": "descargas",
        "menu": "Herramientas > Administrador de descargas…",
        "titulo": "Administrador de descargas",
        # El foco cae en la edición interna del combo y NVDA no le pone nombre.
        "primero": "",
    },
)
