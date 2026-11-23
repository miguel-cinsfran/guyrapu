# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""F1 abre el manual en la sección de la ventana.

Un solo registro relaciona cada ventana con su ancla del manual. Las anclas
se escriben a mano en los títulos de `docs/es/MANUAL.md` y
`docs/en/MANUAL.md` con un ancla HTML, así que no cambian cuando el manual
se reordena o se cambia un título.

`os.startfile` no lleva la parte `#ancla` de una ruta: para llegar a la
sección se escribe una página mínima de redirección en la carpeta temporal
y se abre esa página, como se abre el manual hoy.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import _

# Clave de ventana -> ancla escrita a mano en los dos manuales.
ANCLAS = {
    "panel_obs": "panel-obs",
    "restream": "restream",
    "musica": "musica",
    "descargas": "descargas",
    "ia": "ia",
    "preferencias": "preferencias",
    "transmitir": "transmitir",
    "microfono": "microfono",
    "voces": "voces",
    "chat": "chat",
    "comandos": "comandos",
    "disparadores": "alertas",
    "mensajes": "mensajes-automaticos",
    "encuestas": "encuestas",
    "preguntas": "preguntas",
    "metas": "metas",
    "medios": "medios",
    "estilos": "estilos",
    "palabras": "palabras-bloqueadas",
    "ensayo": "probar-sin-directo",
}


def pagina_de_redireccion(destino: Path, ancla: str, titulo: str) -> str:
    """HTML mínimo que el navegador abre en la sección del manual."""
    url = destino.as_uri() + "#" + ancla
    return (
        "<!DOCTYPE html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{html.escape(titulo)}</title>\n"
        "</head>\n"
        "<body>\n"
        f"<script>location.replace({json.dumps(url)});</script>\n"
        f'<p><a href="{html.escape(url, quote=True)}">{html.escape(titulo)}</a></p>\n'
        "</body>\n"
        "</html>\n"
    )


def destino_documento(nombre: str, idioma: str, ancla: str | None,
                      titulo: str) -> Path:
    """La ruta que hay que abrir: el documento, o su página de redirección."""
    destino = paths.documento(nombre, idioma)
    if ancla is None:
        return destino
    pagina = paths.pagina_redireccion(nombre, ancla)
    pagina.write_text(pagina_de_redireccion(destino, ancla, titulo),
                      encoding="utf-8")
    return pagina


def abrir(ventana, clave: str) -> None:
    """Abre el manual en la sección que le toca a la clave."""
    from guyrapu.ui import gui_menu
    gui_menu.abrir_documento_paquete(
        ventana, "MANUAL", _("Manual de uso"), ANCLAS[clave])


def atender_f1(ventana, evento, clave: str) -> bool:
    """Abre el manual con F1 y dice si tomó la tecla."""
    if evento.GetKeyCode() != wx.WXK_F1:
        return False
    abrir(ventana, clave)
    return True


def enlazar(ventana, clave: str) -> None:
    """Toma F1 en la ventana y deja pasar las demás teclas."""
    def al_tecla(evento):
        if not atender_f1(ventana, evento, clave):
            evento.Skip()
    ventana.Bind(wx.EVT_CHAR_HOOK, al_tecla)
