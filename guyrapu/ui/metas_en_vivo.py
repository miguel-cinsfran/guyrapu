# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Atiende las metas del directo y pone su tarjeta en el vídeo.

Une la decisión pura de `metas` con la app: carga las metas guardadas, arma
el evento desde el mensaje y, con el chat conectado, suma el avance y pone
la tarjeta de la meta cumplida.

La atiende `chat_vivo.encolar`, que registra cualquier error sin cortar la
lectura del chat.
"""

from __future__ import annotations

from guyrapu.core import diagnostico, paths
from guyrapu.core.idioma import _
from guyrapu.interaction import medios_guardados, metas, metas_guardadas
from guyrapu.interaction.cola_pantalla import Pieza
from guyrapu.interaction.evento import desde_entrante
from guyrapu.ui import gui_envio_chat
from guyrapu.ui.accesibilidad import anunciar_con_sonido

logger = diagnostico.obtener_logger(__name__)

# Los mismos diez segundos de fábrica de una tarjeta en el vídeo.
SEGUNDOS = 10


def _en_vivo(frame):
    en_vivo = getattr(frame, "_metas_en_vivo", None)
    if en_vivo is None:
        en_vivo = MetasEnVivo(frame)
        frame._metas_en_vivo = en_vivo
    return en_vivo


def atender(frame, registro) -> None:
    """Atiende el mensaje con la instancia de metas de esa ventana."""
    _en_vivo(frame).atender(registro)


def reiniciar(frame) -> None:
    """Vuelve a cero el avance de las metas de esa ventana."""
    en_vivo = getattr(frame, "_metas_en_vivo", None)
    if en_vivo is not None:
        en_vivo.reiniciar()


def _evento(registro):
    return desde_entrante(
        registro.autor, registro.texto, registro.tipo, registro.monto,
        registro.identificador, registro.rol, registro.plataforma)


class MetasEnVivo:
    """El avance de las metas de una sesión y su tarjeta en el vídeo."""

    def __init__(self, frame):
        self._frame = frame
        self._progresos = {}
        self._cargado = False
        self._mtime = None

    def atender(self, registro) -> None:
        if not self._frame._conectado:
            return
        self._recargar()
        evento = _evento(registro)
        for progreso in self._progresos.values():
            if not progreso.meta.activa or not progreso.sumar(evento):
                continue
            if progreso.recien_cumplida():
                self._cumplida(progreso)

    def reiniciar(self) -> None:
        """Olvida el avance, para una conexión nueva del directo."""
        self._progresos = {}
        self._cargado = False

    def _cumplida(self, progreso) -> None:
        anunciar_con_sonido(
            _("Meta cumplida: {nombre}.").format(nombre=progreso.meta.nombre),
            "meta_cumplida")
        self._poner(progreso)

    def _poner(self, progreso) -> None:
        meta = progreso.meta
        medio = self._medio(meta.festejo)
        segundos = SEGUNDOS
        datos = {"estilo": meta.estilo, "nombre": meta.nombre}
        if medio is not None:
            datos["medio"] = medio
            if medio["tipo"] in ("sonido", "video") and medio["duracion"]:
                segundos = max(1, medio["duracion"])
        pieza = Pieza(tipo="meta", texto=metas.texto(meta, progreso.valor),
                      segundos=segundos, datos=datos)
        gui_envio_chat.capa_de_video(self._frame).agregar_pieza(pieza)

    def _medio(self, nombre):
        """El medio de la biblioteca con ese nombre, o None si ya no está."""
        return medios_guardados.medio_para_video(
            medios_guardados.cargar(paths.medios()),
            paths.carpeta_medios(), nombre)

    def _recargar(self) -> None:
        """Vuelve a leer las metas si el archivo cambió, sin perder el avance."""
        ruta = paths.metas()
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if self._cargado and mtime == self._mtime:
            return
        self._cargado = True
        self._mtime = mtime
        anteriores = self._progresos
        self._progresos = {}
        for datos in metas_guardadas.cargar(ruta):
            meta = metas_guardadas.a_meta(datos)
            progreso = anteriores.get(meta.nombre)
            if progreso is None:
                progreso = metas.Progreso(meta)
            else:
                progreso.meta = meta
            self._progresos[meta.nombre] = progreso
