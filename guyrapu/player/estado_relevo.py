# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué sabe el reproductor del relevo de ffmpeg y cómo cambia ese estado.

Guarda el relevo vivo, las fuentes con las que se puede reiniciar, el
desfase y la ventana del directo, y el estado del VOD que va en modo
grabado. Cada transición es un método con nombre. No conoce la interfaz:
las reaperturas agendadas se detienen con su Stop() y el relevo con su
detener().
"""

from dataclasses import dataclass

from guyrapu.core import diagnostico

logger = diagnostico.obtener_logger(__name__)


@dataclass
class EstadoRelevo:
    """Estado del relevo en curso, con los valores de un panel recién abierto."""

    # Relevo de ffmpeg para directos con vídeo y audio separados (ver
    # relevo_ffmpeg.py): evita el input-slave de VLC, que pierde la
    # sincronía entre dos HLS independientemente en vivo cada 60-90 s.
    ffmpeg: object = None
    gen: int = 0
    # Búsqueda en directo por relevo: fuentes (vídeo, audio) para poder
    # reiniciar ffmpeg, segmentos por detrás del borde y ventana HLS
    # (s por segmento, segmentos) leída al arrancar. Ver _saltar_en_relevo.
    fuentes: tuple | None = None
    desfase: int = 0
    ventana: tuple | None = None
    # VOD por relevo en modo grabado (ver _ir_a): base en ms desde la
    # que arranca el flujo reabierto; None salvo mientras hay relevo.
    vod_base_ms: int | None = None
    vod_ultima: int | None = None
    vod_recuperaciones: int = 0
    reintentos: int = 0
    # Reapertura agendada por _ir_a (debounce de 400 ms) y contador de
    # recuperaciones tras un corte a mitad del vídeo (ver _on_timer).
    vod_reapertura: object = None
    # Destino guardado al mover la posición con el VOD por relevo en
    # pausa: no se reabre el relevo hasta reanudar (ver _ir_a). None
    # salvo mientras hay un salto en pausa pendiente de reanudar.
    vod_destino_en_pausa: int | None = None
    # Reapertura agendada por _saltar_en_relevo con el mismo debounce:
    # cada pulsación anuncia al instante y el reinicio de ffmpeg espera
    # 400 ms por si viene otra pulsación encadenada (ver _saltar_en_relevo).
    directo_reapertura: object = None
    # Dice si este vídeo va en modo relevo grabado. Sobrevive a las
    # reaperturas: la base se limpia en cada una, esta bandera no.
    vod_por_relevo: bool = False

    def detener_reapertura_vod(self) -> None:
        pendiente = self.vod_reapertura
        if pendiente is not None:
            try:
                pendiente.Stop()
            except Exception as error:
                logger.debug("no se pudo detener la reapertura pendiente: %s", error)

    def soltar(self) -> None:
        self.detener_reapertura_vod()
        self.vod_reapertura = None
        directa = self.directo_reapertura
        self.directo_reapertura = None
        if directa is not None:
            try:
                directa.Stop()
            except Exception as error:
                logger.debug("no se pudo detener la reapertura directa: %s", error)
        self.vod_destino_en_pausa = None
        relevo = self.ffmpeg
        self.ffmpeg = None
        self.vod_base_ms = None
        if relevo is not None:
            relevo.detener()

    def olvidar_vod(self) -> None:
        self.vod_por_relevo = False
        self.vod_destino_en_pausa = None
        self.vod_recuperaciones = 0
        self.vod_ultima = None

    def al_detener(self) -> None:
        """Limpia lo que el panel deja al detener, después de llamar a
        _detener_relevo_ffmpeg, que hace el soltar()."""
        self.fuentes = None
        self.desfase = 0
        self.ventana = None
        self.olvidar_vod()

    def nueva_generacion(self) -> int:
        self.gen = self.gen + 1
        return self.gen

    def adoptar(self, relevo, fuentes, desfase=0, inicio_ms=None) -> None:
        """El relevo arrancó: lo adopta. Con inicio_ms es el modo grabado y
        deja la base y la última en ese punto; sin él es el directo."""
        self.ffmpeg = relevo
        self.fuentes = fuentes
        self.desfase = int(desfase or 0)
        self.reintentos = 0
        if inicio_ms is None:
            self.vod_base_ms = None
        else:
            self.vod_base_ms = int(inicio_ms)
            self.vod_ultima = int(inicio_ms)

    def fallo_al_arrancar(self, grabado: bool) -> None:
        self.ffmpeg = None
        self.fuentes = None
        self.desfase = 0
        if grabado:
            self.vod_base_ms = None
            self.vod_por_relevo = False
