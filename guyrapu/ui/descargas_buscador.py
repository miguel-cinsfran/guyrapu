# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pestaña de búsqueda en YouTube: un campo que busca o encola.

La búsqueda corre en un hilo y una nueva descarta la anterior.
"""

from __future__ import annotations

import time

import wx

from guyrapu.core.idioma import _
from guyrapu.downloads import busqueda_youtube
from guyrapu.downloads.busqueda_youtube import (
    CANTIDAD_DEFECTO, Filtros, clasificar_entrada, es_enlace_de_lista, ordenar)
from guyrapu.downloads.textos_busqueda import (
    texto_detalles, texto_duracion, texto_fecha, texto_vistas)
from guyrapu.downloads import busquedas_recientes
from guyrapu.ui.accesibilidad import anunciar, entregar_intro, nombre_accesible
from guyrapu.ui.aviso_importante import avisar
from guyrapu.ui import buscador_acciones, buscador_escucha, buscador_lista
from guyrapu.ui.buscador_acciones import AccionesResultado
from guyrapu.ui import buscador_contenido
from guyrapu.ui import buscador_tandas
from guyrapu.ui.buscador_filtros import FiltrosBusqueda
from guyrapu.ui.lista_acciones import ListaConAcciones
from guyrapu.ui.tema import boton_principal

_CANTIDADES = tuple(str(n) for n in busqueda_youtube.CANTIDADES)


def _celdas(resultados) -> list:
    """Las celdas de la lista, una tupla por resultado."""
    ahora = time.time()
    return [(r.titulo, r.canal, texto_duracion(r.duracion),
             texto_vistas(r.vistas), texto_fecha(r.marca_tiempo, ahora))
            for r in resultados]


class PaginaBuscador(wx.Panel):
    """La pestaña de búsqueda, con su estado."""

    def __init__(self, parent, agregar_urls, ruta_recientes,
                 abrir_en_app=None, musica=None):
        super().__init__(parent)
        self._agregar_urls = agregar_urls
        self._abrir_en_app = abrir_en_app
        self._escucha = buscador_escucha.EscuchaBuscador(musica)
        self._acciones = AccionesResultado(
            agregar_urls, abrir_en_app, self._escucha.agregar_musica)
        self._ruta = ruta_recientes
        self._recientes = busquedas_recientes.cargar(ruta_recientes)
        self._resultados = []
        self._texto = ""
        self._filtros = Filtros()
        self._cantidad = CANTIDAD_DEFECTO
        self._inicio = 1
        self._generacion = 0
        self._crear_controles()
        self._tandas = buscador_tandas.Tandas(self.lista, self.btn_mas)
        self._vista = buscador_contenido.VistaContenido(
            self, self._sincronizar_contenido, self._restaurar_vista,
            self._agregar_urls, self._cantidad_actual)
        self.btn_volver.Bind(wx.EVT_BUTTON, self._vista.volver)
        self.btn_todo.Bind(wx.EVT_BUTTON, self._vista.todo)
        self._cargar_opciones()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        self._crear_campo(vs)
        self._crear_filtros(vs)
        self._crear_lista(vs)
        self._crear_pie(vs)
        self.SetSizer(vs)

    def _crear_campo(self, vs):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(self, label=_("B&uscar o pegar enlace:"))
        fila.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.campo = wx.ComboBox(
            self, style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
            name=_("Buscar o pegar enlace"))
        self.campo.Bind(wx.EVT_TEXT_ENTER, self._on_buscar)
        fila.Add(self.campo, 1, wx.EXPAND)
        self.btn_buscar = wx.Button(self, label=_("&Buscar"), name="BuscarYoutube")
        boton_principal(self.btn_buscar)
        self.btn_buscar.Bind(wx.EVT_BUTTON, self._on_buscar)
        fila.Add(self.btn_buscar, 0, wx.LEFT, 8)
        vs.Add(fila, 0, wx.EXPAND | wx.ALL, 8)
        self.filtros = FiltrosBusqueda(self, self._on_orden)
        self.filtros.chk_filtros.Bind(wx.EVT_CHECKBOX, self._on_filtros)
        vs.Add(self.filtros.chk_filtros, 0, wx.ALL, 8)

    def _crear_filtros(self, vs):
        vs.Add(self.filtros.sizer, 0, wx.EXPAND | wx.ALL, 8)
        fila_cantidad = wx.BoxSizer(wx.HORIZONTAL)
        lbl_cantidad = wx.StaticText(self, label=_("Ca&ntidad:"))
        fila_cantidad.Add(lbl_cantidad, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.cho_cantidad = wx.Choice(self, choices=list(_CANTIDADES),
                                     name=_("Cantidad"))
        fila_cantidad.Add(self.cho_cantidad, 0)
        vs.Add(fila_cantidad, 0, wx.ALL, 8)

    def _crear_lista(self, vs):
        self.lista = wx.ListCtrl(self, style=wx.LC_REPORT,
                                 name="ListaResultados")
        nombre_accesible(self.lista, _("Resultados de la búsqueda"))
        self.lista.InsertColumn(0, _("Título"), width=280)
        self.lista.InsertColumn(1, _("Canal"), width=160)
        self.lista.InsertColumn(2, _("Duración"), width=80)
        self.lista.InsertColumn(3, _("Vistas"), width=110)
        self.lista.InsertColumn(4, _("Fecha"), width=110)
        self.lista.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_elegir)
        self.lista.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activar)
        self.lista.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self._lista_acciones = ListaConAcciones(
            self.lista, buscador_lista.acciones_de(
                self.resultados_elegidos, self._abrir_en_app is not None,
                self._escucha.hay_musica, self._acciones,
                lambda resultado: self._ver_contenido_de(resultado),
                self.agregar_a_la_cola,
                lambda resultado: self._escucha.alternar(resultado)),
            _("Sin resultados"))
        entregar_intro(self.lista, self._on_activar)
        vs.Add(self.lista, 1, wx.EXPAND | wx.ALL, 8)

    def _crear_pie(self, vs):
        lbl = wx.StaticText(self, label=_("D&etalles:"))
        vs.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.txt_detalles = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY,
            name=_("Detalles"))
        self.txt_detalles.SetMinSize((-1, 90))
        vs.Add(self.txt_detalles, 0, wx.EXPAND | wx.ALL, 8)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_volver = self._crear_boton(
            fila, _("&Volver a los resultados"), "VolverResultados")
        self.btn_todo = self._crear_boton(
            fila, _("Agregar l&ista entera"), "AgregarListaEntera")
        self.btn_agregar = wx.Button(self, label=_("&Agregar a la cola"), name="AgregarACola")
        self.btn_agregar.Bind(wx.EVT_BUTTON, lambda _event: self.agregar_a_la_cola())
        fila.Add(self.btn_agregar, 0, wx.RIGHT, 8)
        self.btn_mas = wx.Button(self, label=_("Mostrar &más"), name="MostrarMas")
        self.btn_mas.Bind(wx.EVT_BUTTON, self._on_mas)
        fila.Add(self.btn_mas, 0)
        vs.Add(fila, 0, wx.ALL, 8)

    def _crear_boton(self, fila, etiqueta, nombre):
        boton = wx.Button(self, label=etiqueta, name=nombre)
        boton.Show(False)
        fila.Add(boton, 0, wx.RIGHT, 8)
        return boton

    def _cargar_opciones(self):
        self.campo.Set(self._recientes)
        self.campo.SetValue("")
        self.filtros.cargar_opciones()
        try:
            inicial = _CANTIDADES.index(str(self._cantidad))
        except ValueError:
            inicial = _CANTIDADES.index(str(CANTIDAD_DEFECTO))
        self.cho_cantidad.SetSelection(inicial)

    def _cantidad_actual(self) -> int:
        idx = self.cho_cantidad.GetSelection()
        if 0 <= idx < len(_CANTIDADES):
            return int(_CANTIDADES[idx])
        return CANTIDAD_DEFECTO

    def _on_buscar(self, _event):
        texto = self.campo.GetValue()
        clase, valor = clasificar_entrada(texto)
        if clase == "vacio":
            buscador_tandas.sonar("error")
            anunciar(_("Escribe una búsqueda o un enlace."))
            return
        if clase == "enlace":
            self.campo.SetValue("")
            if es_enlace_de_lista(valor):
                self._entrar_en_contenido(valor, con_retorno=False)
                return
            self._agregar_urls([valor])
            return
        if self._vista.activa:
            self._vista.cerrar()
        self._recientes = busquedas_recientes.agregar(self._recientes, valor)
        busquedas_recientes.guardar(self._ruta, self._recientes)
        self.campo.Set(self._recientes)
        self.campo.SetValue(valor)
        self._texto = valor
        self._filtros = self.filtros.actuales()
        self._cantidad = self._cantidad_actual()
        buscador_tandas.sonar("busqueda_iniciada")
        anunciar(_("Buscando"))
        self._lanzar(mas=False)

    def _lanzar(self, mas: bool) -> None:
        if not mas:
            self.txt_detalles.SetValue("")
            self._lista_acciones.fijar([])
        self._tandas.pedir(
            lambda inicio, cantidad: busqueda_youtube.buscar(
                self._texto, self._filtros, inicio, cantidad),
            self._cantidad, self._al_tanda, mas, nombre="BusquedaYoutube")
        self._inicio = self._tandas.inicio
        self._generacion = self._tandas.generacion

    def _al_volver(self, generacion, respuesta, mas):
        if not self:
            return
        inicio = self._inicio if mas else 1
        self._tandas.llegada(generacion, respuesta, inicio, self._cantidad,
                             mas, self._al_tanda)
        self._inicio = self._tandas.inicio
        self._generacion = self._tandas.generacion

    def _al_tanda(self, nuevos, mas, respuesta, foco_en_mas):
        if not self:
            return
        if respuesta.error:
            self.txt_detalles.SetValue(respuesta.error)
            buscador_tandas.sonar("busqueda_fallida")
            anunciar(respuesta.error)
            if foco_en_mas:
                self.lista.SetFocus()
            return
        self._resultados = self._tandas.acumulado
        if mas:
            self._volver_mas(nuevos, foco_en_mas)
        else:
            self._volver_primera(nuevos, foco_en_mas)

    def _volver_primera(self, nuevos, foco_en_mas):
        self._resultados = ordenar(self._resultados, self._filtros.orden)
        if not nuevos:
            self.txt_detalles.SetValue(_("Sin resultados"))
            buscador_tandas.sonar("busqueda_sin_resultados")
            anunciar(_("Sin resultados"))
            return
        self._poner_filas()
        buscador_contenido.enfocar_fila(self.lista, 0)
        buscador_tandas.sonar("busqueda_resultados")
        buscador_tandas.anunciar_tanda(len(nuevos), mas=False)
        if foco_en_mas or wx.Window.FindFocus() in (self.campo, self.btn_buscar):
            self.lista.SetFocus()

    def _volver_mas(self, nuevos, foco_en_mas):
        if not nuevos:
            buscador_tandas.sonar("busqueda_sin_resultados")
            anunciar(_("No hay más resultados"))
            if foco_en_mas:
                self.lista.SetFocus()
            return
        for sel in self._lista_acciones.indices():
            self.lista.Select(sel, False)
        if self._filtros.orden == "relevancia":
            self._poner_filas(nuevos[0].id)
            buscador_contenido.enfocar_fila(
                self.lista, len(self._resultados) - len(nuevos))
        else:
            self._resultados = ordenar(self._resultados, self._filtros.orden)
            self._poner_filas(nuevos[0].id)
            indice = [r.id for r in self._resultados].index(nuevos[0].id)
            buscador_contenido.enfocar_fila(self.lista, indice)
        if foco_en_mas:
            self.lista.SetFocus()
        buscador_tandas.sonar("busqueda_resultados")
        buscador_tandas.anunciar_tanda(len(nuevos), mas=True)

    def _on_mas(self, _event):
        motivo = (self._vista.motivo if self._vista.activa
                  else self._tandas.motivo)
        if motivo:
            anunciar(f"{motivo}.")
            return
        if self._vista.activa:
            self._vista.mas()
        elif self._texto:
            self._lanzar(mas=True)

    def _on_orden(self, _event):
        orden = self.filtros.orden_elegido()
        sel = self.lista.GetFirstSelected()
        elegido = self._resultados[sel].id if 0 <= sel < len(self._resultados) else None
        self._filtros = Filtros(
            self._filtros.tipo, self._filtros.duracion,
            self._filtros.fecha, orden)
        self._resultados = ordenar(self._resultados, orden)
        self._poner_filas(elegido)
        if elegido is not None:
            for i, resultado in enumerate(self._resultados):
                if resultado.id == elegido:
                    buscador_contenido.enfocar_fila(self.lista, i)
                    break

    def _on_filtros(self, _event):
        self.filtros.aplicar_visibilidad()

    def _on_elegir(self, _event):
        sel = self.lista.GetFirstSelected()
        if 0 <= sel < len(self._resultados):
            self.txt_detalles.SetValue(
                texto_detalles(self._resultados[sel], time.time()))

    def agregar_a_la_cola(self) -> None:
        """La acción de agregar, compartida por el menú y el botón."""
        self._on_agregar(None)

    def _on_agregar(self, _event):
        indices = self._lista_acciones.indices()
        if not indices:
            buscador_tandas.sonar("error")
            anunciar(_("Selecciona un resultado."))
            return
        elegidos = self.resultados_elegidos(indices)
        urls, rechazos = buscador_acciones.reparto_para_agregar(elegidos)
        for mensaje in rechazos:
            avisar(mensaje, "error", error=True)
        if urls:
            self._agregar_urls(urls, titulo=buscador_acciones.titulo_para_anunciar(elegidos))

    def _on_activar(self, event):
        indices = self._lista_acciones.indices()
        if not self._vista.activa and len(indices) == 1:
            elegido = self._resultados[indices[0]] \
                if 0 <= indices[0] < len(self._resultados) else None
            if elegido is not None and elegido.tipo in ("lista", "canal"):
                self._entrar_en_contenido(
                    elegido.url, es_canal=elegido.tipo == "canal")
                return
        self._on_agregar(event)

    def _on_key(self, event):
        tecla = event.GetKeyCode()
        if tecla == wx.WXK_BACK and self._vista.activa:
            self._vista.volver()
        elif self._escucha.al_teclear(event, self.lista, self._resultados):
            return
        else:
            event.Skip()

    def _entrar_en_contenido(self, url, con_retorno=True, es_canal=False) -> None:
        self._vista.mostrar(url, {
            "resultados": self._resultados, "texto": self._texto,
            "filtros": self._filtros, "inicio": self._inicio,
            "elegidos": [self._resultados[i].id
                         for i in self._lista_acciones.indices()
                         if 0 <= i < len(self._resultados)],
        }, con_retorno, es_canal)

    def _ver_contenido_de(self, resultado) -> None:
        if resultado is not None:
            self._entrar_en_contenido(
                resultado.url, es_canal=resultado.tipo == "canal")

    def _sincronizar_contenido(self, todos, _nuevos, _mas) -> None:
        self._resultados = list(todos)
        self._poner_filas()

    def _restaurar_vista(self, guardados) -> None:
        self._resultados = guardados["resultados"]
        self._texto = guardados["texto"]
        self._filtros = guardados["filtros"]
        self._inicio = guardados["inicio"]
        elegidos = guardados["elegidos"]
        self._poner_filas(elegidos[0] if elegidos else None)
        for i, resultado in enumerate(self._resultados):
            if resultado.id in elegidos:
                self.lista.Select(i)
        buscador_contenido.enfocar_fila(self.lista, self.lista.GetFirstSelected())
        self._tandas.actualizar_boton()

    def _poner_filas(self, elegida=None) -> None:
        self._lista_acciones.poner_al_dia(
            [r.id for r in self._resultados], _celdas(self._resultados),
            elegida)
        if not self._resultados:
            self.lista.DeleteAllItems()

    def resultados_elegidos(self, indices=None) -> list:
        """Los resultados de esas filas, o de las elegidas si no se dice."""
        if indices is None:
            indices = self._lista_acciones.indices()
        return [self._resultados[i] for i in indices
                if 0 <= i < len(self._resultados)]

    def fijar_texto(self, url: str | None) -> None:
        self.campo.SetValue(url or "")
