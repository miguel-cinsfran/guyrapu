# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Lógica de mensajes programados, sin acceso a la interfaz ni a la red."""

from __future__ import annotations

import json
import math
import re

from guyrapu.core import archivos
from guyrapu.capture import redaccion
from guyrapu.core.idioma import _, ngettext
from guyrapu.interaction import contenido, descripcion_disparador


MINUTOS_MINIMOS = 5  # Piso de prudencia contra el antispam.
SEGUNDOS_ENTRE_ENVIOS = 60  # Si dos vencen a la vez, el segundo espera.
# La usan el cuadro y las pruebas.
MAX_CARACTERES = redaccion.MAXIMO_CHAT

VALORES_POR_DEFECTO = {
    "nombre": "",
    "texto": "",
    "medio": "",
    "minutos_min": 10,
    "minutos_max": 10,
    "activo": False,
    "proximo": 0.0,
    "destino": "chat",
    "estilo": "clasico",
    "segundos_pantalla": 10,
    "mensajes_entre": 0,
}

_URL_RE = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)


def validar_mensaje(texto: str, medio: str, destino: str,
                    minutos_min: int, minutos_max: int) -> tuple[str, str]:
    """Valida un mensaje y devuelve un error y un aviso, en ese orden."""
    # Traductores: validación de mensajes programados (error).
    error = contenido.validar(
        texto, medio, destino, nombre=_("El mensaje automático"),
        # Traductores: validación de mensajes programados (error). {actual} es el largo y {maximo} el tope.
        error_largo=_("El mensaje tiene {actual} caracteres y el máximo es "
                      "{maximo}."))
    if error:
        return error, ""
    if minutos_min < MINUTOS_MINIMOS:
        # Traductores: validación de mensajes programados (error). {minimo} es el mínimo.
        return _("El intervalo mínimo son {minimo} minutos.").format(minimo=MINUTOS_MINIMOS), ""
    if minutos_max < minutos_min:
        # Traductores: validación de mensajes programados (error).
        return _("El intervalo máximo no puede ser menor que el mínimo."), ""
    aviso = ""
    # Se avisan las formas habituales de URL; YouTube puede bloquearlas.
    if _URL_RE.search(texto):
        # Traductores: aviso de la ventana de mensajes programados cuando el texto trae un enlace.
        aviso = _("YouTube suele bloquear los enlaces en el chat del directo. "
                  "Escribe el nombre de usuario en vez del enlace completo.")
    return "", aviso


def calcular_proximo(minutos_min: int, minutos_max: int,
                     ahora: float, aleatorio) -> float:
    """Calcula el instante del próximo envío usando un azar inyectado."""
    if minutos_min == minutos_max:
        return ahora + minutos_min * 60
    return ahora + aleatorio(minutos_min * 60, minutos_max * 60)


def iniciar_reloj(mensajes: list[dict], ahora: float, aleatorio) -> None:
    """Da cuerda al reloj de los mensajes activos de esta sesión."""
    for mensaje in mensajes:
        if mensaje.get("activo", False):
            mensaje["proximo"] = calcular_proximo(
                mensaje.get("minutos_min", 10),
                mensaje.get("minutos_max", mensaje.get("minutos_min", 10)),
                ahora, aleatorio)


def _va_a(mensaje: dict, destinos) -> bool:
    propio = mensaje.get("destino", "chat")
    if propio == "ambos":
        return bool(destinos)
    return propio in destinos


def elegir_envio(mensajes: list[dict], ahora: float,
                 ultimo_envio: float | None,
                 destinos=("chat",)) -> dict | None:
    """Devuelve el mensaje activo vencido más antiguo que va a esos destinos."""
    if ultimo_envio is not None and ahora - ultimo_envio < SEGUNDOS_ENTRE_ENVIOS:
        return None
    vencidos = [
        mensaje for mensaje in mensajes
        if mensaje.get("activo", False) and mensaje.get("proximo", float("inf")) <= ahora
        and _va_a(mensaje, destinos)
    ]
    return min(vencidos, key=lambda mensaje: mensaje["proximo"]) if vencidos else None


