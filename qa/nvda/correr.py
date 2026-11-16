# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Punto de entrada del carril de NVDA.

Ordena la corrida: guardia de presencia, estado anotado, respaldo, cierre del
NVDA de la PC, perfil de prueba, copia portátil, arranque, conexión y canario.
Por cualquier camino pasa por la devolución, que deja el NVDA de la PC como
estaba y borra la tarea de respaldo. Si el guion muere de golpe, la tarea
programada corre `devolver.py`.

    python qa/nvda/correr.py --canario
    python qa/nvda/correr.py --reglas
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from qa.nvda import cliente as cliente_nvda  # noqa: E402
from qa.nvda import (devolver, nvda_local, perfil, recorrido, reglas,  # noqa: E402
                     seguridad, trampas)
from qa.nvda.recorrido import InstrumentoRoto  # noqa: E402

COD_OK = 0
COD_INSTRUMENTO = 2
COD_PRESENCIA = 3
COD_VERSION = 4
COD_CORTE = 5
COD_RESPALDO = 6

ESPERADOS = (
    ("tab", "Opción de prueba", "casilla"),
    ("tab", "Aceptar", "botón"),
)


class Cortado(Exception):
    """Llegó teclado o ratón físico durante la corrida."""


class ReglasFallidas(InstrumentoRoto):
    """Alguna regla no saltó en su trampa o saltó en la ventana limpia."""

    def __init__(self, fallos, lineas):
        super().__init__("; ".join(fallos))
        self.lineas = lineas


def _revisar(vigilante) -> None:
    if vigilante.cortado:
        raise Cortado()


def _unir_habla(eventos) -> str:
    return " ".join(evento.get("texto", "") for evento in eventos
                    if evento.get("tipo") == "habla").strip()


def _conectar(vigilante, ruta_estado, tope_s=30.0):
    limite = time.monotonic() + tope_s
    ultimo = "sin carril.json"
    while time.monotonic() < limite:
        _revisar(vigilante)
        try:
            cliente = cliente_nvda.Cliente(ruta_estado)
            cliente.version()
            return cliente
        except (OSError, KeyError, ValueError,
                cliente_nvda.ErrorCliente) as exc:
            ultimo = str(exc)
            time.sleep(0.25)
    raise InstrumentoRoto(
        f"el complemento no respondió en {tope_s:.0f} s: {ultimo}")


def _esperar_foco(cliente, nombre, vigilante, tope_s=20.0) -> None:
    limite = time.monotonic() + tope_s
    while time.monotonic() < limite:
        _revisar(vigilante)
        if cliente.foco().get("nombre") == nombre:
            return
        time.sleep(0.25)
    raise InstrumentoRoto("la ventana canario no tomó el foco")


def _paso_canario(cliente, gesto, nombre, rol, vigilante) -> str:
    marca = cliente.marca()
    cliente.tecla(gesto)
    _revisar(vigilante)
    habla = _unir_habla(cliente.desde(marca))
    foco = cliente.foco()
    if nombre not in habla:
        raise InstrumentoRoto(f"después de {gesto} no se oyó «{nombre}»")
    if foco.get("nombre") != nombre:
        raise InstrumentoRoto(
            f"después de {gesto} el foco es «{foco.get('nombre')}»")
    texto_rol = (foco.get("rol_texto") or "").lower()
    if rol not in texto_rol or rol not in habla.lower():
        raise InstrumentoRoto(
            f"«{nombre}» no dijo el rol {rol} en habla y foco")
    return (f"{gesto}: habla={habla!r}; "
            f"foco={foco.get('nombre')!r}, rol={foco.get('rol_texto')!r}")


def _canario(cliente, vigilante) -> list:
    guion = Path(__file__).with_name("canario.py")
    proceso = subprocess.Popen([sys.executable, str(guion)])
    lineas = []
    try:
        _esperar_foco(cliente, "Nombre:", vigilante)
        inicial = _unir_habla(cliente.desde(0))
        if "Canario listo" not in inicial:
            raise InstrumentoRoto("no se oyó «Canario listo»")
        lineas.append("anuncio inicial: " + inicial)
        for gesto, nombre, rol in ESPERADOS:
            lineas.append(_paso_canario(
                cliente, gesto, nombre, rol, vigilante))
        cliente.tecla("alt+f4")
        return lineas
    finally:
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait(timeout=5)


