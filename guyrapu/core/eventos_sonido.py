# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Catálogo único de los eventos de sonido de la aplicación, en orden."""

from __future__ import annotations

from typing import NamedTuple


class EventoSonido(NamedTuple):
    """Clave, nombre visible y evento cuyo archivo usa."""

    clave: str
    nombre: str
    sonido: str | None = None


# Cada evento se declara una sola vez. El nombre es el llano para la página
# Sonidos de Preferencias: registro de la app, impersonal, sin jerga, lo
# importante primero, hasta unas seis palabras, sin repetir. Un sonido
# asignado es la clave de otro evento cuyo archivo usa; `None` es que usa
# `<clave>.wav`.
CATALOGO: tuple[EventoSonido, ...] = (
    EventoSonido("app_inicio", nombre="Inicio de la aplicación"),
    EventoSonido("conectando", nombre="Conexión en curso", sonido="espera"),
    EventoSonido("conectado", nombre="Conexión establecida", sonido="reanudar"),
    EventoSonido("desconectado", nombre="Desconexión del chat", sonido="pausa"),
    # Corte y vuelta automáticos del chat, distintos de conectar a mano.
    EventoSonido(
        "chat_cortado",
        nombre="Chat desconectado",
        sonido="transmision_problema"),
    EventoSonido(
        "chat_reconectado",
        nombre="Chat reconectado",
        sonido="transmision_recuperada"),
    EventoSonido("mensaje_nuevo", nombre="Mensaje nuevo del chat"),
    EventoSonido("mensaje_tiktok", nombre="Mensaje de TikTok"),
    EventoSonido(
        "mensaje_propietario",
        nombre="Mensaje del propietario del canal"),
    EventoSonido("mensaje_moderador", nombre="Mensaje del moderador"),
    EventoSonido(
        "mensaje_verificado",
        nombre="Mensaje de una cuenta verificada"),
    EventoSonido("mensaje_miembro", nombre="Mensaje de un miembro del canal"),
    EventoSonido("superchat", nombre="Super Chat"),
    EventoSonido("nuevo_miembro", nombre="Nuevo miembro del canal"),
    EventoSonido("error", nombre="Error"),
    EventoSonido("pausa", nombre="Lectura en pausa"),
    EventoSonido("reanudar", nombre="Lectura reanudada"),
    EventoSonido("copiar", nombre="Texto copiado"),
    EventoSonido("voz_cambiada", nombre="Voz cambiada", sonido="copiar"),
    # v0.6 online y acciones que antes reutilizaban otros sonidos:
    EventoSonido("enviado", nombre="Mensaje enviado", sonido="copiar"),
    EventoSonido("comentario", nombre="Comentario publicado", sonido="copiar"),
    EventoSonido("moderacion", nombre="Acción de moderación", sonido="copiar"),
    EventoSonido("cola_vaciada", nombre="Cola de lectura vaciada", sonido="copiar"),
    EventoSonido("transporte_en_curso", nombre="Reproductor ocupado", sonido="espera"),
    # Operación larga en curso: se repite cada dos segundos mientras espera.
    EventoSonido("espera", nombre="Espera"),
    # Eventos de TikTok y tramos de regalo por tamaño en diamantes:
    EventoSonido("seguir", nombre="Nuevo seguidor del directo"),
    EventoSonido("compartir", nombre="Alguien compartió el directo"),
    EventoSonido("cofre", nombre="Cofre de regalos recibido"),
    EventoSonido("me_gusta", nombre="Me gusta del directo"),
    EventoSonido("regalo_chico", nombre="Regalo chico recibido"),
    EventoSonido("regalo_mediano", nombre="Regalo mediano recibido"),
    EventoSonido("regalo_grande", nombre="Regalo grande recibido"),
    EventoSonido("entrada", nombre="Alguien entró al directo"),
    # Orilla de las listas y fin del directo de TikTok (suena distinto a
    # «desconectado», que sigue para YouTube y el resto de los cortes):
    EventoSonido("orilla", nombre="Principio o final de una lista"),
    EventoSonido("fin_directo", nombre="Fin del directo"),
    # Avisos del gestor de descargas, cada fin con su resultado:
    EventoSonido("descarga_iniciada", nombre="Descarga iniciada", sonido="descarga_avance"),
    EventoSonido("descarga_completada", nombre="Descarga completada"),
    EventoSonido("descarga_fallida", nombre="Descarga fallida"),
    EventoSonido("descarga_cancelada", nombre="Descarga cancelada", sonido="pausa"),
    # Avisos del supervisor de transmisión y descartes del chat:
    EventoSonido("al_aire", nombre="Directo en curso"),
    EventoSonido("transmision_detenida", nombre="Transmisión detenida"),
    EventoSonido("transmision_problema", nombre="Problema de la transmisión"),
    EventoSonido("grabacion_problema", nombre="Problema de la grabación", sonido="aviso"),
    EventoSonido("aviso", nombre="Aviso general"),
    # Vuelta de la conexión con el servicio: alivio, distinto de la alarma:
    EventoSonido("transmision_recuperada", nombre="Transmisión recuperada"),
    # Confirmación de cierre, distinta del descenso de transmision_detenida:
    EventoSonido("directo_finalizado", nombre="Cierre confirmado del directo", sonido="fin_directo"),
    # Pregunta antes de transmitir a TikTok cuando Restream manda a otros
    # destinos encendidos.
    EventoSonido("destinos_de_mas", nombre="Otros destinos de Restream", sonido="aviso"),
    # Ventanas que se abren solas al arrancar o al terminar bien:
    EventoSonido(
        "actualizacion_disponible",
        nombre="Actualización disponible"),
    EventoSonido(
        "actualizacion_lista",
        nombre="Actualización lista para instalar",
        sonido="copiar"),
    # Música: cambio, fin, fallo e igualación al medir muchas canciones:
    EventoSonido("musica_tema", nombre="Canción cambiada"),
    EventoSonido("musica_fin", nombre="Canción terminada"),
    EventoSonido("musica_fallo", nombre="Error al reproducir la canción"),
    EventoSonido("musica_igualando", nombre="Igualación del volumen"),
    # Preguntar a la IA: consulta que sale, espera que suena, respuesta que
    # llega, fallo, captura agregada, consulta cancelada y captura negra:
    EventoSonido("ia_enviada", nombre="Consulta enviada a la IA", sonido="espera"),
    EventoSonido("ia_respuesta", nombre="Respuesta de la IA"),
    EventoSonido("ia_error", nombre="Error de la IA", sonido="error"),
    EventoSonido("ia_analizando", nombre="La IA está analizando"),
    EventoSonido("ia_captura", nombre="Captura agregada", sonido="copiar"),
    EventoSonido("ia_cancelada", nombre="Consulta a la IA cancelada", sonido="pausa"),
    EventoSonido("ia_imagen_negra", nombre="Captura negra detectada", sonido="error"),
    # Atajos globales que otro programa ya ocupa: tono de ocupado.
    EventoSonido("atajos_ocupados", nombre="Atajos globales ocupados", sonido="aviso"),
    # El micrófono quedó activado y en tres segundos no entró nada.
    EventoSonido("microfono_sin_senal", nombre="Micrófono sin señal"),
    # Nivel del micrófono en la prueba por tramos: bien o para revisar.
    EventoSonido("microfono_bien", nombre="Micrófono con buen nivel"),
    EventoSonido(
        "microfono_revisar",
        nombre="Nivel del micrófono para revisar"),
    # Pausa del directo de TikTok y su vuelta: cada una con su sonido.
    EventoSonido("directo_pausado", nombre="Directo de TikTok en pausa"),
    EventoSonido("directo_reanudado", nombre="Directo de TikTok continúa"),
    # Búsqueda de descargas: pedido, con filas, vacía y con fallo.
    EventoSonido("busqueda_iniciada", nombre="Búsqueda en curso", sonido="espera"),
    EventoSonido("busqueda_resultados", nombre="Búsqueda con resultados", sonido="copiar"),
    EventoSonido("busqueda_sin_resultados", nombre="Búsqueda sin resultados", sonido="copiar"),
    EventoSonido("busqueda_fallida", nombre="Búsqueda fallida", sonido="error"),
    # Cola de descargas: agregado, proceso, fin de la cola y lista parcial.
    EventoSonido("descarga_encolada", nombre="Descarga agregada a la cola", sonido="copiar"),
    EventoSonido("descarga_procesando", nombre="Procesamiento de descarga", sonido="descarga_avance"),
    EventoSonido(
        "cola_descargas_terminada",
        nombre="Cola de descargas terminada"),
    EventoSonido("descarga_parcial", nombre="Descarga parcial", sonido="descarga_fallida"),
    # Elección de formato de un vídeo: consulta y fallo, cada uno con el suyo.
    EventoSonido("formatos_cargando", nombre="Carga de formatos", sonido="espera"),
    EventoSonido("formatos_fallidos", nombre="Formatos no disponibles", sonido="error"),
    # TikTok frena las consultas seguidas: espera un minuto antes de mirar.
    EventoSonido("tiktok_limitado", nombre="TikTok limita las consultas", sonido="espera"),
    # Encuadre de cámara: el rostro sale y vuelve, cada uno con el suyo.
    EventoSonido("encuadre_fuera", nombre="Rostro fuera del encuadre"),
    EventoSonido("encuadre_dentro", nombre="Rostro de vuelta en el encuadre"),
    # Grabación desde la ventana de Transmisión, cada resultado con el suyo.
    EventoSonido("grabacion_iniciada", nombre="Grabación iniciada", sonido="reanudar"),
    EventoSonido("grabacion_detenida", nombre="Grabación detenida", sonido="pausa"),
    EventoSonido("grabacion_en_pausa", nombre="Grabación en pausa", sonido="pausa"),
    EventoSonido("grabacion_reanudada", nombre="Grabación reanudada", sonido="reanudar"),
    # Clip de los últimos segundos guardado con el búfer de repetición.
    EventoSonido("clip", nombre="Clip guardado", sonido="copiar"),
    # Reconexión del relevo de un directo de YouTube: intento y aviso final.
    EventoSonido("reconectando_directo", nombre="Reconexión del directo", sonido="transmision_problema"),
    EventoSonido("directo_con_cortes", nombre="Directo con cortes seguidos", sonido="transmision_problema"),
    # Estado de Restream por su WebSocket: destinos y señal de OBS.
    EventoSonido(
        "restream_destino_caido",
        nombre="Destino de Restream desconectado",
        sonido="transmision_problema"),
    EventoSonido(
        "restream_destino_vuelve",
        nombre="Destino de Restream de vuelta",
        sonido="transmision_recuperada"),
    EventoSonido("restream_sin_senal", nombre="Restream sin señal", sonido="transmision_problema"),
    EventoSonido(
        "restream_senal_vuelve",
        nombre="Señal de Restream recuperada",
        sonido="transmision_recuperada"),
    EventoSonido("restream_senal_debil", nombre="Señal débil en Restream", sonido="aviso"),
    # Avance de una descarga en curso y descarga que sigue en cero.
    EventoSonido("descarga_avance", nombre="Avance de descarga"),
    EventoSonido("descarga_quieta", nombre="Descarga quieta"),
    # Encuestas del directo de TikTok: apertura y cierre.
    EventoSonido("encuesta", nombre="Encuesta abierta"),
    EventoSonido("encuesta_fin", nombre="Encuesta terminada"),
    # Metas y batallas del directo de TikTok.
    EventoSonido("meta", nombre="Meta cumplida"),
    EventoSonido("batalla", nombre="Batalla iniciada"),
    EventoSonido("batalla_fin", nombre="Batalla terminada"),
    # El vigilante de OBS: deja de responder y vuelve.
    EventoSonido(
        "obs_sin_respuesta",
        nombre="OBS no responde",
        sonido="transmision_problema"),
    EventoSonido(
        "obs_responde",
        nombre="OBS vuelve a responder",
        sonido="transmision_recuperada"),
    # Acciones pedidas por el usuario que salen bien, sus pasos de espera y
    # el fin o el corte de lo que se mira en el reproductor.
    EventoSonido("listo", nombre="Acción completada", sonido="copiar"),
    EventoSonido(
        "transmision_paso",
        nombre="Preparación de la transmisión",
        sonido="espera"),
    EventoSonido(
        "reproduccion_terminada",
        nombre="Reproducción finalizada",
        sonido="fin_directo"),
    EventoSonido(
        "reproduccion_cortada",
        nombre="Reproducción interrumpida",
        sonido="transmision_problema"),
)

EVENTOS = [evento.clave for evento in CATALOGO]

# Nombre llano de cada evento, en el orden del catálogo.
NOMBRES = {evento.clave: evento.nombre for evento in CATALOGO}

# Sonido con el que suena cada evento que no usa su propio archivo. Un
# evento fuera de la tabla suena con `<evento>.wav`.
SONIDOS = {evento.clave: evento.sonido for evento in CATALOGO
           if evento.sonido is not None}
