# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Catálogo único de los eventos de sonido de la aplicación, en orden."""

from __future__ import annotations

from typing import NamedTuple

from guyrapu.core.idioma import N_


class EventoSonido(NamedTuple):
    """Clave, nombre visible, evento cuyo archivo usa y familia."""

    clave: str
    nombre: str
    sonido: str | None = None
    familia: str | None = None


# Familias en el orden en que se muestran, con su nombre visible.
FAMILIAS: tuple[tuple[str, str], ...] = (
    # Traductores: familia de los sonidos de acciones que salen bien.
    ("completado", N_("Completado")),
    # Traductores: familia de los sonidos de error.
    ("error", N_("Error")),
    # Traductores: familia de los sonidos de algo en curso o en espera.
    ("en_curso", N_("En curso")),
    # Traductores: familia de los sonidos de algo que se enciende o vuelve.
    ("activado", N_("Activado")),
    # Traductores: familia de los sonidos de algo que se apaga o se detiene.
    ("desactivado", N_("Desactivado")),
    # Traductores: familia de los sonidos de advertencia.
    ("advertencia", N_("Advertencia")),
    # Traductores: familia de los sonidos de algo en vivo que se cae.
    ("desconexion", N_("Desconexión")),
    # Traductores: familia de los sonidos de algo en vivo que vuelve.
    ("reconexion", N_("Reconexión")),
    # Traductores: familia de los sonidos de la transmisión y el directo.
    ("transmision", N_("Transmisión y directo")),
    # Traductores: familia de los sonidos del chat.
    ("chat", N_("Chat")),
    # Traductores: familia de los sonidos de las descargas.
    ("descargas", N_("Descargas")),
    # Traductores: familia de los sonidos de la inteligencia artificial.
    ("ia", N_("Inteligencia artificial")),
    # Traductores: familia de los sonidos de la música.
    ("musica", N_("Música")),
    # Traductores: familia de los sonidos de los indicadores.
    ("indicadores", N_("Indicadores")),
    # Traductores: familia de los sonidos de la aplicación.
    ("aplicacion", N_("Aplicación")),
)

