# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Proveedor de voz Phonon, sobre la biblioteca ptts y paquetes locales.

La única razón de este módulo para cambiar es cómo se habla con `ptts`. Es
el único archivo que la importa, y la importa al crear el motor, no al
importar el módulo. Las voces salen de las fichas de los paquetes instalados
en `voces/`, sin red.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from guyrapu.core import diagnostico
from guyrapu.core import paquetes_instalacion
from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.voice.proveedores.base import (
    Capacidades,
    MotorNoDisponible,
    Proveedor,
)

logger = diagnostico.obtener_logger(__name__)

_ID = "phonon"
_LICENCIA = N_("Según cada paquete de voces: Phonon en español y portugués, "
               "CC BY-NC 4.0; en inglés, Apache 2.0")
_MSG_SIN_VOCES = N_("No hay voces de Phonon instaladas. Descarga un paquete "
                    "de voces en Preferencias, Voces.")

_TASA_PREDETERMINADA = 24000
_RANGO_VELOCIDAD = (0.86, 1.29)

# Puntos medidos el 13/11/2026: más allá de -0.45 Phonon vuelve a ir más
# lento, así que el resto de la velocidad lo pone el estiramiento.
_PUNTOS_DURACION = ((0.864, 0.3), (1.0, 0.0), (1.288, -0.45))

_hilos_configurados = False


@dataclass(frozen=True)
class _VozInstalada:
    nombre: str
    mostrado: str
    idioma: str
    archivo: Path
    paquete: str
    carpeta: Path


def _paquetes() -> list[dict]:
    return [ficha for ficha in paquetes_instalacion.instalados("voz")
            if ficha.get("proveedor") == _ID]


def _voces_instaladas() -> list[_VozInstalada]:
    voces = []
    vistos = set()
    base = paths.carpeta_voces()
    for ficha in _paquetes():
        paquete = str(ficha.get("id", ""))
        idioma = str(ficha.get("idioma", ""))
        carpeta = base / paquete
        for voz in ficha.get("voces", ()):
            nombre = voz.get("nombre")
            archivo = voz.get("archivo")
            if not nombre or not archivo:
                continue
            mostrado = nombre
            if nombre in vistos:
                mostrado = f"{nombre} ({idioma})"
            vistos.add(nombre)
            voces.append(_VozInstalada(
                nombre=nombre, mostrado=mostrado, idioma=idioma,
                archivo=carpeta / archivo, paquete=paquete, carpeta=carpeta))
    return voces


def delta_duracion(factor) -> float:
    """Convierte el factor de velocidad a la condición `duration_delta`."""
    factor = float(factor)
    if factor <= _PUNTOS_DURACION[0][0]:
        return _PUNTOS_DURACION[0][1]
    for (x0, y0), (x1, y1) in zip(_PUNTOS_DURACION, _PUNTOS_DURACION[1:]):
        if factor <= x1:
            return y0 + (y1 - y0) * (factor - x0) / (x1 - x0)
    return _PUNTOS_DURACION[-1][1]


def _ptts():
    import ptts
    return ptts


def _fijar_hilos(ptts_modulo) -> None:
    global _hilos_configurados
    if _hilos_configurados:
        return
    from guyrapu.voice.motor_local import HILOS_SINTESIS
    ptts_modulo.set_num_threads(HILOS_SINTESIS)
    _hilos_configurados = True


class SintetizadorPhonon:
    """Sintetizador de `motor_local` sobre un modelo de ptts."""

    rango_velocidad = _RANGO_VELOCIDAD
    ganancia_voz = 1.0

    def __init__(self, ptts_modulo=None):
        self._ptts = ptts_modulo if ptts_modulo is not None else _ptts()
        self._voces = _voces_instaladas()
        self._modelos = {}
        self._activo = None
        self._nombre = None

    @property
    def tasa(self) -> int:
        if self._activo is None:
            return _TASA_PREDETERMINADA
        return int(self._activo.sample_rate)

    def voces(self) -> list[str]:
        return [voz.mostrado for voz in self._voces]

    def elegir_voz(self, idx) -> bool:
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return False
        if not 0 <= idx < len(self._voces):
            return False
        voz = self._voces[idx]
        modelo = self._modelo(voz)
        if modelo is None:
            return False
        self._activo = modelo
        self._nombre = voz.nombre
        return True

    def _modelo(self, voz):
        if voz.paquete in self._modelos:
            return self._modelos[voz.paquete]
        try:
            _fijar_hilos(self._ptts)
            modelo = self._ptts.TTS(
                model=str(voz.carpeta), lang=voz.idioma[:2].lower(),
                quant="q8_0")
            for otra in self._voces:
                if otra.paquete == voz.paquete:
                    modelo.add_voice(otra.nombre, str(otra.archivo))
        except Exception as exc:
            logger.warning("No se pudo cargar el modelo de Phonon %s: %s",
                           voz.paquete, exc)
            return None
        self._modelos[voz.paquete] = modelo
        return modelo

    def sintetizar(self, texto, velocidad_propia):
        if self._activo is None or self._nombre is None:
            return iter(())
        self._activo.set_conditions(
            {"duration_delta": delta_duracion(velocidad_propia)})
        return self._activo.stream(texto, voice=self._nombre)

    def cerrar(self) -> None:
        self._modelos.clear()
        self._activo = None
        self._nombre = None


def listar_voces(fabrica_contexto=None) -> list[str]:
    return [voz.mostrado for voz in _voces_instaladas()]


def crear(clave_elevenlabs=None):
    if not listar_voces():
        raise MotorNoDisponible(_(_MSG_SIN_VOCES))
    from guyrapu.voice.motor_local import MotorLocal
    return MotorLocal(SintetizadorPhonon(_ptts()))


_CAPACIDADES = Capacidades(streaming=True, tono=True, nube=False)

PROVEEDOR_PHONON = Proveedor(
    id=_ID,
    nombre=N_("Phonon, voces locales"),
    licencia=_LICENCIA,
    capacidades=_CAPACIDADES,
    crear=crear,
    listar_voces=listar_voces,
)
