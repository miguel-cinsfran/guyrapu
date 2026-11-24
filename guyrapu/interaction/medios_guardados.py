# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La colección de medios y las copias de sus archivos.

Puro y sin wx. Única razón para cambiar: el formato guardado de un medio y
cómo se copian, renombran y borran los archivos de la biblioteca.
"""

from __future__ import annotations

import json
import math
import shutil
import unicodedata
from pathlib import Path

from guyrapu.core import archivos, diagnostico
from guyrapu.interaction import medios
from guyrapu.music import sonoridad

logger = diagnostico.obtener_logger(__name__)

VOLUMEN_POR_DEFECTO = 100


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip()


def _duracion(valor) -> int:
    try:
        numero = int(float(valor))
    except (TypeError, ValueError):
        return 0
    return max(0, numero)


def _volumen(valor) -> int:
    if isinstance(valor, bool):
        return VOLUMEN_POR_DEFECTO
    try:
        numero = int(float(valor))
    except (TypeError, ValueError, OverflowError):
        return VOLUMEN_POR_DEFECTO
    return max(0, min(sonoridad.VOLUMEN_MAXIMO_VLC, numero))


def _ganancia(valor):
    if isinstance(valor, bool):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero):
        return None
    return max(sonoridad.GANANCIA_MINIMA_DB,
               min(sonoridad.GANANCIA_MAXIMA_DB, numero))


def normalizar(datos: dict) -> dict:
    """Los datos de un medio tal como se guardan, con los tipos forzados."""
    datos = datos if isinstance(datos, dict) else {}
    archivo = Path(_texto(datos.get("archivo"))).name
    nombre = _texto(datos.get("nombre")) or Path(archivo).stem
    tipo = _texto(datos.get("tipo"))
    if tipo not in medios.CLAVES:
        tipo = medios.tipo_de(archivo) or ""
    return {
        "nombre": nombre,
        "descripcion": _texto(datos.get("descripcion")),
        "tipo": tipo,
        "archivo": archivo,
        "duracion": _duracion(datos.get("duracion")),
        "ganancia_db": _ganancia(datos.get("ganancia_db")),
        "volumen": _volumen(datos.get("volumen")),
    }


def indice_de_archivo(guardados, archivo) -> int | None:
    """El índice del medio que usa esa copia, o None si ya no está."""
    nombre = Path(_texto(archivo)).name
    for indice, medio in enumerate(guardados):
        if normalizar(medio)["archivo"] == nombre:
            return indice
    return None


def cargar(ruta) -> list[dict]:
    """Carga los medios y devuelve una lista aunque el archivo esté roto."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except FileNotFoundError:
        return []
    except Exception as exc:
        logger.warning("No se pudo leer %s (se usa una lista vacía): %s",
                       Path(ruta).name, exc)
        return []
    if not isinstance(datos, list):
        logger.warning("No se pudo leer %s (se usa una lista vacía): "
                       "no es una lista", Path(ruta).name)
        return []
    return [normalizar(medio) for medio in datos
            if isinstance(medio, dict)]


def guardar(ruta, medios_guardados) -> None:
    """Guarda la colección mediante un temporal para conservar la anterior."""
    archivos.escribir_json_atomico(
        ruta, [normalizar(medio) for medio in medios_guardados], indent=2)


def provisional(origen, duracion) -> dict:
    """Los datos de un medio recién elegido, antes de copiar su archivo."""
    base = Path(origen)
    return normalizar({
        "nombre": base.stem,
        "archivo": base.name,
        "tipo": medios.tipo_de(base.name),
        "duracion": duracion,
    })


def _clave_de_orden(nombre) -> str:
    descompuesto = unicodedata.normalize("NFD", str(nombre))
    return "".join(c for c in descompuesto
                   if not unicodedata.combining(c)).lower()


def nombres_en_carpeta(carpeta) -> list[str]:
    """Los nombres de archivo de medios de la carpeta, sin subcarpetas."""
    try:
        return sorted(
            (hijo.name for hijo in Path(carpeta).iterdir()
             if hijo.is_file() and medios.es_medio(hijo.name)),
            key=_clave_de_orden)
    except OSError:
        return []


def sincronizar(guardados, nombres) -> list[dict]:
    """La lista final a partir de lo guardado y de los archivos presentes."""
    por_archivo = {}
    for guardado in guardados:
        medio = normalizar(guardado)
        por_archivo[medio["archivo"]] = medio
    presentes = list(dict.fromkeys(nombres))
    conservados = [por_archivo[n] for n in presentes if n in por_archivo]
    nuevos = [provisional(n, 0) for n in presentes if n not in por_archivo]
    usados = {medio["nombre"] for medio in conservados}
    for medio in nuevos:
        base = medio["nombre"]
        nombre, numero = base, 2
        while nombre in usados:
            nombre = f"{base} ({numero})"
            numero += 1
        medio["nombre"] = nombre
        usados.add(nombre)
    return sorted(conservados + nuevos,
                  key=lambda medio: _clave_de_orden(medio["nombre"]))


def _nombre_libre(carpeta: Path, nombre: str) -> str:
    if not (carpeta / nombre).exists():
        return nombre
    base = Path(nombre)
    numero = 2
    while True:
        candidato = f"{base.stem} ({numero}){base.suffix}"
        if not (carpeta / candidato).exists():
            return candidato
        numero += 1


def copiar(carpeta, origen) -> str:
    """Copia el archivo a la carpeta con un nombre libre y devuelve ese nombre."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    final = _nombre_libre(carpeta, Path(origen).name)
    shutil.copyfile(origen, carpeta / final)
    return final


def agregar(carpeta, origen, datos: dict) -> dict:
    """Copia el archivo y devuelve el medio ya guardado."""
    final = copiar(carpeta, origen)
    return normalizar({**datos, "archivo": final})


def duplicar(carpeta, medio, nombre: str) -> dict:
    """Copia el archivo de un medio y devuelve la copia con su nombre nuevo."""
    datos = normalizar(medio)
    datos["archivo"] = copiar(carpeta, archivo_de(carpeta, datos))
    datos["nombre"] = nombre
    return normalizar(datos)


def archivo_de(carpeta, medio) -> Path:
    """La ruta del archivo de un medio dentro de la carpeta de la biblioteca."""
    return Path(carpeta) / normalizar(medio)["archivo"]


def medio_para_video(guardados, carpeta, nombre):
    """El medio con ese nombre listo para la capa del vídeo, o None."""
    nombre = _texto(nombre)
    if not nombre:
        return None
    for guardado in guardados:
        datos = normalizar(guardado)
        if datos["nombre"] != nombre:
            continue
        return {
            "ruta": str(archivo_de(carpeta, datos)),
            "tipo": datos["tipo"],
            "duracion": datos["duracion"],
            "ganancia_db": datos["ganancia_db"],
            "volumen": datos["volumen"],
        }
    return None


def eliminar(carpeta, medio) -> None:
    """Borra la copia del medio; si ya no está, no falla."""
    try:
        archivo_de(carpeta, medio).unlink()
    except FileNotFoundError:
        pass


def rutas(carpeta, medios_guardados) -> list[Path]:
    """Los archivos de cada medio, para llevarlos dentro de un paquete."""
    return [archivo_de(carpeta, medio) for medio in medios_guardados]
