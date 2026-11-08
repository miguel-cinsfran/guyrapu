# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Editor de listas de música: el nombre, la lista y la carpeta.

Editar y crear comparten un solo cuadro. La lista que se edita va en
«Canciones de la lista», en su orden y sin casillas; la carpeta va en
«Todas las canciones», con una casilla marcada en las que ya están. Qué
canciones tiene la lista y en qué orden lo resuelve `ListaEnEdicion`, sin
wx, para poder comprobarlo solo.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _, ngettext
from guyrapu.music import anuncios, listas, vista
from guyrapu.music.edicion_lista import ListaEnEdicion
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui import musica_menus, paleta

MAX_NOMBRE = 60
TITULO_NUEVA = N_("Nueva lista")
TITULO_EDITAR = N_("Editar lista")
TEXTO_NOMBRE_LARGO = N_("El nombre no puede tener más de 60 caracteres")
ACCION_CANCELAR = "cancelar"
ACCION_MENU = "menu"


def validar_nombre(nombre):
    """El nombre limpio; levanta `ErrorListas` con el motivo si no sirve."""
    limpio = listas.validar_nombre(nombre)
    if len(limpio) > MAX_NOMBRE:
        raise listas.ErrorListas(_(TEXTO_NOMBRE_LARGO))
    return limpio


def accion_tecla(codigo, modificadores, en_lista):
    """Qué hacer con la tecla, según su código, sus modificadores y el foco.

    `en_lista` es "lista", "todas" o None. Enter en cualquiera de las dos
    reproduce; el resto de las teclas de la lista propia actúan solo en
    ella. Fuera de las listas, Enter sigue su camino hacia Guardar.
    """
    if codigo == wx.WXK_ESCAPE:
        return ACCION_CANCELAR
    if codigo in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
        if en_lista in ("lista", "todas"):
            return musica_menus.ACCION_REPRODUCIR
        return None
    if en_lista != "lista":
        return None
    if codigo in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
        return musica_menus.ACCION_QUITAR
    if codigo == wx.WXK_UP and modificadores & wx.MOD_ALT:
        return musica_menus.ACCION_SUBIR
    if codigo == wx.WXK_DOWN and modificadores & wx.MOD_ALT:
        return musica_menus.ACCION_BAJAR
    if codigo == wx.WXK_WINDOWS_MENU or (
            codigo == wx.WXK_F10 and modificadores & wx.MOD_SHIFT):
        return ACCION_MENU
    return None


