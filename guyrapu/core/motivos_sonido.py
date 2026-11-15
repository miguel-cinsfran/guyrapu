# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Por qué suena cada evento del catálogo de sonidos."""

from __future__ import annotations

# Motivo de cada evento, agrupados en el orden en que se decide: ante la duda
# entre dos, gana el primero que encaje.
MOTIVOS: dict[str, tuple[str, ...]] = {
    # El sonido es la única información.
    "sin_texto": (
        "orilla",
        "encuadre_fuera",
        "encuadre_dentro",
        "microfono_bien",
        "microfono_revisar",
        "microfono_sin_senal",
    ),
    # La app avisa sin que el usuario lo pida.
    "llega_solo": (
        "actualizacion_lista",
        "aviso",
        "destinos_de_mas",
        "restream_senal_debil",
        "transmision_problema",
        "reconectando_directo",
        "directo_con_cortes",
        "restream_destino_caido",
        "restream_sin_senal",
        "chat_cortado",
        "obs_sin_respuesta",
        "reproduccion_cortada",
        "transmision_recuperada",
        "restream_destino_vuelve",
        "restream_senal_vuelve",
        "chat_reconectado",
        "obs_responde",
        "fin_directo",
        "directo_pausado",
        "directo_reanudado",
        "mensaje_nuevo",
        "mensaje_tiktok",
        "mensaje_propietario",
        "mensaje_moderador",
        "mensaje_verificado",
        "mensaje_miembro",
        "superchat",
        "nuevo_miembro",
        "seguir",
        "compartir",
        "cofre",
        "me_gusta",
        "regalo_chico",
        "regalo_mediano",
        "regalo_grande",
        "entrada",
        "encuesta",
        "encuesta_fin",
        "meta",
        "batalla",
        "batalla_fin",
        "descarga_quieta",
        "descarga_completada",
        "cola_descargas_terminada",
        "actualizacion_disponible",
    ),
    # Algo falló.
    "error": (
        "error",
        "ia_error",
        "busqueda_fallida",
        "formatos_fallidos",
        "ia_imagen_negra",
        "grabacion_problema",
        "atajos_ocupados",
        "descarga_fallida",
        "descarga_parcial",
        "musica_fallo",
    ),
    # Terminó bien algo que el usuario pidió y tardó.
    "fin_de_espera": (
        "listo",
        "copiar",
        "voz_cambiada",
        "enviado",
        "comentario",
        "moderacion",
        "cola_vaciada",
        "clip",
        "ia_captura",
        "busqueda_resultados",
        "busqueda_sin_resultados",
        "descarga_encolada",
        "conectado",
        "al_aire",
        "directo_finalizado",
        "reproduccion_terminada",
        "ia_respuesta",
        "musica_igualada",
        "app_inicio",
    ),
    # Algo pedido sigue en curso.
    "en_espera": (
        "espera",
        "conectando",
        "transporte_en_curso",
        "ia_enviada",
        "busqueda_iniciada",
        "formatos_cargando",
        "tiktok_limitado",
        "transmision_paso",
        "descarga_iniciada",
        "descarga_procesando",
        "descarga_avance",
        "ia_analizando",
        "musica_igualando",
    ),
    # Prender o apagar algo cuyo estado no se oye.
    "estado": (
        "reanudar",
        "grabacion_iniciada",
        "grabacion_reanudada",
        "pausa",
        "desconectado",
        "grabacion_detenida",
        "grabacion_en_pausa",
        "ia_cancelada",
        "descarga_cancelada",
        "transmision_detenida",
    ),
    # El eco de algo que el usuario ya oye.
    "opcional": (
        "musica_tema",
        "musica_fin",
    ),
}

# Motivo de cada evento, para consultarlo por su clave.
MOTIVO_POR_CLAVE: dict[str, str] = {
    clave: motivo
    for motivo, claves in MOTIVOS.items()
    for clave in claves
}
