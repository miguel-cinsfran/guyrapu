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
)
