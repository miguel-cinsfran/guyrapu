# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pedirle a la IA una descripción del archivo de un medio.

Lee la imagen o el primer cuadro del GIF, la manda como JPEG y devuelve la
respuesta limpia al cuadro del medio. La espera es la común, con Cancelar.
"""

from __future__ import annotations

import io
import threading
from datetime import datetime

import wx

from guyrapu.ai import ajustes_ia
from guyrapu.ai import catalogo
from guyrapu.ai import claves
from guyrapu.ai import consulta
from guyrapu.ai import conversacion
from guyrapu.ai import descripcion_medio
from guyrapu.ai import envio_ia
from guyrapu.ai import proveedores
from guyrapu.ai import ventana_ia
from guyrapu.core import diagnostico
from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.ui import confirmar as confirmaciones
from guyrapu.ui import ia_privacidad
from guyrapu.ui.ventana_espera import VentanaEspera
from guyrapu.voice.sound_player import reproducir

logger = diagnostico.obtener_logger(__name__)

# Traductores: título de la espera mientras la IA propone la descripción.
TITULO_ESPERA = N_("Describir imagen")
# Traductores: texto inicial de la espera mientras la IA propone la descripción.
TEXTO_ESPERA = N_("Pidiendo la descripción a la IA…")
INTERVALO_CANCELACION_MS = 100


def jpeg_de(ruta) -> bytes:
    """El archivo como JPEG en memoria; de un GIF, su primer cuadro."""
    imagen = wx.Image(str(ruta), wx.BITMAP_TYPE_ANY)
    salida = io.BytesIO()
    imagen.SaveFile(salida, wx.BITMAP_TYPE_JPEG)
    return salida.getvalue()


def pedir(padre, ruta, al_listo) -> None:
    """Pide la descripción del archivo y se la pasa a `al_listo`, ya limpia."""
    charla = conversacion.Conversacion()
    charla.agregar_captura(jpeg_de(ruta), _("Imagen"),
                           ventana_ia.hora_de(datetime.now()))
    ajustes = ajustes_ia.leer(paths.config_ini())
    muestra = catalogo.cargar(paths.catalogo_ia(),
                              paths.catalogo_ia_empaquetado())
    try:
        clave = claves.leer(ajustes.proveedor)
    except OSError as fallo:
        logger.warning("Descripción de medio: sin clave: %s", fallo)
        clave = None
    try:
        preparada = consulta.preparar(
            charla, _(descripcion_medio.PREGUNTA), ajustes, muestra, clave, "")
    except consulta.FaltaConfiguracion as fallo:
        _avisar_error(padre, fallo)
        return
    proveedor = proveedores.por_id(ajustes.proveedor)
    if proveedor is None:
        proveedor = proveedores.PROVEEDORES[0]
    if not ia_privacidad.confirmar(padre, ajustes, proveedor.nombre):
        return
    reproducir("ia_enviada")
    _esperar(padre, preparada, clave, al_listo)


def _esperar(padre, preparada, clave, al_listo) -> None:
    parada = threading.Event()
    espera = VentanaEspera(padre, _(TITULO_ESPERA), _(TEXTO_ESPERA),
                           parada=parada)
    resultado = {}

    def revisar(_evento):
        if parada.is_set():
            espera.EndModal(wx.ID_CANCEL)

    temporizador = wx.Timer(espera)
    espera.Bind(wx.EVT_TIMER, revisar, temporizador)
    temporizador.Start(INTERVALO_CANCELACION_MS)

    def terminar(valor):
        resultado["valor"] = valor
        try:
            espera.EndModal(wx.ID_OK)
        except RuntimeError as fallo:
            logger.debug("la espera ya no existe: %s", fallo)

    def enviar():
        try:
            respuesta = envio_ia.enviar(preparada.pedido, clave,
                                        preparada.tiempo_espera)
        except Exception as fallo:
            wx.CallAfter(terminar, fallo)
            return
        wx.CallAfter(terminar, respuesta)

    diagnostico.crear_hilo(enviar, "DescripcionMedioIA").start()
    try:
        espera.ShowModal()
    finally:
        temporizador.Stop()
        espera.Destroy()
    valor = resultado.get("valor")
    if parada.is_set() or valor is None:
        return
    if isinstance(valor, Exception):
        _avisar_error(padre, valor)
        return
    reproducir("ia_respuesta")
    al_listo(descripcion_medio.limpiar(valor.texto))


def _avisar_error(padre, fallo) -> None:
    try:
        detalle = fallo.detalle
    except AttributeError:
        detalle = str(fallo)
    logger.warning("Descripción de medio: falló la consulta: %s", detalle)
    reproducir("ia_error")
    confirmaciones.avisar(
        padre, consulta.texto_de_error(fallo), _("Error"), _("Aceptar"),
        icono=confirmaciones.ICON_ERROR)
