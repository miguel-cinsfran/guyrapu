# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cola y volcado agrupado del chat en vivo.

El ControladorChat guarda los mensajes que llegan, los vuelca a la lista en
lotes con un temporizador y reconstruye la vista al cambiar el filtro.
"""

from __future__ import annotations

import time

import wx

from guyrapu.capture import traduccion_chat
from guyrapu.capture.tiktok_filtros import debe_pasar_me_gusta
from guyrapu.core import comando_clip
from guyrapu.core import diagnostico
from guyrapu.core import plataformas
from guyrapu.core import sonidos_eventos
from guyrapu.core.idioma import N_, _
from guyrapu.core.avisos_tiktok import (
    con_sonido, evento_de_mensaje, modo_evento, pasa_filtro,
)
from guyrapu.interaction import ensayo, informe_ensayo
from guyrapu.core.config import (
    TIPO_ME_GUSTA, TIPO_MIEMBRO, TIPO_STICKER, TIPO_SUPERCHAT, TIPO_TEXTO,
)
from guyrapu.translation import idiomas
from guyrapu.ui import (
    comandos_clips, comandos_en_vivo, disparadores_en_vivo, metas_en_vivo,
)
from guyrapu.ui.accesibilidad import anunciar_con_sonido
from guyrapu.ui.lista_chat import ListaChat, MensajeChat
from guyrapu.ui.participacion_chat import Participacion
from guyrapu.voice import sound_player as _snd


# Ráfagas de mensajes del chat: en vez de un Append/Delete por mensaje (mucho
# repintado en el hilo de GUI mientras NVDA navega la lista), se agrupan y se
# vuelcan juntos cada tanto. Ver ControladorChat.encolar / volcar.
MS_VOLCADO_CHAT = 120

# Traductores: única fila del chat sin mensajes; dice qué aparece y cómo se llena.
VACIO_CHAT = N_(
    "No hay mensajes en el chat. Aquí aparecen los mensajes y avisos del directo "
    "a medida que llegan. Conecta un directo para verlos.")


logger = diagnostico.obtener_logger(__name__)


def es_linea_vacia(texto) -> bool:
    """Reconoce la fila de vacío para no contarla ni leerla como mensaje."""
    return texto == _(VACIO_CHAT)


def filas_de_chat(lista) -> list[str]:
    """Solo las filas de la lista que son mensajes, sin la línea de vacío."""
    return [texto for texto in (lista.GetString(i)
                                for i in range(lista.GetCount()))
            if not es_linea_vacia(texto)]


def poner_linea_vacia(lista) -> None:
    """Deja la línea de vacío elegida cuando el chat no tiene mensajes."""
    if lista.GetCount() == 0:
        lista.Append(_(VACIO_CHAT))
        lista.SetSelection(0)


def sacar_linea_vacia(lista) -> None:
    """Quita la línea de vacío antes de que entre el primer mensaje."""
    if lista.GetCount() == 1 and es_linea_vacia(lista.GetString(0)):
        lista.Delete(0)


class ControladorChat:
    """Estado y volcado del chat en vivo, separado de la ventana principal."""

    def __init__(self, lista, maximo, *, activo, autor_oculto,
                 formatear, al_superchat, config=None, varios_chats=None,
                 ajustes_clip=None, guardar_clip=None, reloj=time.monotonic):
        self.lista = lista
        self._config = config
        self._varios_chats = varios_chats or (lambda: False)
        self.modelo = ListaChat(maximo)
        self.participacion = Participacion()
        self.filtro = None
        self._pendientes: list[MensajeChat] = []
        self._timer = None
        self._activo = activo
        self._autor_oculto = autor_oculto
        self._formatear = formatear
        self._al_superchat = al_superchat
        self._ultimo_me_gusta = None
        self._ajustes_clip = ajustes_clip or comandos_clips.leer_ajustes_clips_chat
        self._guardar_clip = guardar_clip or comandos_clips.guardar_clip_del_chat
        self._reloj = reloj
        self._ultimo_clip_chat = None
        self._clip_en_curso = False
        self._traducciones = {}
        self.recibidos = 0

    def encolar(self, registro: MensajeChat) -> None:
        frame = self.lista.GetTopLevelParent()
        informe = ensayo.empezar_informe(frame)
        self._quizas_clip(registro)
        self._quizas_comando(registro)
        self._quizas_disparador(registro)
        self._quizas_meta(registro)
        if informe is not None:
            self._terminar_informe(frame, registro, informe)
        self.recibidos += 1 if registro.tipo == TIPO_TEXTO else 0
        if self._modo(registro) == "ocultar":
            return
        self._pendientes.append(registro)
        self._pedir_traduccion(registro)
        # Si el temporizador ya corre, NO reiniciarlo: con un chat activo
        # (mensajes cada menos de MS_VOLCADO_CHAT) reiniciar pospondría el
        # volcado indefinidamente y no aparecería nada hasta una pausa.
        if self._timer is None:
            self._timer = wx.CallLater(MS_VOLCADO_CHAT, self.volcar)

    def _terminar_informe(self, frame, registro, informe) -> None:
        general = (informe_ensayo.MOTIVO_EVENTO if registro.tipo != TIPO_TEXTO
                   else informe_ensayo.MOTIVO_MENSAJE)
        texto = informe.texto(_(general))
        anunciar_con_sonido(
            texto, "listo" if informe.respondio else "aviso")
        ventana = getattr(frame, "_ventana_ensayo", None)
        if ventana is not None and not ventana.cerrado:
            ventana.agregar_resultado(registro, texto)

    def _quizas_clip(self, registro: MensajeChat) -> None:
        """Atiende el comando !clip que llega en el hilo de la interfaz."""
        try:
            if not comando_clip.es_pedido(registro.texto):
                return
            ajustes = self._ajustes_clip()
            if not ajustes.activo:
                return
            ahora = self._reloj()
            if not comando_clip.decidir(
                    registro.texto, ahora, self._ultimo_clip_chat,
                    ajustes.minutos):
                return
            if self._clip_en_curso:
                return
            self._clip_en_curso = True
            self._guardar_clip(registro.autor, self._clip_terminado)
        except Exception as error:
            self._clip_en_curso = False
            logger.debug("no se pudo atender el comando !clip: %s", error)

    def _quizas_comando(self, registro: MensajeChat) -> None:
        """Atiende el comando que llega en el hilo de la interfaz.

        Un error se registra y nunca corta la lectura del chat.
        """
        try:
            comandos_en_vivo.atender(
                self.lista.GetTopLevelParent(), registro, self._reloj())
        except Exception as error:
            logger.debug("no se pudo atender el comando del chat: %s", error)

    def _quizas_disparador(self, registro: MensajeChat) -> None:
        """Atiende el disparador que llega en el hilo de la interfaz.

        Un error se registra y nunca corta la lectura del chat.
        """
        try:
            disparadores_en_vivo.atender(
                self.lista.GetTopLevelParent(), registro, self._reloj())
        except Exception as error:
            logger.debug("no se pudo atender el disparador del chat: %s",
                         error)

    def _quizas_meta(self, registro: MensajeChat) -> None:
        """Atiende la meta que llega en el hilo de la interfaz.

        Un error se registra y nunca corta la lectura del chat.
        """
        try:
            metas_en_vivo.atender(
                self.lista.GetTopLevelParent(), registro)
        except Exception as error:
            logger.debug("no se pudo atender la meta del chat: %s", error)

    def _clip_terminado(self, guardado: bool) -> None:
        self._clip_en_curso = False
        if guardado:
            self._ultimo_clip_chat = self._reloj()

    def _pedir_traduccion(self, registro: MensajeChat) -> None:
        """Pide la traducción de la fila, si la lista se traduce."""
        if registro.tipo != TIPO_TEXTO or not traduccion_chat.traduce_lista():
            return
        pedido = traduccion_chat.pedir(registro.texto)
        if pedido is None:
            return
        pedido.al_terminar(lambda: self._traduccion_lista(registro, pedido))

    def _traduccion_lista(self, registro, pedido) -> None:
        resultado = pedido.resultado
        if resultado is None or not resultado.origen:
            return
        if idiomas.sigla(resultado.origen) == idiomas.sigla(pedido.destino):
            return
        wx.CallAfter(self._actualizar_fila, registro, resultado)

    def _actualizar_fila(self, registro: MensajeChat, traduccion) -> None:
        """Guarda la traducción y cambia la fila sin mover foco ni selección."""
        self._traducciones[registro] = traduccion
        self._podar_traducciones()
        try:
            indice = next(indice for indice, actual
                          in enumerate(self.modelo.todos) if actual is registro)
        except StopIteration:
            return
        if indice not in self.modelo.visibles:
            return
        fila = self.modelo.visibles.index(indice)
        if fila < self.lista.GetCount():
            self.lista.SetString(fila, self._texto_fila(registro))

    def traduccion(self, registro: MensajeChat):
        """La traducción guardada de ese registro, o None."""
        return self._traducciones.get(registro)

    def _modo(self, registro: MensajeChat) -> str | None:
        """Modo del evento del mensaje, o None para un texto común."""
        if self._config is None:
            return None
        return modo_evento(
            self._config, evento_de_mensaje(registro.tipo, registro.texto))

    def _procesar(self, registro: MensajeChat) -> bool:
        """Aplica UN mensaje ya desencolado al modelo y a la lista. Devuelve si
        quedó visible (se le hizo Append). Solo lo llama volcar."""
        if self._autor_oculto(registro.autor):
            return False
        self.participacion.sumar(registro)
        # El modelo (lista_chat) recorta el historial y dice cuántas filas viejas
        # borrar al principio, para que fila y mensaje sigan alineados: si no,
        # pasados 500 mensajes, copiar o banear caerían sobre el mensaje
        # equivocado.
        visible = pasa_filtro(self.filtro, registro.tipo)
        borrar = self.modelo.agregar(registro, visible)
        for _sin_uso in range(borrar):
            self.lista.Delete(0)

        modo = self._modo(registro)
        sonar = con_sonido(modo)
        if registro.tipo in (TIPO_SUPERCHAT, TIPO_STICKER):
            self._al_superchat(registro.monto)
        if sonar:
            self._reproducir(registro)

        if visible:
            sacar_linea_vacia(self.lista)
            self.lista.Append(self._texto_fila(registro))
        return visible

    def _podar_traducciones(self) -> None:
        """Olvida las traducciones de los mensajes que ya salieron del historial."""
        vivos = set(self.modelo.todos)
        vivos.update(self._pendientes)
        self._traducciones = {registro: traduccion
                              for registro, traduccion
                              in self._traducciones.items()
                              if registro in vivos}

    def _texto_fila(self, registro: MensajeChat) -> str:
        texto = self._formatear(
            registro.autor, self._texto_mensaje(registro), registro.hora,
            registro.tipo, registro.monto)
        if self._varios_chats():
            texto += plataformas.sufijo(registro.plataforma)
        return texto

    def _texto_mensaje(self, registro: MensajeChat) -> str:
        """El mensaje que se ve: la traducción con su idioma, o el original."""
        traduccion = self._traducciones.get(registro)
        if (traduccion is None or self._config is None
                or not self._config.get("traducir_chat", False)
                or self._config.get("traducir_que", "voz_lista") != "voz_lista"):
            return registro.texto
        forma = self._config.get("traducir_idioma_original", "completo")
        return traduccion.texto + idiomas.mencion(traduccion.origen, forma)

    def _reproducir(self, registro: MensajeChat) -> None:
        """Suena el registro según su tipo, con el mismo aviso de siempre."""
        if registro.tipo in (TIPO_SUPERCHAT, TIPO_STICKER):
            _snd.reproducir(sonidos_eventos.sonido_de_mensaje(
                registro.tipo, registro.rol, registro.monto,
                registro.plataforma, nivel=registro.nivel))
        elif registro.tipo == TIPO_MIEMBRO:
            _snd.reproducir("nuevo_miembro")
        elif registro.tipo == TIPO_ME_GUSTA:
            # Suena como mucho uno cada 3 s; a la lista entra como aviso.
            ahora = time.monotonic()
            if debe_pasar_me_gusta(self._ultimo_me_gusta, ahora):
                self._ultimo_me_gusta = ahora
                _snd.reproducir(sonidos_eventos.sonido_de_mensaje(
                    registro.tipo, registro.rol, registro.monto,
                    registro.plataforma))
        else:
            _snd.reproducir(sonidos_eventos.sonido_de_mensaje(
                registro.tipo, registro.rol, plataforma=registro.plataforma,
                propio=self._propio_plataforma()))

    def _propio_plataforma(self) -> bool:
        """Si este mensaje común suena con el sonido propio de su plataforma."""
        return bool(self._config) and sonidos_eventos.usar_sonido_plataforma(
            self._config, self._varios_chats())

    def volcar(self) -> None:
        """Procesa TODOS los mensajes en espera de una vez: modelo y vista se
        mutan juntos aquí (nunca al encolar), así que fila↔mensaje se mantienen
        alineados igual que antes. Con más de un pendiente, Freeze/Thaw evita
        repintar fila a fila."""
        self._timer = None
        pendientes, self._pendientes = self._pendientes, []
        # El ensayo no conecta el chat, pero sus mensajes también se vuelcan:
        # `activo` mira la conexión real y no debe descartarlos.
        if not pendientes or not (
                self._activo() or ensayo.en_ensayo(self.lista.GetTopLevelParent())):
            return
        freeze = len(pendientes) > 1
        if freeze:
            self.lista.Freeze()
        hubo_visible = False
        try:
            for registro in pendientes:
                if self._procesar(registro):
                    hubo_visible = True
        finally:
            if freeze:
                self.lista.Thaw()
        # Un solo SetFirstItem al final (no uno por mensaje), y solo si el foco
        # no está en la lista (si el usuario está navegando, no le movemos la
        # vista) y algo se añadió de verdad.
        if hubo_visible and wx.Window.FindFocus() is not self.lista:
            self.lista.SetFirstItem(self.lista.GetCount() - 1)
        poner_linea_vacia(self.lista)

    def volcar_ya(self) -> None:
        """Vuelca ya lo encolado, sin esperar el temporizador. Se usa antes de
        leer/reconstruir la lista desde el modelo (cambio de filtro) para que
        no falte lo más reciente todavía sin procesar."""
        if self._timer is not None:
            try:
                self._timer.Stop()
            except Exception as exc:
                logger.debug("No se pudo parar el temporizador del chat: %s", exc)
            self._timer = None
        self.volcar()

    def descartar(self) -> None:
        """Tira lo encolado sin procesarlo. Se usa donde hoy se limpia la lista
        entera (desconectar, cambiar de vídeo): esos mensajes pertenecen a la
        sesión que se está borrando."""
        if self._timer is not None:
            try:
                self._timer.Stop()
            except Exception as exc:
                logger.debug("No se pudo parar el temporizador del chat: %s", exc)
            self._timer = None
        self._pendientes.clear()

    def vaciar(self) -> None:
        """Deja el chat en limpio, con la línea de vacío como única fila."""
        self.descartar()
        self.modelo.limpiar()
        self.participacion.limpiar()
        self._traducciones.clear()
        self.lista.Clear()
        poner_linea_vacia(self.lista)

    def reconstruir(self) -> None:
        # Que lo que acaba de llegar (aún en cola, sin pasar por el modelo) no
        # se pierda del recuento/reconstrucción: se procesa YA con el estado
        # vigente antes de leer el modelo.
        self.volcar_ya()
        self.lista.Clear()
        visibles = self.modelo.reconstruir(
            lambda it: not self._autor_oculto(it.autor)
            and pasa_filtro(self.filtro, it.tipo))
        if visibles:
            sacar_linea_vacia(self.lista)
        for registro in visibles:
            self.lista.Append(self._texto_fila(registro))
        poner_linea_vacia(self.lista)
