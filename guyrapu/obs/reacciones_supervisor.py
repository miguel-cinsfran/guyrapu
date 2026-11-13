# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Reacciones de la supervisión a lo que OBS informa durante el directo.

La espera del arranque, los avisos que no se repiten y los fallos de lectura
viven acá para que el supervisor no rinda la transmisión ante un tropiezo.
Sin wx: recibe los invocables que usa y no lee atributos del supervisor.
"""

from __future__ import annotations

from guyrapu.core import diagnostico, vigilancia
from guyrapu.core.idioma import _
from guyrapu.obs import obs_salida
from guyrapu.obs import obs_vigilante
from guyrapu.obs.duraciones import duracion_legible

logger = diagnostico.obtener_logger(__name__)

# Sonido por tipo de aviso de la vigilancia. Los problemas de red y de
# sobrecarga comparten el de transmisión con problema; la vuelta de la conexión
# tiene el suyo, distinto, para no sonar a alarma cuando ya se resolvió.
SONIDOS_AVISO = {
    "reconexion": "transmision_problema",
    "red": "transmision_problema",
    "sobrecarga": "transmision_problema",
    "vuelta": "transmision_recuperada",
}

# Si YouTube no confirmó el directo, se vuelve a consultar cada intervalo
# durante este plazo, contado desde la primera confirmación fallida.
INTERVALO_RECONFIRMACION = 30.0
PLAZO_RECONFIRMACION = 600.0


def segundos_de_cierre(actual, ultimo_activo):
    """Los segundos del fin: el estado final, o el último activo si viene en cero."""
    def segundos(estado):
        try:
            return int(float((estado or {}).get("outputDuration", 0)))
        except (TypeError, ValueError):
            return 0
    return segundos(actual) or segundos(ultimo_activo)


def esperar_arranque(esperar_salida, cliente, parada, anunciar, frase):
    """Espera a que OBS envíe, sin rendirse si todavía no lo logra.

    Devuelve `(veredicto, recuperado)`. Los veredictos que no terminan se
    anuncian una sola vez cada uno, sin cuadro, y se vuelve a preguntar.
    """
    anunciados = set()
    while True:
        veredicto = esperar_salida(cliente, parada)
        if parada is not None and parada.is_set():
            return "", bool(anunciados)
        if veredicto == "enviando":
            return veredicto, bool(anunciados)
        if veredicto == "sin_salida":
            anunciar(frase(veredicto), "transmision_problema", True)
            return veredicto, bool(anunciados)
        if veredicto not in anunciados:
            anunciados.add(veredicto)
            sonido = ("transmision_problema" if veredicto == "reconectando"
                      else "aviso")
            anunciar(frase(veredicto), sonido)


def esperar_la_salida(esperar_salida, cliente, parada, anunciar, destino,
                      servicio="") -> str:
    """Espera el envío de OBS y anuncia la frase de cada veredicto."""
    def frase(veredicto):
        return obs_salida.frase_salida(veredicto, destino, servicio=servicio)
    veredicto, recuperado = esperar_arranque(
        esperar_salida, cliente, parada, anunciar, frase)
    if veredicto != "enviando":
        return veredicto
    sonido = "transmision_recuperada" if recuperado else "conectado"
    anunciar(frase(veredicto), sonido)
    return veredicto


def marcar_importante(salida_confirmada, sonido, texto,
                      importante=False) -> bool:
    """Decide si el aviso abre cuadro, según lo que OBS ya confirmó."""
    if (salida_confirmada and sonido in ("error", "transmision_problema")
            and "YouTube no confirmó el fin" not in texto):
        return False
    return importante or "YouTube no confirmó el fin" in texto


def anunciar_fin(actual, ultimo_activo, resumen, anunciar) -> None:
    """Anuncia el fin del directo con la duración y el resumen de cuadros."""
    segundos = segundos_de_cierre(actual, ultimo_activo)
    frase = _("La transmisión terminó. Duró {duracion}.").format(
        duracion=duracion_legible(segundos))
    texto = resumen()
    if texto:
        frase = "{} {}".format(frase, texto)
    anunciar(frase, "transmision_detenida")


class Reconfirmador:
    """Vuelve a consultar YouTube si no confirmó el directo a tiempo."""

    def __init__(self, destino, id_video, esperar, parada, reloj, al_confirmar):
        self._destino = destino
        self._id_video = id_video
        self._esperar = esperar
        self._parada = parada
        self._reloj = reloj
        self._al_confirmar = al_confirmar
        self._desde = self._ultima = reloj()

    def consultar(self) -> None:
        if self._destino != "YouTube" or not self._id_video or self._esperar is None:
            return
        ahora = self._reloj()
        if ahora - self._desde > PLAZO_RECONFIRMACION:
            return
        if ahora - self._ultima < INTERVALO_RECONFIRMACION:
            return
        self._ultima = ahora
        if self._esperar(self._id_video, self._parada, 0):
            self._al_confirmar()


def revisar_directo(anterior, actual, estadisticas_anterior, estadisticas,
                    avisos, avisar_sobrecarga, anunciar, panel_tapado, gestor,
                    anunciar_panel, reconfirmar):
    """Da los avisos de una vuelta y devuelve las estadísticas de referencia."""
    for tipo, frase in obs_salida.problemas_en_directo(
            anterior, actual, estadisticas_anterior, estadisticas):
        if tipo == "sobrecarga" and not avisar_sobrecarga():
            continue
        if avisos.toca(tipo):
            anunciar(frase, SONIDOS_AVISO[tipo])
    nombre = panel_tapado(gestor)
    if nombre and avisos.toca(nombre):
        anunciar_panel(nombre)
    if reconfirmar is not None:
        reconfirmar.consultar()
    return estadisticas if estadisticas is not None else estadisticas_anterior


class LectorDeEstado:
    """Lee el estado de OBS sin que un fallo corte la vigilancia."""

    def __init__(self, gestor, parada, anunciar, en_ejecucion):
        self._gestor = gestor
        self._parada = parada
        self._en_ejecucion = en_ejecucion
        self._vigilancia = vigilancia.Vigilancia(
            anunciar,
            caida=vigilancia.Aviso(_(obs_vigilante.MENSAJE_SIN_RESPUESTA),
                                   "obs_sin_respuesta"),
            vuelta=vigilancia.Aviso(_(obs_vigilante.MENSAJE_RESPONDE),
                                    "obs_responde"),
            rendicion=vigilancia.Aviso(
                _(obs_vigilante.MENSAJE_SIN_RESPUESTA), "obs_sin_respuesta"))

    def leer(self):
        """Devuelve `(estado, obs_apagado)`; el estado es None si no contestó."""
        try:
            if self._vigilancia.caido:
                self._gestor.conectar(self._parada)
            estado = self._gestor.estado_transmision(self._parada)
        except Exception as error:
            logger.debug("no se pudo leer el estado de OBS: %s", error)
            return self._fallo()
        self._vigilancia.leida(True)
        return estado, False

    def _fallo(self):
        if self._parada is not None and self._parada.is_set():
            return None, False
        if not self._sigue_en_ejecucion():
            return None, True
        self._vigilancia.leida(False)
        return None, False

    def _sigue_en_ejecucion(self) -> bool:
        try:
            return bool(self._en_ejecucion())
        except Exception:
            # Un fallo al comprobar la ejecución no puede callar una falla
            # real de OBS.
            return True