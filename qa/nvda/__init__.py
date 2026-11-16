# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Carril de NVDA del banco de QA: un NVDA portátil que dice en texto.

No es parte de la aplicación y la aplicación no lo conoce. Las piezas de
`dentro/` se copian a la carpeta de borrador de un perfil de prueba y corren
dentro de NVDA. Las de este nivel lo manejan desde fuera: arman el perfil,
arrancan la copia portátil, le mandan teclas y guardan lo que dijo.
"""
