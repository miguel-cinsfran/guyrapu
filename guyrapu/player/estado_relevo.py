# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué sabe el reproductor del relevo de ffmpeg en curso.

Solo datos, sin decisiones: guarda el relevo vivo, las fuentes con las que
se puede reiniciar, el desfase y la ventana del directo, y el estado del
VOD que va en modo grabado. El panel lo lee y lo escribe por campo.
"""

from dataclasses import dataclass


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