def puede_enviar(activo: bool, conectado: bool, es_tiktok: bool,
                 live_chat_id: str, propio: bool, sesion: bool) -> bool:
    """Dice si los mensajes automáticos pueden mandarse ahora mismo.

    Solo al chat de un directo propio de YouTube con sesión iniciada: en
    un directo ajeno la app lee pero no escribe.
    """
    return bool(activo and conectado and not es_tiktok and live_chat_id
                and propio and sesion)


def _nombre_del_texto(texto: str) -> str:
    """El comienzo del texto, para los mensajes guardados sin nombre."""
    recorte = texto[:40]
    if len(texto) > 40 and " " in recorte:
        recorte = recorte.rsplit(" ", 1)[0]
    return recorte.strip()


def validar_nombre(nombre: str, otros) -> str:
    """Valida el nombre contra los otros mensajes y devuelve el error o ""."""
    limpio = str(nombre or "").strip()
    if not limpio:
        return _("El mensaje necesita un nombre.")
    clave = limpio.casefold()
    for otro in otros:
        existente = (otro.get("nombre", "") if isinstance(otro, dict)
                     else otro)
        if str(existente).strip().casefold() == clave:
            return _("Ya hay un mensaje llamado {nombre}.").format(nombre=limpio)
    return ""


def describir_mensaje(mensaje: dict) -> str:
    """Devuelve la línea accesible que representa un mensaje."""
    if mensaje.get("activo", False):
        # Traductores: estado en la lista de mensajes programados.
        estado = _("Activo")
    else:
        # Traductores: estado en la lista de mensajes programados.
        estado = _("Pausado")
    minimo = mensaje.get("minutos_min", 10)
    maximo = mensaje.get("minutos_max", minimo)
    if minimo == maximo and minimo == 1:
        # Traductores: intervalo en la lista de mensajes programados. {minimo} es cada cuántos minutos.
        intervalo = _("cada {minimo} minuto").format(minimo=minimo)
    elif minimo == maximo:
        # Traductores: intervalo en la lista de mensajes programados. {minimo} es cada cuántos minutos.
        intervalo = _("cada {minimo} minutos").format(minimo=minimo)
    else:
        # Traductores: intervalo en la lista de mensajes programados. {minimo} es el mínimo y {maximo} el máximo.
        intervalo = _("entre {minimo} y {maximo} minutos").format(minimo=minimo, maximo=maximo)
    # Traductores: destino en la lista de mensajes programados.
    destino = {"video": _("vídeo"), "ambos": _("chat y vídeo")}.get(
        mensaje.get("destino", "chat"), _("chat"))
    nombre = str(mensaje.get("nombre", "")).strip() or _nombre_del_texto(
        str(mensaje.get("texto", "")))
    # Traductores: línea de la lista de mensajes programados. {nombre} es el nombre, {estado} es activo o pausado, {destino} es chat, vídeo o chat y vídeo, e {intervalo} la frecuencia.
    fila = _("{nombre}: {estado}, {destino}, {intervalo}").format(
        nombre=nombre, estado=estado, destino=destino, intervalo=intervalo)
    medio = descripcion_disparador.medio(mensaje.get("medio", ""))
    return fila + (", " + medio if medio else "")


def describir_proximo(mensajes: list[dict], ahora: float) -> str:
    """Describe cuándo vence el siguiente mensaje activo."""
    activos = [
        mensaje for mensaje in mensajes
        if mensaje.get("activo", False) and "proximo" in mensaje
    ]
    if not activos:
        return ""
    # proximo <= 0 es el valor recién cargado del disco (aún sin cuerda): no
    # es «en menos de un minuto», es que todavía no se ha programado.
    con_hora = [mensaje["proximo"] for mensaje in activos if mensaje["proximo"] > 0]
    if not con_hora:
        # Traductores: estado F2 de los mensajes automáticos cuando aún no hay hora.
        return _("Próximo mensaje automático: pendiente de programar")
    restante = min(con_hora) - ahora
    if restante < 60:
        # Traductores: estado F2 de los mensajes automáticos cuando falta menos de un minuto.
        return _("Próximo mensaje automático: en menos de un minuto")
    minutos = math.ceil(restante / 60)
    # Traductores: estado F2 de los mensajes automáticos. {minutos} es en cuántos minutos se envía.
    return ngettext("Próximo mensaje automático: en {minutos} minuto",
                    "Próximo mensaje automático: en {minutos} minutos",
                    minutos).format(minutos=minutos)


