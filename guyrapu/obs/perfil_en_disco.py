# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El formato de los archivos de un perfil de OBS en disco.

Lee y escribe `basic.ini` y `service.json` de la carpeta de un perfil sin
hablar con el WebSocket. Los ajustes viven en `ajustes_perfil` y los
codificadores de la PC, en `codificadores_obs`.
"""

from __future__ import annotations

import configparser
import json
import os
import tempfile
from fractions import Fraction

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.obs import ajustes_perfil, obs_cliente

# Traductores: {perfil} es el nombre de un perfil de OBS.
MENSAJE_SIN_CARPETA = N_(
    "No se encontró la carpeta del perfil {perfil} de OBS.")
# Traductores: {perfil} es el nombre de un perfil de OBS.
MENSAJE_NO_LEIDO = N_(
    "No se pudo leer el perfil {perfil} de OBS.")


def carpeta_de_perfil(nombre):
    """La carpeta del perfil, la que lleva ese nombre en su basic.ini."""
    try:
        carpetas = list(paths.carpeta_obs("perfiles").iterdir())
    except OSError:
        return None
    for carpeta in carpetas:
        basic = carpeta / "basic.ini"
        if not basic.is_file():
            continue
        analizador = configparser.ConfigParser(interpolation=None)
        try:
            analizador.read(basic, encoding="utf-8-sig")
        except (OSError, UnicodeError, configparser.Error):
            continue
        if analizador.get("General", "Name", fallback="") == nombre:
            return carpeta
    return None


def _carpeta(nombre):
    carpeta = carpeta_de_perfil(nombre)
    if carpeta is None:
        raise obs_cliente.ObsError(
            _(MENSAJE_SIN_CARPETA).format(perfil=nombre))
    return carpeta


def _leer_texto(carpeta, nombre):
    try:
        return (carpeta / "basic.ini").read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise obs_cliente.ObsError(
            _(MENSAJE_NO_LEIDO).format(perfil=nombre)) from error


def _desescapar(valor):
    return valor.strip().replace("\\\\", "\\")


def _escapar(valor):
    return str(valor).replace("\\", "\\\\")


def _secciones(texto):
    """Las secciones y claves de un basic.ini, con el escape deshecho."""
    secciones = {}
    actual = None
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith((";", "#")):
            continue
        if limpia.startswith("[") and limpia.endswith("]"):
            actual = limpia[1:-1].strip()
            secciones.setdefault(actual, {})
            continue
        if actual is None or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        secciones[actual][clave.strip()] = _desescapar(valor)
    return secciones


def _entero(valor, defecto=0):
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return defecto


def _fps(secciones):
    """Numerador y denominador de los fps según el FPSType del perfil."""
    video = secciones.get("Video", {})
    tipo = _entero(video.get("FPSType"), 0)
    if tipo == 1:
        return _entero(video.get("FPSInt"), 30), 1
    if tipo == 2:
        return (_entero(video.get("FPSNum"), 30),
                _entero(video.get("FPSDen"), 1) or 1)
    texto = str(video.get("FPSCommon") or "").strip()
    if not texto:
        return 30, 1
    try:
        numero = Fraction(texto).limit_denominator(1001)
    except (ValueError, ZeroDivisionError):
        return 30, 1
    return numero.numerator, numero.denominator


def _video(secciones):
    """El vídeo con la forma que devuelve el WebSocket."""
    video = secciones.get("Video", {})
    numerador, denominador = _fps(secciones)
    return {
        "baseWidth": _entero(video.get("BaseCX"), 1920),
        "baseHeight": _entero(video.get("BaseCY"), 1080),
        "outputWidth": _entero(video.get("OutputCX"), 1280),
        "outputHeight": _entero(video.get("OutputCY"), 720),
        "fpsNumerator": numerador,
        "fpsDenominator": denominador,
    }


def _modo(secciones):
    return str(secciones.get("Output", {}).get("Mode") or "").strip().lower()


def _carpeta_grabacion(secciones):
    if _modo(secciones) == "advanced":
        return str(secciones.get("AdvOut", {}).get("RecFilePath") or "")
    return str(secciones.get("SimpleOutput", {}).get("FilePath") or "")


def _parametros(secciones):
    codificador = str(
        secciones.get("SimpleOutput", {}).get("StreamEncoder") or "")
    parametros = {}
    for categoria, nombre in ajustes_perfil.claves_de_lectura(codificador):
        parametros[(categoria, nombre)] = str(
            secciones.get(categoria, {}).get(nombre) or "")
    return parametros


def _leer_json(ruta):
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def _servicio(carpeta):
    """El service.json con la forma que devuelve el WebSocket."""
    datos = _leer_json(carpeta / "service.json")
    if datos is None:
        return {}
    return {
        "streamServiceType": datos.get("type"),
        "streamServiceSettings": datos.get("settings") or {},
    }


def _ajustes(carpeta, secciones):
    return ajustes_perfil.desde_obs(
        _video(secciones), _servicio(carpeta),
        _carpeta_grabacion(secciones), _parametros(secciones))


def leer_ajustes(nombre):
    """Los ajustes que dicen los archivos del perfil."""
    carpeta = _carpeta(nombre)
    return _ajustes(carpeta, _secciones(_leer_texto(carpeta, nombre)))


def leer_para_editar(nombre):
    """Ajustes, modo Avanzado y servicio personalizado, de los archivos."""
    carpeta = _carpeta(nombre)
    secciones = _secciones(_leer_texto(carpeta, nombre))
    servicio = _servicio(carpeta)
    personalizado = (str(servicio.get("streamServiceType") or "")
                     == "rtmp_custom")
    return (_ajustes(carpeta, secciones), _modo(secciones) == "advanced",
            personalizado)


def esta_en_avanzado(nombre):
    """Dice si el perfil está en modo Avanzado, sin tocar OBS."""
    carpeta = _carpeta(nombre)
    return _modo(_secciones(_leer_texto(carpeta, nombre))) == "advanced"


def encoder_avanzado(nombre):
    """El [AdvOut] Encoder que dejó el modo Avanzado."""
    carpeta = _carpeta(nombre)
    secciones = _secciones(_leer_texto(carpeta, nombre))
    return str(secciones.get("AdvOut", {}).get("Encoder") or "")


def _escribir_texto(ruta, texto, con_bom=True):
    codificacion = "utf-8-sig" if con_bom else "utf-8"
    descriptor, temporal = tempfile.mkstemp(
        dir=ruta.parent, prefix=ruta.name + ".", suffix=".tmp")
    with os.fdopen(descriptor, "w", encoding=codificacion,
                   newline="") as archivo:
        archivo.write(texto)
    os.replace(temporal, ruta)


def _pendientes(texto, cambios):
    """Las claves cuyo valor cambia, agrupadas por sección."""
    actuales = _secciones(texto)
    pendientes = {}
    for (seccion, clave), valor in cambios.items():
        valor = str(valor)
        if actuales.get(seccion, {}).get(clave) == valor:
            continue
        pendientes.setdefault(seccion, {})[clave] = valor
    return pendientes


def _editar(texto, cambios):
    """Cambia solo las líneas pedidas y deja el resto igual."""
    pendientes = _pendientes(texto, cambios)
    salto = "\r\n" if "\r\n" in texto else "\n"
    lineas = texto.replace("\r\n", "\n").split("\n")
    if lineas and lineas[-1] == "":
        lineas.pop()
    inicio_de = {}
    fin_de = {}
    actual = None
    for indice, linea in enumerate(lineas):
        limpia = linea.strip()
        if limpia.startswith("[") and limpia.endswith("]"):
            actual = limpia[1:-1].strip()
            inicio_de.setdefault(actual, indice)
            fin_de.setdefault(actual, indice)
            continue
        if actual is None:
            continue
        if limpia:
            fin_de[actual] = indice
        if "=" not in linea or limpia.startswith((";", "#")):
            continue
        clave = linea.split("=", 1)[0].strip()
        if clave in pendientes.get(actual, {}):
            valor = _escapar(pendientes[actual].pop(clave))
            lineas[indice] = f"{clave}={valor}"
    inserciones = []
    al_final = []
    for seccion, valores in pendientes.items():
        if not valores:
            continue
        nuevas = [f"{clave}={_escapar(valor)}"
                  for clave, valor in valores.items()]
        if seccion in inicio_de:
            inserciones.append((fin_de[seccion] + 1, nuevas))
        else:
            al_final.append(f"[{seccion}]")
            al_final.extend(nuevas)
    for posicion, nuevas in sorted(inserciones, reverse=True):
        lineas[posicion:posicion] = nuevas
    if al_final and lineas and lineas[-1].strip():
        lineas.append("")
    lineas.extend(al_final)
    resultado = salto.join(lineas)
    if texto.endswith(("\n", "\r")) or al_final:
        resultado += salto
    return resultado


def _escribir_servicio(carpeta, ajustes):
    if not ajustes.servidor or not ajustes.clave:
        return
    ruta = carpeta / "service.json"
    datos = _leer_json(ruta) or {}
    actual = {
        "streamServiceType": datos.get("type"),
        "streamServiceSettings": datos.get("settings") or {},
    }
    nuevos = ajustes_perfil.datos_servicio(actual, ajustes)
    datos["type"] = nuevos["streamServiceType"]
    datos["settings"] = nuevos["streamServiceSettings"]
    _escribir_texto(ruta, json.dumps(
        datos, ensure_ascii=False, separators=(",", ":")), con_bom=False)


def guardar_ajustes(nombre, ajustes):
    """Escribe en los archivos del perfil lo mismo que el WebSocket."""
    ajustes_perfil.validar(ajustes)
    carpeta = _carpeta(nombre)
    video = ajustes_perfil.datos_video(ajustes)
    cambios = {
        ("Video", "BaseCX"): video["baseWidth"],
        ("Video", "BaseCY"): video["baseHeight"],
        ("Video", "OutputCX"): video["outputWidth"],
        ("Video", "OutputCY"): video["outputHeight"],
        ("Video", "FPSType"): "2",
        ("Video", "FPSNum"): video["fpsNumerator"],
        ("Video", "FPSDen"): video["fpsDenominator"],
    }
    for categoria, clave, valor in ajustes_perfil.parametros_obs(ajustes):
        cambios[(categoria, clave)] = valor
    if ajustes.carpeta_grabacion:
        cambios[("SimpleOutput", "FilePath")] = ajustes.carpeta_grabacion
        cambios[("AdvOut", "RecFilePath")] = ajustes.carpeta_grabacion
    _escribir_texto(carpeta / "basic.ini",
                    _editar(_leer_texto(carpeta, nombre), cambios))
    _escribir_servicio(carpeta, ajustes)


def pasar_a_sencillo(nombre, codificador, bitrate):
    """Pasa el perfil a Sencillo con el codificador y el bitrate recibidos."""
    carpeta = _carpeta(nombre)
    _escribir_texto(carpeta / "basic.ini", _editar(
        _leer_texto(carpeta, nombre), {
            ("SimpleOutput", "StreamEncoder"): codificador,
            ("SimpleOutput", "VBitrate"): str(int(bitrate)),
            ("Output", "Mode"): "Simple",
        }))
