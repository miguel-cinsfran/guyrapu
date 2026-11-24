# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Declaración única de los grupos y las acciones de los atajos de teclado.

Cada acción se declara una sola vez con su tecla de fábrica, su rótulo, su
grupo, si se puede editar y si se guarda en la configuración. Las tablas
que consume el resto de la app se derivan de acá en sus propios módulos.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.idioma import N_


@dataclass(frozen=True, slots=True)
class Grupo:
    titulo: str
    modificador: str | None


@dataclass(frozen=True, slots=True)
class Accion:
    nombre: str
    tecla: str
    etiqueta: str
    grupo: Grupo
    editable: bool
    guardar: bool


REPRODUCTOR = Grupo(N_("Reproductor (Ctrl)"), "ctrl")
CHAT = Grupo(N_("Chat (Alt)"), "alt")
VENTANAS = Grupo(N_("Ventanas (Ctrl+Mayús)"), "ctrl+shift")
DIRECTO_OBS = Grupo(N_("Directo y OBS (Alt+Mayús)"), "alt+shift")
VOZ = Grupo(N_("Voz y lectura (teclas F)"), "f")
MUSICA = Grupo(N_("Música (Ctrl+Alt)"), "ctrl+alt")
INTERACCION = Grupo(N_("Interacción en directo (Ctrl+Alt+Mayús)"), "ctrl+alt+shift")
FIJOS_NAVEGACION = Grupo(N_("Ventana y navegación (fijos)"), None)
FIJOS_RECIENTES = Grupo(N_("Recientes y filtro del chat (fijos)"), None)

GRUPOS = [
    REPRODUCTOR, CHAT, VENTANAS, DIRECTO_OBS, VOZ,
    MUSICA, INTERACCION, FIJOS_NAVEGACION, FIJOS_RECIENTES,
]

