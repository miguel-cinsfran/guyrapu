# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué cuenta como defecto en una parada del foco del carril.

Recibe el recorrido de una ventana y el conjunto de textos del catálogo
inglés, y devuelve los hallazgos con regla, nivel, ventana, paso, tecla y
detalle. Es puro: no toca NVDA, ni Windows, ni ventanas.

Todas las reglas nacen como «aviso». El paso a freno y el código 1 llegan
con las ventanas de la app.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
RUTA_CATALOGO = RAIZ / "idiomas" / "en" / "LC_MESSAGES" / "guyrapu.po"

NIVELES = {
    "sin_nombre": "aviso",
    "rol_contenedor": "aviso",
    "nombre_repetido": "aviso",
    "ingles": "aviso",
    "atajo_repetido": "aviso",
    "paso_mudo": "aviso",
    "foco_perdido": "aviso",
    "espera_no_oida": "aviso",
    "recorrido": "aviso",
}

ROLES_CONTENEDOR = frozenset({
    "UNKNOWN", "WINDOW", "PANE", "PANEL", "FRAME", "APPLICATION"})

LETRAS_MINIMAS_TEXTO = 4
LARGO_MINIMO_NOMBRE = 3

# NVDA dice el nombre del combo y después el rol, aunque el foco sea la
# edición interna del combo y no traiga nombre propio.
_COMBO_NOMBRADO = re.compile(r"^\s*(.+?)\s+cuadro combinado\b", re.IGNORECASE)


def normalizar(texto) -> str:
    """La forma en que se comparan dos textos del catálogo o del habla."""
    limpio = str(texto).replace("&", "").replace("…", "")
    limpio = limpio.replace("...", "")
    limpio = " ".join(limpio.split())
    return limpio.rstrip(":").strip().casefold()


def _letras(texto) -> int:
    return sum(1 for caracter in str(texto) if caracter.isalpha())


def leer_catalogo_ingles(ruta=None) -> set:
    """Los textos ingleses traducidos, distintos del original y con letras.

    Se comparan normalizados y se descartan los de menos de cuatro letras,
    que son los que el habla repite sin querer.
    """
    from babel.messages import pofile

    ruta = Path(ruta) if ruta else RUTA_CATALOGO
    with open(ruta, "rb") as archivo:
        catalogo = pofile.read_po(archivo)
    textos = set()
    for mensaje in catalogo:
        original = mensaje.id
        traduccion = mensaje.string
        if not isinstance(original, str) or not isinstance(traduccion, str):
            continue
        if not original.strip() or _letras(traduccion) < LETRAS_MINIMAS_TEXTO:
            continue
        if normalizar(traduccion) == normalizar(original):
            continue
        textos.add(normalizar(traduccion))
    return textos


def identidad(foco) -> tuple:
    """La ventana nativa más el nombre y el rol: dos controles no se confunden."""
    return (str(foco.get("hwnd")), str(foco.get("nombre") or ""),
            str(foco.get("rol_nombre") or foco.get("rol") or ""))


def _frases(paso) -> list:
    frases = []
    for evento in paso.get("habla") or ():
        partes = evento.get("partes")
        if partes:
            frases.extend(str(parte) for parte in partes if str(parte).strip())
            continue
        texto = str(evento.get("texto") or "")
        if texto.strip():
            frases.append(texto)
    return frases


def _combo_nombrado(frases) -> bool:
    """El habla empieza con un nombre seguido de «cuadro combinado»."""
    return bool(_COMBO_NOMBRADO.match(" ".join(frases)))


def _atajo(foco) -> str:
    """El atajo si es Alt más una letra, ya en minúsculas para comparar."""
    atajo = str(foco.get("atajo") or "").strip().casefold()
    if len(atajo) == 5 and atajo.startswith("alt+") and atajo[4].isalpha():
        return atajo
    return ""


def _perdido(foco, datos) -> bool:
    rol = str(foco.get("rol_nombre") or foco.get("rol") or "")
    if rol in ROLES_CONTENEDOR:
        return True
    if not str(foco.get("nombre") or "").strip():
        return True
    estados = {str(estado).casefold() for estado in foco.get("estados") or ()}
    if "unavailable" in estados:
        return True
    pid = foco.get("pid")
    pid_ventana = datos.get("pid")
    return (pid is not None and pid_ventana is not None
            and int(pid) != int(pid_ventana))


