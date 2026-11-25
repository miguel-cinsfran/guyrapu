# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Atiende los comandos del chat y manda sus respuestas.

Une la decisión pura de `atencion` con la app: carga los comandos del
archivo, arma el evento desde el mensaje, agrega la tarjeta al vídeo, manda
la respuesta al chat de YouTube y avisa una sola vez si la cuota la corta.

La atiende `chat_vivo.encolar`, que registra cualquier error sin cortar la
lectura del chat.
"""

from __future__ import annotations

import time
from dataclasses import replace

import wx

from guyrapu.capture.estado_espectadores import _fmt_num
from guyrapu.core import diagnostico, paths, plataformas
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.core.config_musica import DONDE_AHORA, DONDE_CONTINUACION
from guyrapu.core.idioma import N_, _
from guyrapu.core.sonidos_eventos import ROL_PROPIETARIO
from guyrapu.downloads import busqueda_youtube
from guyrapu.interaction import (
    atencion, comandos, comandos_guardados, conversion_disparadores, ensayo,
    filtro_publico, informe_ensayo, medio_en_video, pedido_musica,
    rastro_en_vivo)
from guyrapu.music.modelo import Tema
from guyrapu.interaction.evento import desde_entrante, persona as persona_de_evento
from guyrapu.ui import encuesta_en_vivo, gui_envio_chat, preguntas_en_vivo
from guyrapu.ui.accesibilidad import anunciar_con_sonido
from guyrapu.youtube import cuota

# Con más de 8000 unidades usadas quedan menos de 2000 de las 10 000.
CUOTA_BAJA = 8000

# Traductores: respuesta al chat y aviso al streamer cuando un pedido de música
# no se agrega. {usuario} es quien lo pidió y {motivo} por qué no se sumó.
TEXTO_RECHAZO = N_("Pedido de música de {usuario} no agregado: {motivo}")

logger = diagnostico.obtener_logger(__name__)


def _en_vivo(frame):
    en_vivo = getattr(frame, "_comandos_en_vivo", None)
    if en_vivo is None:
        en_vivo = ComandosEnVivo(frame)
        frame._comandos_en_vivo = en_vivo
    return en_vivo


def _cuota_baja() -> bool:
    return cuota.usadas_hoy() > CUOTA_BAJA


def atender(frame, registro, ahora) -> None:
    """Atiende el mensaje con la instancia de comandos de esa ventana."""
    _en_vivo(frame).atender(registro, ahora)


def enviar_respuesta(frame, texto) -> bool:
    """Manda un texto al chat como las respuestas de los comandos."""
    return _en_vivo(frame).enviar_respuesta(texto)


def disparar(frame, numero, ahora=None) -> None:
    """Usa el comando de ese número con la instancia de la ventana."""
    _en_vivo(frame).disparar(numero, ahora)


def _evento(registro):
    return desde_entrante(
        registro.autor, registro.texto, registro.tipo, registro.monto,
        registro.identificador, registro.rol, registro.plataforma)


def _evento_del_dueno():
    return desde_entrante(
        "", "", TIPO_TEXTO, "", "", ROL_PROPIETARIO, plataformas.YOUTUBE)


class ComandosEnVivo:
    """Los comandos de una sesión, con sus respuestas y su freno de cuota."""

    def __init__(self, frame):
        conversion_disparadores.convertir_en_disco()
        self._frame = frame
        self._atencion = atencion.Atencion()
        self._cargado = False
        self._mtime = None
        self._cargado_palabras = False
        self._mtime_palabras = None
        self._avisado_cuota = False
        self._respondidos = 0
        self._ultimo = ("", "")
        self._pausados = False
        self._pendientes_musica = []
        self._en_curso = []

    def alternar_pausa(self) -> bool:
        """Invierte el freno de todos los comandos y devuelve el estado nuevo."""
        self._pausados = not self._pausados
        return self._pausados

    def atender(self, registro, ahora) -> None:
        if registro.tipo != TIPO_TEXTO:
            return
        evento = _evento(registro)
        if encuesta_en_vivo.votar(self._frame, evento, ahora):
            return
        informe = ensayo.informe(self._frame)
        self._recargar()
        if self._pausados:
            motivo = _(informe_ensayo.MOTIVO_PAUSA_GENERAL)
            nombre = self._atencion.nombre_del_comando(evento)
            if nombre:
                rastro_en_vivo.escribir(rastro_en_vivo.comando(
                    nombre, motivo))
            if informe is not None:
                informe.motivo(motivo)
            return
        if preguntas_en_vivo.recibir(self._frame, evento, ahora):
            return
        respuesta = self._atencion.atender(
            evento, ahora,
            chat_disponible=self._chat_disponible(),
            cuota_baja=_cuota_baja())
        if respuesta is not None:
            rastro_en_vivo.escribir(rastro_en_vivo.comando(
                respuesta.nombre, al_video=respuesta.al_video,
                al_chat=respuesta.al_chat))
            if informe is not None:
                informe.comando(respuesta.nombre)
            if respuesta.especial == comandos.ESPECIAL_MUSICA:
                self._pedir_musica(respuesta, evento, registro.texto)
            else:
                self._mandar(respuesta, registro.autor)
        else:
            motivo = self._atencion.motivo(evento, ahora)
            if motivo:
                nombre = self._atencion.nombre_del_comando(evento)
                rastro_en_vivo.escribir(rastro_en_vivo.comando(nombre, motivo))
            if informe is not None:
                informe.motivo(motivo)

    def disparar(self, numero, ahora=None) -> None:
        """Usa el comando de ese número como si lo pidiera el dueño."""
        if not ensayo.en_vivo_o_ensayo(self._frame):
            anunciar_con_sonido(
                _("Conecta un directo para usar los atajos de los comandos"),
                "error")
            return
        self._recargar()
        if ahora is None:
            ahora = time.monotonic()
        respuesta = self._atencion.atender(
            _evento_del_dueno(), ahora, atajo=numero,
            chat_disponible=self._chat_disponible(),
            cuota_baja=_cuota_baja())
        if respuesta is None:
            anunciar_con_sonido(
                _("Ningún comando usa Ctrl+Alt+Mayús+{numero}").format(
                    numero=numero), "error")
            return
        self._mandar(respuesta, "")

    def _pedir_musica(self, respuesta, evento, texto) -> None:
        """Anota el pedido en curso y lo resuelve en otro hilo."""
        invocacion = comandos.leer(texto)
        pedido = invocacion.argumentos if invocacion else ""
        ajustes = pedido_musica.ajustes_de(
            getattr(self._frame, "_config", None))
        self._podar_pendientes()
        en_curso = pedido_musica.Pendiente(persona_de_evento(evento), "")
        self._en_curso.append(en_curso)
        # El pedido propio no se cuenta a sí mismo: con tope 1 debe poder entrar.
        pendientes = tuple(self._pendientes_musica) + tuple(
            actual for actual in self._en_curso if actual is not en_curso)
        diagnostico.crear_hilo(
            self._resolver_musica, "PedidoMusica",
            args=(respuesta, evento, pedido, ajustes, pendientes,
                  en_curso)).start()

    def _resolver_musica(self, respuesta, evento, texto, ajustes,
                         pendientes, en_curso) -> None:
        pedido = pedido_musica.resolver(
            texto, busqueda_youtube.buscar, ajustes=ajustes,
            pendientes=pendientes, persona=persona_de_evento(evento),
            palabras=filtro_publico.cargar(paths.palabras_bloqueadas()))
        wx.CallAfter(self._terminar_musica, respuesta, evento, pedido, ajustes,
                     en_curso)

    def _podar_pendientes(self) -> None:
        """Sacar los pedidos que ya suenan o que salieron de la cola."""
        if not self._pendientes_musica:
            return
        musica = getattr(self._frame, "_musica", None)
        estado = musica.estado() if musica is not None else None
        cola = getattr(estado, "cola", ())
        if not isinstance(cola, (tuple, list)):
            return
        vigentes = {pedido_musica.clave_de(tema.origen) for tema in cola}
        actual = estado.actual
        if actual is not None:
            vigentes.discard(pedido_musica.clave_de(actual.origen))
        self._pendientes_musica = [
            pendiente for pendiente in self._pendientes_musica
            if pedido_musica.clave_de(pendiente.url) in vigentes]

    def _terminar_musica(self, respuesta, evento, pedido, ajustes,
                         en_curso) -> None:
        self._en_curso = [actual for actual in self._en_curso
                          if actual is not en_curso]
        if pedido.motivo:
            rastro_en_vivo.escribir(rastro_en_vivo.pedido_musica(
                False, motivo=pedido.motivo))
            self._rechazar(evento, pedido, ajustes)
            return
        tema = Tema(origen=pedido.tema.url, titulo=pedido.tema.titulo,
                    duracion_ms=pedido.tema.duracion * 1000)
        self._poner_tema(tema, ajustes.donde)
        rastro_en_vivo.escribir(rastro_en_vivo.pedido_musica(
            True, destino=ajustes.donde))
        self._pendientes_musica.append(
            pedido_musica.Pendiente(persona_de_evento(evento), pedido.tema.url))
        titulo = self._atencion.tapar(pedido.tema.titulo)
        respuesta = replace(
            respuesta, texto=respuesta.texto.replace("{titulo}", titulo))
        self._mandar(respuesta, evento.autor)

    def _poner_tema(self, tema, donde) -> None:
        musica = self._frame._musica
        if donde == DONDE_AHORA:
            musica.reproducir_ahora([tema])
        elif donde == DONDE_CONTINUACION:
            musica.poner_a_continuacion([tema])
        else:
            musica.agregar_temas([tema])

    def _rechazar(self, evento, pedido, ajustes) -> None:
        texto = _(TEXTO_RECHAZO).format(
            usuario=evento.autor or _("el público"), motivo=pedido.motivo)
        anunciar_con_sonido(texto, "pedido_musica_rechazado")
        if ajustes.responder and evento.plataforma == plataformas.YOUTUBE:
            self.enviar_respuesta(texto)

    def _mandar(self, respuesta, autor) -> None:
        self._respondidos += 1
        palabra = respuesta.nombre
        if not palabra.startswith("!"):
            palabra = "!" + palabra
        self._ultimo = (palabra, autor)
        self._poner_en_video(respuesta)
        if respuesta.al_chat and respuesta.texto.strip():
            gui_envio_chat.enviar_respuesta_chat(self._frame, respuesta.texto)
        if respuesta.freno_cuota:
            self._avisar_cuota()

    def _poner_en_video(self, respuesta) -> None:
        if not ensayo.en_vivo_o_ensayo(self._frame):
            return
        medio = medio_en_video.resolver(respuesta.medio)
        texto = respuesta.texto if respuesta.al_video else ""
        if not texto and medio is None:
            return
        gui_envio_chat.capa_de_video(self._frame).agregar_comando(
            respuesta, medio)

    def enviar_respuesta(self, texto) -> bool:
        """Manda un texto al chat con el mismo freno de cuota de los comandos."""
        if not self._chat_disponible():
            return False
        if _cuota_baja():
            self._avisar_cuota()
            return False
        gui_envio_chat.enviar_respuesta_chat(self._frame, texto)
        return True

    def frase_estado(self) -> str:
        """La frase para F2, o "" si no hay pausa ni comandos respondidos."""
        resumen = ""
        if self._respondidos:
            palabra, autor = self._ultimo
            # Traductores: parte del estado F2 (comandos). {n} es el nº de comandos
            # respondidos, {palabra} el último comando y {autor} quien lo pidió.
            resumen = _(
                "Comandos respondidos: {n}, el último {palabra} de {autor}").format(
                    n=_fmt_num(self._respondidos), palabra=palabra, autor=autor)
        if not self._pausados:
            return resumen
        return _("Comandos en pausa") + (". " + resumen if resumen else "")

    def _recargar(self) -> None:
        """Vuelve a leer los comandos y las palabras si cambiaron."""
        self._recargar_comandos()
        self._recargar_palabras()

    def _recargar_comandos(self) -> None:
        ruta = paths.comandos()
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if self._cargado and mtime == self._mtime:
            return
        self._cargado = True
        self._mtime = mtime
        self._atencion.fijar_comandos([
            comandos_guardados.a_comando(datos)
            for datos in comandos_guardados.cargar(ruta)])

    def _recargar_palabras(self) -> None:
        ruta = paths.palabras_bloqueadas()
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if self._cargado_palabras and mtime == self._mtime_palabras:
            return
        self._cargado_palabras = True
        self._mtime_palabras = mtime
        self._atencion.fijar_palabras_bloqueadas(
            filtro_publico.cargar(ruta))

    def _chat_disponible(self) -> bool:
        return "chat" in gui_envio_chat.destinos_disponibles(self._frame)

    def _avisar_cuota(self) -> None:
        if self._avisado_cuota:
            return
        self._avisado_cuota = True
        from guyrapu.ui import gui as _gui
        # Traductores: aviso único de la sesión cuando la poca cuota de YouTube corta las respuestas al chat.
        _gui.anunciar_con_sonido(
            _("Queda poca cuota de YouTube: las respuestas de los comandos "
              "ya no se muestran en el chat, solo en el vídeo."),
            "aviso")
