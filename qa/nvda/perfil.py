# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Perfil de prueba de NVDA para el carril.

Arma cada corrida un perfil nuevo bajo `%LOCALAPPDATA%\\guyrapu-qa`, con un
`nvda.ini` que apaga todo lo que interrumpe una medición (actualizaciones,
bienvenida, estadísticas, seguimiento del ratón, sonidos de inicio y salida)
y deja cargar la carpeta de borrador con el sintetizador espía y el
complemento del carril.

Lo que no es puro son las escrituras y la copia de `dentro/`, y van contra
la carpeta de trabajo del carril. La decisión de negarse cuando la ruta cae
en `%APPDATA%\nvda` sí es pura y está probada.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

NOMBRE_BASE = "guyrapu-qa"
NOMBRE_PERFIL = "perfil-nvda"
NOMBRE_VERSION = "version_nvda.txt"
NOMBRE_REGISTRO = "nvda.log"
NOMBRE_FIN_LIMPIO = "fin-limpio.txt"

INI = """schemaVersion = 2

[general]
language = es
showWelcomeDialogAtStartup = False
playStartAndExitSounds = False
askToExit = False

[update]
autoCheck = False
startupNotification = False
allowUsageStats = False
askedAllowUsageStats = True

[mouse]
enableMouseTracking = False

[presentation]
reportKeyboardShortcuts = True
reportObjectDescriptions = True
[[progressBarUpdates]]
progressBarOutputMode = off

[virtualBuffers]
autoSayAllOnPageLoad = False

[speech]
synth = espia_guyrapu
symbolLevel = 100
unicodeNormalization = DISABLED

[keyboard]
handleInjectedKeys = True

[development]
enableScratchpadDir = True

[screenCurtain]
enabled = False
"""


def carpeta_base(localappdata=None) -> Path:
    """`%LOCALAPPDATA%\\guyrapu-qa`, donde vive todo lo que arma el carril."""
    base = localappdata or os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    return Path(base) / NOMBRE_BASE


def ruta_perfil(localappdata=None) -> Path:
    return carpeta_base(localappdata) / NOMBRE_PERFIL


def ruta_portatil(version, localappdata=None) -> Path:
    return carpeta_base(localappdata) / f"nvda-{version}"


def ruta_estado(localappdata=None) -> Path:
    return carpeta_base(localappdata) / "estado-carril.json"


def ruta_registro(localappdata=None) -> Path:
    return ruta_perfil(localappdata) / NOMBRE_REGISTRO


def ruta_fin_limpio(localappdata=None) -> Path:
    return carpeta_base(localappdata) / NOMBRE_FIN_LIMPIO


def version_esperada() -> str:
    archivo = Path(__file__).resolve().parent / NOMBRE_VERSION
    return archivo.read_text(encoding="utf-8").strip()


def dentro_de(ruta, raiz) -> bool:
    """Si `ruta` es `raiz` o cae dentro, comparando como Windows.

    Se resuelven los enlaces y uniones del sistema: una carpeta que apunta a
    `%APPDATA%\\nvda` no puede colarse como si fuera otra.
    """
    ruta = os.path.normcase(os.path.realpath(str(ruta)))
    raiz = os.path.normcase(os.path.realpath(str(raiz)))
    return ruta == raiz or ruta.startswith(raiz + os.sep)


def perfil_seguro(destino, appdata=None) -> Path:
    """Devuelve el destino o se niega a escribir sobre la configuración real."""
    base = appdata or os.environ.get("APPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Roaming")
    protegido = Path(base) / "nvda"
    if dentro_de(destino, protegido):
        raise ValueError(
            f"el perfil de prueba no puede vivir en {protegido}: "
            f"el carril nunca toca el NVDA de la PC")
    return Path(destino)


def contenido_ini() -> str:
    return INI


def armar_perfil(destino=None, dentro=None, appdata=None,
                 localappdata=None) -> Path:
    """Deja un perfil recién armado, con el espía en su carpeta de borrador."""
    destino = Path(destino) if destino else ruta_perfil(localappdata)
    perfil_seguro(destino, appdata)
    # Se arma de cero para que un carril.json o un eventos.jsonl viejo no
    # haga creer al cliente que la corrida anterior sigue viva.
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    (destino / "nvda.ini").write_text(contenido_ini(), encoding="utf-8")
    origen = Path(dentro) if dentro else Path(__file__).resolve().parent / "dentro"
    shutil.copytree(origen, destino / "scratchpad", dirs_exist_ok=True)
    return destino