def _problema_de_recorrido(datos) -> str:
    primero = datos.get("primero") or {}
    lista = datos.get("primero_lista")
    identidad_primera = identidad(primero)

    def es_primera(foco):
        if identidad(foco) == identidad_primera:
            return True
        if not lista:
            return False
        rol = str(foco.get("rol_nombre") or foco.get("rol") or "")
        return rol.casefold() == "listitem" and foco.get("padre") == lista

    def clave(foco):
        return identidad_primera if es_primera(foco) else identidad(foco)

    pasos = datos.get("pasos") or []
    focos_ida = [paso.get("foco") or {} for paso in pasos
                 if paso.get("fase") == "ida"]
    focos_vuelta = [paso.get("foco") or {} for paso in pasos
                    if paso.get("fase") == "vuelta"]
    ida = [identidad_primera] + [clave(foco) for foco in focos_ida]
    vuelta = [identidad_primera] + [clave(foco) for foco in focos_vuelta]
    if not any(clave(foco) == identidad_primera for foco in focos_ida):
        return "la ida con Tab no vuelve a la primera parada antes del tope"
    if vuelta != list(reversed(ida)):
        return "la vuelta con Mayús+Tab no da las mismas paradas al revés"
    return ""


def _hallazgo(regla, datos, paso=None, detalle="") -> dict:
    tecla = None
    if paso is not None:
        tecla = (datos["pasos"][paso] or {}).get("tecla")
    return {
        "regla": regla,
        "nivel": NIVELES[regla],
        "ventana": datos.get("ventana"),
        "paso": paso,
        "tecla": tecla,
        "detalle": detalle,
    }


def analizar(datos, catalogo_ingles) -> list:
    """Los hallazgos de un recorrido, en el orden en que aparecen sus pasos."""
    hallazgos = []
    vistos_atajos = {}
    catalogo = catalogo_ingles or set()
    for indice, paso in enumerate(datos.get("pasos") or []):
        foco = paso.get("foco") or {}
        nombre = str(foco.get("nombre") or "").strip()
        rol = str(foco.get("rol_nombre") or foco.get("rol") or "")
        frases = _frases(paso)
        if not nombre and not _combo_nombrado(frases):
            hallazgos.append(_hallazgo(
                "sin_nombre", datos, indice, "la parada no tiene nombre"))
        if paso.get("tecla") == "tab" and rol in ROLES_CONTENEDOR:
            hallazgos.append(_hallazgo(
                "rol_contenedor", datos, indice,
                f"la parada de Tab tiene el rol {rol}"))
        if (paso.get("fase") != "pagina"
                and len(nombre) >= LARGO_MINIMO_NOMBRE
                and " ".join(frases).casefold().count(nombre.casefold()) >= 2):
            hallazgos.append(_hallazgo(
                "nombre_repetido", datos, indice,
                f"«{nombre}» se oye más de una vez"))
        if any(normalizar(frase) in catalogo for frase in frases + [nombre]):
            hallazgos.append(_hallazgo(
                "ingles", datos, indice, "hay un texto del catálogo inglés"))
        if paso.get("fase") != "pagina":
            hallazgos.extend(_revisar_atajo(
                datos, indice, foco, vistos_atajos))
        if paso.get("fase") == "accion":
            if not frases:
                hallazgos.append(_hallazgo(
                    "paso_mudo", datos, indice, "la acción no dijo nada"))
            if _perdido(foco, datos):
                hallazgos.append(_hallazgo(
                    "foco_perdido", datos, indice,
                    "después de la acción el foco quedó perdido"))
        if paso.get("espera") and not paso.get("oida"):
            frase = paso["espera"]
            dicho = str(paso.get("espera_dicho") or "").strip()
            hallazgos.append(_hallazgo(
                "espera_no_oida", datos, indice,
                f"no se oyó «{frase}»: NVDA dijo {dicho!r}"))
    problema = _problema_de_recorrido(datos)
    if problema:
        hallazgos.append(_hallazgo("recorrido", datos, None, problema))
    return hallazgos


def _revisar_atajo(datos, indice, foco, vistos) -> list:
    atajo = _atajo(foco)
    if not atajo:
        return []
    identidad_atajo = identidad(foco)
    previo = vistos.get(atajo)
    vistos.setdefault(atajo, (identidad_atajo, indice))
    if previo is None or previo[0] == identidad_atajo:
        return []
    return [_hallazgo(
        "atajo_repetido", datos, indice,
        f"«{atajo}» ya estaba en el paso {previo[1]}")]
