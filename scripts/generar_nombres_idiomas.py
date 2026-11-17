# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Genera la tabla de nombres de idiomas con Babel.

Escribe `guyrapu/translation/nombres_idiomas.json`: por cada código ISO
639-1 que conoce Babel, su nombre en español y en inglés. La app no
importa Babel: lee la tabla ya generada.

Se corre a mano cuando Babel agrega idiomas o corrige nombres:

    .venv/Scripts/python.exe scripts/generar_nombres_idiomas.py
"""

import json
from pathlib import Path

from babel import Locale, localedata

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "guyrapu" / "translation" / "nombres_idiomas.json"


def _codigos():
    return sorted(codigo for codigo in localedata.locale_identifiers()
                  if len(codigo) == 2 and codigo.isalpha())


def tabla() -> dict:
    """Nombre del idioma en español y en inglés, por código."""
    nombres = {}
    for codigo in _codigos():
        idioma = Locale.parse(codigo)
        es = idioma.get_language_name("es")
        en = idioma.get_language_name("en")
        if es and en:
            nombres[codigo] = {"es": es, "en": en}
    return nombres


def main() -> None:
    nombres = tabla()
    texto = json.dumps(nombres, ensure_ascii=False, indent=2, sort_keys=True)
    DESTINO.write_text(texto + "\n", encoding="utf-8")
    print(f"{DESTINO} con {len(nombres)} idiomas")


if __name__ == "__main__":
    main()
