# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Chat adicional de TikTok mientras el principal es de YouTube.

Lleva la vida del chat adicional (abrirlo, pararlo y decir si está activo) y
la vista que deja pasar sus mensajes, eventos y estados sin tocar nada del
directo principal.
"""

from __future__ import annotations

import re

from guyrapu.capture import tiktok_captura
from guyrapu.capture.conexion import Conexiones, _VistaNula
from guyrapu.core.idioma import _
from guyrapu.ui.vista_captura import VistaGui
from guyrapu.voice import sound_player as _snd

_USUARIO_RE = re.compile(r"^@?([\w.]+)$")


class VistaAdicional(_VistaNula):
    """Mensajes, eventos y estados del adicional; nada del directo."""

    def __init__(self, vista=None, conexion_propia=False, al_parar=None):
        self._vista = vista if vista is not None else VistaGui()
        self.conexion_propia = conexion_propia
        self._al_parar = al_parar
        self._conectado = False
        self._espectadores = None

    @property
    def activa(self):
        return self._vista.activa

    def set_espectadores(self, n, total=None):
        self._espectadores = (n, total)
        return True

    def espectadores(self):
        return self._espectadores

    def olvidar_espectadores(self):
        self._espectadores = None

    def agregar_mensaje(self, autor, mensaje, hora, tipo="", monto="",
                        canal_id="", plataforma="", rol=""):
        return self._vista.agregar_mensaje(
            autor, mensaje, hora, tipo, monto, canal_id,
            plataforma=plataforma, rol=rol)

    def anunciar(self, texto):
        if not self._vista.activa:
            return False
        self._vista.anunciar(_("TikTok: ") + texto)
        return True

    def set_conectado(self, conectado, sonido=None):
        if not conectado:
            estaba = self._conectado
            self._conectado = False
            self._parar()
            if estaba:
                _snd.reproducir(sonido or "desconectado")
            return True
        self._conectado = True
        self._vista.anunciar(_("TikTok: ") + _("Conectado al directo. Leyendo el chat."))
        return True

    def set_conectado_si_existe(self, conectado, sonido=None):
        if not conectado:
            self._parar()
        return True

    def _parar(self):
        self.olvidar_espectadores()
        if self._al_parar:
            self._al_parar()


class ChatAdicional:
    """Un único chat adicional de TikTok, con su propia sesión de captura."""

    def __init__(self, cola, config, stats, parada, crear_hilo=None,
                 vista_gui=None):
        self._usuario = ""
        self._activo = False
        self._vista = VistaAdicional(vista=vista_gui, al_parar=self._parar)
        self._conexiones = Conexiones(
            cola, config, stats, parada, crear_hilo=crear_hilo,
            vista=self._vista)

    def activo(self) -> bool:
        return self._activo

    def enlace(self) -> str:
        """Enlace del directo de TikTok que se está leyendo, o cadena vacía."""
        if not self._activo or not self._usuario:
            return ""
        return f"https://www.tiktok.com/@{self._usuario}/live"

    def espectadores(self):
        return self._vista.espectadores()

    def conectar(self, url, principal_activo=None) -> bool:
        if principal_activo is not None and not principal_activo():
            self._rechazar(_("Conecta primero un directo de YouTube para leer "
                             "un chat adicional de TikTok."))
            return False
        usuario = _usuario_de_entrada(url)
        if not usuario:
            self._rechazar(_("El enlace no es de un directo de TikTok."))
            return False
        if self._activo and usuario == self._usuario:
            self._rechazar(_("Ya estás leyendo el chat de TikTok de @{usuario}."
                            ).format(usuario=usuario))
            return False
        if self._activo:
            self.detener()
        self._usuario = usuario
        self._activo = True
        self._conexiones.conectar(self.enlace())
        return True

    def detener(self) -> None:
        if not self._activo and not self._usuario:
            return
        self._activo = False
        self._usuario = ""
        self._vista.olvidar_espectadores()
        self._conexiones.desconectar()

    def _parar(self) -> None:
        self._activo = False
        self._usuario = ""

    def _rechazar(self, texto: str) -> None:
        _snd.reproducir("error")
        self._vista.anunciar(texto)


def _usuario_de_entrada(entrada: str) -> str:
    """Usuario de TikTok a partir de una URL o de un @usuario suelto."""
    usuario = tiktok_captura.usuario_de_url(entrada)
    if usuario:
        return usuario
    coincidencia = _USUARIO_RE.match((entrada or "").strip())
    return coincidencia.group(1).lower() if coincidencia else ""


def texto_enlace_directo(enlace_principal: str) -> tuple[str, str]:
    """Texto a copiar y frase a anunciar al copiar el enlace del directo."""
    if not enlace_principal:
        return "", _("No hay ningún directo conectado.")
    adicional = (_INSTANCIA.enlace()
                 if _INSTANCIA is not None and _INSTANCIA.activo() else "")
    if adicional:
        return (f"{enlace_principal}\n{adicional}",
                _("Enlaces de YouTube y TikTok copiados."))
    return enlace_principal, _("Enlace del directo copiado.")


_INSTANCIA: ChatAdicional | None = None


def usar(instancia: ChatAdicional | None) -> None:
    global _INSTANCIA
    _INSTANCIA = instancia


def activo() -> bool:
    return _INSTANCIA is not None and _INSTANCIA.activo()


def espectadores():
    if _INSTANCIA is None or not _INSTANCIA.activo():
        return None
    return _INSTANCIA.espectadores()


def campos_de_estado() -> dict:
    """Los campos de SnapshotSesion con los espectadores del adicional."""
    datos = espectadores()
    if datos is None:
        return {}
    return {"espectadores_adicional": datos[0],
            "espectadores_adicional_total": datos[1]}


def _instancia(cola, config, stats, parada, crear_hilo=None) -> ChatAdicional:
    global _INSTANCIA
    if _INSTANCIA is None:
        _INSTANCIA = ChatAdicional(cola, config, stats, parada,
                                   crear_hilo=crear_hilo)
    return _INSTANCIA


def conectar(url, principal_activo=None, *, cola, config, stats, parada,
             crear_hilo=None) -> bool:
    return _instancia(cola, config, stats, parada, crear_hilo).conectar(
        url, principal_activo)


def conectar_ventana(ventana, url) -> bool:
    return conectar(
        url,
        principal_activo=lambda: (ventana._conectado
                                  and not ventana.sesion.es_tiktok),
        cola=ventana._cola, config=ventana._config, stats=ventana._stats,
        parada=ventana._parada)


def detener() -> None:
    if _INSTANCIA is not None:
        _INSTANCIA.detener()


class MixinChatAdicional:
    """Método de ventana que expone el chat adicional."""

    def conectar_chat_adicional(self, url):
        return conectar_ventana(self, url)