def _a_bool(valor) -> bool:
    if isinstance(valor, str):
        return valor.strip().lower() in ("true", "1", "yes", "si", "sí", "on")
    return bool(valor)


def _normalizar_mensaje(mensaje: dict) -> dict:
    resultado = dict(VALORES_POR_DEFECTO)
    resultado.update(mensaje)
    # Un JSON editado a mano puede traer "10" o "true": se fuerzan los tipos
    # conocidos para que el temporizador de la GUI no reviente con un TypeError.
    for clave, defecto in VALORES_POR_DEFECTO.items():
        valor = resultado[clave]
        try:
            if isinstance(defecto, bool):
                resultado[clave] = _a_bool(valor)
            elif isinstance(defecto, int):
                resultado[clave] = int(float(valor))   # admite "15" y "15.0"
            elif isinstance(defecto, float):
                resultado[clave] = float(valor)
            else:
                resultado[clave] = "" if valor is None else str(valor)
        except (TypeError, ValueError):
            resultado[clave] = defecto
    resultado["nombre"] = resultado["nombre"].strip() or _nombre_del_texto(resultado["texto"])
    return _acotar_mensaje(resultado)


def _acotar_mensaje(mensaje: dict) -> dict:
    if mensaje["destino"] not in ("video", "chat", "ambos"):
        mensaje["destino"] = "chat"
    mensaje["segundos_pantalla"] = max(3, min(60, mensaje["segundos_pantalla"]))
    mensaje["mensajes_entre"] = max(0, min(100, mensaje["mensajes_entre"]))
    return mensaje


def cargar(ruta) -> list[dict]:
    """Carga mensajes y devuelve una lista segura aunque el archivo esté roto."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if not isinstance(datos, list):
            return []
        return [_normalizar_mensaje(mensaje) for mensaje in datos
                if isinstance(mensaje, dict)]
    except Exception:
        return []


def guardar(ruta, mensajes: list[dict]) -> None:
    """Guarda mensajes mediante un temporal para conservar el archivo anterior."""
    archivos.escribir_json_atomico(ruta, mensajes, indent=2)


class ProgramadorMensajes:
    """Estado de los mensajes automáticos de la ventana principal."""

    def __init__(self, mensajes: list[dict]):
        self.mensajes = mensajes
        self.reloj_iniciado = False
        self.ultimo_envio = None
        self.en_curso = False
        self.mensajes_chat = 0
        self._base_chat = 0
        self._envios = {}

    def recargar(self, mensajes):
        self.mensajes = mensajes
        self.reloj_iniciado = False
        self._envios.clear()

    def detener_reloj(self):
        self.reloj_iniciado = False

    def iniciar_reloj_si_falta(self, ahora, aleatorio):
        if self.reloj_iniciado:
            return
        iniciar_reloj(self.mensajes, ahora, aleatorio)
        self.reloj_iniciado = True
        self._base_chat = self.mensajes_chat

    def fijar_mensajes_chat(self, total):
        self.mensajes_chat = int(total)

    def _tiene_sus_mensajes(self, mensaje) -> bool:
        minimo = mensaje.get("mensajes_entre", 0)
        desde = self._envios.get(id(mensaje), self._base_chat)
        return self.mensajes_chat - desde >= minimo

    def siguiente(self, ahora, destinos=("chat",)) -> dict | None:
        if self.en_curso:
            return None
        disponibles = [mensaje for mensaje in self.mensajes
                       if self._tiene_sus_mensajes(mensaje)
                       and _va_a(mensaje, destinos)]
        return elegir_envio(disponibles, ahora, self.ultimo_envio, destinos)

    def empezar_envio(self):
        self.en_curso = True

    def envio_hecho(self, mensaje, ahora, aleatorio):
        self.en_curso = False
        mensaje["proximo"] = calcular_proximo(
            mensaje.get("minutos_min", 10),
            mensaje.get("minutos_max", mensaje.get("minutos_min", 10)),
            ahora, aleatorio)
        self.ultimo_envio = ahora
        self._envios[id(mensaje)] = self.mensajes_chat

    def envio_fallido(self):
        self.en_curso = False
