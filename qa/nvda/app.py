# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo el carril levanta la aplicación real y recorre sus ventanas.

La sonda del banco graba los anuncios y atiende las órdenes, pero su lector es
mudo. Acá se instala un doble que reenvía cada anuncio al lector de verdad y al
grabador de la sonda. Después se abre cada ventana de `ventanas_app` por el
menú, se conduce con el complemento de NVDA y se guarda su transcripción.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from qa import banco_app, sonda
from qa.nvda import recorrido, reglas, transcripcion, ventanas_app
from qa.nvda.recorrido import InstrumentoRoto

RAIZ = Path(__file__).resolve().parent.parent.parent

COD_TRANSCRIPCION = 7
VAR_DATOS = "GUYRAPU_QA_DATOS"


class TranscripcionCambiada(RuntimeError):
    """Una transcripción aprobada cambió y la nueva no se aprobó."""

    def __init__(self, lineas):
        super().__init__("cambió una transcripción aprobada")
        self.lineas = lineas


class DobleLector:
    """Le habla al lector real y deja la misma copia en la sonda."""

    def __init__(self, real, grabador):
        self._real = real
        self._grabador = grabador

    def speak(self, texto, interrupt=False):
        if self._real is not None:
            self._real.speak(texto, interrupt=interrupt)
        self._grabador.speak(texto, interrupt=interrupt)

    def braille(self, texto):
        if self._real is not None:
            self._real.braille(texto)
        self._grabador.braille(texto)


def falta_prism() -> bool:
    """Avisa por stderr si prism no se importa y dice cómo correr el carril."""
    try:
        import prism  # noqa: F401
    except ImportError:
        print("Falta el paquete prism: corré el carril con uv run python "
              "qa/nvda/correr.py.", file=sys.stderr)
        return True
    return False


def _aislar_datos() -> None:
    """Deja la carpeta de datos del carril y le copia la configuración real."""
    ruta = os.environ.get(VAR_DATOS)
    if not ruta:
        return
    from guyrapu.core import paths

    carpeta = Path(ruta)
    carpeta.mkdir(parents=True, exist_ok=True)
    origen = paths.carpeta_datos() / "config.ini"
    if origen.exists():
        shutil.copy2(origen, carpeta / "config.ini")
    paths.carpeta_datos = lambda: carpeta


def preparar() -> None:
    """Aísla los datos, instala la sonda y deja el lector real tras un doble."""
    _aislar_datos()
    from guyrapu.ui import accesibilidad, gui

    originales = (gui._lector_init, accesibilidad._lector_init)
    sonda.instalar()
    grabador = accesibilidad._lector

    def _con_doble(original):
        def _init():
            original()
            accesibilidad._lector = DobleLector(accesibilidad._lector,
                                                grabador)
        return _init

    gui._lector_init = _con_doble(originales[0])
    accesibilidad._lector_init = _con_doble(originales[1])


def arrancar(ruta_main) -> None:
    """Prepara la sonda y cede el control a `main.py` como si nada."""
    preparar()
    import runpy
    runpy.run_path(str(ruta_main), run_name="__main__")


class Aplicacion(banco_app.Aplicacion):
    """La aplicación real, con la sonda del banco y la salida al lector."""

    def arrancar(self) -> None:
        entorno = dict(os.environ)
        datos = self.anuncios_ruta.parent / "datos"
        datos.mkdir(parents=True, exist_ok=True)
        entorno[VAR_DATOS] = str(datos)
        entorno[sonda.VAR_DESTINO] = str(self.anuncios_ruta)
        entorno[sonda.VAR_ORDENES] = str(self.ordenes_ruta)
        entorno[sonda.VAR_RESULTADOS] = str(self.resultados_ruta)
        codigo = (
            "import sys; sys.path.insert(0, r'%s'); "
            "import qa.nvda.app as carril; carril.arrancar(r'%s')"
            % (RAIZ, RAIZ / "main.py")
        )
        # La salida de la aplicación NO se tira: wx escribe ahí sus avisos de
        # widgets mal construidos, y hoy no los lee nadie.
        self._salida = open(self.salida_ruta, "w", encoding="utf-8",
                            errors="replace")
        self.proceso = subprocess.Popen(
            [sys.executable, "-c", codigo], cwd=str(RAIZ), env=entorno,
            stdout=self._salida, stderr=subprocess.STDOUT)


