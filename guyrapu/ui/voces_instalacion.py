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

def titulo(accion, cantidad, nombre=""):
    """El título de la espera: el nombre si es uno, la cuenta si son varios."""
    if cantidad == 1:
        return (_("Instalar {nombre}") if accion == "instalar"
                else _("Actualizar {nombre}")).format(nombre=nombre)
    if accion == "instalar":
        return ngettext("Instalar {n} paquete de voces",
                        "Instalar {n} paquetes de voces", cantidad).format(
                            n=cantidad)
    return ngettext("Actualizar {n} paquete de voces",
                    "Actualizar {n} paquetes de voces", cantidad).format(
                        n=cantidad)


def texto_descarga(nombre, indice, cantidad):
    """El estado antes de cada paquete, con su puesto en el lote."""
    if cantidad == 1:
        return _("Descargando {nombre}.").format(nombre=nombre)
    return _("Descargando {nombre}, {i} de {n}.").format(
        nombre=nombre, i=indice, n=cantidad)


def texto_final(cantidad, correctas, fallidos, cancelada, accion, nombre):
    """El único texto al terminar y su sonido, como hoy si es uno solo."""
    actualizar = accion == "actualizar"
    if cancelada:
        return ((_("Actualización cancelada.") if actualizar
                 else _("Instalación cancelada.")), None)
    if cantidad == 1:
        if correctas:
            frase = (_("Actualización completada: {nombre}.")
                     if actualizar
                     else _("Instalación completada: {nombre}."))
            return frase.format(nombre=nombre), "listo"
        motivo = fallidos[0][1] if fallidos else ""
        return (_("No se pudo instalar {nombre}: {motivo}. Revisa la "
                  "conexión a internet y vuelve a intentarlo.").format(
                      nombre=nombre,
                      motivo=motivo or _("motivo desconocido")), "error")
    if not fallidos:
        frase = (ngettext("{n} paquete actualizado.",
                          "{n} paquetes actualizados.", cantidad)
                 if actualizar else
                 ngettext("{n} paquete instalado.",
                          "{n} paquetes instalados.", cantidad))
        return frase.format(n=cantidad), "listo"
    nombres = ", ".join(nombre for nombre, _motivo in fallidos)
    frase = (_("{ok} de {n} paquetes actualizados. No se pudo actualizar: "
               "{nombres}.") if actualizar else
             _("{ok} de {n} paquetes instalados. No se pudo instalar: "
               "{nombres}."))
    return frase.format(ok=correctas, n=cantidad, nombres=nombres), "error"


def empezar(paquetes, accion, crear_espera, poner_espera, al_progreso,
            al_preparar, al_terminar):
    """Instala los paquetes en orden en un hilo, con una sola espera."""
    parada = threading.Event()
    cantidad = len(paquetes)
    primer_nombre = voces_disponibles.nombre(paquetes[0])
    nombre = primer_nombre if cantidad == 1 else ""
    titulo_ = titulo(accion, cantidad, nombre)
    espera = crear_espera(
        titulo_, texto_descarga(primer_nombre, 1, cantidad), parada)
    poner_espera(espera)
    def trabajar():
        correctas = 0
        fallidos = []
        cancelada = False
        for indice, paquete in enumerate(paquetes, 1):
            if parada.is_set():
                cancelada = True
                break
            nombre_paquete = voces_disponibles.nombre(paquete)
            wx.CallAfter(espera.estado,
                         texto_descarga(nombre_paquete, indice, cantidad))
            wx.CallAfter(al_preparar)
            def aviso(porcentaje, nombre=nombre_paquete):
                wx.CallAfter(al_progreso, porcentaje, nombre)
            resultado = paquetes_instalacion.instalar(
                paquete.catalogo, aviso, parada.is_set)
            if resultado.cancelada:
                cancelada = True
                break
            if resultado.correcta:
                correctas += 1
            else:
                fallidos.append((nombre_paquete, resultado.motivo))
        texto, sonido = texto_final(
            cantidad, correctas, fallidos, cancelada, accion, nombre)
        wx.CallAfter(al_terminar, texto, sonido)
    diagnostico.crear_hilo(trabajar, titulo_).start()
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

def terminar_instalacion(espera, texto, sonido):
    if espera is None:
        return
    try:
        espera.terminar(texto, error=sonido == "error")
        if sonido:
            _snd.reproducir(sonido)
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
    if len(entradas) == 1:
        anunciar(_("Paquete eliminado: {nombre}.").format(
            nombre=voces_disponibles.nombre(entradas[0])))
    else:
        anunciar(ngettext("{n} paquete eliminado.", "{n} paquetes eliminados.",
                          len(entradas)).format(n=len(entradas)))
    al_cambiar(entradas[0], indice)
    return True
