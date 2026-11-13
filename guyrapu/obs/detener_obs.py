# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Secuencia de detener la transmisión: pedir a OBS que pare y esperar.

Las funciones reciben lo que usan (crear el gestor, anunciar, reloj,
dormir) y no guardan ni leen atributos del supervisor. Solo las llama
`SupervisorTransmision`.
"""

from __future__ import annotations

from guyrapu.core import diagnostico, esperas
from guyrapu.core.idioma import _
from guyrapu.core.tiempo import resolver_tiempo

logger = diagnostico.obtener_logger(__name__)

# Al detener: cuánto se espera a que OBS apague la salida, cada cuánto se
# consulta, y desde cuándo se avisa de que la espera sigue.
LIMITE_ESPERA_OBS = 90.0
INTERVALO_ESPERA_OBS = 1.0
AVISO_ESPERA_OBS = 3.0


def detener(crear_gestor, anunciar, reloj, dormir, resumen=None,
            obs_activo=None) -> None:
    """Pide parar a OBS y espera a que confirme, sin congelar la ventana.

    Corre en el hilo DetenerSupervisor, así que puede dormir con `dormir`
    directamente: esperar con la parada volvería enseguida porque la parada
    ya está puesta.
    """
    gestor = None
    try:
        gestor = crear_gestor()
        gestor.conectar()
    except Exception as error:
        _cerrar_gestor(gestor)
        _anunciar_sin_respuesta(anunciar, error, resumen, obs_activo)
        return
    try:
        try:
            activa = bool(
                gestor.estado_transmision().get("outputActive"))
        except Exception:
            # Sin respuesta al preguntar el estado, se asume activa:
            # mejor mandar StopStream de más que dejar la salida
            # corriendo. `_esperar_a_obs` dirá lo que toque si OBS
            # sigue sin responder.
            activa = True
        if not activa:
            _anunciar_detenida(anunciar, resumen)
            return
        try:
            gestor.detener_transmision()
        except Exception as error:
            logger.debug("no se pudo detener la transmisión en OBS: %s", error)
        _esperar_a_obs(gestor, anunciar, reloj, dormir, resumen,
                       obs_activo)
    finally:
        _cerrar_gestor(gestor)


def _esperar_a_obs(gestor, anunciar, reloj, dormir, resumen,
                   obs_activo) -> None:
    """Consulta a OBS hasta que la salida se apague, con un límite."""
    inicio = reloj()
    estado = {"avisado": False, "error": None}

    def consultar():
        try:
            activa = bool(
                gestor.estado_transmision().get("outputActive"))
        except Exception as error:
            estado["error"] = error
            return "sin_respuesta"
        if not activa:
            return "detenida"
        transcurrido = reloj() - inicio
        if not estado["avisado"] and transcurrido >= AVISO_ESPERA_OBS:
            anunciar(_("Deteniendo la transmisión. Esperando a que OBS confirme."),
                     None)
            estado["avisado"] = True
        return "sigue"

    resultado = esperas.esperar(
        consultar, lambda veredicto: veredicto != "sigue",
        cadencia=esperas.Fija(INTERVALO_ESPERA_OBS),
        plazo=LIMITE_ESPERA_OBS, tiempo=resolver_tiempo(reloj, dormir))
    if resultado.valor == "sin_respuesta":
        _anunciar_sin_respuesta(anunciar, estado["error"], resumen, obs_activo)
    elif resultado.valor == "detenida":
        _anunciar_detenida(anunciar, resumen)
    else:
        anunciar(
            _("OBS sigue transmitiendo. Detén la transmisión en OBS."),
            "error", True)


def _anunciar_sin_respuesta(anunciar, error, resumen, obs_activo) -> None:
    # Sin poder hablar con OBS, la señal depende de si OBS sigue abierto:
    # si no corre, la transmisión ya no sale y está detenida.
    try:
        corre = bool(obs_activo()) if obs_activo is not None else False
    except Exception:
        corre = False
    if corre:
        anunciar(
            _("No se pudo conectar con OBS para detener la transmisión."),
            "error", True)
    else:
        _anunciar_detenida(anunciar, resumen)


def _anunciar_detenida(anunciar, resumen) -> None:
    frase = _("Transmisión detenida.")
    texto = resumen() if resumen is not None else ""
    if texto:
        frase = "{} {}".format(frase, texto)
    anunciar(frase, "transmision_detenida", True)


def _cerrar_gestor(gestor) -> None:
    if gestor is None:
        return
    try:
        gestor.cerrar()
    except Exception as error:
        logger.debug("no se pudo cerrar el gestor de OBS: %s", error)
