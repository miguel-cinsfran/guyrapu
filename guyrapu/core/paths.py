# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ubicación de cada archivo y carpeta, en un solo lugar.

Es el ÚNICO módulo de la aplicación que sabe dónde vive cada archivo:
ningún otro arma rutas de datos o de instalación por su cuenta. Solo usa
biblioteca estándar, para no provocar imports circulares.

Dos raíces: `carpeta_instalacion` (lo que viene con el programa) y
`carpeta_datos` (lo que escribe el usuario, en la subcarpeta `data`).
Ninguna función de este módulo crea nada en disco, salvo `audio_temporal`,
que sí crea su carpeta para el WAV de ElevenLabs.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from guyrapu.core.carpetas_windows import carpeta_musica_windows

# Depende de la ubicación de este archivo: vive en `guyrapu/core/`, así que
# la raíz en desarrollo está tres niveles arriba.
_RAIZ_DESARROLLO = Path(__file__).resolve().parent.parent.parent

NOMBRE_CREDENCIALES = "credenciales.json"
NOMBRE_CLIENTE_APP = "cliente_app.json"
NOMBRE_FFMPEG = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
NOMBRE_YTDLP = "yt-dlp.exe"
NOMBRE_DENO = "deno.exe"
# Manifiesto que construir.bat escribe en la raíz del paquete distribuible.
NOMBRE_MANIFIESTO = "paquete.json"
# Huellas de los sonidos de cada tema, para que el instalador conserve
# los que el usuario cambió o agregó al actualizar.
NOMBRE_MANIFIESTO_SONIDOS = "sonidos.json"


