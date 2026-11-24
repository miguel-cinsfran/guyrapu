# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo el carril levanta la aplicación real y recorre sus ventanas.

La sonda del banco graba los anuncios y atiende las órdenes, pero su lector es
mudo. Acá se instala un doble que reenvía cada anuncio al lector de verdad y al
grabador de la sonda. Después se abre cada ventana de `ventanas_app` por el
menú, se conduce con el complemento de NVDA y se guarda su transcripción.
"""

from __future__ import annotations

import configparser
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from qa import banco_app, foco_ventanas, sonda
from qa.nvda import (
    recorrido, reglas, teclado_estado, transcripcion, ventanas_app)
from qa.nvda.recorrido import InstrumentoRoto

RAIZ = Path(__file__).resolve().parent.parent.parent

COD_TRANSCRIPCION = 7
INTENTOS = 3
ESPERA_REINTENTO = 3
VAR_DATOS = "GUYRAPU_QA_DATOS"
ESPACIO_CREDENCIALES = "GuyrapuCarril/"


class TranscripcionCambiada(RuntimeError):
    """Una transcripción aprobada cambió y la nueva no se aprobó."""

    def __init__(self, lineas):
        super().__init__("cambió una transcripción aprobada")
        self.lineas = lineas


class _SinFrente(RuntimeError):
    """El frente no se pudo tomar; lleva quién lo tenía y si se abrió."""

    def __init__(self, mensaje, abierta):
        self.plano = foco_ventanas.describir_primer_plano()
        if not abierta:
            mensaje += (f": primer plano {self.plano['proceso']!r} "
                        f"«{self.plano['titulo']}»")
        super().__init__(mensaje)
        self.abierta = abierta


class _GrabadorSonidos(logging.Handler):
    """Anota el nombre de cada sonido del catálogo que realmente sonó."""

    def __init__(self, ruta):
        super().__init__(level=logging.DEBUG)
        self._ruta = Path(ruta)

    def emit(self, registro):
        mensaje = registro.getMessage()
        if "SONIDO evento=" not in mensaje or "omitido" in mensaje:
            return
        evento = mensaje.split("SONIDO evento=", 1)[1].split()[0]
        try:
            with open(self._ruta, "a", encoding="utf-8") as archivo:
                archivo.write(evento + "\n")
        except OSError as exc:
            logging.getLogger(__name__).debug(
                "no se pudo anotar el sonido: %s", exc)


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
    """Deja la carpeta aislada con el INI de fábrica y los ajustes del carril."""
    ruta = os.environ.get(VAR_DATOS)
    if not ruta:
        return
    from guyrapu.core import config_predeterminada, paths

    carpeta = Path(ruta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / "config.ini"
    config_predeterminada.escribir(destino)
    ajustes = [ajuste for entrada in ventanas_app.VENTANAS
               for ajuste in entrada.get("ajustes") or ()]
    # Música lee [musica] carpeta del INI: vacía cae en la Música de Windows y
    # la transcripción cambia según la PC. Medido el 19/11/2026.
    carpeta_musica = carpeta / "musica"
    carpeta_musica.mkdir(exist_ok=True)
    ajustes.append({"seccion": "musica", "clave": "carpeta",
                    "valor": str(carpeta_musica)})
    if ajustes:
        parser = configparser.ConfigParser(interpolation=None,
                                           default_section="__none__")
        parser.read(destino, encoding="utf-8")
        for ajuste in ajustes:
            seccion = ajuste["seccion"]
            if not parser.has_section(seccion):
                parser.add_section(seccion)
            parser.set(seccion, ajuste["clave"], ajuste["valor"])
        with open(destino, "w", encoding="utf-8") as salida:
            parser.write(salida)
    paths.carpeta_datos = lambda: carpeta


def _aislar_claves() -> None:
    """Apunta las claves de IA al espacio del carril, sin tocar las reales."""
    from guyrapu.ai import claves

    original = claves._destino

    def _destino_carril(proveedor, prefijo):
        return ESPACIO_CREDENCIALES + original(proveedor, prefijo)

    claves._destino = _destino_carril


def preparar() -> None:
    """Aísla datos y claves, instala la sonda y deja el lector real tras un doble."""
    _aislar_datos()
    _aislar_claves()
    ruta_sonidos = os.environ.get(recorrido.VAR_SONIDOS)
    if ruta_sonidos:
        logger_sonidos = logging.getLogger("guyrapu.sound_player")
        logger_sonidos.setLevel(logging.DEBUG)
        logger_sonidos.addHandler(_GrabadorSonidos(ruta_sonidos))
    from guyrapu.ui import accesibilidad, gui
    from guyrapu.voice import sound_player

    originales = (gui._lector_init, accesibilidad._lector_init)
    sonda.instalar()
    sound_player.silenciar_todo(False)
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
        sonidos = self.anuncios_ruta.parent / "sonidos.txt"
        entorno[recorrido.VAR_SONIDOS] = str(sonidos)
        os.environ[recorrido.VAR_SONIDOS] = str(sonidos)
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
    analizador.add_argument("--ventana", action="extend", nargs="+",
                            metavar="NOMBRE",
                            help="recorre esas ventanas de la aplicación, "
                                 "en el orden dado")


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


def _intentar_ventana(banco, cliente, entrada, pid, catalogo, aprobar):
    from qa.nvda.correr import _lineas_de_ventana

    nombre = entrada["nombre"]
    # Si otra ventana tiene el primer plano, el diálogo se construye sin él y
    # el SetFocus de su __init__ no llega al lector. Medido el 19/11/2026 con
    # Música y un terminal en primer plano.
    if not banco.al_frente():
        raise _SinFrente(
            f"no se pudo traer al frente la app para «{entrada['titulo']}»",
            False)
    banco.pedir("menu_click", etiqueta=entrada["menu"], tiempo=10.0)
    titulo_menu = entrada.get("titulo_menu") or entrada["titulo"]
    if banco.esperar_ventana(titulo_menu, segundos=15.0) is None:
        raise InstrumentoRoto(f"no se abrió la ventana «{titulo_menu}»")
    if not banco.al_frente():
        raise _SinFrente(
            f"no se pudo traer al frente la ventana «{entrada['titulo']}»",
            True)
    datos_ventana = {
        "nombre": nombre,
        "pid": pid,
        "primero": entrada["primero"],
    }
    if entrada.get("primero_lista"):
        datos_ventana["primero_lista"] = entrada["primero_lista"]
    if entrada.get("pulsar"):
        datos_ventana["pulsar"] = entrada["pulsar"]
    if entrada.get("pagina"):
        datos_ventana["pagina"] = entrada["pagina"]
        datos_ventana["paginas"] = (entrada["paginas"] if "paginas" in entrada
                                   else _paginas_de_interaccion())
    if entrada.get("acciones"):
        datos_ventana["acciones"] = entrada["acciones"]
    opciones = {"tope": entrada["tope"]} if "tope" in entrada else {}
    datos = recorrido.conducir(cliente, datos_ventana, **opciones)
    banco.pedir("cerrar_ventana", ventana=entrada["titulo"], tiempo=10.0)
    hallazgos = reglas.analizar(datos, catalogo)
    lineas = _lineas_de_ventana(nombre, datos, hallazgos)
    diferencia = transcripcion.comparar(
        nombre,
        transcripcion.texto(datos, entrada.get("valor_variable") or ()),
        aprobar)
    if diferencia:
        lineas.append(f"transcripción distinta en «{nombre}»:")
        lineas.extend(diferencia.splitlines())
        return lineas, True
    return lineas, False


def _ventana(banco, cliente, entrada, pid, catalogo, aprobar):
    """Recorre la ventana y reintenta si el primer plano se pierde."""
    for intento in range(INTENTOS):
        try:
            return _intentar_ventana(
                banco, cliente, entrada, pid, catalogo, aprobar)
        except _SinFrente as falla:
            if intento == INTENTOS - 1:
                raise InstrumentoRoto(str(falla)) from None
            plano = falla.plano
            print(f"reintento de {entrada['nombre']}: primer plano "
                  f"{plano['proceso']} «{plano['titulo']}»", flush=True)
            if falla.abierta:
                banco.pedir("cerrar_ventana", ventana=entrada["titulo"],
                            tiempo=10.0)
            time.sleep(ESPERA_REINTENTO)


def recorrer(cliente, args, iniciales=(), revisar=None) -> list:
    seleccion = list(ventanas_app.VENTANAS)
    pedidas = getattr(args, "ventana", None) or ()
    if pedidas:
        conocidas = {entrada["nombre"]: entrada for entrada in seleccion}
        for nombre in pedidas:
            if nombre not in conocidas:
                raise InstrumentoRoto(f"no hay ventana «{nombre}»")
        seleccion = [conocidas[nombre] for nombre in pedidas]
    aprobar = bool(getattr(args, "aprobar", False))
    catalogo = reglas.leer_catalogo_ingles()
    lineas = list(iniciales)
    lineas.append("== ventanas de la aplicación ==")
    diferentes = False
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as base:
        banco = Aplicacion(Path(base))
        try:
            with teclado_estado.con_bloq_mayus_apagado():
                banco.arrancar()
                if not banco.esperar_lista():
                    raise InstrumentoRoto(
                        "la aplicación no abrió su ventana principal")
                pid = _pid(banco)
                for entrada in seleccion:
                    print(f"ventana {entrada['nombre']}", flush=True)
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
