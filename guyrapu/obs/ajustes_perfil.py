# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los ajustes de un perfil de OBS en modo Sencillo, sin hablar con OBS.

El tipo con los ajustes, sus valores permitidos, la correspondencia con las
secciones y claves de OBS y los valores iniciales de un perfil nuevo.
Todo lo que usa el cliente webSocket vive en `perfiles_obs`.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.idioma import N_

CODIFICADORES = ("x264", "qsv", "nvenc", "amd")
PRIORIDAD_CODIFICADORES = ("nvenc", "qsv", "amd", "x264")
FPS_VALIDOS = (20, 24, 25, 30, 48, 50, 60)
BITRATES_AUDIO = (64, 96, 128, 160, 192, 256, 320)
FORMATOS_GRABACION = ("mkv", "mp4", "hybrid_mp4", "mov", "flv")
CALIDADES_GRABACION = ("Stream", "Small", "HQ", "Lossless")
MUESTREOS = (44100, 48000)
CANALES = ("Mono", "Stereo")
MONITOREO_ID_POR_DEFECTO = "default"
MONITOREO_NOMBRE_POR_DEFECTO = N_("Por defecto")

PRESETS = {
    "x264": ("ultrafast", "superfast", "veryfast", "faster", "fast",
             "medium"),
    "qsv": ("speed", "balanced", "quality"),
    "nvenc": ("p1", "p2", "p3", "p4", "p5", "p6", "p7"),
    "amd": ("speed", "balanced", "quality"),
}
CLAVES_PRESET = {
    "x264": "Preset",
    "qsv": "QSVPreset",
    "nvenc": "NVENCPreset2",
    "amd": "AMDPreset",
}
PRESET_INTERMEDIO = {
    "x264": "veryfast",
    "qsv": "balanced",
    "nvenc": "p4",
    "amd": "balanced",
}


@dataclass(frozen=True, slots=True)
class AjustesPerfil:
    """Lo que la ventana de perfiles edita y lo que se lee de OBS."""

    ancho_lienzo: int = 1920
    alto_lienzo: int = 1080
    ancho_salida: int = 1280
    alto_salida: int = 720
    fps: int = 30
    servidor: str = ""
    clave: str = ""
    codificador: str = "x264"
    bitrate_video: int = 2500
    bitrate_audio: int = 160
    preset: str = "veryfast"
    bitrate_dinamico: bool = False
    reconectar: bool = True
    espera_reconexion: int = 2
    reintentos: int = 25
    carpeta_grabacion: str = ""
    formato_grabacion: str = "mkv"
    calidad_grabacion: str = "Stream"
    buffer_clips: bool = False
    segundos_buffer: int = 30
    muestreo: int = 48000
    canales: str = "Stereo"
    monitoreo_id: str = MONITOREO_ID_POR_DEFECTO
    monitoreo_nombre: str = MONITOREO_NOMBRE_POR_DEFECTO


def par(valor) -> int:
    """El ancho que OBS conserva: múltiplo de 4 (medido el 03/11: 854 queda 852)."""
    valor = int(valor)
    return valor - valor % 4


def presets_para(codificador) -> tuple:
    return PRESETS.get(str(codificador or "").strip().lower(), ())


def clave_preset(codificador) -> str:
    return CLAVES_PRESET.get(str(codificador or "").strip().lower(), "Preset")


def preset_intermedio(codificador) -> str:
    return PRESET_INTERMEDIO.get(str(codificador or "").strip().lower(),
                                 "veryfast")


def mejor_codificador(disponibles) -> str:
    """El primero de los disponibles en el orden de preferencia."""
    vistos = set(disponibles or ())
    for codificador in PRIORIDAD_CODIFICADORES:
        if codificador in vistos:
            return codificador
    return "x264"


def _exigir(condicion, nombre):
    if not condicion:
        raise ValueError(f"Ajuste no permitido: {nombre}.")


