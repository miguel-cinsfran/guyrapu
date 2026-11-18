# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página única de descargas del administrador.

Muestra en una sola lista lo que está en curso, lo que espera y lo
terminado, con filtro, menú contextual y acciones por fila.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.downloads import filas_descargas
from guyrapu.downloads import historial_descargas
from guyrapu.ui import aviso_progreso
from guyrapu.ui import barra_progreso
from guyrapu.ui.descargas_acciones import AccionesDescarga
from guyrapu.ui.gui import nombre_accesible, _T, _tc
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones

_ESTADOS_FINALES = ("completado", "parcial", "cancelado", "error")
_ETIQUETAS_ESTADO = {"en_cola": N_("en cola"), "descargando": N_("descargando"),
                     "completado": N_("completado"), "parcial": N_("con errores"),
                     "cancelado": N_("cancelado"), "error": N_("error")}


def _texto_estado(estado: str, mensaje: str) -> str:
    """Celda «Estado» de lo terminado: el motivo acompaña al estado."""
    texto = _(_ETIQUETAS_ESTADO.get(estado, estado)) if estado else ""
    if mensaje and estado in _ESTADOS_FINALES:
        texto = _("{estado}: {mensaje}").format(estado=texto, mensaje=mensaje[:80])
    return texto[:200]


def _formatear_velocidad(velocidad) -> str:
    """«850 KB/s» o «3 MB/s», sin decimales porque el lector los lee mal."""
    if not velocidad or velocidad <= 0:
        return ""
    if velocidad < 1024 * 1024:
        return f"{round(velocidad / 1024):.0f} KB/s"
    return f"{round(velocidad / (1024 * 1024)):.0f} MB/s"


def _formatear_tiempo(eta) -> str:
    """«quedan 2 minutos», «queda 1 minuto» o «quedan 45 segundos»."""
    if not eta:
        return ""
    segundos = max(0, int(eta))
    if segundos >= 60:
        minutos = int(round(segundos / 60))
        if minutos <= 1:
            return _("queda 1 minuto")
        return _("quedan {n} minutos").format(n=minutos)
    segundos = int(round(segundos / 5)) * 5
    if segundos <= 0:
        return ""
    return _("quedan {n} segundos").format(n=segundos)


def texto_de_item(item) -> str:
    """Celda «Estado» de un ítem activo: estado, vídeo, velocidad y tiempo."""
    if item.estado != "descargando":
        return _texto_estado(item.estado, item.mensaje)
    partes = [_("procesando") if item.procesando
              else _(_ETIQUETAS_ESTADO.get(item.estado, item.estado))]
    if item.total > 1:
        partes.append(_("vídeo {indice} de {total}").format(
            indice=item.indice, total=item.total))
    if not item.procesando:
        velocidad = _formatear_velocidad(item.velocidad)
        if velocidad:
            partes.append(velocidad)
        tiempo = _formatear_tiempo(item.eta)
        if tiempo:
            partes.append(tiempo)
    return ", ".join(partes)[:200]


_FILTROS_ORDEN = (filas_descargas.TODAS, filas_descargas.EN_CURSO,
                 filas_descargas.EN_ESPERA, filas_descargas.COMPLETADAS,
                 filas_descargas.CON_ERRORES)


def _texto_filtro(filtro: str, cantidad: int) -> str:
    if filtro == filas_descargas.EN_CURSO:
        return _("En curso ({cantidad})").format(cantidad=cantidad)
    if filtro == filas_descargas.EN_ESPERA:
        return _("En espera ({cantidad})").format(cantidad=cantidad)
    if filtro == filas_descargas.COMPLETADAS:
        return _("Completadas ({cantidad})").format(cantidad=cantidad)
    if filtro == filas_descargas.CON_ERRORES:
        return _("Con errores ({cantidad})").format(cantidad=cantidad)
    return _("Todas ({cantidad})").format(cantidad=cantidad)