def carpeta_instalacion() -> Path:
    """Lo que viene con el programa: junto al .exe, o la raíz en desarrollo."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return _RAIZ_DESARROLLO


def carpeta_datos() -> Path:
    """Lo que escribe el usuario: la subcarpeta `data` junto al programa."""
    return carpeta_instalacion() / "data"


# ── Datos (los escribe el usuario) ───────────────────────────────────────────

def config_ini() -> Path:
    return carpeta_datos() / "config.ini"


def config_anterior() -> Path:
    # Copia de respaldo de las preferencias anteriores: una sola, se pisa en
    # cada importación o restablecimiento.
    return carpeta_datos() / "config.anterior.ini"


def credenciales() -> Path:
    return carpeta_datos() / NOMBRE_CREDENCIALES


def historial_lives() -> Path:
    return carpeta_datos() / "historial_lives.json"


def historial_descargas() -> Path:
    return carpeta_datos() / "historial_descargas.json"


def grabaciones() -> Path:
    return carpeta_datos() / "grabaciones.json"


def busquedas_recientes() -> Path:
    return carpeta_datos() / "busquedas_recientes.json"


def alias() -> Path:
    return carpeta_datos() / "alias.json"


def perfiles_restream() -> Path:
    return carpeta_datos() / "perfiles_restream.json"


def mensajes_programados() -> Path:
    return carpeta_datos() / "mensajes_programados.json"


def comandos() -> Path:
    return carpeta_datos() / "comandos.json"


def encuestas() -> Path:
    return carpeta_datos() / "encuestas.json"


def medios() -> Path:
    return carpeta_datos() / "medios.json"


def carpeta_medios() -> Path:
    # Las copias de los archivos de la biblioteca de medios, para que sigan
    # andando si el original se mueve o se borra.
    return carpeta_datos() / "medios"


def palabras_bloqueadas() -> Path:
    return carpeta_datos() / "palabras_bloqueadas.json"


def fin_pendiente() -> Path:
    # Fines de directo pedidos a YouTube y todavía sin confirmar: se
    # reintentan al abrir la app. Es un dato del usuario, no una preferencia.
    return carpeta_datos() / "fin_pendiente.json"


def fin_pendiente_log() -> Path:
    # Cada intento y el resultado del proceso que finaliza directos con la
    # app cerrada. Nace ya dentro de data/, así que no entra en datos_a_migrar().
    return carpeta_datos() / "fin-pendiente.log"


def cuota_youtube() -> Path:
    # Unidades de la API de YouTube gastadas en el día del Pacífico. Nace ya
    # dentro de data/, así que no entra en datos_a_migrar().
    return carpeta_datos() / "cuota_youtube.json"


def cuota_youtube_pagina() -> Path:
    # Tabla de costos que publica Google, leída una vez por semana. Nace ya
    # dentro de data/, así que no entra en datos_a_migrar().
    return carpeta_datos() / "cuota_youtube_pagina.json"


def catalogo_ia() -> Path:
    # Copia del catálogo de modelos que la app renueva sola: no entra en
    # datos_a_migrar(), se vuelve a bajar.
    return carpeta_datos() / "catalogo_ia.json"


def disenos_escena() -> Path:
    # Diseños de escena propios del usuario: nacen ya dentro de data/, así
    # que no entran en datos_a_migrar().
    return carpeta_datos() / "disenos_escena.json"


def estilos_avisos() -> Path:
    # Estilos de aviso propios del usuario: nacen ya dentro de data/, así
    # que no entran en datos_a_migrar().
    return carpeta_datos() / "estilos_avisos.json"


def fondos_de_avisos() -> Path:
    # PNG de las tarjetas de aviso que se arman en OBS: nacen ya dentro de
    # data/, así que no entran en datos_a_migrar().
    return carpeta_datos() / "fondos-avisos"


def gratis_ia() -> Path:
    # Marcas de qué modelos responde la clave gratuita de un proveedor: se
    # rehacen al actualizar la lista, así que no entra en datos_a_migrar().
    return carpeta_datos() / "gratis_ia.json"


def listas_musica() -> Path:
    # Listas de reproducción propias del usuario (.m3u8), creadas desde la
    # ventana de listas de música. No entra en datos_a_migrar(): esa lista
    # solo mueve datos del formato viejo de la raíz a data/, y esta carpeta
    # nace ya dentro de data/.
    return carpeta_datos() / "listas"


def estado_musica() -> Path:
    # Lo que suena y por dónde iba, para retomar al abrir. Se borra solo
    # cuando la preferencia de retomar está apagada o la cola termina.
    return carpeta_datos() / "musica_estado.json"


def cache_etiquetas_musica() -> Path:
    # Etiquetas de la música local ya leídas con libVLC, para no releerlas
    # en cada arranque. Nace ya dentro de data/.
    return carpeta_datos() / "etiquetas_musica.json"


def cache_sonoridad_musica() -> Path:
    # Ganancias de la música local ya medidas con ffmpeg, para no medirlas
    # en cada arranque. Nace ya dentro de data/.
    return carpeta_datos() / "sonoridad_musica.json"


def sounds_ini() -> Path:
    # Va con los datos porque la app lo escribe al cambiar el tema.
    return carpeta_datos() / "sounds.ini"


def log_principal() -> Path:
    return carpeta_datos() / "guyrapu.log"


def log_detallado() -> Path:
    return carpeta_datos() / "guyrapu-debug.log"


def log_fallos() -> Path:
    return carpeta_datos() / "guyrapu-fallos.log"


def ytdlp_actualizado() -> Path:
    # La copia que la app renueva sola, dentro de data.
    return carpeta_datos() / NOMBRE_YTDLP


def ytdlp_actualizado_anterior() -> Path:
    # Las versiones con el nombre viejo la dejaban fuera de data.
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "YTChat TTS" / NOMBRE_YTDLP


def pares_de_nombres_anteriores() -> tuple[list, list]:
    registros = [(carpeta_datos() / f"{p}{s}", nueva()) for p in ("bellbird", "ytchat")
                 for s, nueva in (("-debug.log", log_detallado), ("-fallos.log", log_fallos), (".log", log_principal))]
    return ([(ytdlp_actualizado_anterior(), ytdlp_actualizado())], registros)


def cache_audio() -> Path:
    return carpeta_datos() / "cache-audio"


def cache_video() -> Path:
    return carpeta_datos() / "cache-video"


def resumenes_sesion() -> Path:
    # Resúmenes de participación de cada directo, para agradecer al cerrar.
    # Nacen ya dentro de data/, así que no entran en datos_a_migrar().
    return carpeta_datos() / "resumenes_sesion"


def audio_temporal() -> Path:
    """Carpeta donde ElevenLabs deja el WAV de cada frase, creada si falta."""
    carpeta = carpeta_datos() / "audio_temporal"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def descargas_por_defecto() -> Path:
    # Son vídeos y audios del usuario y quedan a la vista, junto al programa.
    return carpeta_instalacion() / "Descargas"


def musica_por_defecto() -> Path:
    # Como «Descargas»: queda a la vista, junto al programa.
    return carpeta_instalacion() / "Música"


def resolver_carpeta_musica(texto) -> str:
    """La carpeta de música configurada como ruta absoluta.

    Vacía da la Música de Windows (lo que tienen quienes ya usan la app);
    relativa cuelga de la instalación; absoluta queda igual.
    """
    valor = (texto or "").strip()
    if not valor:
        return carpeta_musica_windows()
    if Path(valor).anchor:
        return valor
    return str(carpeta_instalacion() / valor)


def datos_a_migrar() -> list[Path]:
    """Rutas de datos que la migración mueve de la raíz a `data/`."""
    return [
        config_ini(),
        credenciales(),
        historial_lives(),
        historial_descargas(),
        alias(),
        mensajes_programados(),
        log_principal(),
        log_detallado(),
        log_fallos(),
        cache_audio(),
        cache_video(),
    ]


def carpeta_obs(tipo) -> Path:
    sub = {"perfiles": "basic/profiles", "registros": "logs", "config": "plugin_config/obs-websocket/config.json"}
    sub["lienzo_vertical"] = "plugin_config/vertical-canvas/config.json"
    sub["sentinel"] = ".sentinel"
    return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "obs-studio" / sub[tipo]


# ── Instalación (viene con el programa) ──────────────────────────────────────

def carpeta_sonidos() -> Path:
    return carpeta_instalacion() / "sounds"


def carpeta_guia() -> Path:
    # Pitidos de la guía de encuadre: fijos, iguales para los dos temas.
    return carpeta_sonidos() / "guia"


def modelo_rostros() -> Path:
    return carpeta_instalacion() / "modelos" / "face_detection_yunet_2023mar.onnx"


def carpeta_idiomas() -> Path:
    return carpeta_instalacion() / "idiomas"


def documento(nombre, idioma) -> Path:
    """Ruta del documento HTML en el idioma pedido, con el español de respaldo."""
    corto = (idioma or "").strip().lower()
    if corto != "pseudo":
        corto = corto.split("_")[0].split("-")[0]
    if corto and corto != "pseudo":
        ruta = carpeta_instalacion() / "docs" / corto / f"{nombre}.html"
        if ruta.is_file():
            return ruta
    return carpeta_instalacion() / "docs" / "es" / f"{nombre}.html"


def pagina_redireccion(nombre, ancla) -> Path:
    """Página temporal que lleva a una sección del documento."""
    return Path(tempfile.gettempdir()) / f"guyrapu-{nombre.lower()}-{ancla}.html"


def pagina_overlay() -> Path:
    return carpeta_instalacion() / "web" / "chat.html"


def config_predeterminada_ini() -> Path:
    return carpeta_instalacion() / "config.predeterminado.ini"


def ffmpeg_empaquetado() -> Path:
    return carpeta_instalacion() / NOMBRE_FFMPEG


def ytdlp_empaquetado() -> Path:
    return carpeta_instalacion() / NOMBRE_YTDLP


def deno_empaquetado() -> Path:
    return carpeta_instalacion() / NOMBRE_DENO


def carpeta_vlc_empaquetada() -> Path:
    return carpeta_instalacion() / "vlc"


def carpeta_voces() -> Path:
    return carpeta_instalacion() / "voces"


def ejecutable_actual() -> str:
    """Nombre simple del ejecutable que está corriendo."""
    return Path(sys.executable).name


def orden_de_la_app() -> list[str]:
    """El .exe solo empaquetado, o el intérprete con main.py desde el código."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, str(_RAIZ_DESARROLLO / "main.py")]


def carpeta_interna() -> Path:
    return carpeta_instalacion() / "_internal"


def cliente_app() -> Path:
    # El cliente de Google de la app viaja junto al ejecutable: no es un
    # dato del usuario y por eso cuelga de la instalación, no de los datos.
    return carpeta_instalacion() / NOMBRE_CLIENTE_APP


def catalogo_ia_empaquetado() -> Path:
    # Copia del catálogo que viaja en el paquete, junto al ejecutable.
    return carpeta_instalacion() / "catalogo_ia.json"


def marca_migracion_accesos() -> Path:
    return carpeta_datos() / "migracion-accesos.ok"