def validar(ajustes) -> None:
    _exigir(ajustes.ancho_lienzo > 0 and ajustes.ancho_lienzo % 2 == 0,
            "ancho del lienzo")
    _exigir(ajustes.alto_lienzo > 0 and ajustes.alto_lienzo % 2 == 0,
            "alto del lienzo")
    _exigir(ajustes.ancho_salida > 0 and ajustes.ancho_salida % 2 == 0,
            "ancho de salida")
    _exigir(ajustes.alto_salida > 0 and ajustes.alto_salida % 2 == 0,
            "alto de salida")
    _exigir(ajustes.fps in FPS_VALIDOS, "fotogramas por segundo")
    _exigir(ajustes.codificador in CODIFICADORES, "codificador")
    _exigir(ajustes.bitrate_video > 0, "bitrate de vídeo")
    _exigir(ajustes.bitrate_audio in BITRATES_AUDIO, "bitrate de audio")
    _exigir(ajustes.preset in presets_para(ajustes.codificador), "preset")
    _exigir(ajustes.espera_reconexion >= 0, "espera de reconexión")
    _exigir(ajustes.reintentos >= 0, "reintentos de reconexión")
    _exigir(ajustes.formato_grabacion in FORMATOS_GRABACION,
            "formato de grabación")
    _exigir(ajustes.calidad_grabacion in CALIDADES_GRABACION,
            "calidad de grabación")
    _exigir(ajustes.segundos_buffer >= 0, "segundos del búfer de clips")
    _exigir(ajustes.muestreo in MUESTREOS, "frecuencia de muestreo")
    _exigir(ajustes.canales in CANALES, "canales de audio")


def valores_iniciales(vertical=False, codificador="x264") -> AjustesPerfil:
    """El perfil nuevo: horizontal o vertical, en modo Sencillo."""
    if vertical:
        lienzo, salida = (1080, 1920), (720, 1280)
    else:
        lienzo, salida = (1920, 1080), (1280, 720)
    return AjustesPerfil(
        ancho_lienzo=lienzo[0], alto_lienzo=lienzo[1],
        ancho_salida=salida[0], alto_salida=salida[1],
        fps=30,
        codificador=codificador,
        bitrate_video=2500,
        bitrate_audio=160,
        preset=preset_intermedio(codificador),
        formato_grabacion="mkv",
        calidad_grabacion="Stream",
        buffer_clips=False,
        segundos_buffer=30,
        muestreo=48000,
        canales="Stereo",
    )


CLAVES_PERFIL = (
    ("SimpleOutput", "VBitrate"),
    ("SimpleOutput", "ABitrate"),
    ("SimpleOutput", "DynamicBitrate"),
    ("Output", "Reconnect"),
    ("Output", "RetryDelay"),
    ("Output", "MaxRetries"),
    ("SimpleOutput", "RecFormat2"),
    ("SimpleOutput", "RecQuality"),
    ("SimpleOutput", "RecRB"),
    ("SimpleOutput", "RecRBTime"),
    ("Audio", "SampleRate"),
    ("Audio", "ChannelSetup"),
    ("Audio", "MonitoringDeviceId"),
    ("Audio", "MonitoringDeviceName"),
)


def claves_de_lectura(codificador) -> tuple:
    """Las claves que hay que pedir a OBS para armar los ajustes."""
    return ((("SimpleOutput", "StreamEncoder"),
             ("SimpleOutput", clave_preset(codificador)))
            + CLAVES_PERFIL)


def _texto(parametros, categoria, nombre, defecto="") -> str:
    valor = parametros.get((categoria, nombre))
    return defecto if valor is None or valor == "" else str(valor)


def _entero(valor, defecto=0):
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return defecto


def _booleano(valor):
    return str(valor or "").strip().lower() == "true"


def _fps(video):
    numerador = _entero(video.get("fpsNumerator"), 30)
    denominador = _entero(video.get("fpsDenominator"), 1) or 1
    return max(1, round(numerador / denominador))