def _texto_progreso(fila) -> str:
    if fila.estado in ("descargando", "en_cola"):
        return f"{fila.progreso:.0f} %"
    if fila.estado == "completado":
        return "100 %"
    return ""


def _texto_estado_fila(fila) -> str:
    if fila.estado in ("descargando", "en_cola") and fila.item is not None:
        return texto_de_item(fila.item)
    return _texto_estado(fila.estado, fila.mensaje)


def _celdas(fila) -> tuple:
    return (_texto_progreso(fila), _texto_estado_fila(fila),
            (fila.nombre or "")[:300],
            filas_descargas.fecha_legible(fila.fecha))


def _motivo_de(pagina, clave) -> str:
    fila = pagina._fila_elegida()
    return filas_descargas.motivo(fila, clave) if fila is not None else ""


def _acciones(pagina):
    orden = (("abrir_archivo", _("&Abrir archivo"), "intro"),
             ("abrir_carpeta", _("Abrir car&peta"), None),
             ("cancelar", _("&Cancelar descarga"), None),
             ("reintentar", _("&Reintentar"), None),
             ("volver_a_descargar", _("&Volver a descargar"), None),
             ("copiar", _("Copiar &enlace"), None),
             ("eliminar", _("E&liminar de la lista"), "suprimir"))
    acciones = [
        Accion(clave, etiqueta, getattr(pagina, clave), tecla=tecla,
               motivo=lambda clave=clave: _motivo_de(pagina, clave))
        for clave, etiqueta, tecla in orden]
    acciones.append(Accion("cancelar_todas", _("Cancelar &todas"),
                           pagina.cancelar_todas, necesita_elemento=False))
    acciones.append(Accion("eliminar_completadas", _("Eliminar c&ompletadas"),
                           pagina.eliminar_completadas,
                           necesita_elemento=False))
    return tuple(acciones)