ACCIONES = [
    Accion("rep_play", "ctrl+p", N_("Reproducir o pausar"), REPRODUCTOR, True, True),
    Accion("rep_retro", "ctrl+left", N_("Retroceder 1 minuto"), REPRODUCTOR, True, True),
    Accion("rep_avanz", "ctrl+right", N_("Avanzar 1 minuto"), REPRODUCTOR, True, True),
    Accion("rep_directo", "ctrl+end", N_("Ir al directo"), REPRODUCTOR, True, True),
    Accion("rep_detener", "ctrl+d", N_("Detener vídeo"), REPRODUCTOR, True, True),
    Accion("rep_mute", "ctrl+m", N_("Silenciar o activar audio"), REPRODUCTOR, True, True),
    Accion("rep_vol_menos", "ctrl+down", N_("Bajar volumen del reproductor"),
           REPRODUCTOR, True, True),
    Accion("rep_vol_mas", "ctrl+up", N_("Subir volumen del reproductor"), REPRODUCTOR, True, True),
    Accion("pantalla_completa", "ctrl+f", N_("Pantalla completa"), REPRODUCTOR, True, True),
    Accion("enviar_chat", "alt+enter", N_("Enviar mensaje al chat"), CHAT, True, True),
    Accion("buscar_chat", "alt+b", N_("Buscar en el chat"), CHAT, True, True),
    Accion("participacion_chat", "alt+p", N_("Participación en el chat"), CHAT, True, True),
    Accion("abrir_preferencias", "ctrl+shift+p", N_("Abrir Preferencias"), VENTANAS, True, True),
    Accion("abrir_historial", "ctrl+shift+h", N_("Abrir el historial de directos"),
           VENTANAS, True, True),
    Accion("abrir_restream", "ctrl+shift+r", N_("Abrir Restream"), VENTANAS, True, True),
    Accion("abrir_obs", "ctrl+shift+o", N_("Abrir panel de OBS"), VENTANAS, True, True),
    Accion("mensajes_automaticos", "ctrl+shift+a", N_("Abrir la ventana Interacción"),
           VENTANAS, True, True),
    Accion("descargas_abrir", "ctrl+shift+d", N_("Abrir Administrador de descargas"),
           VENTANAS, True, True),
    Accion("musica_ventana", "ctrl+shift+m", N_("Abrir la ventana de música"),
           VENTANAS, True, True),
    Accion("preguntar_ia", "ctrl+shift+i", N_("Preguntar a la IA sobre la imagen"),
           VENTANAS, True, True),
    # Traductores: acción del atajo que conecta el chat.
    Accion("conectar", "alt+shift+c", N_("Conectar"), DIRECTO_OBS, True, True),
    # Traductores: acción del atajo que desconecta el chat.
    Accion("desconectar", "alt+shift+d", N_("Desconectar"), DIRECTO_OBS, True, True),
    Accion("ir_lista", "alt+shift+l", N_("Ir a la lista del panel actual"),
           DIRECTO_OBS, True, True),
    Accion("copiar_enlace", "alt+shift+e", N_("Copiar enlace del directo"),
           DIRECTO_OBS, True, True),
    Accion("marcar_incidencia", "alt+shift+i", N_("Marcar incidencia"), DIRECTO_OBS, True, True),
    Accion("obs_micro", "alt+shift+m", N_("Silenciar el micrófono de OBS"),
           DIRECTO_OBS, True, True),
    Accion("obs_grabar", "alt+shift+g", N_("Iniciar o detener la grabación"),
           DIRECTO_OBS, True, True),
    Accion("obs_pausar_grabacion", "alt+shift+p", N_("Pausar o reanudar la grabación"),
           DIRECTO_OBS, True, True),
    Accion("guardar_clip", "alt+shift+r", N_("Guardar clip"), DIRECTO_OBS, True, True),
    Accion("avisos_sobrecarga", "alt+shift+a", N_("Activar o desactivar los avisos de sobrecarga"),
           DIRECTO_OBS, True, True),
    Accion("mostrar_obs", "alt+shift+o", N_("Mostrar OBS"), DIRECTO_OBS, True, True),
    Accion("pausa", "f5", N_("Pausar o reanudar lectura"), VOZ, True, True),
    Accion("detener_tts", "f8", N_("Detener voz actual"), VOZ, True, True),
    Accion("velocidad_menos", "f9", N_("Bajar velocidad de la voz"), VOZ, False, True),
    Accion("velocidad_mas", "f10", N_("Subir velocidad de la voz"), VOZ, False, True),
    Accion("volumen_menos", "f11", N_("Bajar volumen de la voz"), VOZ, False, True),
    Accion("volumen_mas", "f12", N_("Subir volumen de la voz"), VOZ, False, True),
    Accion("tono_menos", "ctrl+f9", N_("Bajar tono de la voz"), VOZ, True, True),
    Accion("tono_mas", "ctrl+f10", N_("Subir tono de la voz"), VOZ, True, True),
    Accion("silenciar_lectura", "f4", N_("Silenciar lectura"), VOZ, True, True),
    Accion("silenciar_sonidos", "f7", N_("Silenciar sonidos"), VOZ, True, True),
    Accion("anunciar_estado", "f2", N_("Anunciar estado"), VOZ, True, True),
    Accion("anunciar_autor", "f3", N_("Anunciar autor del último mensaje"), VOZ, True, True),
    Accion("describir_escena", "ctrl+f2", N_("Describir escena de OBS"), VOZ, True, True),
    Accion("consulta_rapida_ia", "ctrl+shift+f2", N_("Preguntar a la IA sobre la escena"),
           VOZ, True, True),
    Accion("anunciar_encuadre", "ctrl+f3", N_("Anunciar encuadre de cámara"), VOZ, True, True),
    Accion("avisos_encuadre", "ctrl+shift+f3", N_("Avisar si el rostro queda fuera del encuadre"),
           VOZ, True, True),
    Accion("camara_visible", "alt+f3", N_("Mostrar u ocultar la cámara"), VOZ, True, True),
    Accion("musica_play", "ctrl+alt+space", N_("Reproducir o pausar la música"),
           MUSICA, True, True),
    Accion("musica_siguiente", "ctrl+alt+right", N_("Siguiente canción"), MUSICA, True, True),
    Accion("musica_anterior", "ctrl+alt+left", N_("Canción anterior"), MUSICA, True, True),
    Accion("musica_vol_mas", "ctrl+alt+up", N_("Subir el volumen de la música"),
           MUSICA, True, True),
    Accion("musica_vol_menos", "ctrl+alt+down", N_("Bajar el volumen de la música"),
           MUSICA, True, True),
    Accion("musica_que_suena", "ctrl+alt+t", N_("Anunciar canción actual"), MUSICA, True, True),
    Accion("musica_silenciar", "ctrl+alt+m", N_("Silenciar o activar el audio de la música"),
           MUSICA, True, True),
    Accion("musica_aleatorio", "ctrl+alt+a", N_("Orden aleatorio de la música"),
           MUSICA, True, True),
    Accion("musica_repetir", "ctrl+alt+r", N_("Cambiar la repetición de la música"),
           MUSICA, True, True),
    Accion("musica_detener", "ctrl+alt+d", N_("Detener música"), MUSICA, True, True),
    Accion("musica_adelantar", "ctrl+alt+shift+right", N_("Avanzar la música 10 segundos"),
           MUSICA, True, True),
    Accion("musica_retroceder", "ctrl+alt+shift+left", N_("Retroceder la música 10 segundos"),
           MUSICA, True, True),
    Accion("video_pausar", "ctrl+alt+shift+p", N_("Pausar la cola del vídeo"),
           INTERACCION, True, True),
    Accion("video_saltar", "ctrl+alt+shift+s", N_("Omitir el mensaje del vídeo"),
           INTERACCION, True, True),
    Accion("video_vaciar", "ctrl+alt+shift+v", N_("Vaciar la cola del vídeo"),
           INTERACCION, True, True),
    Accion("video_silenciar", "ctrl+alt+shift+m", N_("Silenciar los medios"),
           INTERACCION, True, True),
    Accion("video_panico", "ctrl+alt+shift+q", N_("Modo pánico"), INTERACCION, True, True),
    Accion("mensajes_automaticos_alternar", "ctrl+alt+shift+a",
           N_("Activar o desactivar los mensajes automáticos"),
           INTERACCION, True, True),
    Accion("comandos_pausar", "ctrl+alt+shift+c", N_("Pausar los comandos del chat"),
           INTERACCION, True, True),
    Accion("encuesta_cerrar", "ctrl+alt+shift+e", N_("Cerrar la encuesta"),
           INTERACCION, True, True),
    Accion("pregunta_siguiente", "ctrl+alt+shift+r", N_("Leer la siguiente pregunta"),
           INTERACCION, True, True),
    Accion("interaccion_estado", "ctrl+alt+shift+i", N_("Estado de la interacción"),
           INTERACCION, True, True),
    Accion("salir", "alt+f4", N_("Salir de la aplicación"), FIJOS_NAVEGACION, False, False),
    Accion("region_siguiente", "f6", N_("Región siguiente"), FIJOS_NAVEGACION, False, False),
    Accion("region_anterior", "shift+f6", N_("Región anterior"), FIJOS_NAVEGACION, False, False),
    Accion("chat_reciente_1", "ctrl+shift+1", N_("Leer el último mensaje del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_reciente_2", "ctrl+shift+2", N_("Leer el mensaje 2 desde el final del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_reciente_3", "ctrl+shift+3", N_("Leer el mensaje 3 desde el final del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_reciente_4", "ctrl+shift+4", N_("Leer el mensaje 4 desde el final del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_reciente_5", "ctrl+shift+5", N_("Leer el mensaje 5 desde el final del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_reciente_6", "ctrl+shift+6", N_("Leer el mensaje 6 desde el final del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_reciente_7", "ctrl+shift+7", N_("Leer el mensaje 7 desde el final del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_reciente_8", "ctrl+shift+8", N_("Leer el mensaje 8 desde el final del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_reciente_9", "ctrl+shift+9", N_("Leer el mensaje 9 desde el final del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_reciente_10", "ctrl+shift+0", N_("Leer el mensaje 10 desde el final del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_filtro_anterior", "ctrl+shift+sc0c", N_("Filtro anterior del chat"),
           FIJOS_RECIENTES, False, False),
    Accion("chat_filtro_siguiente", "ctrl+shift+sc0d", N_("Filtro siguiente del chat"),
           FIJOS_RECIENTES, False, False),
]


def predeterminados() -> list[tuple[str, str]]:
    """Pares acción y tecla de fábrica guardables, en orden de Preferencias."""
    return [(a.nombre, a.tecla) for a in ACCIONES if a.guardar]


def fijos_defaults() -> dict[str, str]:
    """Combinaciones reservadas que no se guardan en la configuración."""
    return {a.nombre: a.tecla for a in ACCIONES if not a.guardar}


def fijos() -> set[str]:
    """Acciones cuya tecla no se puede cambiar en el editor de atajos."""
    return {a.nombre for a in ACCIONES if not a.editable}


def grupos() -> list[tuple[str, list[str]]]:
    """Título y acciones de cada grupo, en el orden de Preferencias."""
    return [(g.titulo, [a.nombre for a in ACCIONES if a.grupo is g])
            for g in GRUPOS]


def areas() -> dict[str, str | None]:
    """Modificador obligatorio por acción; None en los grupos fijos."""
    return {a.nombre: a.grupo.modificador for a in ACCIONES}


def etiquetas() -> dict[str, str]:
    """Rótulo de cada acción en el orden en que se declara."""
    return {a.nombre: a.etiqueta for a in ACCIONES}