def desde_obs(video, servicio, carpeta, parametros) -> AjustesPerfil:
    """Arma los ajustes con lo que devuelve el WebSocket de OBS."""
    ajustes_servicio = (servicio or {}).get("streamServiceSettings") or {}
    codificador = _texto(parametros, "SimpleOutput", "StreamEncoder", "x264")
    preset = (_texto(parametros, "SimpleOutput", clave_preset(codificador))
              or preset_intermedio(codificador))
    return AjustesPerfil(
        ancho_lienzo=par(video.get("baseWidth", 1920)),
        alto_lienzo=par(video.get("baseHeight", 1080)),
        ancho_salida=par(video.get("outputWidth", 1280)),
        alto_salida=par(video.get("outputHeight", 720)),
        fps=_fps(video),
        servidor=str(ajustes_servicio.get("server") or ""),
        clave=str(ajustes_servicio.get("key") or ""),
        codificador=codificador,
        bitrate_video=_entero(
            _texto(parametros, "SimpleOutput", "VBitrate"), 2500),
        bitrate_audio=_entero(
            _texto(parametros, "SimpleOutput", "ABitrate"), 160),
        preset=preset,
        bitrate_dinamico=_booleano(
            _texto(parametros, "SimpleOutput", "DynamicBitrate")),
        reconectar=_booleano(_texto(parametros, "Output", "Reconnect")),
        espera_reconexion=_entero(
            _texto(parametros, "Output", "RetryDelay"), 2),
        reintentos=_entero(_texto(parametros, "Output", "MaxRetries"), 25),
        carpeta_grabacion=str(carpeta or ""),
        formato_grabacion=(
            _texto(parametros, "SimpleOutput", "RecFormat2") or "mkv"),
        calidad_grabacion=(
            _texto(parametros, "SimpleOutput", "RecQuality") or "Stream"),
        buffer_clips=_booleano(_texto(parametros, "SimpleOutput", "RecRB")),
        segundos_buffer=_entero(
            _texto(parametros, "SimpleOutput", "RecRBTime"), 30),
        muestreo=_entero(_texto(parametros, "Audio", "SampleRate"), 48000),
        canales=(_texto(parametros, "Audio", "ChannelSetup") or "Stereo"),
        monitoreo_id=(_texto(parametros, "Audio", "MonitoringDeviceId")
                      or MONITOREO_ID_POR_DEFECTO),
        monitoreo_nombre=(_texto(parametros, "Audio", "MonitoringDeviceName")
                          or MONITOREO_NOMBRE_POR_DEFECTO),
    )


def datos_video(ajustes) -> dict:
    return {
        "baseWidth": par(ajustes.ancho_lienzo),
        "baseHeight": par(ajustes.alto_lienzo),
        "outputWidth": par(ajustes.ancho_salida),
        "outputHeight": par(ajustes.alto_salida),
        "fpsNumerator": int(ajustes.fps),
        "fpsDenominator": 1,
    }


def datos_servicio(actual, ajustes) -> dict:
    actual = actual or {}
    tipo = str(actual.get("streamServiceType") or "rtmp_custom")
    valores = dict(actual.get("streamServiceSettings") or {})
    if tipo == "rtmp_custom":
        valores = {"server": ajustes.servidor, "key": ajustes.clave}
    else:
        valores["key"] = ajustes.clave
    return {"streamServiceType": tipo, "streamServiceSettings": valores}


def _texto_booleano(valor) -> str:
    return "true" if valor else "false"


def parametros_obs(ajustes) -> tuple:
    """Las claves del perfil que se leen y escriben por el WebSocket."""
    return (
        ("SimpleOutput", "StreamEncoder", ajustes.codificador),
        ("SimpleOutput", "VBitrate", str(int(ajustes.bitrate_video))),
        ("SimpleOutput", "ABitrate", str(int(ajustes.bitrate_audio))),
        ("SimpleOutput", clave_preset(ajustes.codificador), ajustes.preset),
        ("SimpleOutput", "DynamicBitrate",
         _texto_booleano(ajustes.bitrate_dinamico)),
        ("Output", "Reconnect", _texto_booleano(ajustes.reconectar)),
        ("Output", "RetryDelay", str(int(ajustes.espera_reconexion))),
        ("Output", "MaxRetries", str(int(ajustes.reintentos))),
        ("SimpleOutput", "RecFormat2", ajustes.formato_grabacion),
        ("SimpleOutput", "RecQuality", ajustes.calidad_grabacion),
        ("SimpleOutput", "RecRB", _texto_booleano(ajustes.buffer_clips)),
        ("SimpleOutput", "RecRBTime", str(int(ajustes.segundos_buffer))),
        ("Audio", "SampleRate", str(int(ajustes.muestreo))),
        ("Audio", "ChannelSetup", ajustes.canales),
        ("Audio", "MonitoringDeviceId", ajustes.monitoreo_id),
        ("Audio", "MonitoringDeviceName", ajustes.monitoreo_nombre),
    )
