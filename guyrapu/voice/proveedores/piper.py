# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Proveedor de voz de Piper sobre los paquetes instalados en `voces/`.

Este es el único módulo que importa la biblioteca `piper`: la carga al crear
el motor para que quien no use voces de Piper no la pague. Las voces salen
de las fichas instaladas, sin red.
"""

from __future__ import annotations

import inspect

from guyrapu.core import diagnostico
from guyrapu.core import paquetes_instalacion
from guyrapu.core import paths
from guyrapu.core import voces_disponibles
from guyrapu.core.idioma import N_, _
from guyrapu.voice.proveedores.base import (
    Capacidades,
    MotorNoDisponible,
    Proveedor,
)

logger = diagnostico.obtener_logger(__name__)

_TASA_PREDETERMINADA = 22050

_avisado_hilos = False

_NOMBRE = N_("Piper, voces locales")
_LICENCIA = N_(
    "Según cada voz: dominio público, CC0, CC BY, CC BY-SA, Apache 2.0 o "
    "Unlicense")
_MSG_SIN_VOCES = N_(
    "No hay voces de Piper instaladas. Descarga una voz desde Preferencias.")
_MSG_SIN_PIPER = N_("No se pudo cargar Piper: {detalle}")


def _onnx(ficha):
    identificador = ficha.get("id")
    if not isinstance(identificador, str) or not identificador:
        return None
    for archivo in ficha.get("archivos") or []:
        if not isinstance(archivo, dict):
            continue
        ruta = archivo.get("ruta")
        if isinstance(ruta, str) and ruta.endswith(".onnx"):
            return paths.carpeta_voces() / identificador / ruta
    return None


def _entradas():
    entradas = []
    for ficha in paquetes_instalacion.instalados("voz"):
        if ficha.get("proveedor") != "piper":
            continue
        voces = ficha.get("voces")
        if not isinstance(voces, list) or not voces:
            continue
        modelo = _onnx(ficha)
        if modelo is None:
            continue
        for voz in voces:
            if not isinstance(voz, dict) or not str(voz.get("nombre", "")).strip():
                continue
            entradas.append((ficha, voz, modelo))
    return entradas


def _nombres(entradas):
    bases = []
    for ficha, voz, _modelo in entradas:
        nombre = str(voz.get("nombre", "")).strip()
        idioma = voz.get("idioma") or ficha.get("idioma")
        bases.append((nombre, idioma, voz))
    cuentas = {}
    for nombre, idioma, _voz in bases:
        clave = (nombre, str(idioma))
        cuentas[clave] = cuentas.get(clave, 0) + 1
    nombres = []
    vistos = {}
    for nombre, idioma, voz in bases:
        lugar = voces_disponibles.nombre_idioma(idioma)
        if cuentas[(nombre, str(idioma))] > 1:
            genero = voces_disponibles.nombre_genero(voz.get("genero"))
            texto = f"{nombre}, {genero}, {lugar}" if genero else f"{nombre}, {lugar}"
        else:
            texto = f"{nombre}, {lugar}"
        cuenta = vistos.get(texto, 0) + 1
        vistos[texto] = cuenta
        nombres.append(texto if cuenta == 1 else f"{texto}, {cuenta}")
    return nombres


def _a_float32(trozo):
    import numpy as np

    datos = getattr(trozo, "audio_float_array", trozo)
    datos = np.asarray(datos)
    if np.issubdtype(datos.dtype, np.integer):
        return datos.astype(np.float32) / 32768.0
    return datos.astype(np.float32, copy=False)


def _cargar(PiperVoice, modelo):
    global _avisado_hilos

    from guyrapu.voice.motor_local import HILOS_SINTESIS

    try:
        parametros = inspect.signature(PiperVoice.load).parameters
    except (TypeError, ValueError):
        parametros = {}
    hilos = {nombre: HILOS_SINTESIS
             for nombre in ("intra_op_num_threads", "inter_op_num_threads")
             if nombre in parametros}
    if not hilos and not _avisado_hilos:
        logger.info("Piper no permite fijar los hilos de onnxruntime; "
                    "se usan los del sistema.")
        _avisado_hilos = True
    return PiperVoice.load(modelo, **hilos)


class SintetizadorPiper:
    """Sintetizador de Piper con la interfaz de `motor_local.Sintetizador`."""

    rango_velocidad = (0.5, 2.0)
    ganancia_voz = 1.0

    def __init__(self, entradas, clases):
        self._entradas = list(entradas)
        self._clases = clases
        self._voz = None
        self._indice = None
        self._modelo = None
        self.tasa = _TASA_PREDETERMINADA

    def voces(self) -> list[str]:
        return _nombres(self._entradas)

    def elegir_voz(self, idx) -> bool:
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return False
        if not 0 <= idx < len(self._entradas):
            return False
        if idx == self._indice and self._voz is not None:
            return True
        PiperVoice, _SynthesisConfig = self._clases
        modelo = self._entradas[idx][2]
        if self._voz is not None and self._modelo == modelo:
            voz = self._voz
        else:
            try:
                voz = _cargar(PiperVoice, modelo)
            except Exception as exc:
                logger.warning("No se pudo cargar la voz de Piper %s: %s",
                               modelo, exc)
                return False
        # Solo se conserva el modelo elegido: cada uno ocupa decenas de MB.
        self._voz = voz
        self._indice = idx
        self._modelo = modelo
        self.tasa = int(voz.config.sample_rate)
        return True

    def sintetizar(self, texto, velocidad_propia):
        voz = self._voz
        if voz is None:
            return
        _PiperVoice, SynthesisConfig = self._clases
        parametros = {"length_scale": 1.0 / float(velocidad_propia)}
        hablante = self._entradas[self._indice][1].get("hablante")
        if hablante is not None:
            parametros["speaker_id"] = int(hablante)
        configuracion = SynthesisConfig(**parametros)
        for trozo in voz.synthesize(texto, configuracion):
            yield _a_float32(trozo)

    def cerrar(self) -> None:
        self._voz = None
        self._indice = None
        self._modelo = None


def crear(clave_elevenlabs=None, salida=None, al_avisar=None):
    entradas = _entradas()
    if not entradas:
        raise MotorNoDisponible(_(_MSG_SIN_VOCES))
    try:
        from piper import PiperVoice, SynthesisConfig
    except Exception as exc:
        raise MotorNoDisponible(_(_MSG_SIN_PIPER).format(detalle=exc)) from exc
    from guyrapu.voice.motor_local import MotorLocal

    return MotorLocal(SintetizadorPiper(
        entradas, (PiperVoice, SynthesisConfig)), salida=salida,
        al_avisar=al_avisar, motor="piper")


def listar_voces(fabrica_contexto=None) -> list[str]:
    return _nombres(_entradas())


PROVEEDOR_PIPER = Proveedor(
    id="piper",
    nombre=_NOMBRE,
    nombre_corto="Piper",
    licencia=_LICENCIA,
    capacidades=Capacidades(streaming=True, tono=True, nube=False, local=True),
    crear=crear,
    listar_voces=listar_voces,
)