def agregar_argumentos(analizador) -> None:
    analizador.add_argument("--aprobar", action="store_true",
                            help="aprueba las transcripciones nuevas")
    analizador.add_argument("--ventana",
                            help="recorre solo esa ventana de la aplicación")


def _pid(banco) -> int:
    pid = int(banco.pedir("pid").get("datos", {}).get("pid") or 0)
    if not pid:
        raise InstrumentoRoto("la aplicación no dijo su pid")
    return pid


def _paginas_de_interaccion() -> list:
    """Los nombres que muestra la lista de páginas, en su orden."""
    from guyrapu.core import idioma
    from guyrapu.ui import interaccion_ventana

    return [idioma._(etiqueta)
            for _clave, etiqueta in interaccion_ventana.PAGINAS]


def _ventana(banco, cliente, entrada, pid, catalogo, aprobar):
    from qa.nvda.correr import _lineas_de_ventana

    nombre = entrada["nombre"]
    banco.pedir("menu_click", etiqueta=entrada["menu"], tiempo=10.0)
    if banco.esperar_ventana(entrada["titulo"], segundos=15.0) is None:
        raise InstrumentoRoto(
            f"no se abrió la ventana «{entrada['titulo']}»")
    if not banco.al_frente():
        raise InstrumentoRoto(
            f"no se pudo traer al frente la ventana «{entrada['titulo']}»")
    datos_ventana = {
        "nombre": nombre,
        "pid": pid,
        "primero": entrada["primero"],
    }
    if entrada.get("pagina"):
        datos_ventana["pagina"] = entrada["pagina"]
        datos_ventana["paginas"] = _paginas_de_interaccion()
    datos = recorrido.conducir(cliente, datos_ventana)
    banco.pedir("cerrar_ventana", ventana=entrada["titulo"], tiempo=10.0)
    hallazgos = reglas.analizar(datos, catalogo)
    lineas = _lineas_de_ventana(nombre, datos, hallazgos)
    diferencia = transcripcion.comparar(
        nombre, transcripcion.texto(datos), aprobar)
    if diferencia:
        lineas.append(f"transcripción distinta en «{nombre}»:")
        lineas.extend(diferencia.splitlines())
        return lineas, True
    return lineas, False


def recorrer(cliente, args, iniciales=(), revisar=None) -> list:
    seleccion = list(ventanas_app.VENTANAS)
    pedida = getattr(args, "ventana", None)
    if pedida:
        seleccion = [entrada for entrada in seleccion
                     if entrada["nombre"] == pedida]
        if not seleccion:
            raise InstrumentoRoto(f"no hay ventana «{pedida}»")
    aprobar = bool(getattr(args, "aprobar", False))
    catalogo = reglas.leer_catalogo_ingles()
    lineas = list(iniciales)
    lineas.append("== ventanas de la aplicación ==")
    diferentes = False
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as base:
        banco = Aplicacion(Path(base))
        try:
            banco.arrancar()
            if not banco.esperar_lista():
                raise InstrumentoRoto(
                    "la aplicación no abrió su ventana principal")
            pid = _pid(banco)
            for entrada in seleccion:
                if revisar is not None:
                    revisar()
                nuevas, distinta = _ventana(
                    banco, cliente, entrada, pid, catalogo, aprobar)
                lineas.extend(nuevas)
                diferentes = diferentes or distinta
        finally:
            banco.cerrar()
    if diferentes:
        raise TranscripcionCambiada(lineas)
    return lineas
