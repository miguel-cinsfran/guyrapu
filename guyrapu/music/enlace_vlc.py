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


def debe_reintentar(vino_del_cache, sono, reintentado, sigue_pedida) -> bool:
    """Si un error de VLC antes de sonar merece pedir la dirección otra vez."""
    return bool(vino_del_cache and not sono and not reintentado
                and sigue_pedida)


class EnlaceVlc:
    """Resuelve el audio de un enlace y lo deja sonando en el adaptador.

    El resultado llega en otro hilo: comparte con el adaptador su candado, su
    cola y la ficha pedida, para descartar lo que quede viejo. De cada
    reproductor abierto guarda si la dirección vino del caché y si llegó a
    sonar, para reintentar una sola vez cuando la dirección guardada ya no
    sirve.
    """

    def __init__(self, adaptador):
        self._adaptador = adaptador
        self._abiertos = {}

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
            url, del_cache = enlaces.url_audio_con_cache(tema.origen)
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
            self.abrir(url, ficha, del_cache, tema)

    def abrir(self, url, ficha, vino_del_cache, tema):
        adaptador = self._adaptador
        reproductor = adaptador._instancia.media_player_new()
        if reproductor is None:
            adaptador._fallar(ficha)
            return
        if adaptador._salida_audio is not None:
            motor_vlc.fijar_salida_audio(reproductor, adaptador._salida_audio)
        if adaptador._dispositivo:
            reproductor.audio_output_device_set(None, adaptador._dispositivo)
        self._abiertos[reproductor] = {
            "tema": tema,
            "vino_del_cache": vino_del_cache,
            "sono": False,
            "reintentado": False,
        }
        try:
            media = adaptador._instancia.media_new(url)
            for opcion in _opciones_enlace():
                media.add_option(opcion)
            reproductor.set_media(media)
        except Exception as exc:
            logger.debug("No se pudo preparar el enlace: %s", exc)
            adaptador._fallar(ficha, reproductor)
            return
        reproductor.audio_set_volume(adaptador._volumen)
        adaptador._enganchar(reproductor, ficha)
        preparado_en_pausa = adaptador._pausa_pendiente
        adaptador._pausa_pendiente = False
        if not preparado_en_pausa and reproductor.play() == -1:
            adaptador._fallar(ficha, reproductor)
            return
        anterior = adaptador._actual
        adaptador._actual = reproductor
        adaptador._iniciado = not preparado_en_pausa
        adaptador._ficha_actual = ficha
        if anterior is not None:
            adaptador._soltar(anterior)

    def sonar(self, reproductor):
        """Anota que el reproductor llegó a sonar."""
        datos = self._abiertos.get(reproductor)
        if datos is not None:
            datos["sono"] = True

    def olvidar(self, reproductor):
        """Descarta lo anotado de un reproductor que se cierra."""
        self._abiertos.pop(reproductor, None)

    def manejar_error(self, ficha, reproductor) -> bool:
        """Encarga el reintento si el error fue antes de sonar y la dirección
        venía del caché. Devuelve si el reintento quedó pedido."""
        adaptador = self._adaptador
        if reproductor is None:
            return False
        with adaptador._lock:
            datos = self._abiertos.get(reproductor)
            if datos is None:
                return False
            sigue_pedida = (not adaptador._cerrado
                            and ficha == adaptador._pedida)
            if not debe_reintentar(datos["vino_del_cache"], datos["sono"],
                                   datos["reintentado"], sigue_pedida):
                return False
            datos["reintentado"] = True
            tema = datos["tema"]
            adaptador._pendiente = ficha
            adaptador._actual = None
            adaptador._iniciado = False
            adaptador._ficha_actual = None
            adaptador._cruce_largo = False
            diagnostico.crear_hilo(
                self.reintentar, "musica-enlace", args=(tema, ficha)).start()
        return True

    def reintentar(self, tema, ficha):
        """Pide la dirección fresca después de olvidar la del caché."""
        adaptador = self._adaptador
        with adaptador._lock:
            if adaptador._cerrado or ficha != adaptador._pedida:
                return
            adaptador._pendiente = ficha
        enlaces.CACHE.olvidar(enlaces.id_de_url(tema.origen))
        self.resolver(tema, ficha)

    def consumir_error(self, ficha, reproductor) -> bool:
        """Atiende un error de VLC y dice si hay que avisarlo como fallo."""
        adaptador = self._adaptador
        reintentar = self.manejar_error(ficha, reproductor)
        with adaptador._lock:
            cerrar = (reproductor is not None
                      and reproductor is not adaptador._actual)
        if cerrar:
            adaptador._soltar(reproductor)
        return not reintentar


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
