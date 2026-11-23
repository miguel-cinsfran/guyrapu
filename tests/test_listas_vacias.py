# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Todo texto de lista vacía dice qué hay y cómo se llena, no solo que está vacía."""

import unittest

from guyrapu.ai import ventana_ia
from guyrapu.core import historial, voces_disponibles
from guyrapu.ui import (
    chat_buscar, chat_participacion, chat_vivo, descargas_buscador,
    descargas_listas, dialogo_estado, elegir_formato, escena_pagina_audio,
    escena_pagina_escena, escena_pagina_fuentes, gui_grabaciones,
    gui_historial, musica_colecciones, musica_editor_lista,
    musica_ventana_acciones, obs_pagina_perfiles, preferencias_sonidos,
    restream_pagina_destinos, restream_pagina_eventos,
    restream_pagina_perfiles)

TEXTOS = (
    (chat_buscar, "TEXTO_ESCRIBE"),
    (chat_buscar, "TEXTO_SIN_COINCIDENCIAS"),
    (chat_participacion, "TEXTO_VACIO"),
    (chat_vivo, "VACIO_CHAT"),
    (descargas_buscador, "VACIO"),
    (descargas_buscador, "CARGANDO"),
    (descargas_buscador, "SIN_RESULTADOS"),
    (descargas_listas, "VACIO"),
    (dialogo_estado, "SIN_ESTADO"),
    (elegir_formato, "VACIO"),
    (escena_pagina_audio, "VACIO"),
    (escena_pagina_escena, "VACIO"),
    (escena_pagina_fuentes, "VACIO"),
    (gui_grabaciones, "_NO_HAY"),
    (gui_historial, "VACIO"),
    (ventana_ia, "FILA_GUIA"),
    (musica_colecciones, "TEXTO_CARGANDO"),
    (musica_colecciones, "TEXTO_SIN_CARPETA"),
    (musica_ventana_acciones, "TEXTO_COLA_VACIA"),
    (musica_ventana_acciones, "TEXTO_SIN_CANCIONES"),
    (musica_editor_lista, "TEXTO_LISTA_VACIA"),
    (musica_editor_lista, "TEXTO_TODAS_VACIO"),
    (musica_editor_lista, "TEXTO_TODAS_SIN_COINCIDENCIAS"),
    (obs_pagina_perfiles, "VACIO"),
    (preferencias_sonidos, "VACIO"),
    (historial, "VACIO"),
    (restream_pagina_destinos, "SIN_CUENTA"),
    (restream_pagina_destinos, "VACIO"),
    (restream_pagina_eventos, "SIN_CUENTA"),
    (restream_pagina_eventos, "VACIO"),
    (restream_pagina_eventos, "FALLO"),
    (restream_pagina_perfiles, "VACIO"),
    (voces_disponibles, "VACIO_CARGANDO"),
    (voces_disponibles, "VACIO_FILTRO"),
    (voces_disponibles, "VACIO_FALLO"),
    (voces_disponibles, "VACIO_SIN_PAQUETES"),
    (voces_disponibles, "VACIO_BUSQUEDA"),
)


class TestTextosDeListasVacias(unittest.TestCase):

    def test_ningun_texto_es_solo_no_hay(self):
        for modulo, nombre in TEXTOS:
            with self.subTest(modulo=modulo.__name__, nombre=nombre):
                texto = getattr(modulo, nombre)
                frases = [frase for frase in texto.split(".") if frase.strip()]
                self.assertGreaterEqual(len(frases), 2, texto)


if __name__ == "__main__":
    unittest.main()