class PaginaDescargas(wx.Panel):
    """Lista única de descargas, con filtro y menú contextual."""

    def __init__(self, parent, gestor, ruta, preparar_opciones):
        super().__init__(parent)
        self._gestor = gestor
        self._ruta = ruta
        aviso_progreso.vigilar()
        self._acciones = AccionesDescarga(
            gestor, ruta, preparar_opciones, self._tras_cambiar)
        self._historial = historial_descargas.cargar(self._ruta)
        self._filas: list = []
        self._filtro = filas_descargas.TODAS
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(self._seccion_filtro(), 0, wx.EXPAND | wx.ALL, 8)
        vs.Add(self._seccion_lista(), 1, wx.EXPAND | wx.ALL, 8)
        vs.Add(self._seccion_botones(), 0, wx.ALL, 8)
        self.SetSizer(vs)
        self.refrescar()

    def _seccion_filtro(self):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(self, label=_("&Mostrar:"), name="EtiquetaMostrar")
        lbl.SetForegroundColour(_T.text)
        fila.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.cho_mostrar = wx.Choice(
            self, choices=[_texto_filtro(f, 0) for f in _FILTROS_ORDEN],
            name=_("Mostrar"))
        _tc(self.cho_mostrar)
        self.cho_mostrar.SetSelection(0)
        self.cho_mostrar.Bind(wx.EVT_CHOICE, self._on_filtro)
        fila.Add(self.cho_mostrar, 1, wx.EXPAND)
        return fila

    def _seccion_lista(self):
        self.lista = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
                                 name="ListaDescargas")
        nombre_accesible(self.lista, _("Lista de descargas"))
        self.lista.AssignImageList(
            barra_progreso.lista_de_imagenes(self.lista.GetBackgroundColour()),
            wx.IMAGE_LIST_SMALL)
        self.lista.InsertColumn(0, _("Progreso"), width=120)
        self.lista.InsertColumn(1, _("Estado"), width=160)
        self.lista.InsertColumn(2, _("Nombre"), width=320)
        self.lista.InsertColumn(3, _("Fecha"), width=140)
        self._lista_acciones = ListaConAcciones(
            self.lista, _acciones(self), _("No hay descargas en esta vista."))
        return self.lista

    def _seccion_botones(self):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cancelar = wx.Button(self, label=_("C&ancelar descarga"),
                                      name="CancelarDescarga")
        self.btn_cancelar.Bind(wx.EVT_BUTTON, self._on_cancelar)
        fila.Add(self.btn_cancelar, 0, wx.RIGHT, 8)
        self.btn_vaciar = wx.Button(self, label=_("Vaciar l&ista"),
                                    name="VaciarLista")
        self.btn_vaciar.Bind(wx.EVT_BUTTON, self._on_vaciar)
        fila.Add(self.btn_vaciar, 0)
        for boton in (self.btn_cancelar, self.btn_vaciar):
            boton.SetBackgroundColour(_T.btn)
            boton.SetForegroundColour(_T.btn_t)
        return fila

    def _on_filtro(self, _event):
        idx = self.cho_mostrar.GetSelection()
        if 0 <= idx < len(_FILTROS_ORDEN):
            self._filtro = _FILTROS_ORDEN[idx]
        self.refrescar()

    def refrescar(self) -> None:
        """Pone al día las filas sin mover el foco ni la selección."""
        todas = filas_descargas.construir(self._gestor.lista(), self._historial)
        self._actualizar_choice(filas_descargas.cantidades(todas))
        filtradas = filas_descargas.filtrar(todas, self._filtro)
        claves = [f.clave for f in filtradas]
        self._lista_acciones.poner_al_dia(
            claves, [_celdas(f) for f in filtradas])
        self._filas = filtradas
        self._actualizar_imagenes(filtradas)

    def _tras_cambiar(self) -> None:
        self._historial = historial_descargas.cargar(self._ruta)
        self.refrescar()

    def _actualizar_choice(self, cantidades: dict) -> None:
        for i, filtro in enumerate(_FILTROS_ORDEN):
            texto = _texto_filtro(filtro, cantidades.get(filtro, 0))
            if self.cho_mostrar.GetString(i) != texto:
                self.cho_mostrar.SetString(i, texto)

    def _actualizar_imagenes(self, filtradas: list) -> None:
        for i, fila in enumerate(filtradas):
            imagen = barra_progreso.tramo(fila.estado, fila.progreso)
            actual = self.lista.GetItem(i).GetImage()
            if (imagen != -1 or actual >= 0) and actual != imagen:
                self.lista.SetItemImage(i, imagen)

    def agregar_enlace(self, url: str) -> None:
        """Encola sin fila optimista: sale en el refresco."""
        self._gestor.encolar(url, lambda *_a: None, lambda *_a: None)
        self.refrescar()

    def agregar_entrada(self, _entrada: dict) -> None:
        """Refleja una entrada recién persistida."""
        self._historial = historial_descargas.cargar(self._ruta)
        self.refrescar()

    def _fila_elegida(self):
        idx = self.lista.GetFirstSelected()
        if idx < 0 or idx >= len(self._filas):
            return None
        return self._filas[idx]

    def abrir_archivo(self) -> None:
        self._acciones.abrir_archivo(self._fila_elegida())

    def abrir_carpeta(self) -> None:
        self._acciones.abrir_carpeta(self._fila_elegida())

    def reintentar(self) -> None:
        self._acciones.reintentar(self._fila_elegida())

    def volver_a_descargar(self) -> None:
        self._acciones.volver_a_descargar(self._fila_elegida())

    def copiar(self) -> None:
        self._acciones.copiar(self._fila_elegida())

    def cancelar(self) -> None:
        self._acciones.cancelar(self._fila_elegida())

    def eliminar(self) -> None:
        self._acciones.eliminar(self._fila_elegida())

    def cancelar_todas(self) -> None:
        self._acciones.cancelar_todas()

    def eliminar_completadas(self) -> None:
        self._acciones.eliminar_completadas()

    def _on_cancelar(self, _event):
        self._acciones.cancelar(self._fila_elegida())

    def _on_vaciar(self, _event) -> None:
        self._acciones.vaciar(self)