# Cada evento se declara una sola vez. El nombre es el llano para la página
# Sonidos de Preferencias: registro de la app, impersonal, sin jerga, lo
# importante primero, hasta unas seis palabras, sin repetir. Un sonido
# asignado es la clave de otro evento cuyo archivo usa; `None` es que usa
# `<clave>.wav`. Las entradas van agrupadas por familia, en el orden de
# `FAMILIAS`, porque la página las muestra así.
CATALOGO: tuple[EventoSonido, ...] = (
    # Acciones pedidas por el usuario que salen bien, sus pasos de espera y
    # el fin o el corte de lo que se mira en el reproductor.
    EventoSonido("listo", nombre=N_("Acción completada"), sonido="copiar",
                 familia="completado"),
    EventoSonido("copiar", nombre=N_("Texto copiado"), familia="completado"),
    EventoSonido("voz_cambiada", nombre=N_("Voz cambiada"), sonido="copiar",
                 familia="completado"),
    # v0.6 online y acciones que antes reutilizaban otros sonidos:
    EventoSonido("enviado", nombre=N_("Mensaje enviado"), sonido="copiar",
                 familia="completado"),
    EventoSonido("comentario", nombre=N_("Comentario publicado"), sonido="copiar",
                 familia="completado"),
    EventoSonido("moderacion", nombre=N_("Acción de moderación"), sonido="copiar",
                 familia="completado"),
    EventoSonido("cola_vaciada", nombre=N_("Cola de lectura vaciada"), sonido="copiar",
                 familia="completado"),
    EventoSonido("clip", nombre=N_("Clip guardado"), sonido="copiar",
                 familia="completado"),
    EventoSonido("ia_captura", nombre=N_("Captura agregada"), sonido="copiar",
                 familia="completado"),
    EventoSonido("busqueda_resultados", nombre=N_("Búsqueda con resultados"), sonido="copiar",
                 familia="completado"),
    EventoSonido("busqueda_sin_resultados", nombre=N_("Búsqueda sin resultados"), sonido="copiar",
                 familia="completado"),
    EventoSonido("descarga_encolada", nombre=N_("Descarga agregada a la cola"), sonido="copiar",
                 familia="completado"),
    # Ventanas que se abren solas al arrancar o al terminar bien:
    EventoSonido("actualizacion_lista",
                 nombre=N_("Actualización lista para instalar"),
                 sonido="copiar", familia="completado"),
    EventoSonido("error", nombre=N_("Error"), familia="error"),
    EventoSonido("ia_error", nombre=N_("Error de la IA"), sonido="error",
                 familia="error"),
    EventoSonido("busqueda_fallida", nombre=N_("Búsqueda fallida"), sonido="error",
                 familia="error"),
    # Elección de formato de un vídeo: consulta y fallo, cada uno con el suyo.
    EventoSonido("formatos_fallidos", nombre=N_("Formatos no disponibles"), sonido="error",
                 familia="error"),
    EventoSonido("ia_imagen_negra", nombre=N_("Captura negra detectada"), sonido="error",
                 familia="error"),
    # Operación larga en curso: se repite cada dos segundos mientras espera.
    EventoSonido("espera", nombre=N_("Espera"), familia="en_curso"),
    EventoSonido("conectando", nombre=N_("Conexión en curso"), sonido="espera",
                 familia="en_curso"),
    EventoSonido("transporte_en_curso", nombre=N_("Reproductor ocupado"), sonido="espera",
                 familia="en_curso"),
    # Preguntar a la IA: consulta que sale, espera que suena, respuesta que
    # llega, fallo, captura agregada, consulta cancelada y captura negra:
    EventoSonido("ia_enviada", nombre=N_("Consulta enviada a la IA"), sonido="espera",
                 familia="en_curso"),
    # Búsqueda de descargas: pedido, con filas, vacía y con fallo.
    EventoSonido("busqueda_iniciada", nombre=N_("Búsqueda en curso"), sonido="espera",
                 familia="en_curso"),
    # Elección de formato de un vídeo: consulta y fallo, cada uno con el suyo.
    EventoSonido("formatos_cargando", nombre=N_("Carga de formatos"), sonido="espera",
                 familia="en_curso"),
    # TikTok frena las consultas seguidas: espera un minuto antes de mirar.
    EventoSonido("tiktok_limitado", nombre=N_("TikTok limita las consultas"), sonido="espera",
                 familia="en_curso"),
    EventoSonido("transmision_paso",
                 nombre=N_("Preparación de la transmisión"),
                 sonido="espera", familia="en_curso"),
    EventoSonido("reanudar", nombre=N_("Lectura reanudada"), familia="activado"),
    EventoSonido("conectado", nombre=N_("Conexión establecida"), sonido="reanudar",
                 familia="activado"),
    # Grabación desde la ventana de Transmisión, cada resultado con el suyo.
    EventoSonido("grabacion_iniciada", nombre=N_("Grabación iniciada"), sonido="reanudar",
                 familia="activado"),
    EventoSonido("grabacion_reanudada", nombre=N_("Grabación reanudada"), sonido="reanudar",
                 familia="activado"),
    EventoSonido("pausa", nombre=N_("Lectura en pausa"), familia="desactivado"),
    EventoSonido("desconectado", nombre=N_("Desconexión del chat"), sonido="pausa",
                 familia="desactivado"),
    # Grabación desde la ventana de Transmisión, cada resultado con el suyo.
    EventoSonido("grabacion_detenida", nombre=N_("Grabación detenida"), sonido="pausa",
                 familia="desactivado"),
    EventoSonido("grabacion_en_pausa", nombre=N_("Grabación en pausa"), sonido="pausa",
                 familia="desactivado"),
    # Preguntar a la IA: consulta que sale, espera que suena, respuesta que
    # llega, fallo, captura agregada, consulta cancelada y captura negra:
    EventoSonido("ia_cancelada", nombre=N_("Consulta a la IA cancelada"), sonido="pausa",
                 familia="desactivado"),
    # Avisos del gestor de descargas, cada fin con su resultado:
    EventoSonido("descarga_cancelada", nombre=N_("Descarga cancelada"), sonido="pausa",
                 familia="desactivado"),
    EventoSonido("aviso", nombre=N_("Aviso general"), familia="advertencia"),
    EventoSonido("grabacion_problema", nombre=N_("Problema de la grabación"), sonido="aviso",
                 familia="advertencia"),
    # Pregunta antes de transmitir a TikTok cuando Restream manda a otros
    # destinos encendidos.
    EventoSonido("destinos_de_mas", nombre=N_("Otros destinos de Restream"), sonido="aviso",
                 familia="advertencia"),
    # Atajos globales que otro programa ya ocupa: tono de ocupado.
    EventoSonido("atajos_ocupados", nombre=N_("Atajos globales ocupados"), sonido="aviso",
                 familia="advertencia"),
    # Estado de Restream por su WebSocket: destinos y señal de OBS.
    EventoSonido("restream_senal_debil", nombre=N_("Señal débil en Restream"), sonido="aviso",
                 familia="advertencia"),
    # Avisos del supervisor de transmisión y descartes del chat:
    EventoSonido("transmision_problema", nombre=N_("Problema de la transmisión"),
                 familia="desconexion"),
    # Reconexión del relevo de un directo de YouTube: intento y aviso final.
    EventoSonido("reconectando_directo", nombre=N_("Reconexión del directo"), sonido="transmision_problema",
                 familia="desconexion"),
    EventoSonido("directo_con_cortes", nombre=N_("Directo con cortes seguidos"), sonido="transmision_problema",
                 familia="desconexion"),
    # Estado de Restream por su WebSocket: destinos y señal de OBS.
    EventoSonido("restream_destino_caido",
                 nombre=N_("Destino de Restream desconectado"),
                 sonido="transmision_problema", familia="desconexion"),
    EventoSonido("restream_sin_senal", nombre=N_("Restream sin señal"), sonido="transmision_problema",
                 familia="desconexion"),
    # Corte y vuelta automáticos del chat, distintos de conectar a mano.
    EventoSonido("chat_cortado", nombre=N_("Chat desconectado"), sonido="transmision_problema",
                 familia="desconexion"),
    # El vigilante de OBS: deja de responder y vuelve.
    EventoSonido("obs_sin_respuesta", nombre=N_("OBS no responde"), sonido="transmision_problema",
                 familia="desconexion"),
    EventoSonido("reproduccion_cortada", nombre=N_("Reproducción interrumpida"), sonido="transmision_problema",
                 familia="desconexion"),
    # Vuelta de la conexión con el servicio: alivio, distinto de la alarma:
    EventoSonido("transmision_recuperada", nombre=N_("Transmisión recuperada"),
                 familia="reconexion"),
    # Estado de Restream por su WebSocket: destinos y señal de OBS.
    EventoSonido("restream_destino_vuelve",
                 nombre=N_("Destino de Restream de vuelta"),
                 sonido="transmision_recuperada", familia="reconexion"),
    EventoSonido("restream_senal_vuelve",
                 nombre=N_("Señal de Restream recuperada"),
                 sonido="transmision_recuperada", familia="reconexion"),
    # Corte y vuelta automáticos del chat, distintos de conectar a mano.
    EventoSonido("chat_reconectado", nombre=N_("Chat reconectado"), sonido="transmision_recuperada",
                 familia="reconexion"),
    # El vigilante de OBS: deja de responder y vuelve.
    EventoSonido("obs_responde", nombre=N_("OBS vuelve a responder"), sonido="transmision_recuperada",
                 familia="reconexion"),
    EventoSonido("al_aire", nombre=N_("Directo en curso"), familia="transmision"),
    EventoSonido("transmision_detenida", nombre=N_("Transmisión detenida"),
                 familia="transmision"),
    EventoSonido("fin_directo", nombre=N_("Fin del directo"), familia="transmision"),
    # Confirmación de cierre, distinta del descenso de transmision_detenida:
    EventoSonido("directo_finalizado", nombre=N_("Cierre confirmado del directo"), sonido="fin_directo",
                 familia="transmision"),
    EventoSonido("reproduccion_terminada", nombre=N_("Reproducción finalizada"), sonido="fin_directo",
                 familia="transmision"),
    # Pausa del directo de TikTok y su vuelta: cada una con su sonido.
    EventoSonido("directo_pausado", nombre=N_("Directo de TikTok en pausa"),
                 familia="transmision"),
    EventoSonido("directo_reanudado", nombre=N_("Directo de TikTok continúa"),
                 familia="transmision"),
    EventoSonido("mensaje_nuevo", nombre=N_("Mensaje nuevo del chat"),
                 familia="chat"),
    EventoSonido("mensaje_tiktok", nombre=N_("Mensaje de TikTok"), familia="chat"),
    EventoSonido("mensaje_propietario",
                 nombre=N_("Mensaje del propietario del canal"), familia="chat"),
    EventoSonido("mensaje_moderador", nombre=N_("Mensaje del moderador"),
                 familia="chat"),
    EventoSonido("mensaje_verificado",
                 nombre=N_("Mensaje de una cuenta verificada"), familia="chat"),
    EventoSonido("mensaje_miembro", nombre=N_("Mensaje de un miembro del canal"),
                 familia="chat"),
    EventoSonido("superchat", nombre=N_("Super Chat"), familia="chat"),
    EventoSonido("nuevo_miembro", nombre=N_("Nuevo miembro del canal"),
                 familia="chat"),
    # Eventos de TikTok y tramos de regalo por tamaño en diamantes:
    EventoSonido("seguir", nombre=N_("Nuevo seguidor del directo"),
                 familia="chat"),
    EventoSonido("compartir", nombre=N_("Alguien compartió el directo"),
                 familia="chat"),
    EventoSonido("cofre", nombre=N_("Cofre de regalos recibido"), familia="chat"),
    EventoSonido("me_gusta", nombre=N_("Me gusta del directo"), familia="chat"),
    EventoSonido("regalo_chico", nombre=N_("Regalo chico recibido"),
                 familia="chat"),
    EventoSonido("regalo_mediano", nombre=N_("Regalo mediano recibido"),
                 familia="chat"),
    EventoSonido("regalo_grande", nombre=N_("Regalo grande recibido"),
                 familia="chat"),
    EventoSonido("entrada", nombre=N_("Alguien entró al directo"),
                 familia="chat"),
    # Encuestas del directo de TikTok: apertura y cierre.
    EventoSonido("encuesta", nombre=N_("Encuesta abierta"), familia="chat"),
    EventoSonido("encuesta_fin", nombre=N_("Encuesta terminada"), familia="chat"),
    # Metas y batallas del directo de TikTok.
    EventoSonido("meta", nombre=N_("Meta cumplida"), familia="chat"),
    EventoSonido("batalla", nombre=N_("Batalla iniciada"), familia="chat"),
    EventoSonido("batalla_fin", nombre=N_("Batalla terminada"), familia="chat"),
    # Avisos del gestor de descargas, cada fin con su resultado:
    EventoSonido("descarga_iniciada", nombre=N_("Descarga iniciada"), sonido="descarga_avance",
                 familia="descargas"),
    EventoSonido("descarga_procesando", nombre=N_("Procesamiento de descarga"), sonido="descarga_avance",
                 familia="descargas"),
    # Avance de una descarga en curso y descarga que sigue en cero.
    EventoSonido("descarga_avance", nombre=N_("Avance de descarga"),
                 familia="descargas"),
    EventoSonido("descarga_quieta", nombre=N_("Descarga quieta"),
                 familia="descargas"),
    EventoSonido("descarga_completada", nombre=N_("Descarga completada"),
                 familia="descargas"),
    EventoSonido("descarga_fallida", nombre=N_("Descarga fallida"),
                 familia="descargas"),
    # Cola de descargas: agregado, proceso, fin de la cola y lista parcial.
    EventoSonido("descarga_parcial", nombre=N_("Descarga parcial"), sonido="descarga_fallida",
                 familia="descargas"),
    EventoSonido("cola_descargas_terminada",
                 nombre=N_("Cola de descargas terminada"), familia="descargas"),
    EventoSonido("ia_analizando", nombre=N_("La IA está analizando"),
                 familia="ia"),
    EventoSonido("ia_respuesta", nombre=N_("Respuesta de la IA"), familia="ia"),
    # Música: cambio, fin, fallo e igualación al medir muchas canciones:
    EventoSonido("musica_tema", nombre=N_("Canción cambiada"), familia="musica"),
    EventoSonido("musica_fin", nombre=N_("Canción terminada"), familia="musica"),
    EventoSonido("musica_fallo", nombre=N_("Error al reproducir la canción"),
                 familia="musica"),
    EventoSonido("musica_igualando", nombre=N_("Igualación del volumen"),
                 familia="musica"),
    # Orilla de las listas y fin del directo de TikTok (suena distinto a
    # «desconectado», que sigue para YouTube y el resto de los cortes):
    EventoSonido("orilla", nombre=N_("Principio o final de una lista"),
                 familia="indicadores"),
    # Encuadre de cámara: el rostro sale y vuelve, cada uno con el suyo.
    EventoSonido("encuadre_fuera", nombre=N_("Rostro fuera del encuadre"),
                 familia="indicadores"),
    EventoSonido("encuadre_dentro", nombre=N_("Rostro de vuelta en el encuadre"),
                 familia="indicadores"),
    # Nivel del micrófono en la prueba por tramos: bien o para revisar.
    EventoSonido("microfono_bien", nombre=N_("Micrófono con buen nivel"),
                 familia="indicadores"),
    EventoSonido("microfono_revisar",
                 nombre=N_("Nivel del micrófono para revisar"),
                 familia="indicadores"),
    # El micrófono quedó activado y en tres segundos no entró nada.
    EventoSonido("microfono_sin_senal", nombre=N_("Micrófono sin señal"),
                 familia="indicadores"),
    # Ventanas que se abren solas al arrancar o al terminar bien:
    EventoSonido("app_inicio", nombre=N_("Inicio de la aplicación"),
                 familia="aplicacion"),
    EventoSonido("actualizacion_disponible",
                 nombre=N_("Actualización disponible"), familia="aplicacion"),
)

EVENTOS = [evento.clave for evento in CATALOGO]

# Nombre llano de cada evento, en el orden del catálogo.
NOMBRES = {evento.clave: evento.nombre for evento in CATALOGO}

# Sonido con el que suena cada evento que no usa su propio archivo. Un
# evento fuera de la tabla suena con `<evento>.wav`.
SONIDOS = {evento.clave: evento.sonido for evento in CATALOGO
           if evento.sonido is not None}
