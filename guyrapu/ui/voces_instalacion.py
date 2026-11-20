# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Instalar, actualizar y eliminar paquetes desde Administrar voces."""
from __future__ import annotations
import threading
import wx
from guyrapu.core import diagnostico, paquetes_instalacion, voces_disponibles
from guyrapu.core.idioma import _, ngettext, pgettext
from guyrapu.ui import confirmar
from guyrapu.voice import sound_player as _snd
logger = diagnostico.obtener_logger(__name__)

def empezar(paquete, accion, nombre, crear_espera, poner_espera,
            al_progreso, al_terminar):
    parada = threading.Event()
    titulo = (_("Instalar {nombre}") if accion == "instalar"
              else _("Actualizar {nombre}")).format(nombre=nombre)
    espera = crear_espera(
        titulo, _("Descargando {nombre}.").format(nombre=nombre), parada)
    poner_espera(espera)
    def aviso(porcentaje):
        wx.CallAfter(al_progreso, porcentaje, nombre)
    def trabajar():
        resultado = paquetes_instalacion.instalar(paquete, aviso, parada.is_set)
        wx.CallAfter(al_terminar, resultado, accion, nombre)
    diagnostico.crear_hilo(trabajar, titulo).start()
    try:
        espera.ShowModal()
    finally:
        espera.Destroy()
        poner_espera(None)

def aviso_porcentaje(espera, ultimo, porcentaje, nombre):
    if porcentaje is None or porcentaje == ultimo:
        return ultimo
    if (ultimo is not None and porcentaje < ultimo + 10
            and porcentaje != 100):
        return ultimo
    if espera is not None:
        try:
            espera.estado(
                _("Descargando {nombre}: {porcentaje} por ciento").format(
                    nombre=nombre, porcentaje=porcentaje))
        except RuntimeError as error:
            logger.debug("la espera ya no existe: %s", error)
    return porcentaje

def terminar_instalacion(espera, resultado, accion, nombre):
    if espera is None:
        return
    try:
        if resultado.cancelada:
            espera.terminar(_("Instalación cancelada."))
        elif resultado.correcta:
            frase = (_("Actualización completada: {nombre}.")
                     if accion == "actualizar"
                     else _("Instalación completada: {nombre}."))
            espera.terminar(frase.format(nombre=nombre))
            _snd.reproducir("listo")
        else:
            espera.terminar(
                _("No se pudo instalar {nombre}: {motivo}. Revisa la "
                  "conexión a internet y vuelve a intentarlo.").format(
                      nombre=nombre,
                      motivo=resultado.motivo or _("motivo desconocido")),
                error=True)
    except RuntimeError as error:
        logger.debug("la espera ya no existe: %s", error)

def eliminar(padre, entradas, indice, anunciar, error, al_cambiar):
    """Elimina los paquetes elegidos con una sola confirmación."""
    for entrada in entradas:
        if entrada.instalado is None:
            anunciar(_("{nombre} no está instalado.").format(
                nombre=voces_disponibles.nombre(entrada)))
            return False
    if len(entradas) == 1:
        pregunta = _(
            "¿Eliminar {nombre}? Se liberan {tamano} del disco. Para "
            "volver a usarlo, hay que instalarlo de nuevo.").format(
                nombre=voces_disponibles.nombre(entradas[0]),
                tamano=voces_disponibles.tamano(entradas[0]))
    else:
        pregunta = ngettext(
            "¿Eliminar {n} paquete de voces? Para volver a usarlos, hay "
            "que instalarlos de nuevo.",
            "¿Eliminar {n} paquetes de voces? Para volver a usarlos, hay "
            "que instalarlos de nuevo.", len(entradas)).format(n=len(entradas))
    if not confirmar.preguntar(
            padre, pregunta, _("Eliminar paquete de voces"),
            pgettext("paquete de voces", "&Eliminar"), _("&Cancelar"),
            predeterminado_si=False):
        return False
    for entrada in entradas:
        nombre = voces_disponibles.nombre(entrada)
        resultado = paquetes_instalacion.borrar(
            voces_disponibles.identificador(entrada), "voz")
        if not resultado.correcta:
            error(_("No se pudo eliminar {nombre}: {motivo}.").format(
                nombre=nombre,
                motivo=resultado.motivo or _("motivo desconocido")))
            return False
        anunciar(_("Paquete eliminado: {nombre}.").format(nombre=nombre))
    al_cambiar(entradas[0], indice)
    return True
