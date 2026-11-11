# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Decisiones del botón directo de transmisión, sin interfaz.

Vive aparte de wx para poder probarse sin ventana: si el botón se ve, qué
dice y en qué orden se prepara OBS antes de transmitir. Quien llama traduce
los fallos con `obs_cliente.mensaje_de_fallo_obs`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.obs import perfil_por_uso, perfil_previo
from guyrapu.restream import transmitir

logger = diagnostico.obtener_logger(__name__)


ALTERNAR = "alternar"
ESPERAR_DETENCION = "esperar_detencion"
DETENER_SUPERVISADA = "detener_supervisada"
FALTA_DESTINO = "falta_destino"
FALTA_USUARIO = "falta_usuario"
REVISAR = "revisar"


def decidir_transmision(*, hay_supervisor, deteniendo, con_supervisor,
                        transmitiendo, destino, usuario_tiktok) -> str:
    """Elige qué hace el botón Transmitir según el estado actual.

    Las tres funciones son perezosas porque cada una consulta al
    supervisor o normaliza lo escrito y solo conviene llamarla si la
    rama llega a necesitarla.
    """
    if not hay_supervisor:
        return ALTERNAR
    if deteniendo():
        return ESPERAR_DETENCION
    if con_supervisor():
        return DETENER_SUPERVISADA
    if transmitiendo:
        return ALTERNAR
    if not destino:
        return FALTA_DESTINO
    if destino == "TikTok" and not usuario_tiktok():
        return FALTA_USUARIO
    return REVISAR


def cuenta_restream_conectada(opcion, avisar) -> bool:
    """¿Se puede seguir o falta conectar la cuenta de Restream?

    Solo un perfil de Restream la necesita. Si falta, avisa con `avisar`
    (texto, sonido y error) y devuelve False.
    """
    from guyrapu.restream import ganchos
    if not transmitir.es_restream(opcion):
        return True
    if ganchos.cuenta_conectada():
        return True
    avisar(_(ganchos.MENSAJE_SIN_CUENTA), "error", error=True)
    return False


def leer_destinos_de_mas(opcion):
    """Los destinos de Restream que sobran para un directo de TikTok.

    Solo con la opción «TikTok» y la cuenta de Restream conectada, y se
    llama desde el hilo que revisa OBS, nunca desde el principal. Si la
    lectura falla, deja la advertencia en el registro y no hay destinos.
    """
    from guyrapu.restream import cuenta, destinos_de_mas, ganchos
    if opcion != "TikTok" or not ganchos.cuenta_conectada():
        return ()
    try:
        canales = cuenta.canales()
    except Exception as error:
        logger.warning(
            "no se pudieron leer los destinos de Restream: %s", error)
        return ()
    return destinos_de_mas.de_mas(canales)


def _avisar_ya_transmitiendo(anunciar, tras_anunciar):
    anunciar(_("OBS ya está transmitiendo. Con este mismo botón "
               "puedes finalizar el directo."))
    if tras_anunciar is not None:
        tras_anunciar()


def resolver_revision(preparacion, opcion, destino_obs, usuario, *,
                      confirmar, supervisar, anunciar, ya_transmitiendo,
                      iniciar, recordar_destino, guardar_usuario,
                      tras_anunciar=None) -> None:
    """Decide qué se hace con el resultado de revisar OBS.

    `ya_transmitiendo` e `iniciar` son los efectos de cada botón al marcar
    su estado o mostrar la transmisión. `recordar_destino` y
    `guardar_usuario` guardan lo propio de cada uno, o no hacen nada. La
    vuelta al perfil anterior y el aviso de que no se transmitió viven aquí
    una sola vez.
    """
    if preparacion.ya_transmitiendo:
        ya_transmitiendo()
        _avisar_ya_transmitiendo(anunciar, tras_anunciar)
        return
    if transmitir.es_restream(opcion):
        recordar_destino()
        supervisar("iniciar", opcion, "")
    elif destino_obs == "YouTube":
        recordar_destino()
        supervisar("iniciar", opcion, usuario,
                   revision=preparacion.revision)
    elif not confirmar(preparacion.revision):
        perfil_previo.volver_sin_directo()
        anunciar(_("No se transmitió."))
        return
    else:
        guardar_usuario()
        recordar_destino()
        supervisar("iniciar", opcion, usuario)
    iniciar()


@dataclass(frozen=True, slots=True)
class Preparacion:
    """Resultado de `preparar`: o ya se transmite, o hay revisión."""

    ya_transmitiendo: bool
    revision: Any = None
    destinos_de_mas: tuple = ()


def es_directo_propio(es_tiktok, usuario_sesion, usuario_guardado,
                      conectado_por_transmision) -> bool:
    """¿El contenido conectado es el directo del propio usuario?

    Vale si la conexión la pidió la transmisión, o si es TikTok y el
    usuario de la sesión coincide con el guardado (sin importar
    mayúsculas ni la arroba inicial). En YouTube solo cuenta la
    conexión pedida: reconocer el canal propio queda para cuando
                      exista transmitir a YouTube desde la app.
    """
    if conectado_por_transmision:
        return True
    if not es_tiktok:
        return False
    from guyrapu.capture import tiktok_vivo
    sesion = tiktok_vivo.usuario_tiktok(usuario_sesion or "")
    guardado = tiktok_vivo.usuario_tiktok(usuario_guardado or "")
    return bool(sesion) and sesion.lower() == guardado.lower()