def _corrida(args, vigilante, ruta_copia, ruta_perfil, accion, instalado,
             actual) -> list:
    if not nvda_local.cerrar(actual):
        raise InstrumentoRoto(
            "el NVDA de la PC no terminó de cerrarse; no se arranca la copia")
    _revisar(vigilante)
    perfil.armar_perfil(ruta_perfil)
    _revisar(vigilante)
    if accion == "armar":
        if nvda_local.crear_portatil(instalado, ruta_copia) != 0:
            raise InstrumentoRoto("no se pudo armar la copia portátil")
    nvda_local.lanzar(
        ruta_copia / "nvda.exe",
        ["-c", str(ruta_perfil), "-f", str(perfil.ruta_registro()),
         "-l", "10"])
    cliente = _conectar(vigilante, ruta_perfil / "carril.json")
    if getattr(args, "reglas", False):
        lineas = _canario(cliente, vigilante)
        return _reglas(cliente, vigilante, lineas)
    if not args.canario:
        return ["NVDA respondió"]
    return _canario(cliente, vigilante)


def _escribir_informe(lineas) -> Path:
    salida = RAIZ / "qa" / "salida" / "nvda"
    salida.mkdir(parents=True, exist_ok=True)
    destino = salida / time.strftime("informe-%Y%m%d-%H%M%S.txt")
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


def _linea_paso(indice, paso) -> str:
    foco = paso.get("foco") or {}
    habla = " ".join(str(evento.get("texto") or "")
                     for evento in paso.get("habla") or [])
    return (f"paso {indice} {paso.get('tecla')} [{paso.get('fase')}]: "
            f"habla={habla!r}; foco={foco.get('nombre')!r}, "
            f"rol={foco.get('rol_nombre')!r}; "
            f"espera_agotada={paso.get('agotado')}; "
            f"ms_habla={paso.get('ms_habla')}")


def _lineas_de_ventana(nombre, datos, hallazgos) -> list:
    lineas = [f"--- {nombre}: {datos.get('ventana')} ---"]
    pasos = datos.get("pasos") or []
    for indice, paso in enumerate(pasos):
        lineas.append(_linea_paso(indice, paso))
    tiempos = [paso["ms_habla"] for paso in pasos
               if paso.get("ms_habla") is not None]
    lineas.append(f"máximo de la última habla: "
                  f"{max(tiempos) if tiempos else None} ms")
    if not hallazgos:
        lineas.append("sin hallazgos")
    for hallazgo in hallazgos:
        lineas.append(
            f"hallazgo {hallazgo['regla']} ({hallazgo['nivel']}) "
            f"ventana={hallazgo['ventana']} paso={hallazgo['paso']} "
            f"tecla={hallazgo['tecla']}: {hallazgo['detalle']}")
    return lineas


def _fallos_de_reglas(por_ventana) -> list:
    fallos = []
    for nombre in reglas.NIVELES:
        hallazgos = por_ventana.get(nombre) or []
        if not any(hallazgo["regla"] == nombre for hallazgo in hallazgos):
            fallos.append(f"la regla «{nombre}» no saltó en su trampa")
    for hallazgo in por_ventana.get("limpia") or []:
        fallos.append(
            f"la regla «{hallazgo['regla']}» saltó en la limpia "
            f"en el paso {hallazgo['paso']}")
    return fallos


def _reglas(cliente, vigilante, iniciales=()) -> list:
    catalogo = reglas.leer_catalogo_ingles()
    nombres = ["limpia"] + [nombre for nombre, datos in trampas.VENTANAS.items()
                            if datos["regla"]]
    lineas = list(iniciales)
    lineas.append("== reglas del carril ==")
    por_ventana = {}
    for nombre in nombres:
        _revisar(vigilante)
        datos = trampas.VENTANAS[nombre]
        try:
            recorrido_datos = recorrido.recorrer(datos, cliente)
        except (InstrumentoRoto, OSError) as exc:
            lineas.append(f"{nombre}: instrumento roto: {exc}")
            raise ReglasFallidas([str(exc)], lineas) from None
        hallazgos = reglas.analizar(recorrido_datos, catalogo)
        lineas.extend(_lineas_de_ventana(nombre, recorrido_datos, hallazgos))
        por_ventana[nombre] = hallazgos
    _revisar(vigilante)
    fallos = _fallos_de_reglas(por_ventana)
    if fallos:
        lineas.append("instrumento roto: " + "; ".join(fallos))
        raise ReglasFallidas(fallos, lineas)
    lineas.append("reglas: instrumento en verde")
    return lineas


def _copiar_registro(ruta_informe) -> None:
    origen = perfil.ruta_registro()
    if not origen.is_file():
        return
    destino = Path(ruta_informe).with_name(
        Path(ruta_informe).stem + "-nvda.log")
    shutil.copyfile(origen, destino)
    print(f"Registro de NVDA: {destino}")