class DialogoEditorLista(wx.Dialog):
    """El nombre de una lista, sus canciones y la carpeta con casillas."""

    def __init__(self, parent, nombre="", temas_carpeta=(), temas_lista=(),
                 reproducir=None):
        super().__init__(
            parent, title=_(TITULO_EDITAR if nombre else TITULO_NUEVA),
            name="EditorLista")
        self._reproducir = reproducir
        self._temas_carpeta = ListaEnEdicion(temas_carpeta).temas
        self._lista = ListaEnEdicion(temas_lista)
        self._visibles_todas = []
        self._actualizando_todas = False
        self._nombre = None
        self._crear_controles()
        if nombre:
            self.txt_nombre.SetValue(nombre)
        self._cargar_lista()
        self._cargar_todas()
        self.Bind(wx.EVT_CHAR_HOOK, self._tecla)
        self.lb_todas.Bind(wx.EVT_LIST_ITEM_CHECKED, self._al_marcar)
        self.lb_todas.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self._al_desmarcar)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        (self.lb_lista if nombre else self.txt_nombre).SetFocus()

    def _crear_controles(self):
        self._panel = panel = wx.Panel(self, name="PanelEditorLista")
        vs = wx.BoxSizer(wx.VERTICAL)
        self._agregar_nombre(panel, vs)
        self._agregar_lista(panel, vs)
        self._agregar_buscar(panel, vs)
        self._agregar_todas(panel, vs)
        vs.Add(self._crear_botones(panel), 0, wx.ALL, 12)
        panel.SetSizer(vs)
        contenedor = wx.BoxSizer(wx.VERTICAL)
        contenedor.Add(panel, 1, wx.EXPAND)
        self.SetSizer(contenedor)
        self.txt_buscar.Bind(wx.EVT_TEXT, lambda _evento: self._aplicar_filtro())

    def _agregar_nombre(self, panel, vs):
        vs.Add(wx.StaticText(panel, label=_("&Nombre:")), 0, wx.ALL, 12)
        self.txt_nombre = self._campo(
            panel, _("Nombre de la lista"), MAX_NOMBRE)
        vs.Add(self.txt_nombre, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
               12)

    def _agregar_lista(self, panel, vs):
        vs.Add(wx.StaticText(
            panel, label=_("&Canciones de la lista:")), 0, wx.ALL, 12)
        self.lb_lista = self._lista_ctrl(
            panel, _("Canciones de la lista"), 120)
        vs.Add(self.lb_lista, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

    def _agregar_buscar(self, panel, vs):
        vs.Add(wx.StaticText(panel, label=_("&Buscar:")), 0, wx.ALL, 12)
        self.txt_buscar = self._campo(panel, _("Buscar canciones"))
        vs.Add(self.txt_buscar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
               12)

    def _agregar_todas(self, panel, vs):
        vs.Add(wx.StaticText(
            panel, label=_("&Todas las canciones:")), 0, wx.ALL, 12)
        self.lb_todas = self._lista_ctrl(
            panel, _("Todas las canciones"), 180)
        self.lb_todas.EnableCheckBoxes(True)
        vs.Add(self.lb_todas, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
               12)

    def _lista_ctrl(self, panel, nombre, alto):
        lista = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, name=nombre)
        nombre_accesible(lista, nombre)
        lista.InsertColumn(0, _("Canción"), width=420)
        lista.SetMinSize((460, alto))
        return lista

    def _campo(self, panel, nombre, largo=None):
        campo = wx.TextCtrl(panel, name=nombre)
        if largo is not None:
            campo.SetMaxLength(largo)
        nombre_accesible(campo, nombre)
        return campo

    def _crear_botones(self, panel):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_guardar = wx.Button(panel, wx.ID_OK, _("&Guardar"),
                                      name=_("Guardar"))
        self.btn_cancelar = wx.Button(panel, wx.ID_CANCEL, _("Cancelar"),
                                       name=_("Cancelar"))
        for boton in (self.btn_guardar, self.btn_cancelar):
            fila.Add(boton, 0, wx.RIGHT, 8)
        self.btn_guardar.SetDefault()
        self.btn_guardar.Bind(wx.EVT_BUTTON, self._guardar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        return fila

    def _cargar_lista(self):
        self.lb_lista.DeleteAllItems()
        for tema in self._lista.temas:
            self.lb_lista.InsertItem(
                self.lb_lista.GetItemCount(), vista.fila_tema(tema))

    def _cargar_todas(self):
        self._aplicar_filtro()

    def _aplicar_filtro(self):
        self._visibles_todas = list(vista.filtrar_lista(
            self._temas_carpeta, self.txt_buscar.GetValue()))
        self._actualizando_todas = True
        try:
            self.lb_todas.DeleteAllItems()
            for tema in self._visibles_todas:
                indice = self.lb_todas.InsertItem(
                    self.lb_todas.GetItemCount(), vista.fila_tema(tema))
                self.lb_todas.CheckItem(indice, self._lista.contiene(tema))
        finally:
            self._actualizando_todas = False

    def _tema_todas(self, indice):
        if 0 <= indice < len(self._visibles_todas):
            return self._visibles_todas[indice]
        return None

    def _al_marcar(self, evento):
        if self._actualizando_todas:
            return
        tema = self._tema_todas(evento.GetIndex())
        if tema is not None and self._lista.agregar(tema):
            self._cargar_lista()
            self._anunciar_agregado(tema)

    def _al_desmarcar(self, evento):
        if self._actualizando_todas:
            return
        tema = self._tema_todas(evento.GetIndex())
        if tema is not None and self._lista.quitar(tema) is not None:
            self._cargar_lista()
            self._anunciar_quitado(tema)

    def _anunciar_agregado(self, tema):
        total = len(self._lista.temas)
        # Traductores: {nombre} es la canción y {n} cuántas hay en total.
        texto = ngettext(
            "Agregada a la lista: {nombre}. {n} canción en total",
            "Agregada a la lista: {nombre}. {n} canciones en total", total)
        anunciar(texto.format(
            nombre=anuncios.nombre_tema(tema, False), n=total))

    def _anunciar_quitado(self, tema):
        total = len(self._lista.temas)
        # Traductores: {nombre} es la canción y {n} cuántas quedan.
        texto = ngettext(
            "Eliminada de la lista: {nombre}. Queda {n} canción",
            "Eliminada de la lista: {nombre}. Quedan {n} canciones", total)
        anunciar(texto.format(
            nombre=anuncios.nombre_tema(tema, False), n=total))

    def _en_que_lista(self):
        foco = wx.Window.FindFocus()
        if foco is self.lb_lista:
            return "lista"
        if foco is self.lb_todas:
            return "todas"
        return None

    def _indice_de(self, lista):
        indice = lista.GetFocusedItem()
        if indice == -1:
            indice = lista.GetFirstSelected()
        return indice

    def _tema_de(self, en_lista):
        if en_lista == "lista":
            indice = self._indice_de(self.lb_lista)
            if 0 <= indice < len(self._lista.temas):
                return self._lista.temas[indice]
        elif en_lista == "todas":
            return self._tema_todas(self._indice_de(self.lb_todas))
        return None

    def _reproducir_en(self, en_lista):
        if self._reproducir is None:
            return
        tema = self._tema_de(en_lista)
        if tema is not None:
            self._reproducir(tema)

    def _quitar_actual(self):
        indice = self._indice_de(self.lb_lista)
        tema = self._lista.quitar_en(indice)
        if tema is None:
            return
        self._cargar_lista()
        self._marcar_en_todas(tema, False)
        self._enfocar_tras_quitar(indice)
        self._anunciar_quitado(tema)

    def _marcar_en_todas(self, tema, marcada):
        for indice, candidato in enumerate(self._visibles_todas):
            if candidato.origen == tema.origen:
                self._actualizando_todas = True
                try:
                    self.lb_todas.CheckItem(indice, marcada)
                finally:
                    self._actualizando_todas = False
                return

    def _enfocar_tras_quitar(self, indice):
        self.lb_lista.SetFocus()
        total = self.lb_lista.GetItemCount()
        if total:
            nuevo = min(indice, total - 1)
            self.lb_lista.Focus(nuevo)
            self.lb_lista.Select(nuevo)

    def _mover_actual(self, paso):
        indice = self._indice_de(self.lb_lista)
        if indice < 0:
            return
        nuevo = self._lista.mover(indice, paso)
        self._cargar_lista()
        self.lb_lista.SetFocus()
        self.lb_lista.Focus(nuevo)
        self.lb_lista.Select(nuevo)
        total = len(self._lista.temas)
        anunciar(anuncios.aviso_tema_movido(nuevo + 1, total).texto)

    def _menu_lista(self):
        if self._indice_de(self.lb_lista) < 0:
            return
        musica_menus.mostrar_menu(
            self.lb_lista, musica_menus.entradas_lista_editada(),
            self._accion_lista)

    def _accion_lista(self, accion):
        if accion == musica_menus.ACCION_REPRODUCIR:
            self._reproducir_en("lista")
        elif accion == musica_menus.ACCION_QUITAR:
            self._quitar_actual()
        elif accion == musica_menus.ACCION_SUBIR:
            self._mover_actual(-1)
        elif accion == musica_menus.ACCION_BAJAR:
            self._mover_actual(1)

    def _guardar(self, _evento=None):
        try:
            self._nombre = validar_nombre(self.txt_nombre.GetValue())
        except listas.ErrorListas as exc:
            anunciar(str(exc))
            self.txt_nombre.SetFocus()
            self.txt_nombre.SelectAll()
            return
        self.EndModal(wx.ID_OK)

    def datos(self):
        """El nombre limpio y las canciones, en el orden de la lista."""
        if self._nombre is None:
            self._nombre = validar_nombre(self.txt_nombre.GetValue())
        return self._nombre, self._lista.temas

    def _tecla(self, evento):
        en_lista = self._en_que_lista()
        accion = accion_tecla(
            evento.GetKeyCode(), evento.GetModifiers(), en_lista)
        if accion == ACCION_CANCELAR:
            self.EndModal(wx.ID_CANCEL)
            return
        if accion == musica_menus.ACCION_REPRODUCIR:
            self._reproducir_en(en_lista)
            return
        if accion == musica_menus.ACCION_QUITAR:
            self._quitar_actual()
            return
        if accion == musica_menus.ACCION_SUBIR:
            self._mover_actual(-1)
            return
        if accion == musica_menus.ACCION_BAJAR:
            self._mover_actual(1)
            return
        if accion == ACCION_MENU:
            self._menu_lista()
            return
        evento.Skip()


def pedir_lista(parent, nombre="", temas_carpeta=(), temas_lista=(),
                reproducir=None):
    """Abre el editor y devuelve (nombre, temas), o None si se cancela."""
    with DialogoEditorLista(
            parent, nombre, temas_carpeta, temas_lista,
            reproducir=reproducir) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.datos()
