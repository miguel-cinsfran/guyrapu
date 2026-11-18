# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo un enlace de YouTube se convierte en un reproductor de VLC.

Pide la dirección del audio, la abre con libVLC y deja el reproductor sonando
en el adaptador. La petición corre en su propio hilo: el adaptador no se
bloquea mientras yt-dlp responde. Sin ``wx``.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.music import enlaces
from guyrapu.player import motor_vlc


logger = diagnostico.obtener_logger(__name__)


class EnlaceVlc:
    """Resuelve el audio de un enlace y lo deja sonando en el adaptador.

    El resultado llega en otro hilo: comparte con el adaptador su candado, su
    cola y la ficha pedida, para descartar lo que quede viejo.
    """

    def __init__(self, adaptador):
        self._adaptador = adaptador

    def preparar(self, tema, ficha, volumen):
        """Deja pedido el enlace y lo resuelve en su hilo."""
        adaptador = self._adaptador
        adaptador._cruce_largo, adaptador._pendiente = False, ficha
        anterior = adaptador._actual
        adaptador._actual, adaptador._iniciado, adaptador._ficha_actual = (
            None, False, None)
        adaptador._volumen = volumen
        if anterior is not None:
            adaptador._soltar(anterior)
        diagnostico.crear_hilo(
            self.resolver, "musica-enlace", args=(tema, ficha)).start()

    def resolver(self, tema, ficha):
        """Resuelve el audio del enlace y arranca el reproductor. Corre en su
        propio hilo: nunca usa libVLC desde un callback."""
        adaptador = self._adaptador
        try:
            url = enlaces.url_audio(tema.origen)
        except Exception:
            logger.debug("No se pudo resolver el audio del enlace: %s", tema.origen)
            with adaptador._lock:
                if adaptador._pendiente == ficha:
                    adaptador._pendiente = None
                if ficha == adaptador._pedida:
                    # El aviso sale por el hilo consumidor: acá se puede tener
                    # el candado del coordinador y llamarlo acá lo colgaría.
                    adaptador._fallar(ficha)
            return
        with adaptador._lock:
            if adaptador._pendiente == ficha:
                adaptador._pendiente = None
            # La ficha guardada es la pedida: si el usuario ya pidió otro tema,
            # el resultado que llegó tarde se descarta y no toca al que suena.
            if adaptador._cerrado or ficha != adaptador._pedida:
                return
            self.abrir(url, ficha)

    def abrir(self, url, ficha):
        adaptador = self._adaptador
        reproductor = adaptador._instancia.media_player_new()
        if reproductor is None:
            adaptador._fallar(ficha)
            return
        if adaptador._salida_audio is not None:
            motor_vlc.fijar_salida_audio(reproductor, adaptador._salida_audio)
        if adaptador._dispositivo:
            reproductor.audio_output_device_set(None, adaptador._dispositivo)
        try:
            media = adaptador._instancia.media_new(url)
            for opcion in _opciones_enlace():
                media.add_option(opcion)
            reproductor.set_media(media)
        except Exception as exc:
            logger.debug("No se pudo preparar el enlace: %s", exc)
            adaptador._soltar(reproductor)
            adaptador._fallar(ficha)
            return
        reproductor.audio_set_volume(adaptador._volumen)
        adaptador._enganchar(reproductor, ficha)
        preparado_en_pausa = adaptador._pausa_pendiente
        adaptador._pausa_pendiente = False
        if not preparado_en_pausa and reproductor.play() == -1:
            adaptador._soltar(reproductor)
            adaptador._fallar(ficha)
            return
        anterior = adaptador._actual
        adaptador._actual = reproductor
        adaptador._iniciado = not preparado_en_pausa
        adaptador._ficha_actual = ficha
        if anterior is not None:
            adaptador._soltar(anterior)


def _opciones_enlace() -> tuple[str, ...]:
    """Opciones de red del reproductor de vídeo para flujos de YouTube.

    Salen de ``reproductor.opciones_medio``, que es pública, importada al
    momento para no arrastrar la interfaz al cargar este módulo. Si no se
    puede importar, ninguna: el medio igual suena.
    """
    try:
        from guyrapu.player.reproductor import opciones_medio
    except Exception:
        return ()
    return opciones_medio(False, solo_audio=True)
