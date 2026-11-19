# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Banco real de voces: descarga el catálogo, instala la voz más chica y sintetiza.

Usa el catálogo publicado, la descarga con la firma de la app y el
sintetizador del proveedor, sin dobles. La carpeta de voces se sustituye por
una de temporal mientras corre, así nada se escribe en la de la app. Se corre
a mano, con red:

    python qa/voces_real.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from guyrapu.core import (config, paquetes_catalogo,  # noqa: E402
                          paquetes_instalacion, paths, red)
from guyrapu.voice.proveedores import PROVEEDORES  # noqa: E402

FRASE = "Hola, esto es una prueba de voz."
PASO_CATALOGO = "catalogo"
PASO_PAQUETE = "paquete"
PASO_INSTALAR = "instalar"
PASO_VOZ = "voz"


def _tamano(paquete):
    return sum(archivo["bytes"] for archivo in paquete["archivos"])


def seleccionar(texto, version_app, tipos, proveedores):
    """(paquete, descartes): el compatible más chico y los motivos de descarte."""
    paquetes, descartes = paquetes_catalogo.leer(
        texto, version_app, tipos, proveedores)
    return min(paquetes, key=_tamano, default=None), descartes


def tiene_audio(trozos):
    """Si algún trozo trae una muestra distinta de cero."""
    return any(any(muestra != 0 for muestra in trozo) for trozo in trozos)


def linea_final(paso, motivo):
    """(línea, código) con la que cierra la corrida."""
    if paso is None:
        return ("VOCES_REAL codigo=0", 0)
    return (f"VOCES_REAL {paso}: {motivo}", 1)


def _sintetizador(paquete):
    """El sintetizador del proveedor del paquete, sin abrir salida de audio."""
    proveedor = paquete.get("proveedor")
    if proveedor == "piper":
        from piper import PiperVoice, SynthesisConfig
        from guyrapu.voice.proveedores.piper import SintetizadorPiper, _entradas
        return SintetizadorPiper(_entradas(), (PiperVoice, SynthesisConfig))
    if proveedor == "phonon":
        from guyrapu.voice.proveedores.phonon import SintetizadorPhonon, _ptts
        return SintetizadorPhonon(_ptts())
    raise RuntimeError(f"el proveedor {proveedor} no carga voces instaladas")


def _hablar(paquete):
    """Los trozos de una frase corta, con la voz recién instalada."""
    sintetizador = _sintetizador(paquete)
    if not sintetizador.elegir_voz(0):
        raise RuntimeError("el proveedor no pudo cargar la voz instalada")
    try:
        return list(sintetizador.sintetizar(FRASE, 1.0))
    finally:
        sintetizador.cerrar()


def _correr():
    """(paso, motivo) del primer fallo, o (None, "") si pasó todo."""
    try:
        texto = red.pedir_texto(paquetes_catalogo.URL_CATALOGO)
    except Exception as error:
        return (PASO_CATALOGO, f"no se pudo descargar el catálogo: {error}")
    paquete, descartes = seleccionar(
        texto, config.APP_VERSION, {"voz"},
        tuple(proveedor.id for proveedor in PROVEEDORES))
    if paquete is None:
        return (PASO_PAQUETE,
                "ningún paquete de voz compatible; el catálogo trae: "
                + (", ".join(descartes) or "nada"))
    try:
        resultado = paquetes_instalacion.instalar(paquete)
    except Exception as error:
        return (PASO_INSTALAR, f"no se pudo instalar: {error}")
    if not resultado.correcta:
        return (PASO_INSTALAR, resultado.motivo)
    try:
        trozos = _hablar(paquete)
    except Exception as error:
        return (PASO_VOZ, str(error))
    if not tiene_audio(trozos):
        return (PASO_VOZ, "la voz no produjo audio")
    return (None, "")


def principal() -> int:
    with tempfile.TemporaryDirectory(prefix="voces-real-") as temporal:
        carpeta = Path(temporal) / "voces"
        with (mock.patch.object(paths, "carpeta_voces", return_value=carpeta),
              mock.patch.dict(paquetes_instalacion._CARPETAS,
                              {"voz": paths.carpeta_voces})):
            paso, motivo = _correr()
    linea, codigo = linea_final(paso, motivo)
    print(linea)
    return codigo


if __name__ == "__main__":
    sys.exit(principal())
