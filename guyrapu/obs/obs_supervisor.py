# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Supervisor de la transmisión sin interfaz.

Vive aparte de la ventana Transmisión: si la persona cierra esa ventana para
leer el chat, el supervisor sigue. Al iniciar arranca OBS, confirma que la
señal sale, espera a que TikTok muestre el directo, pide conectar el chat, y
después vigila el directo hablando solo ante problemas. Lo crea
`guyrapu/ui/gui_transmitir.py`.
"""

from __future__ import annotations

import threading
import time

from guyrapu.capture import tiktok_vivo
from guyrapu.core import diagnostico, esperas, vigilancia
from guyrapu.core.idioma import _
from guyrapu.core.tiempo import TiempoDeFunciones
from guyrapu.obs import codificadores_obs
from guyrapu.obs import detener_obs
from guyrapu.obs import obs_activacion
from guyrapu.obs import obs_cliente
from guyrapu.obs import obs_clips
from guyrapu.obs import obs_estado
from guyrapu.obs import obs_lanzador
from guyrapu.obs import obs_salida
from guyrapu.obs import reacciones_supervisor
from guyrapu.obs import resumen_directo
from guyrapu.obs.obs_panel import GestorPanelObs
from guyrapu.obs.reacciones_supervisor import (
    SONIDOS_AVISO, segundos_de_cierre)  # noqa: F401
from guyrapu.youtube import emision
from guyrapu.youtube import fin_pendiente

logger = diagnostico.obtener_logger(__name__)


class SupervisorTransmision:
    """Arranca OBS y vigila el directo desde un hilo propio."""

    def __init__(self, destino, usuario_tiktok="",
                 al_anunciar=None, al_conectar_chat=None,
                 crear_gestor=GestorPanelObs,
                 esperar_salida=obs_salida.esperar_salida,
                 esperar_en_vivo=tiktok_vivo.esperar_en_vivo,
                 dormir=time.sleep, reloj=time.monotonic,
                 intervalo_salud=5.0, limite_tiktok=120.0,
                 asegurar=None, al_terminar=None,
                 preparar_emision=None, esperar_emision=None,
                 finalizar_emision=None, ruta_fin_pendiente=None,
                 avisar_sobrecarga=None, servicio=""):
        self._destino = destino
        self._usuario = usuario_tiktok or ""
        self._servicio = servicio
        self._al_anunciar = al_anunciar or (lambda frase, sonido: None)
        self._al_conectar_chat = al_conectar_chat or (lambda url: None)
        self._crear_gestor = crear_gestor
        self._esperar_salida = esperar_salida
        self._esperar_en_vivo = esperar_en_vivo
        self._dormir = dormir
        self._reloj = reloj
        self._intervalo_salud = intervalo_salud
        self._limite_tiktok = limite_tiktok
        self._asegurar = asegurar if asegurar is not None else obs_lanzador.asegurar_obs
        self._al_terminar = al_terminar
        self._preparar_emision = preparar_emision
        self._esperar_emision = esperar_emision
        self._cierre = fin_pendiente.CierreYoutube(
            finalizar_emision, ruta_fin_pendiente, self._anunciar,
            dormir, reloj)
        # Invocable sin argumentos que decide, en cada vuelta, si el aviso de
        # sobrecarga se anuncia. El supervisor no lee la configuración solo:
        # quien lo crea se la pasa.
        self._avisar_sobrecarga = avisar_sobrecarga or (lambda: True)
        self._id_video = None
        self._parada = threading.Event()
        self._corte = threading.Event()
        self._hilo = None
        self._deteniendo = False
        self._ultimo_estado = None
        self._ultima_frase = ""
        self._destino_confirmado = None
        self._salida_confirmada = False
        self._puede_seguir_al_aire = False
        self._reconfirmador = None
        # Muestras del directo para el resumen del final: la primera con la
        # salida activa, la última activa, y el perfil con su codificador.
        self._resumen_primero = None
        self._resumen_ultimo = None
        self._resumen_perfil = None

    @property
    def activo(self) -> bool:
        return self._hilo is not None and self._hilo.is_alive()

    @property
    def deteniendo(self) -> bool:
        # Verdadero desde que detener() empieza con la transmisión activa
        # hasta que _detener_obs deja de esperar a OBS. El fin en YouTube no
        # la mantiene: la salida de OBS ya no emite.
        return self._deteniendo

    @property
    def puede_seguir_al_aire(self) -> bool:
        # Verdadera desde que se pidió a OBS transmitir hasta que se vio la
        # salida inactiva o terminó detener(). Al cerrar la app sigue
        # verdadera: el directo no se corta.
        return self._puede_seguir_al_aire

    def frase_estado(self) -> str:
        """Fase actual para F2, sin repetir lo ya anunciado.

        Si ya se leyó un estado con transmisión activa, nombra el
        destino con la duración del último estado; si no, repite la
        última frase anunciada sin el punto final."""
        ultimo = self._ultimo_estado
        if ultimo is not None and bool(ultimo.get("outputActive")):
            try:
                frase = obs_estado.frase_transmision(ultimo.get("outputActive"),
                                                     ultimo.get("outputDuration", 0),
                                                     ultimo.get("outputSkippedFrames", 0),
                                                     ultimo.get("outputTotalFrames", 0))
            except Exception:
                frase = ""
            if frase:
                if self._destino_confirmado is True:
                    frase = _("{frase}, ya se ve en {destino}").format(frase=frase, destino=self._destino)
                elif self._destino_confirmado is False:
                    frase = _("{frase}, sin confirmar en {destino}").format(
                        frase=frase, destino=self._destino)
                return _("Directo a {destino}: {frase}").format(destino=self._destino, frase=frase)
        texto = (self._ultima_frase or "").strip()
        if texto.endswith("."):
            texto = texto[:-1].rstrip()
        return texto

    def iniciar(self) -> None:
        if self.activo:
            return
        self._parada.clear()
        self._corte.clear()
        self._id_video = None
        self._cierre.reiniciar()
        self._resumen_primero = None
        self._resumen_ultimo = None
        self._resumen_perfil = None
        self._salida_confirmada = False
        self._puede_seguir_al_aire = False
        self._reconfirmador = None
        self._hilo = diagnostico.crear_hilo(
            self._supervisar, "SupervisorTransmision")
        self._hilo.start()

    def detener(self) -> None:
        estaba_activo = self.activo
        if estaba_activo:
            # Antes de la parada: la vigilancia sale enseguida y `activo`
            # pasa a False, pero OBS todavía emite hasta `_detener_obs`.
            self._deteniendo = True
        self._parada.set()
        self._corte.set()
        if estaba_activo:
            try:
                self._detener_obs()
            finally:
                self._deteniendo = False
                self._salida_confirmada = False
                self._puede_seguir_al_aire = False
            self._finalizar_youtube_si_toca()
        hilo = self._hilo
        if hilo is not None:
            hilo.join(2.0)
        # Repite el aviso que ya dio la vigilancia al salir: ahora sí se
        # puede refrescar el botón con la parada confirmada.
        if self._al_terminar is not None:
            try:
                self._al_terminar()
            except Exception as error:
                logger.debug("no se pudo avisar el fin de la supervisión: %s", error)

    def _detener_obs(self) -> None:
        """Pide parar a OBS y espera a que confirme, sin congelar la ventana."""
        detener_obs.detener(
            self._crear_gestor, self._anunciar, self._reloj, self._dormir,
            self._resumen, obs_activacion.obs_esta_en_ejecucion)

    def _resumen(self) -> str:
        if self._resumen_primero is None or self._resumen_ultimo is None:
            return ""
        estado_inicial, estadisticas_iniciales = self._resumen_primero
        estado_final, estadisticas_finales = self._resumen_ultimo
        perfil, codificador = self._resumen_perfil or ("", "")
        return resumen_directo.resumir(
            estado_inicial, estado_final, estadisticas_iniciales,
            estadisticas_finales, perfil, codificador,
            codificadores_obs.codificadores_disponibles())

    def abandonar(self) -> None:
        # Deja de vigilar sin detener OBS y sin anunciar: cerrar la app no
        # corta el directo.
        self._parada.set()
        self._corte.set()
        hilo = self._hilo
        if hilo is not None:
            hilo.join(2.0)

    def _anunciar(self, frase, sonido, importante=False) -> None:
        texto = frase if isinstance(frase, str) else ""
        self._ultima_frase = texto
        marcado = reacciones_supervisor.marcar_importante(
            self._salida_confirmada, sonido, texto, importante)
        self._al_anunciar(frase, sonido, marcado)

    def _panel_tapado(self, gestor):
        # Los dobles viejos de las pruebas no tienen el método y se salta.
        traer = getattr(gestor, "traer_panel_adelante", None)
        if traer is None:
            return None
        try:
            return traer(self._parada)
        except Exception as error:
            logger.debug("no se pudo poner el panel delante: %s", error)
            return None

    def _anunciar_panel_tapado(self, nombre) -> None:
        frase = _("El chat en el vídeo estaba detrás de «{nombre}». Ahora está delante.")
        self._anunciar(frase.format(nombre=nombre), "aviso")

    def _iniciar_transmision(self, gestor, cliente) -> None:
        """Prepara los clips antes de que arranque el directo, sin impedirlo."""
        obs_clips.preparar_para_directo(
            cliente, obs_clips.leer_segundos(),
            al_preparar=lambda: self._anunciar(_("Preparando los clips."), "transmision_paso"),
            al_fallar=lambda error: self._anunciar(
                obs_cliente.mensaje_de_fallo_obs(error), "error"),
            parada=self._parada)
        gestor.iniciar_transmision(self._parada)

    def _probar_obs(self) -> None:
        gestor = self._crear_gestor()
        try:
            gestor.conectar(self._parada)
        finally:
            try:
                gestor.cerrar()
            except Exception as error:
                logger.debug("no se pudo cerrar el gestor de prueba: %s", error)

    def _supervisar(self) -> None:
        gestor = None
        try:
            self._anunciar(_("Iniciando la transmisión."), "conectando")
            if self._parada.is_set():
                return
            self._asegurar(self._probar_obs,
                           al_anunciar=lambda frase: self._anunciar(
                               frase, None),
                           parada=self._parada)
            if self._parada.is_set():
                return
            gestor = self._crear_gestor()
            gestor.conectar(self._parada)
            if self._parada.is_set():
                return
            cliente = getattr(gestor, "_cliente", gestor)
            if self._preparar_emision is not None:
                self._anunciar(_("Creando el directo en YouTube."), "transmision_paso")
                try:
                    self._id_video = self._preparar_emision(
                        cliente, self._parada)
                except emision.EmisionError as error:
                    self._anunciar(str(error), "transmision_problema", True)
                    return
            nombre = self._panel_tapado(gestor)
            if nombre:
                self._anunciar_panel_tapado(nombre)
            self._iniciar_transmision(gestor, cliente)
            self._puede_seguir_al_aire = True
            if self._parada.is_set():
                return
            if self._esperar_la_salida(cliente) is None:
                return
            if self._destino == "TikTok" and self._usuario:
                if not self._confirmar_tiktok():
                    return
            elif self._destino == "YouTube" and self._id_video \
                    and self._esperar_emision is not None:
                if not self._confirmar_youtube():
                    return
            elif self._destino == "TikTok":
                frase = _("No hay usuario de TikTok guardado: conecta el chat manualmente.")
                self._anunciar(frase, "aviso")
            self._vigilar(gestor)
        except Exception as error:
            if self._parada.is_set():
                return
            try:
                self._anunciar(obs_cliente.mensaje_de_fallo_obs(error), "transmision_problema", True)
            except Exception as error_anuncio:
                logger.debug("no se pudo anunciar el fallo de OBS: %s", error_anuncio)
        finally:
            if gestor is not None:
                try:
                    gestor.cerrar()
                except Exception as error:
                    logger.debug("no se pudo cerrar el gestor de OBS: %s", error)
            if self._al_terminar is not None:
                try:
                    self._al_terminar()
                except Exception as error:
                    logger.debug("no se pudo avisar el fin de la supervisión: %s", error)

    def _esperar_la_salida(self, cliente):
        veredicto = reacciones_supervisor.esperar_la_salida(
            self._esperar_salida, cliente, self._parada, self._anunciar,
            self._destino, self._servicio)
        if veredicto != "enviando":
            if veredicto == "sin_salida":
                self._puede_seguir_al_aire = False
            return None
        self._salida_confirmada = True
        return veredicto

    def _confirmar_tiktok(self) -> bool:
        self._anunciar(_("Esperando a que TikTok muestre el directo."), "transmision_paso")
        resultado = self._esperar_en_vivo(
            self._usuario, self._parada,
            limite=self._limite_tiktok)
        if self._parada.is_set():
            return False
        if resultado.en_vivo:
            self._destino_confirmado = True
            self._anunciar(_("Directo iniciado en TikTok"), "al_aire", True)
            self._al_conectar_chat(
                tiktok_vivo.url_directo(self._usuario))
        else:
            self._destino_confirmado = False
            self._anunciar(*tiktok_vivo.aviso_espera(resultado, self._usuario), importante=True)
        return True

    def _confirmar_youtube(self) -> bool:
        self._anunciar(_("Esperando a que YouTube muestre el directo."), "transmision_paso")
        ok = self._esperar_emision(
            self._id_video, self._parada, self._limite_tiktok)
        if self._parada.is_set():
            return False
        if ok:
            self._conectar_youtube()
        else:
            self._destino_confirmado = False
            self._reconfirmador = reacciones_supervisor.Reconfirmador(
                self._destino, self._id_video, self._esperar_emision,
                self._parada, self._reloj, self._conectar_youtube)
            self._anunciar(_("OBS está transmitiendo, pero YouTube todavía no muestra "
                             "el directo."), "transmision_problema", True)
        return True

    def _conectar_youtube(self) -> None:
        self._destino_confirmado = True
        self._reconfirmador = None
        self._anunciar(_("Directo iniciado en YouTube"), "al_aire", True)
        self._al_conectar_chat(emision.url_video(self._id_video))

    def _finalizar_youtube_si_toca(self) -> None:
        self._cierre.finalizar_si_toca(self._id_video)

    def _terminar_transmision(self, actual) -> None:
        self._puede_seguir_al_aire = False
        self._salida_confirmada = False
        reacciones_supervisor.anunciar_fin(
            actual, self._resumen_ultimo and self._resumen_ultimo[0],
            self._resumen, self._anunciar)
        self._finalizar_youtube_si_toca()

    def _vigilar(self, gestor) -> None:
        lector = reacciones_supervisor.LectorDeEstado(
            gestor, self._parada, self._anunciar,
            en_ejecucion=obs_activacion.obs_esta_en_ejecucion)
        avisos = vigilancia.AvisosRepetidos(self._reloj)
        estado = {"anterior": None, "estadisticas": None}
        # La vigilancia duerme con la parada para que detener() despierte
        # enseguida; los dobles de las pruebas inyectan otro dormir y se
        # respeta para no romper su reloj falso.
        dormir = self._parada.wait if self._dormir is time.sleep else self._dormir
        esperas.esperar(
            lambda: self._vuelta_de_vigilancia(gestor, lector, avisos, estado),
            lambda valor: valor != "sigue",
            cadencia=esperas.Fija(self._intervalo_salud),
            parada=self._parada, tiempo=TiempoDeFunciones(self._reloj, dormir))

    def _vuelta_de_vigilancia(self, gestor, lector, avisos, estado) -> str:
        if self._corte.is_set():
            return "termina"
        actual, apagado = lector.leer()
        if apagado:
            self._terminar_transmision(None)
            return "termina"
        if actual is None:
            return "sigue"
        self._ultimo_estado = actual
        if self._parada.is_set() or self._corte.is_set():
            return "termina"
        if not actual.get("outputActive"):
            self._puede_seguir_al_aire = False
            if self._parada.is_set() or self._corte.is_set():
                return "termina"
            if estado["anterior"] is not None:
                self._terminar_transmision(actual)
            return "termina"
        if estado["anterior"] is None:
            estado["estadisticas"] = self._estadisticas(gestor)
            self._resumen_primero = (actual, estado["estadisticas"])
            self._resumen_ultimo = self._resumen_primero
            self._resumen_perfil = resumen_directo.datos_del_perfil(
                getattr(gestor, "_cliente", gestor), self._parada)
        else:
            estadisticas = self._estadisticas(gestor)
            estado["estadisticas"] = reacciones_supervisor.revisar_directo(
                estado["anterior"], actual, estado["estadisticas"],
                estadisticas, avisos, self._avisar_sobrecarga,
                self._anunciar, self._panel_tapado, gestor,
                self._anunciar_panel_tapado, self._reconfirmador)
        estado["anterior"] = actual
        self._resumen_ultimo = (self._ultimo_estado, estado["estadisticas"])
        return "sigue"

    def _estadisticas(self, gestor):
        # Los dobles que no traen estadísticas quedan sin avisos de equipo en
        # esa vuelta; un fallo real de OBS tampoco corta la vigilancia.
        try:
            return gestor.estadisticas(self._parada)
        except Exception as error:
            logger.debug("no se pudieron leer las estadísticas de OBS: %s",
                         error)
            return None
