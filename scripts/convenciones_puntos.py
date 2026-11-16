# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué comandos del menú abren un cuadro y cuáles actúan directo.

Los rótulos van sin `&`, sin la tecla del atajo y sin los puntos
suspensivos: la regla compara el texto visible con esta clasificación y
decide si los puntos que lleva son los que le tocan. Un comando nuevo que
no esté en ninguno de los dos conjuntos es una falta.
"""

from __future__ import annotations

ABREN_CUADRO = frozenset((
    "Acerca de",
    "Actualizar yt-dlp",
    "Administrador de descargas",
    "Administrar voces",
    "Buscar actualizaciones",
    "Buscar en el chat",
    "Descargar este vídeo",
    "Elegir música",
    "Historial de directos",
    "Panel de OBS",
    "Participación en el chat",
    "Preferencias",
    "Preguntar a la IA sobre la imagen",
    "Restream",
    "Transmitir en directo",
))

ACTUAN_DIRECTO = frozenset((
    "Abrir carpeta de registros",
    "Anunciar autor del último mensaje",
    "Anunciar canción actual",
    "Anunciar encuadre de cámara",
    "Anunciar estado",
    "Avanzar 1 minuto",
    "Avanzar 10 segundos",
    "Bajar tono de la voz",
    "Bajar velocidad de la voz",
    "Bajar volumen",
    "Bajar volumen de la voz",
    "Bajar volumen del reproductor",
    "Cambiar repetición",
    "Canción anterior",
    "Cerrar OBS",
    "Conectar",
    "Consulta rápida a la IA",
    "Copiar enlace del directo",
    "Desconectar",
    "Describir escena de OBS",
    "Detener música",
    "Detener reproducción",
    "Detener voz",
    "Enviar mensaje al chat del directo (solo YouTube)",
    "Finalizando el directo",
    "Finalizar directo",
    "Guardar clip",
    "Guía de configuración de la API",
    "Iniciar o detener grabación",
    "Ir a comentarios",
    "Ir a conexión",
    "Ir a la lista del panel actual",
    "Ir al chat del directo",
    "Ir al directo",
    "Ir al reproductor",
    "Leer el mensaje 10 desde el final del chat",
    "Leer el mensaje 2 desde el final del chat",
    "Leer el mensaje 3 desde el final del chat",
    "Leer el mensaje 4 desde el final del chat",
    "Leer el mensaje 5 desde el final del chat",
    "Leer el mensaje 6 desde el final del chat",
    "Leer el mensaje 7 desde el final del chat",
    "Leer el mensaje 8 desde el final del chat",
    "Leer el mensaje 9 desde el final del chat",
    "Leer el último mensaje del chat",
    "Licencias de las voces",
    "Manual de uso",
    "Marcar incidencia",
    "Mostrar OBS",
    "Mostrar u ocultar la cámara",
    "Novedades",
    "Pantalla completa",
    "Pausar lectura",
    "Pausar o reanudar grabación",
    "Región anterior",
    "Región siguiente",
    "Reproducir o pausar",
    "Retroceder 1 minuto",
    "Retroceder 10 segundos",
    "Salir",
    "Siguiente canción",
    "Silenciar o activar audio",
    "Subir tono de la voz",
    "Subir velocidad de la voz",
    "Subir volumen",
    "Subir volumen de la voz",
    "Subir volumen del reproductor",
    "Vaciar cola",
))


def _sin_puntos(etiqueta: str) -> tuple[str, bool]:
    """El rótulo sin los puntos del final y si los llevaba."""
    for puntos in ("…", "..."):
        if etiqueta.endswith(puntos):
            return etiqueta[:-len(puntos)].rstrip(), True
    return etiqueta, False


def faltas_puntos_suspensivos(entradas: list) -> list:
    """Los comandos normales llevan puntos solo si abren un cuadro."""
    faltas = []
    for entrada in entradas:
        if entrada.tipo != "normal":
            continue
        etiqueta, lleva = _sin_puntos(entrada.etiqueta)
        if etiqueta in ABREN_CUADRO:
            if not lleva:
                faltas.append(
                    f"«{entrada.etiqueta}» abre un cuadro y no lleva "
                    "puntos suspensivos")
        elif etiqueta in ACTUAN_DIRECTO:
            if lleva:
                faltas.append(
                    f"«{entrada.etiqueta}» actúa directo y lleva "
                    "puntos suspensivos")
        else:
            faltas.append(
                f"«{entrada.etiqueta}» no está clasificado como abre un "
                "cuadro ni actúa directo")
    return faltas
