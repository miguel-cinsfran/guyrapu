# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Toda lista de la interfaz usa la pieza común o está anotada como pendiente."""

import unittest
from pathlib import Path

RAIZ_UI = Path(__file__).resolve().parent.parent / "guyrapu" / "ui"
PIEZA = "lista_acciones.py"

LLAMADAS_DE_LISTA = (
    "wx.ListBox(",
    "wx.ListCtrl(",
    "wx.ListView(",
    "wx.CheckListBox(",
    "wx.TreeCtrl(",
    "wx.dataview",
)

NOMBRES_DE_LA_PIEZA = ("ListaConAcciones", "ListaConVacio")

# Lo que todavía no pasó a la pieza, con el motivo. Pasar un módulo a la
# pieza obliga a borrar su línea: el alta sin la pieza y la baja de la lista
# son fallos.
PENDIENTES = {
    "descargas_buscador.py": "todavía no pasó a la pieza común",
    "descargas_listas.py": "todavía no pasó a la pieza común",
    "dialogo_estado.py": (
        "lista de solo lectura sin acciones, en dialogo_estado.py:39"),
    "elegir_formato.py": (
        "lista de solo lectura para elegir un formato, en elegir_formato.py:52"),
    "escena_pagina_audio.py": "todavía no pasó a la pieza común",
    "escena_pagina_escena.py": "todavía no pasó a la pieza común",
    "escena_pagina_fuentes.py": "todavía no pasó a la pieza común",
    "gui.py": "todavía no pasó a la pieza común",
    "gui_comentarios.py": "todavía no pasó a la pieza común",
    "gui_grabaciones.py": "todavía no pasó a la pieza común",
    "gui_historial.py": "todavía no pasó a la pieza común",
    "ia_ventana.py": "todavía no pasó a la pieza común",
    "musica_editor_lista.py": "todavía no pasó a la pieza común",
    "musica_ventana.py": "todavía no pasó a la pieza común",
    "preferencias_programados.py": "todavía no pasó a la pieza común",
    "preferencias_sonidos.py": "todavía no pasó a la pieza común",
    "recientes_inicio.py": "todavía no pasó a la pieza común",
    "restream_pagina_destinos.py": "todavía no pasó a la pieza común",
    "restream_pagina_eventos.py": "todavía no pasó a la pieza común",
    "restream_pagina_perfiles.py": "todavía no pasó a la pieza común",
}


def _crea_lista(texto):
    """Si el módulo crea una lista por su cuenta."""
    return any(llamada in texto for llamada in LLAMADAS_DE_LISTA)


def _usa_la_pieza(texto):
    """Si el módulo nombra la pieza común."""
    return any(nombre in texto for nombre in NOMBRES_DE_LA_PIEZA)


def _leer_ui():
    """El texto de cada módulo de la interfaz, por nombre de archivo."""
    return {ruta.name: ruta.read_text(encoding="utf-8")
            for ruta in sorted(RAIZ_UI.rglob("*.py"))}


def _revisar(textos, pendientes):
    """Los fallos en las dos direcciones: sin pieza y pendientes vencidos."""
    sin_pieza = []
    vencidos = []
    for nombre, texto in textos.items():
        if nombre == PIEZA:
            continue
        crea = _crea_lista(texto)
        usa = _usa_la_pieza(texto)
        if crea and not usa and nombre not in pendientes:
            sin_pieza.append(nombre)
        if nombre in pendientes and (usa or not crea):
            vencidos.append(nombre)
    return sin_pieza, vencidos


def _detalle_sin_pieza(nombres):
    return "\n".join(
        f"{nombre}: crea una lista y no usa la pieza común. "
        f"Envuélvela con ListaConAcciones o ListaConVacio o agrégala a "
        f"PENDIENTES con su motivo."
        for nombre in nombres)


def _detalle_vencidos(nombres):
    return "\n".join(
        f"{nombre}: figura en PENDIENTES pero ya usa la pieza o ya no crea "
        f"ninguna lista. Sácala de PENDIENTES."
        for nombre in nombres)


class ListasConPiezaTest(unittest.TestCase):

    def test_una_lista_nueva_usa_la_pieza_o_esta_pendiente(self):
        sin_pieza, _ = _revisar(_leer_ui(), PENDIENTES)
        self.assertEqual(sin_pieza, [], _detalle_sin_pieza(sin_pieza))

    def test_pendientes_que_ya_no_corresponden(self):
        _, vencidos = _revisar(_leer_ui(), PENDIENTES)
        self.assertEqual(vencidos, [], _detalle_vencidos(vencidos))


if __name__ == "__main__":
    unittest.main()
