# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué trae sounds.ini de fábrica y cómo se le pasa a quien ya tiene la app."""

from __future__ import annotations

from guyrapu.core import archivos, diagnostico, paths, sonidos_ini
from guyrapu.core.eventos_sonido import EVENTOS
from guyrapu.core.ini_tipado import leer_booleano


logger = diagnostico.obtener_logger(__name__)

# La nueva vale 1. Se graba en `[sesion] version_sonidos`.
VERSION_SONIDOS = 1

TEXTO_FABRICA = """[sonidos]
volumen = 0.7
# Tema: carpeta en sounds/themes/ con un WAV por sonido y, si hace falta, uno
# con el nombre de un evento. Copia default a mi_tema y pon: tema = mi_tema
tema = default
# Archivos de fábrica:
# app_inicio, mensaje_nuevo, mensaje_tiktok, mensaje_propietario, mensaje_moderador, mensaje_verificado
# mensaje_miembro, superchat, nuevo_miembro, error, pausa, reanudar, copiar, espera, seguir, compartir, cofre, me_gusta
# regalo_chico, regalo_mediano, regalo_grande, entrada, orilla, fin_directo, descarga_completada, descarga_fallida
# al_aire, transmision_detenida, transmision_problema, aviso, transmision_recuperada, actualizacion_disponible
# musica_tema, musica_fin, musica_fallo, musica_igualando, musica_igualada, ia_respuesta, ia_analizando
# microfono_bien, microfono_revisar, directo_pausado, directo_reanudado, cola_descargas_terminada, microfono_sin_senal
# encuadre_dentro, encuadre_fuera, descarga_avance, descarga_quieta, encuesta, encuesta_fin, meta, batalla, batalla_fin
# musica_tema, musica_fin y alerta_en_video vienen callados: se activan en Preferencias, Sonidos.
musica_tema =
musica_fin =
alerta_en_video =
"""


def _callar_musica_tema() -> None:
    """Calla el cambio de canción en el sounds.ini del usuario, si existe.

    Se parte de los callados actuales para no activar ninguno de paso.
    """
    ruta = paths.sounds_ini()
    if not ruta.exists():
        return
    try:
        texto = ruta.read_text(encoding="utf-8")
        callados = sonidos_ini.silenciados(texto)
        if "musica_tema" in callados:
            return
        callados.add("musica_tema")
        archivos.escribir_texto_atomico(
            ruta, sonidos_ini.con_silenciados(texto, callados, EVENTOS))
    except Exception as exc:
        logger.warning(
            "No se pudo callar el cambio de canción en sounds.ini: %s", exc)


def migrar(p, ruta) -> None:
    """Calla una sola vez el cambio de canción de quien lo tenía apagado.

    La versión vive en `[sesion] version_sonidos` y se graba aunque no haya
    nada que cambiar. La clave vieja `[musica] sonido_tema` se deja en
    `config.ini`, sin uso.
    """
    from guyrapu.core import config as _config

    try:
        version = p.getint("sesion", "version_sonidos")
    except Exception:
        version = 0
    if version >= VERSION_SONIDOS:
        return
    if (p.has_option("musica", "sonido_tema")
            and not leer_booleano(p, "musica", "sonido_tema")):
        _callar_musica_tema()
    _config.guardar_opcion(
        ruta, "sesion", "version_sonidos", str(VERSION_SONIDOS))