def _guardia(args):
    """El motivo de la negación, o None si se puede empezar."""
    segundos = seguridad.segundos_desde_ultima_entrada()
    marca = seguridad.leer_fin_limpio(perfil.ruta_fin_limpio())
    try:
        permitido, motivo = seguridad.decidir_guardia(
            segundos, args.sin_espera, args.una_pc, marca)
    except seguridad.ModoRequerido as exc:
        return str(exc)
    return None if permitido else motivo


def _elegir_copia(version):
    ruta_copia = perfil.ruta_portatil(version)
    existe = (ruta_copia / "nvda.exe").is_file()
    instalado = nvda_local.instalado_por_defecto()
    instalada = (version if existe
                 else nvda_local.version_de_ejecutable(instalado))
    accion = nvda_local.decidir_copia(existe, instalada, version)
    return ruta_copia, instalado, accion


def _programar_respaldo(vigilante, minutos) -> bool:
    try:
        vigilante.iniciar()
    except RuntimeError as exc:
        print(f"No se pudieron instalar los ganchos de entrada: {exc}")
        return False
    momento = seguridad.momento_respaldo(minutos)
    linea = seguridad.linea_comando(
        sys.executable, Path(__file__).with_name("devolver.py"))
    creado, detalle = seguridad.crear_respaldo(
        seguridad.NOMBRE_RESPALDO, momento, linea)
    if not creado:
        print(f"No se pudo programar el respaldo: {detalle}")
    return creado


def _con_canario(args, vigilante, ruta_copia, accion, instalado,
                 actual) -> int:
    codigo = COD_OK
    lineas = []
    try:
        lineas = _corrida(args, vigilante, ruta_copia,
                          perfil.ruta_perfil(), accion, instalado, actual)
    except Cortado:
        print("Cortado por teclado o ratón físico: se devuelve el NVDA.")
        codigo = COD_CORTE
    except ReglasFallidas as exc:
        print(f"Instrumento roto: {exc}")
        lineas = exc.lineas
        codigo = COD_INSTRUMENTO
    except InstrumentoRoto as exc:
        print(f"Instrumento roto: {exc}")
        lineas.append(f"instrumento roto: {exc}")
        codigo = COD_INSTRUMENTO
    ruta = _escribir_informe(lineas)
    args.informe = ruta
    print(f"Informe: {ruta}")
    return codigo


def _devolver(ruta_estado, ruta_copia, instalado) -> None:
    try:
        devuelto = devolver.ejecutar_devolucion(
            ruta_estado, ruta_copia, instalado)
    except OSError as exc:
        print(f"No se pudo devolver el NVDA: {exc}")
        devuelto = False
    if devuelto:
        seguridad.borrar_respaldo(seguridad.NOMBRE_RESPALDO)
    else:
        print("No se pudo devolver el NVDA de la PC.")


def ejecutar(args) -> int:
    negado = _guardia(args)
    if negado:
        print(negado)
        return COD_PRESENCIA
    version = perfil.version_esperada()
    try:
        ruta_copia, instalado, accion = _elegir_copia(version)
    except nvda_local.VersionInvalida as exc:
        print(exc)
        return COD_VERSION
    actual = nvda_local.nvda_en_marcha()
    ruta_estado = perfil.ruta_estado()
    seguridad.escribir_estado(ruta_estado, seguridad.estado_inicial(actual))
    vigilante = seguridad.Vigilante()
    codigo = COD_OK
    ruta_informe = None
    try:
        if not _programar_respaldo(vigilante, args.respaldo_minutos):
            codigo = COD_RESPALDO
            return codigo
        codigo = _con_canario(args, vigilante, ruta_copia, accion,
                              instalado, actual)
        ruta_informe = getattr(args, "informe", None)
        return codigo
    finally:
        vigilante.detener()
        if not vigilante.cortado:
            seguridad.anotar_fin_limpio(perfil.ruta_fin_limpio())
        _devolver(ruta_estado, ruta_copia, instalado)
        if codigo != COD_OK and ruta_informe:
            _copiar_registro(ruta_informe)


def main(argv=None) -> int:
    analizador = argparse.ArgumentParser(
        description="Carril de NVDA del banco de QA.")
    analizador.add_argument("--canario", action="store_true",
                            help="recorre la ventana canario")
    analizador.add_argument("--reglas", action="store_true",
                            help="recorre el canario, la limpia y las trampas")
    analizador.add_argument("--sin-espera", action="store_true",
                            help="saltea la guardia de diez minutos")
    analizador.add_argument("--una-pc", action="store_true",
                            help="modo de una sola PC")
    analizador.add_argument("--respaldo-minutos", type=int,
                            default=seguridad.RESPALDO_MINUTOS)
    return ejecutar(analizador.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
