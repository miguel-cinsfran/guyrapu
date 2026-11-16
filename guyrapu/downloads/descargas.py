# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Gestor de descargas con yt-dlp (módulo puro, sin wx).

Frontera pura/plataforma: este módulo no importa `wx` ni el módulo de yt-dlp.

NO se acopla con las 2 llamadas yt-dlp existentes en `main.obtener_info_video`
ni en `reproductor._info_video`: este módulo hace sus PROPIAS llamadas a
el programa independiente, en su propio hilo.

Modos soportados: los nueve de `opciones_formato.FORMATOS`, con sus
argumentos en `argumentos_ytdlp.argumentos_de_formato`.
"""
from __future__ import annotations

import subprocess
import threading
import time  # noqa: F401  (reexport para las pruebas)
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from guyrapu.core import diagnostico
from guyrapu.core.config import obtener_opciones_descarga
from guyrapu.core.idioma import _
from guyrapu.downloads.avisos_item import AvisosItem
from guyrapu.downloads import ffmpeg_bin
from guyrapu.downloads import fila_descargas
from guyrapu.downloads import proceso_descarga
from guyrapu.downloads import ytdlp_bin
from guyrapu.downloads.analisis_enlace import (
    TIEMPO_ESPERA_ANALISIS, analizar_url)
from guyrapu.downloads.opciones_formato import SIMULTANEAS_DEFECTO
from guyrapu.downloads.argumentos_ytdlp import (
    argumentos_descarga, carpeta_base, recortar_url_registro)
from guyrapu.downloads.progreso_ytdlp import PREFIJO_RUTA_FINAL

logger = diagnostico.obtener_logger(__name__)

@dataclass
class ItemDescarga:
    """Una descarga encolada. El estado se va mutando desde el hilo de descarga."""
    id: str
    url: str
    tipo: str                # "video" | "playlist" | "error"
    estado: str = "en_cola"  # en_cola | descargando | completado | error | cancelado
    progreso: float = 0.0    # 0..100
    mensaje: str = ""
    nombre: str = ""
    carpeta: str = ""        # destino elegido al encolar (para el historial)
    rutas: list[str] = field(default_factory=list)
    indice: int = 0
    total: int = 0
    procesando: bool = False
    velocidad: float | None = None
    eta: int | None = None


# ── Helpers puros (testeables en Linux) ──────────────────────────────────────


def _comprobar_herramientas(estado_cb: Callable) -> Optional[str]:
    ruta = ytdlp_bin.ruta_ytdlp()
    if ruta is None:
        estado_cb("error", _("yt-dlp no está instalado"))
        return None

    if not tiene_ffmpeg():
        # Error CLARO (no el genérico de yt-dlp) para que el usuario ciego
        # sepa exactamente qué falta. La GUI ya hace 3-vías con este mensaje.
        estado_cb("error",
                   _("ffmpeg no encontrado. La descarga necesita ffmpeg para "
                     "unir audio y vídeo o extraer audio. Usa la versión "
                     "empaquetada o instala ffmpeg. En desarrollo, basta "
                     "con tener ffmpeg en el PATH."))
        return None
    return ruta


def _estado_inicial() -> dict:
    return {"ultimo_error": "", "ultimo_archivo": "", "ultimo_ts": None,
            "rutas": [], "indice": 0, "total": 0, "procesando": False,
            "ultimo_avance": None, "estancado": False,
            "esperando_detalle": False}


def descargar(url: str, opciones: dict,
              progreso_cb: Callable, estado_cb: Callable,
              cancel_event: threading.Event, al_detalle=None) -> None:
    """Lanza la descarga en el HILO ACTUAL.

    Pensada para correr dentro de `threading.Thread(target=descargar, ...)` que
    crea `GestorDescargas.encolar`. El hilo SIEMPRE termina: las excepciones se
    convierten en `estado_cb("error" | "cancelado", mensaje)` y se hace
    `return`. NUNCA se re-lanza fuera del hilo.

    Callbacks:
      - progreso_cb(pct: float, velocidad, eta, nombre): se invoca desde el
        progress hook de yt-dlp cada vez que hay actualización de bytes.
      - estado_cb(estado: str, mensaje: str): transiciones de estado: primero
        "descargando", luego uno de "completado" | "parcial" | "cancelado" |
        "error".
      - al_detalle(cambios: dict): opcional; avisa la ruta de cada archivo
        terminado, el índice y el total de la lista, y si yt-dlp procesa.
    """
    ruta = _comprobar_herramientas(estado_cb)
    if ruta is None:
        return

    enumerar = bool(opciones.get("enumerar", False))
    carpeta = carpeta_base(opciones)
    al_detalle = al_detalle or (lambda _cambios: None)
    estado = _estado_inicial()

    estado_cb("descargando", "")
    try:
        proceso = proceso_descarga.lanzar_proceso(
            ruta, argumentos_descarga(url, opciones, enumerar))
        proceso_descarga.leer_salida(proceso, cancel_event, carpeta, estado,
                                     progreso_cb, estado_cb, al_detalle)
    except OSError as exc:
        logger.warning("descargar falló: %s", exc)
        estado_cb("error", str(exc) or exc.__class__.__name__)
    except Exception as exc:
        logger.warning("descargar falló: %s", exc)
        estado_cb("error", str(exc) or exc.__class__.__name__)


def tiene_ffmpeg() -> bool:
    """¿Hay ffmpeg disponible? El mismo resolvedor que usa la descarga."""
    return ffmpeg_bin.ruta_ffmpeg() is not None


# ── Gestor de cola ───────────────────────────────────────────────────────────


class GestorDescargas:
    """Cola de descargas. Cada ítem corre en su propio hilo (daemon).

    Los callbacks que recibe `encolar` llevan el `item_id` como primer
    argumento, así la capa de GUI puede actualizar la fila correspondiente
    de su `wx.ListCtrl` sin tener que mantener un mapping externo.
    """

    def __init__(self, opciones: Optional[dict] = None) -> None:
        self._opciones: dict = dict(opciones) if opciones else obtener_opciones_descarga()
        self._items: dict[str, ItemDescarga] = {}
        self._eventos: dict[str, threading.Event] = {}
        self._orden: list[str] = []
        self._suscriptores_fin: list[Callable] = []
        self._lock = threading.Lock()
        self._corriendo = 0
        self._empezados: set[str] = set()

    def set_opciones(self, op: dict) -> None:
        """Reemplaza las opciones para lo que se encole después."""
        with self._lock:
            self._opciones = dict(op)

    def hay_turno(self) -> bool:
        """Si queda un turno libre para descargar ya, sin esperar en cola."""
        with self._lock:
            return self._corriendo < self._opciones.get("simultaneas", SIMULTANEAS_DEFECTO)

    def suscribir_fin(self, callback: Callable) -> None:
        """Añade un aviso de estado sin duplicarlo.

        `callback(estado, mensaje, nombre, item)` corre en el HILO DE DESCARGA:
        quien toque wx debe pasar por wx.CallAfter. Recibe el ItemDescarga
        para que el historial se registre aunque el diálogo esté cerrado.
        """
        with self._lock:
            if callback not in self._suscriptores_fin:
                self._suscriptores_fin.append(callback)

    def _esperar_turno(self, item_id, ev) -> bool:
        # Espera el turno antes de analizar: el contador acota cuántos corren
        # y la fila impone el orden. Si cancelan, vuelve sin tomar el turno.
        while True:
            if ev.is_set():
                return False
            with self._lock:
                bloqueado = fila_descargas.bloqueado_por_anterior(
                    item_id, self._orden, self._empezados, self._items,
                    self._eventos)
                tope = self._opciones.get("simultaneas", SIMULTANEAS_DEFECTO)
                if not bloqueado and self._corriendo < tope:
                    self._corriendo += 1
                    self._empezados.add(item_id)
                    return True
            if bloqueado:
                ev.wait(0.02)
            else:
                ev.wait(0.2)

    def _avisar_suscriptores(self, estado, mensaje, it) -> None:
        # Avisa sin tocar el ítem, desde el hilo de descarga.
        nombre = it.nombre if it.nombre != it.url else ""
        with self._lock:
            suscriptores = list(self._suscriptores_fin)
        for suscriptor in suscriptores:
            try:
                suscriptor(estado, mensaje, nombre, it)
            except Exception as exc:
                logger.warning("suscriptor de descarga lanzó: %s", exc)

    def _avisar_estado(self, it, estado, mensaje, estado_cb) -> None:
        it.estado = estado
        it.mensaje = mensaje
        logger.info("descarga %s: estado %s", it.id, estado)
        try:
            estado_cb(it.id, estado, mensaje)
        except Exception as exc:
            logger.debug("estado_cb lanzó: %s", exc)
        self._avisar_suscriptores(estado, mensaje, it)
        if estado in ("completado", "parcial", "cancelado", "error"):
            logger.info("descarga %s terminó: %s", it.id, estado)

    def _correr(self, item_id, it, ev, url, opciones, avisos) -> None:
        # Doble red de seguridad: capturar lo que sea que se escape.
        tomado = False
        try:
            tomado = self._esperar_turno(item_id, ev)
            if not tomado:
                avisos.estado("cancelado", _("Descarga cancelada"))
                return
            try:
                info = analizar_url(url)
                it.tipo = info.get("tipo", "video")
                it.total = int(info.get("cuenta") or 0)
                titulo = info.get("titulo") or ""
                if titulo:
                    avisos.progreso(it.progreso, "", "", titulo)
                if ev.is_set():
                    # Cancelada durante el análisis: no lanzar yt-dlp para nada.
                    avisos.estado("cancelado", _("Descarga cancelada"))
                    return
                if info.get("en_directo"):
                    avisos.estado("error", _("Un directo en curso no se puede descargar."))
                    return
                logger.info("descarga %s: inicio", item_id)
                opciones_descarga = dict(opciones)
                opciones_descarga["es_lista"] = (it.tipo == "playlist")
                descargar(url, opciones_descarga, avisos.progreso, avisos.estado,
                          ev, avisos.detalle)
            finally:
                if tomado:
                    with self._lock:
                        self._corriendo -= 1
        except Exception as exc:
            logger.warning("hilo descarga: %s", exc)
            avisos.estado("error", str(exc) or exc.__class__.__name__)

    def encolar(self, url: str, progreso_cb: Callable, estado_cb: Callable,
                creado_cb: Optional[Callable] = None) -> str:
        """Crea un ItemDescarga, lo deja en 'en_cola' y lanza su hilo.

        Como mucho las simultáneas elegidas corren a la vez; las demás esperan
        en 'en_cola', en el orden en que se encolaron, y se pueden cancelar
        mientras esperan.

        `progreso_cb(item_id, pct, velocidad, eta, nombre)` y
        `estado_cb(item_id, estado, mensaje)` reciben el id del ítem.
        """
        item_id = uuid.uuid4().hex[:12]
        with self._lock:
            opciones = dict(self._opciones)
        it = ItemDescarga(id=item_id, url=url, tipo="video", nombre=url,
                          carpeta=str(opciones.get("carpeta") or ""))
        ev = threading.Event()
        with self._lock:
            self._items[item_id] = it
            self._eventos[item_id] = ev
            self._orden.append(item_id)
        logger.info("descarga encolada: %s, vídeo %s", item_id,
                    recortar_url_registro(url))
        if creado_cb is not None:
            creado_cb(item_id)

        avisos = AvisosItem(it, item_id, self, progreso_cb, estado_cb)
        hilo = diagnostico.crear_hilo(
            self._correr, f"Descarga-{item_id}",
            args=(item_id, it, ev, url, opciones, avisos))
        hilo.start()
        return item_id

    def cancelar(self, item_id: str) -> None:
        """Marca el evento de cancelación para que termine el proceso."""
        ev = self._eventos.get(item_id)
        if ev is not None:
            ev.set()

    def olvidar(self, item_id: str) -> None:
        """Saca un ítem terminado de la cola. Si sigue activo no hace nada."""
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.estado not in ("completado", "parcial",
                                                   "cancelado", "error"):
                return
            self._items.pop(item_id, None)
            if item_id in self._orden:
                self._orden.remove(item_id)
            self._eventos.pop(item_id, None)
            self._empezados.discard(item_id)

    def obtener(self, item_id: str) -> Optional[ItemDescarga]:
        with self._lock:
            return self._items.get(item_id)

    def lista(self) -> list[ItemDescarga]:
        with self._lock:
            return [self._items[i] for i in self._orden if i in self._items]


_gestor_unico: Optional[GestorDescargas] = None
_lock_gestor_unico = threading.Lock()


def gestor() -> GestorDescargas:
    """Devuelve el gestor de descargas compartido por la aplicación."""
    global _gestor_unico
    with _lock_gestor_unico:
        if _gestor_unico is None:
            _gestor_unico = GestorDescargas()
        return _gestor_unico


def reiniciar_gestor() -> None:
    """Descarta el gestor compartido. Solo se usa en las pruebas."""
    global _gestor_unico
    with _lock_gestor_unico:
        _gestor_unico = None
