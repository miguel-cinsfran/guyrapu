# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las preguntas del público en la sesión de la ventana.

Una sola razón para cambiar: qué se hace con las preguntas mientras la
sesión está abierta. Sumar las que llegan por el chat, avisar cuando la
cola se llena, ofrecerlas a la página y mostrarlas en el vídeo. Los sitios
solo llaman a sus funciones.
"""

from __future__ import annotations

from guyrapu.core import paths
from guyrapu.core.idioma import _
from guyrapu.interaction import ensayo, filtro_publico, preguntas
from guyrapu.interaction.cola_pantalla import Pieza

SEGUNDOS_VIDEO = 15


def _capa(frame):
    from guyrapu.ui import gui_envio_chat
    return gui_envio_chat.capa_de_video(frame)


def _avisar(frase, sonido):
    from guyrapu.ui.accesibilidad import anunciar_con_sonido
    anunciar_con_sonido(frase, sonido)


def _sesion(frame):
    sesion = getattr(frame, "_preguntas_en_vivo", None)
    if sesion is None:
        sesion = SesionPreguntas(frame)
        frame._preguntas_en_vivo = sesion
    return sesion


def recibir(frame, evento, ahora) -> bool:
    """Suma la pregunta del mensaje; dice si el mensaje era para preguntas."""
    invocacion = preguntas.leer(evento.texto)
    if invocacion is None:
        return False
    _sesion(frame).recibir(evento, invocacion.argumentos, ahora)
    return True


def pendientes(frame):
    """Las preguntas pendientes, en el orden en que llegaron."""
    return _sesion(frame).cola.pendientes()


def siguiente(frame):
    """La pregunta más vieja pendiente, o None si no hay ninguna."""
    return _sesion(frame).cola.siguiente()


def responder(frame, id) -> bool:
    """Saca de la cola la pregunta respondida."""
    return _sesion(frame).cola.responder(id)


def descartar(frame, id) -> bool:
    """Saca de la cola la pregunta descartada."""
    return _sesion(frame).cola.descartar(id)


def vaciar(frame) -> None:
    """Descarta todas las preguntas pendientes."""
    _sesion(frame).cola.vaciar()


def suscribir(frame, aviso) -> None:
    """Avisa a esa función cada vez que la cola cambia."""
    _sesion(frame).cola.suscribir(aviso)


def desuscribir(frame, aviso) -> None:
    """Deja de avisar a esa función; si no había sesión, no hace nada."""
    sesion = getattr(frame, "_preguntas_en_vivo", None)
    if sesion is not None:
        sesion.cola.desuscribir(aviso)


def mostrar(frame, id) -> bool:
    """Suma al vídeo la pregunta con ese id, sin sacarla de la cola."""
    pregunta = _sesion(frame).buscar(id)
    if pregunta is None:
        return False
    _capa(frame).agregar_pieza(Pieza(
        tipo="pregunta",
        # Traductores: tarjeta del vídeo con una pregunta del público. {autor} es quien la hizo y {texto} su pregunta.
        texto=_("{autor} pregunta: {texto}").format(
            autor=pregunta.autor, texto=pregunta.texto),
        segundos=SEGUNDOS_VIDEO, datos={"estilo": ""}))
    return True


class SesionPreguntas:
    """Las preguntas de una sesión y las palabras bloqueadas al día."""

    def __init__(self, frame):
        self._frame = frame
        self.cola = preguntas.ColaPreguntas()
        self._palabras = []
        self._cargado = False
        self._mtime = None

    def recibir(self, evento, argumentos, ahora) -> None:
        self._recargar()
        resultado = self.cola.agregar(
            evento, argumentos, self._palabras, ahora)
        if resultado == preguntas.SUMADA:
            informe = ensayo.informe(self._frame)
            if informe is not None:
                informe.pregunta()
        if resultado == preguntas.LLENA and self.cola.avisar_llena():
            # Traductores: aviso cuando la cola de preguntas del público ya tiene su máximo.
            _avisar(_("La cola de preguntas está llena."), "preguntas_llena")

    def buscar(self, id):
        """La pregunta pendiente con ese id, o None si ya no está."""
        return next((pregunta for pregunta in self.cola.pendientes()
                     if pregunta.id == id), None)

    def _recargar(self) -> None:
        ruta = paths.palabras_bloqueadas()
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if self._cargado and mtime == self._mtime:
            return
        self._cargado = True
        self._mtime = mtime
        self._palabras = filtro_publico.cargar(ruta)
