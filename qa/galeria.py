# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Galería de las ventanas de la aplicación, fuera de la aplicación.

Cada muestra se arma en un proceso propio con su biblioteca gráfica, como
prepara `main.py` la ventana principal: idioma español, tema de la app y
datos aislados en una carpeta temporal. Se abre sin activar, se recorren
sus páginas como las elegiría el usuario y se guarda un PNG y un JSON por
captura. Ninguna muestra sale a la red ni lee los datos reales.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import json
import logging
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
_QA = Path(__file__).resolve().parent
for _ruta in (str(_QA), str(_RAIZ)):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

import capturas
import galeria_geometria as geo
import galeria_muestras as muestras

logger = logging.getLogger(__name__)


def _argumentos(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo", action="append", default=[],
                        metavar="NOMBRE", help="arma solo esta muestra; se puede repetir")
    parser.add_argument("--salida", metavar="CARPETA",
                        help="carpeta donde se guarda la galería")
    parser.add_argument("--_muestra", help=argparse.SUPPRESS)
    parser.add_argument("--_carpeta", help=argparse.SUPPRESS)
    parser.add_argument("--_numero", type=int, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def _carpeta_de(args):
    if args.salida:
        return Path(args.salida)
    fecha = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    return _QA / "salida" / "galeria" / fecha


def main(argv=None):
    args = _argumentos(argv)
    if args._muestra:
        return _hijo(args)
    por_nombre = {entrada[0]: entrada for entrada in muestras.MUESTRAS}
    desconocidas = [nombre for nombre in args.solo if nombre not in por_nombre]
    if desconocidas:
        print("No hay muestra con este nombre: " + ", ".join(desconocidas),
              file=sys.stderr)
        return 2
    elegidas = ([por_nombre[n] for n in args.solo] if args.solo
                else list(muestras.MUESTRAS))
    carpeta = _carpeta_de(args)
    carpeta.mkdir(parents=True, exist_ok=True)
    lineas = []
    siguiente = 1
    fallidas = 0
    for nombre, clase, variante, _armar in elegidas:
        nuevas = _una_muestra(siguiente, nombre, clase, variante, carpeta)
        lineas.extend(nuevas)
        fallidas += sum("FALLIDA:" in linea for linea in nuevas)
        siguiente += len(nuevas)
    (carpeta / "indice.md").write_text(_indice(lineas), encoding="utf-8")
    print(f"{len(lineas)} capturas, {fallidas} fallidas en {carpeta}")
    return 1 if fallidas else 0


def _una_muestra(numero, nombre, clase, variante, carpeta):
    import os
    orden = [sys.executable, str(Path(__file__)), "--_muestra", nombre,
             "--_carpeta", str(carpeta), "--_numero", str(numero)]
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.run(orden, cwd=str(_RAIZ), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              env=entorno, timeout=90)
    except subprocess.TimeoutExpired:
        return [geo.linea_indice(numero, nombre, clase, variante, "", "",
                                 0, 0) + " · FALLIDA: tardó más de 90 s"]
    datos = None
    for linea in reversed(proc.stdout.splitlines()):
        if linea.strip().startswith("{"):
            try:
                datos = json.loads(linea)
            except ValueError:
                pass
            break
    if datos is None:
        motivo = (proc.stderr.strip().splitlines() or ["sin salida"])[-1]
        return [geo.linea_indice(numero, nombre, clase, variante, "", "",
                                 0, 0) + " · FALLIDA: " + motivo[-160:]]
    return datos.get("lineas", [])


def _indice(lineas):
    partes = ["# Galería de ventanas", "",
              "Una línea por captura: imagen, muestra, clase, variante, "
              "página y tamaño en píxeles.", ""]
    return "\n".join(partes + (lineas or ["(sin capturas)"])) + "\n"


def _hijo(args):
    import wx
    from guyrapu.core import idioma
    from tests.rutas_temporales import redirigir_rutas

    por_nombre = {entrada[0]: entrada for entrada in muestras.MUESTRAS}
    nombre, clase, variante, armar = por_nombre[args._muestra]
    app = wx.App(False)
    idioma.instalar("es")
    with tempfile.TemporaryDirectory(prefix="galeria-") as temporal:
        contexto = contextlib.ExitStack()
        with contexto:
            datos = _Contexto(Path(temporal), contexto)
            contexto.enter_context(redirigir_rutas(datos.carpeta))
            _silenciar(contexto)
            ventana = armar(datos)
            ventana.ShowWithoutActivating()
            _aplicar_layout(ventana)
            lineas = _capturar(ventana, nombre, clase, variante,
                               args._carpeta, args._numero)
    del app
    print(json.dumps({"lineas": lineas}))
    return 0


class _Contexto:
    def __init__(self, carpeta, pila):
        self.carpeta = carpeta
        self.pila = pila


def _silenciar(pila):
    """Sin voz, sin sonidos y sin hilos que puedan salir a la red."""
    from unittest import mock
    from guyrapu.core import diagnostico
    from guyrapu.ui import accesibilidad
    from guyrapu.voice import sound_player

    pila.enter_context(mock.patch.object(
        accesibilidad, "anunciar", mock.Mock()))
    pila.enter_context(mock.patch.object(
        accesibilidad, "anunciar_con_sonido", mock.Mock()))
    pila.enter_context(mock.patch.object(
        diagnostico, "crear_hilo", mock.Mock()))
    try:
        sound_player.silenciar_todo(True)
    except Exception as exc:
        logger.debug("No se pudieron callar los sonidos: %s", exc)


def _aplicar_layout(ventana):
    """Corre los sizers: mostrar la ventana no basta para que wx los aplique.

    Sin esto los controles quedan en su tamaño mínimo y amontonados en el
    origen, aunque `IsShownOnScreen` diga que están visibles. Medido el
    20/11/2026 con la galería completa.
    """
    import wx
    ventana.Layout()
    for control in _descendientes(ventana):
        sizer = getattr(control, "GetSizer", None)
        if callable(sizer) and sizer():
            control.Layout()
    wx.SafeYield()


def _descendientes(ventana):
    hijos = list(ventana.GetChildren())
    for hijo in hijos:
        yield hijo
        yield from _descendientes(hijo)


def _libros(ventana):
    """Cuadernos de páginas del árbol, reconocidos por lo que saben hacer."""
    hallados = []

    def recorrer(control):
        metodos = ("GetPageCount", "GetPageText", "SetSelection",
                   "GetSelection")
        if all(hasattr(control, metodo) for metodo in metodos):
            if not any(control is libro for libro in hallados):
                hallados.append(control)
        try:
            hijos = list(control.GetChildren())
        except Exception:
            hijos = []
        for hijo in hijos:
            recorrer(hijo)

    recorrer(ventana)
    return hallados


def _capturar(ventana, nombre, clase, variante, salida, numero):
    import wx
    import captura_ventana as cap

    paginas = [(None, None)]
    libros = _libros(ventana)
    if libros:
        paginas = [(libro, i) for libro in libros
                   for i in range(libro.GetPageCount())]
    lineas = []
    for desplazamiento, (libro, i) in enumerate(paginas):
        pagina = None if libro is None else str(libro.GetPageText(i))
        if libro is not None:
            libro.SetSelection(i)
            wx.SafeYield()
            perezoso = getattr(ventana, "_libro_perezoso", None)
            if perezoso is not None:
                perezoso.construir(i)
            _aplicar_layout(ventana)
        n = numero + desplazamiento
        archivo = f"{n:02d}_{nombre}_{capturas.plegar(pagina or 'base')}.png"
        ruta = Path(salida) / archivo
        cap._dejar_pintar(ventana)
        ancho, alto = cap._guardar_png(ventana, ruta)
        contenido = _escribir_json(ventana, ruta.with_suffix(".json"),
                                   nombre, clase, variante, pagina, archivo,
                                   ancho, alto)
        motivo = geo.motivo_invalido(contenido["controles"],
                                     _colores_imagen(ruta),
                                     contenido["tamano"])
        if motivo:
            lineas.append(geo.linea_fallida(n, nombre, clase, variante,
                                            motivo))
        else:
            lineas.append(geo.linea_indice(n, nombre, clase, variante,
                                           pagina, archivo, ancho, alto))
    return lineas


def _escribir_json(ventana, ruta, nombre, clase, variante, pagina, png,
                   ancho, alto):
    origen = ventana.ClientToScreen((0, 0))
    pantalla = _area_de_trabajo()
    contenido = geo.captura_diccionario(
        muestra=nombre, clase=clase, variante=variante, pagina=pagina,
        png=png, tamano=_par(ventana.GetSize()),
        cliente=_par(ventana.GetClientSize()),
        tamano_minimo=_par(ventana.GetMinSize()), pantalla=pantalla,
        controles=_controles(ventana, origen, _ppi()))
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return contenido


def _colores_imagen(ruta):
    """Muestra de píxeles del PNG, para detectar una imagen casi de un color."""
    import wx
    imagen = wx.Image(str(ruta))
    if not imagen.IsOk():
        return []
    ancho_, alto_ = imagen.GetWidth(), imagen.GetHeight()
    paso = max(8, min(ancho_, alto_) // 40)
    return [(imagen.GetRed(x, y), imagen.GetGreen(x, y),
             imagen.GetBlue(x, y))
            for y in range(0, alto_, paso)
            for x in range(0, ancho_, paso)]


def _ppi():
    import wx
    try:
        ppi = wx.Display(0).GetPPI()
        return (int(ppi.GetWidth()), int(ppi.GetHeight()))
    except Exception:
        return (96, 96)


def _area_de_trabajo():
    import wx
    try:
        area = wx.Display(0).GetClientArea()
        return [int(area.GetWidth()), int(area.GetHeight())]
    except Exception as exc:
        logger.debug("No se pudo leer el área de trabajo: %s", exc)
        return list(wx.GetDisplaySize())


def _par(tamano):
    return [int(tamano.GetWidth()), int(tamano.GetHeight())]


def _controles(ventana, origen, ppi):
    salida = []

    def recorrer(control, padre):
        salida.append(_describir_control(control, padre, ventana, origen, ppi))
        try:
            hijos = list(control.GetChildren())
        except Exception:
            hijos = []
        for hijo in hijos:
            recorrer(hijo, control)

    recorrer(ventana, None)
    return salida


def _describir_control(control, padre, ventana, origen, ppi):
    pos = control.ClientToScreen((0, 0))
    tamano = control.GetSize()
    etiqueta = _etiqueta(control)
    fuente = control.GetFont()
    return geo.control_diccionario(
        id=control.GetId(),
        padre=(None if padre is None or padre is ventana else padre.GetId()),
        clase=control.GetClassName(), nombre=control.GetName(),
        etiqueta=etiqueta,
        rect=geo.rect_relativo((pos.x, pos.y, tamano.x, tamano.y), origen),
        visible=control.IsShownOnScreen(), habilitado=control.IsEnabled(),
        enfocable=control.AcceptsFocus(),
        fg=geo.color_hex(control.GetForegroundColour()),
        bg=geo.color_hex(control.GetBackgroundColour()),
        fuente=geo.fuente_diccionario(fuente, ppi),
        texto_px=_medida(control, etiqueta))


def _etiqueta(control):
    try:
        return control.GetLabel() or ""
    except Exception:
        return ""


def _medida(control, etiqueta):
    if not etiqueta:
        return [0, 0]
    lineas = str(etiqueta).split("\n")
    medidas = [control.GetFullTextExtent(linea) for linea in lineas]
    ancho = max(int(m[0]) for m in medidas)
    alto = sum(int(m[1]) for m in medidas)
    return [ancho, alto]


class VerificacionGaleria(unittest.TestCase):
    """Corrida real con tres muestras, una con páginas, en la PC sin dueño."""

    def test_tres_muestras_con_paginas(self):
        destino = _QA / "salida" / "galeria" / "verificacion"
        inicio = time.monotonic()
        codigo = main(["--solo", "interaccion", "--solo", "musica",
                       "--solo", "principal_desconectada",
                       "--salida", str(destino)])
        texto = (destino / "indice.md").read_text(encoding="utf-8")
        capturas = [linea for linea in texto.splitlines()
                    if linea.startswith("- ")]
        print(f"GALERIA: {len(capturas)} capturas, "
              f"{time.monotonic() - inicio:.1f} s, {destino}")
        self.assertEqual(codigo, 0)
        self.assertGreaterEqual(len(capturas), 3)

    def test_galeria_completa(self):
        import collections
        import visual_reglas

        inicio = time.monotonic()
        codigo = main([])
        destino = max((_QA / "salida" / "galeria").glob("20*"),
                      key=lambda ruta: ruta.name)
        texto = (destino / "indice.md").read_text(encoding="utf-8")
        lineas = [linea for linea in texto.splitlines()
                  if linea.startswith("- ")]
        fallidas = [linea for linea in lineas if "FALLIDA:" in linea]
        hallazgos, _ = visual_reglas.analizar(
            visual_reglas.leer_carpeta(destino))
        conteo = collections.Counter(h["regla"] for h in hallazgos)
        print("COMPLETA " + json.dumps({
            "carpeta": destino.name, "capturas": len(lineas),
            "fallidas": len(fallidas), "segundos": round(time.monotonic() - inicio, 1),
            "motivos": [linea.split("FALLIDA: ", 1)[-1] for linea in fallidas],
            "hallazgos": dict(sorted(conteo.items())),
        }, ensure_ascii=False))
        self.assertEqual(codigo, 0)


if __name__ == "__main__":
    sys.exit(main())