def boton_visible(conectado, conectando, propio, transmitiendo) -> bool:
    """¿El botón directo se muestra?

    En la pantalla de inicio (sin conexión ni conexión en curso) o en el
    directo propio. Estar transmitiendo no lo muestra por sí solo: en el
    directo de otro no aparece, y para finalizar se vuelve al inicio
    con Desconectar.
    """
    _sin_uso = transmitiendo
    return (not conectado and not conectando) or bool(propio)


def etiqueta(transmitiendo, deteniendo=False):
    """Etiqueta con atajo y nombre accesible según el estado del directo.

    Mientras OBS confirma la parada el botón sigue visible y habilitado:
    solo cambia lo que dice, para que el nombre accesible avise que se
    espera a OBS.
    """
    if deteniendo:
        return (_("Finalizando el directo"),
                _("Finalizando el directo, esperando a OBS"))
    if transmitiendo:
        return (_("&Finalizar directo"), _("Finalizar directo"))
    return (_("Transm&itir en directo"), _("Transmitir en directo"))


def _perfil_para(destino, actual):
    """Perfil real de OBS al que hay que ir; vacío no cambia el actual."""
    elegido = perfil_por_uso.perfil_elegido(destino)
    return actual if elegido == "" else (elegido or destino)


def _anunciar_preparacion(al_anunciar, actual, perfil, resultado):
    """Anuncia el cambio y, si OBS lo creó, el perfil real que se creó."""
    if actual != perfil:
        al_anunciar(_("Preparando OBS para {destino}.").format(
            destino=perfil))
    if (resultado or {}).get("perfil_creado"):
        creado = (resultado or {}).get("perfil") or perfil
        al_anunciar(_("Se creó en OBS el perfil {destino}.").format(
            destino=creado))


def preparar(gestor, destino: str, asegurar: Callable, al_anunciar: Callable,
             parada=None, cerrar=True, opcion=None) -> Preparacion:
    """Asegura OBS, conecta y deja el destino listo para confirmar.

    Devuelve `Preparacion(ya_transmitiendo=True)` si OBS ya emite (sin
    preparar ni revisar). Si no, prepara el destino (siempre, que es
    idempotente) y devuelve la revisión. Con `cerrar=True` cierra el gestor
    en `finally`; el panel lo comparte con la ventana Escena y pasa
    `cerrar=False`. Las excepciones salen tal cual para que las traduzca
    quien llama.
    """
    try:
        asegurar(gestor.conectar, al_anunciar=al_anunciar, parada=parada)
        gestor.conectar()
        if bool(gestor.estado_transmision().get("outputActive", False)):
            return Preparacion(ya_transmitiendo=True)
        actual = gestor.perfil_actual()
        perfil = _perfil_para(destino, actual)
        resultado = gestor.preparar_destino(destino)
        _anunciar_preparacion(al_anunciar, actual, perfil, resultado)
        revision = gestor.revisar(destino, servicio_propio=(opcion == "TikTok"))
        return Preparacion(ya_transmitiendo=False, revision=revision,
                           destinos_de_mas=leer_destinos_de_mas(opcion))
    finally:
        if cerrar:
            try:
                gestor.cerrar()
            except Exception as error:
                logger.debug("no se pudo cerrar el gestor de OBS: %s", error)


class FalloCierreYoutube(Exception):
    """OBS se detuvo pero YouTube no confirmó el fin del directo."""


def _leer_perfil_actual(gestor, finalizar_youtube):
    """El perfil de OBS antes de detener, solo si hay cierre de YouTube."""
    if finalizar_youtube is None:
        return None
    try:
        return gestor.perfil_actual()
    except Exception:
        return None


def finalizar(gestor, finalizar_youtube=None) -> None:
    """Detiene el directo si OBS transmite, para finalizar sin supervisor.

    Conecta, detiene solo con `outputActive` y cierra en `finally`. Con
    `finalizar_youtube` y perfil de OBS en "YouTube" (leído antes de
    detener), lo llama después de detener OBS para cerrar el directo en
    YouTube; si eso falla, sale como `FalloCierreYoutube`.
    """
    try:
        gestor.conectar()
        perfil = _leer_perfil_actual(gestor, finalizar_youtube)
        if bool(gestor.estado_transmision().get("outputActive", False)):
            gestor.detener_transmision()
        if finalizar_youtube is not None:
            horizontal = perfil_por_uso.perfil_elegido("YouTube")
            if horizontal is None:
                horizontal = "YouTube"
            if horizontal == "" or perfil == horizontal:
                try:
                    finalizar_youtube()
                except FalloCierreYoutube:
                    raise
                except Exception as exc:
                    raise FalloCierreYoutube(
                        _("YouTube no confirmó el fin del directo. "
                          "Finalízalo en YouTube Studio.")) from exc
    finally:
        try:
            gestor.cerrar()
        except Exception as error:
            logger.debug("no se pudo cerrar el gestor de OBS: %s", error)
