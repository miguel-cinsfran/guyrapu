# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El comando Probar de una tarjeta, común a Estilos y Mensajes automáticos.

Su única razón para cambiar es cómo se prueba una tarjeta: pide la espera,
la arma por el único camino a OBS y anuncia la revisión, o abre el cuadro de
error. Lo que iría al chat se dice y nunca se envía.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.ui import aviso_importante, gui_envio_chat
from guyrapu.ui.accesibilidad import anunciar_con_sonido
from guyrapu.voice import sound_player


def probar(texto, estilo, al_chat=""):
    """Prueba una tarjeta y anuncia cómo se verá.

    Con `texto` en None se prueba solo lo que iría al chat, sin tocar OBS.
    """
    sound_player.reproducir("espera")
    frase_chat = (_("Iría al chat: {texto}").format(texto=al_chat)
                  if al_chat else "")
    if texto is None:
        anunciar_con_sonido(frase_chat, "listo")
        return

    from guyrapu.ui import gui

    def al_terminar(frase, error):
        if error:
            aviso_importante.avisar(frase, "error", error=True)
            return
        if frase_chat:
            frase = f"{frase} {frase_chat}"
        anunciar_con_sonido(frase, "listo")

    gui_envio_chat.capa_de_video(gui._gui_frame).probar(
        texto, estilo, al_terminar)
