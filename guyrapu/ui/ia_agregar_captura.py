# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Subventana para elegir qué capturar y preguntarle a la IA.

Lista «Capturar de» con las fuentes de OBS y el fotograma del
reproductor, vista previa y botones Capturar y Cancelar.
"""

from __future__ import annotations

import io
import threading

import wx

from guyrapu.capture import redaccion
from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import obs_activacion
from guyrapu.obs import obs_captura_ia
from guyrapu.obs import obs_cliente
from guyrapu.player import fotograma_video
from guyrapu.ui import ia_captura_video
from guyrapu.ui import formulario, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.espera_sonora import EsperaSonora
from guyrapu.voice.sound_player import reproducir


logger = diagnostico.obtener_logger(__name__)

TEXTO_CARGANDO = N_("Cargando las fuentes de OBS…")
# Traductores: motivo de Capturar mientras se cargan las fuentes de OBS.
TEXTO_CARGANDO_MOTIVO = N_("Cargando las fuentes de OBS")
# Traductores: motivo de Capturar mientras se captura.
TEXTO_CAPTURANDO = N_("Capturando")
# Traductores: motivo de Capturar cuando OBS no ofrece fuentes.
TEXTO_SIN_FUENTES = N_("No hay fuentes para capturar")
TEXTO_OBS_CERRADO = N_("OBS no está abierto.")

ANCHO_VISTA = 320
ALTO_VISTA = 180


def texto_negra(etiqueta, motivo="", fuente="") -> str:
    """Aviso cuando la captura sale negra, en palabras para el usuario."""
    if motivo == "sin_fuente":
        # Traductores: aviso de captura negra; {etiqueta} es lo elegido en «Capturar de».
        return (_("La captura de {etiqueta} está en negro y no se agregó. "
                  "La escena no tiene ninguna captura de pantalla, de "
                  "ventana, de juego ni de cámara. Agrega una en OBS y "
                  "vuelve a intentarlo.").format(etiqueta=etiqueta))
    if motivo == "sin_elegir":
        # Traductores: aviso de captura negra; {etiqueta} lo elegido y {fuente} su origen.
        return (_("La captura de {etiqueta} está en negro y no se agregó. "
                  "La fuente {fuente} no tiene elegido qué capturar. "
                  "Elígelo en las propiedades de la fuente en OBS.").format(
                      etiqueta=etiqueta, fuente=fuente))
    # Traductores: aviso de captura negra; {etiqueta} es lo elegido en «Capturar de».
    return (_("La captura de {etiqueta} está en negro y no se agregó. Ocurre "
              "cuando el equipo no tiene monitor conectado o si la cortina de "
              "pantalla de NVDA está activa. Prueba en OBS el método de "
              "captura Windows 10 para esa fuente.").format(
                  etiqueta=etiqueta))


class DialogoAgregarCaptura(wx.Dialog):
    def __init__(self, padre, cliente, reproductor=None):
        super().__init__(padre, title=_("Agregar captura"),
                         name="DialogoAgregarCaptura")
        self._cliente = cliente
        self._reproductor = reproductor
        self._cerrojo = threading.Lock()
        self._cerrado = False
        self._opciones = ()
        self._resultado = None
        self._generacion_vista = 0

        panel = wx.Panel(self, name="PanelAgregarCaptura")
        self.panel = panel
        vs = wx.BoxSizer(wx.VERTICAL)
        self.rotulo_fuente = wx.StaticText(panel, label=_("&Capturar de:"))
        self.cho_fuente = wx.Choice(
            panel, choices=[_(TEXTO_CARGANDO)], name=_("Capturar de"))
        self.cho_fuente.SetSelection(0)
        nombre_accesible(self.cho_fuente, _("Capturar de"))
        formulario.agregar_fila(vs, self.rotulo_fuente, self.cho_fuente)

        self.bmp_vista = wx.StaticBitmap(
            panel, bitmap=wx.NullBitmap, size=(ANCHO_VISTA, ALTO_VISTA),
            name=_("Vista previa"))
        self.bmp_vista.SetMinSize((ANCHO_VISTA, ALTO_VISTA))
        nombre_accesible(self.bmp_vista, _("Vista previa"))
        formulario.agregar_fila(vs, None, self.bmp_vista)

        self.btn_capturar = wx.Button(panel, wx.ID_OK, _("Captu&rar"), name=_("Capturar"))
        self.btn_capturar.SetDefault()
        self._fijar_motivo(TEXTO_CARGANDO_MOTIVO)
        self.btn_cancelar = wx.Button(panel, wx.ID_CANCEL, _("Ca&ncelar"), name=_("Cancelar"))
        formulario.agregar_pie(vs, [self.btn_capturar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, vs)
        self._temporizador = wx.Timer(self)
        self.cho_fuente.Bind(wx.EVT_CHOICE, self._al_elegir)
        self.btn_capturar.Bind(wx.EVT_BUTTON, self._al_capturar)
        self.btn_cancelar.Bind(wx.EVT_BUTTON, self._al_cancelar)
        self.Bind(wx.EVT_TIMER, self._al_temporizador, self._temporizador)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Bind(wx.EVT_CLOSE, self._al_cerrar)
        self.cho_fuente.SetFocus()
        self._cargar_opciones()

    @property
    def resultado(self):
        return self._resultado

    def _terminar(self, codigo) -> None:
        self._cerrado = True
        self._espera_del_cuadro().detener()
        try:
            self._temporizador.Stop()
        except Exception as error:
            logger.warning("AgregarCaptura: no se pudo frenar el aviso: %s",
                           error)
        self.EndModal(codigo)

    def _al_cerrar(self, event) -> None:
        if self._cerrado:
            event.Skip()
            return
        self._terminar(wx.ID_CANCEL)

    def _al_tecla(self, event) -> None:
        if tecla_escape.es_escape(event.GetKeyCode()):
            self._terminar(wx.ID_CANCEL)
            return
        event.Skip()

    def _al_cancelar(self, _event) -> None:
        self._terminar(wx.ID_CANCEL)

    def _opcion_elegida(self):
        indice = self.cho_fuente.GetSelection()
        if 0 <= indice < len(self._opciones):
            return self._opciones[indice]
        return None

    def _espera_del_cuadro(self):
        if not hasattr(self, "_espera"):
            self._espera = EsperaSonora(self)
        return self._espera

    def _fijar_motivo(self, motivo) -> None:
        self._motivo = motivo
        if motivo in (TEXTO_CARGANDO_MOTIVO, TEXTO_CAPTURANDO):
            self._espera_del_cuadro().empezar()
        self.btn_capturar.SetLabel(redaccion.etiqueta_con_motivo(
            _("Captu&rar"), _(motivo) if motivo else ""))

    def _cargar_opciones(self) -> None:
        paleta.pintar_ventana(self)

        def _trabajo():
            try:
                with self._cerrojo:
                    opciones = ia_captura_video.con_fotograma(
                        obs_captura_ia.opciones(self._cliente),
                        self._reproductor)
            except Exception as error:
                logger.warning("AgregarCaptura: no se pudo listar: %s", error)
                wx.CallAfter(self._opciones_fallaron, error)
                return
            wx.CallAfter(self._opciones_listas, opciones)

        diagnostico.crear_hilo(_trabajo, "AgregarCapturaOpciones").start()

    def _opciones_listas(self, opciones) -> None:
        if self._cerrado:
            return
        self._opciones = tuple(opciones)
        self.cho_fuente.Clear()
        for opcion in self._opciones:
            self.cho_fuente.Append(opcion.etiqueta)
        if self._opciones:
            self.cho_fuente.SetSelection(0)
        self._fijar_motivo("" if self._opciones else TEXTO_SIN_FUENTES)
        self._espera_del_cuadro().terminar("listo")
        self._programar_vista_previa()

    def _opciones_fallaron(self, error) -> None:
        if self._cerrado:
            return
        anunciar(obs_cliente.mensaje_de_fallo_obs(error))
        reproducir("ia_error")
        self._espera_del_cuadro().terminar(None)
        self._terminar(wx.ID_CANCEL)

    def _al_elegir(self, _event) -> None:
        self._programar_vista_previa()

    def _programar_vista_previa(self) -> None:
        if self._cerrado or not self._opciones:
            return
        self._generacion_vista += 1
        self._temporizador.Stop()
        self._temporizador.Start(400, True)

    def _al_temporizador(self, _event) -> None:
        opcion = self._opcion_elegida()
        if opcion is None or self._cerrado:
            return
        generacion = self._generacion_vista

        def _trabajo():
            try:
                with self._cerrojo:
                    jpeg = ia_captura_video.vista_previa(
                        self._cliente, opcion, self._reproductor)
            except Exception as error:
                logger.warning("AgregarCaptura: sin vista previa: %s", error)
                wx.CallAfter(self._vista_fallida, generacion)
                return
            wx.CallAfter(self._vista_lista, generacion, jpeg)

        diagnostico.crear_hilo(_trabajo, "AgregarCapturaVista").start()

    def _vista_lista(self, generacion, jpeg) -> None:
        if self._cerrado or generacion != self._generacion_vista:
            return
        try:
            imagen = wx.Image(io.BytesIO(jpeg))
        except Exception as error:
            logger.warning("AgregarCaptura: vista previa rota: %s", error)
            return
        ancho = imagen.GetWidth()
        alto = imagen.GetHeight()
        if ancho <= 0 or alto <= 0:
            return
        factor = min(ANCHO_VISTA / ancho, ALTO_VISTA / alto)
        if factor < 1:
            nuevo = (max(1, int(ancho * factor)),
                     max(1, int(alto * factor)))
            imagen = imagen.Scale(nuevo[0], nuevo[1], wx.IMAGE_QUALITY_HIGH)
        try:
            self.bmp_vista.SetBitmap(wx.Bitmap(imagen))
        except Exception as error:
            logger.warning("AgregarCaptura: no se pudo mostrar: %s", error)

    def _vista_fallida(self, generacion) -> None:
        if self._cerrado or generacion != self._generacion_vista:
            return
        try:
            self.bmp_vista.SetBitmap(wx.NullBitmap)
        except Exception as error:
            logger.warning("AgregarCaptura: no se pudo vaciar: %s", error)

    def _al_capturar(self, _event) -> None:
        if self._motivo:
            anunciar(f"{_(self._motivo)}.")
            return
        opcion = self._opcion_elegida()
        if opcion is None:
            return
        self._fijar_motivo(TEXTO_CAPTURANDO)

        def _trabajo():
            try:
                with self._cerrojo:
                    captura = ia_captura_video.capturar(
                        self._cliente, opcion, self._reproductor)
            except obs_captura_ia.CapturaFallida as error:
                wx.CallAfter(self._captura_fallida, str(error))
                return
            except Exception as error:
                logger.warning("AgregarCaptura: fallo al capturar: %s", error)
                wx.CallAfter(self._captura_fallida,
                             obs_cliente.mensaje_de_fallo_obs(error))
                return
            wx.CallAfter(self._captura_lista, opcion, captura)

        diagnostico.crear_hilo(_trabajo, "AgregarCapturaCapturar").start()

    def _captura_fallida(self, mensaje) -> None:
        if self._cerrado:
            return
        anunciar(mensaje)
        reproducir("ia_error")
        self._espera_del_cuadro().terminar(None)
        self._fijar_motivo("")
        self.cho_fuente.SetFocus()

    def _captura_lista(self, opcion, captura) -> None:
        if self._cerrado:
            return
        if captura.negra is True:
            anunciar(texto_negra(opcion.etiqueta, captura.motivo,
                                 captura.fuente_motivo))
            reproducir("ia_imagen_negra")
            self._espera_del_cuadro().terminar(None)
            self._fijar_motivo("")
            self.cho_fuente.SetFocus()
            return
        self._resultado = (opcion.fuente, captura)
        self._espera_del_cuadro().terminar("listo")
        self._terminar(wx.ID_OK)


def _cerrar(cliente) -> None:
    try:
        cliente.cerrar()
    except Exception as fallo:
        logger.warning("AgregarCaptura: no se pudo cerrar: %s", fallo)


def _mostrar(padre, cliente, al_terminar, reproductor) -> None:
    dialogo = DialogoAgregarCaptura(padre, cliente, reproductor)
    try:
        if dialogo.ShowModal() == wx.ID_OK and dialogo.resultado:
            al_terminar(dialogo.resultado)
        else:
            al_terminar(None)
    finally:
        try:
            dialogo.Destroy()
        except Exception as fallo:
            logger.warning("AgregarCaptura: no se pudo destruir: %s", fallo)
        _cerrar(cliente)


def _sin_obs(padre, al_terminar) -> None:
    """Toma el fotograma del reproductor sin abrir ningún cuadro."""
    reproductor = fotograma_video.reproductor_de(padre.GetParent())
    if not fotograma_video.muestra_video(reproductor):
        anunciar(_(ia_captura_video.TEXTO_SIN_VIDEO))
        reproducir("ia_error")
        al_terminar(None)
        return
    opcion = ia_captura_video.opcion_fotograma()

    def _trabajo():
        try:
            captura = ia_captura_video.capturar(None, opcion, reproductor)
        except obs_captura_ia.CapturaFallida:
            wx.CallAfter(anunciar, _(ia_captura_video.TEXTO_FOTOGRAMA_FALLIDO))
            wx.CallAfter(reproducir, "ia_error")
            wx.CallAfter(al_terminar, None)
            return
        wx.CallAfter(al_terminar, (opcion.fuente, captura))

    diagnostico.crear_hilo(_trabajo, "AgregarCapturaFotograma").start()


def pedir_captura(padre, al_terminar) -> None:
    """Pide una captura sin bloquear. Llama a `al_terminar`.

    El resultado es `(fuente, captura)` o None, en el hilo de la interfaz.
    """
    if not obs_activacion.obs_esta_en_ejecucion():
        _sin_obs(padre, al_terminar)
        return
    reproductor = fotograma_video.reproductor_de(padre.GetParent())
    cliente = obs_cliente.ClienteObs(obs_cliente.leer_ajustes())

    def _conexion_fallida(error) -> None:
        anunciar(obs_cliente.mensaje_de_fallo_obs(error))
        reproducir("ia_error")
        _cerrar(cliente)
        al_terminar(None)

    def _conexion_lista() -> None:
        _mostrar(padre, cliente, al_terminar, reproductor)

    def _trabajo():
        try:
            cliente.conectar()
        except Exception as error:
            logger.warning("AgregarCaptura: no se pudo conectar: %s", error)
            wx.CallAfter(_conexion_fallida, error)
            return
        wx.CallAfter(_conexion_lista)

    diagnostico.crear_hilo(_trabajo, "AgregarCapturaConectar").start()
