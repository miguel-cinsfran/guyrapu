# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Fuentes de la pestaña Escena: la lista y las acciones sobre una fuente."""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.obs import (
    aplicar_diseno, chat_en_video, consultas_transmision, disenos_fabrica,
    disenos_guardados, obs_disposicion)
from guyrapu.ui import (
    escena_acciones_fuente, escena_agregar_fuente, escena_disenos,
    escena_menu_fuente, escena_version_vertical, lista_acciones)
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import boton, nombre_de_etiqueta

# Traductores: fila de una escena sin fuentes; «Agregar fuente…» es el botón.
VACIO = N_(
    "No hay fuentes en esta escena. Aquí aparecen las fuentes de la escena "
    "elegida en OBS. Usa Agregar fuente… para agregar una.")


def _boton_obs(pagina, etiqueta):
    control = boton(pagina, etiqueta, nombre_de_etiqueta(etiqueta))
    control._etiqueta_base = etiqueta
    return control


class PaginaFuentes(wx.Panel):

    def __init__(self, parent, ventana, gestor, operaciones, registro,
                 escena_elegida):
        super().__init__(parent, name="PaginaFuentes")
        self._ventana = ventana
        self._gestor = gestor
        self._operaciones = operaciones
        self._registro = registro
        self._escena_elegida = escena_elegida
        self._filas = ()
        self._crear_controles()
        self.acciones_fuente = escena_acciones_fuente.AccionesFuente(self)
        self._mover = self.acciones_fuente.mover
        self.acciones = (self.btn_diseno, self.btn_agregar, self.btn_restaurar)
        self._enlazar_eventos()

    @property
    def en_ajuste(self):
        return self._mover.en_curso

    def _crear_controles(self):
        caja = wx.BoxSizer(wx.VERTICAL)
        self._crear_lista(caja)
        self._crear_botones(caja)
        self.SetSizer(caja)

    def _crear_lista(self, caja):
        self.rotulo_fuentes = wx.StaticText(self, label=_("&Fuentes:"))
        self.lst_fuentes = wx.ListBox(
            self, name=nombre_de_etiqueta(_("&Fuentes:")))
        nombre_accesible(self.lst_fuentes, self.lst_fuentes.GetName())
        self.lst_fuentes.SetMinSize((-1, 120))
        self.lista_vacia = lista_acciones.ListaConVacio(
            self.lst_fuentes, _(VACIO))
        caja.Add(self.rotulo_fuentes, 0, wx.LEFT | wx.TOP, 8)
        caja.AddSpacer(4)
        caja.Add(self.lst_fuentes, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    def _crear_botones(self, caja):
        self.btn_diseno = _boton_obs(self, _("&Aplicar diseño…"))
        self.btn_agregar = boton(
            self, _("Agregar f&uente…"),
            nombre_de_etiqueta(_("Agregar f&uente…")))
        self.btn_restaurar = _boton_obs(self, _("Deshacer todos los cambi&os"))
        fila = wx.WrapSizer(wx.HORIZONTAL, flags=0)
        for control in (self.btn_diseno, self.btn_agregar, self.btn_restaurar):
            fila.Add(control, 0, wx.RIGHT, 8)
        caja.Add(fila, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

    def _enlazar_eventos(self):
        self.lst_fuentes.Bind(wx.EVT_KEY_DOWN, self._tecla_fuente)
        self.lst_fuentes.Bind(wx.EVT_CONTEXT_MENU, self._menu_contextual)
        self.btn_diseno.Bind(wx.EVT_BUTTON, self._aplicar_diseno)
        self.btn_agregar.Bind(wx.EVT_BUTTON, self._agregar_fuente)
        self.btn_restaurar.Bind(wx.EVT_BUTTON, self._restaurar)

    def cargar(self, filas, fuente):
        self._filas = tuple(filas or ())
        indice = next((i for i, fila in enumerate(self._filas)
                       if fila.nombre == fuente), None)
        self.lista_vacia.fijar(
            [fila.texto for fila in self._filas], indice)

    def fuente(self):
        indice = self.lista_vacia.indice()
        if indice is not None:
            return self._filas[indice].nombre
        return ""

    def _fila(self):
        indice = self.lista_vacia.indice()
        if indice is not None:
            return self._filas[indice]
        return None

    def _escena(self):
        return self._escena_elegida()

    def _destino(self):
        return self._escena(), self.fuente()

    def _tecla_fuente(self, event):
        if self.acciones_fuente.tecla(event):
            return
        tecla = event.GetKeyCode()
        if (tecla == wx.WXK_WINDOWS_MENU
                or (tecla == wx.WXK_F10 and event.ShiftDown())):
            self._mostrar_menu_fuente(self.lst_fuentes)
            return
        event.Skip()

    def _menu_contextual(self, _event):
        self._mostrar_menu_fuente(self.lst_fuentes)

    def _mostrar_menu_fuente(self, ancla):
        fila = self._fila()
        if fila is None:
            self.lista_vacia.sin_elemento()
            return
        menu = escena_menu_fuente.menu_de_fuente(
            fila, self.acciones_fuente)
        ancla.PopupMenu(menu)
        menu.Destroy()

    def _posicion_tamano(self):
        self.acciones_fuente.posicion_tamano()

    def _ordenar(self, movimiento):
        self.acciones_fuente.ordenar(
            "frente" if movimiento == "cima" else movimiento)

    def _mostrar_snap(self, snap, filas=None):
        if filas is not None:
            self.cargar(filas, self.fuente())

    def _anunciar_snap(self, snap):
        anunciar(self._descripcion_corta(snap))

    def _descripcion_corta(self, snap):
        return obs_disposicion.describir_fuente(
            self.fuente(), snap, obs_disposicion.ACTIVOS_DEFECTO)

    def _aplicar_diseno(self, event):
        if not self._operaciones.puede_correr():
            return
        escena = self._escena()
        if not escena:
            anunciar(_("Sin selección"))
            return
        if (escena_version_vertical.es_gemela_con_original(self, escena)
                and escena_version_vertical.perfil_vertical(self)):
            escena_version_vertical.aplicar_a_gemela(self, escena)
            return
        self._operaciones.en_hilo(
            lambda: aplicar_diseno.fuentes_y_lienzo(self._gestor, escena),
            lambda datos: self._abrir_disenos(escena, *datos))

    def _abrir_disenos(self, escena, fuentes, vertical):
        if not any(fuente.tipo != "chat" for fuente in fuentes):
            anunciar(_("La escena no tiene fuentes para un diseño."))
            return
        guardados = disenos_guardados.cargar()
        elegido = escena_disenos.pedir_diseno(
            self, fuentes, guardados, vertical)
        self.btn_diseno.SetFocus()
        if elegido is None:
            return
        nombre, diseno = elegido
        self._operaciones.en_hilo(
            lambda: self._aplicar_diseno_elegido(escena, diseno),
            lambda datos: self._diseno_aplicado(nombre, datos))

    def _aplicar_diseno_elegido(self, escena, diseno):
        config = getattr(getattr(self._ventana, "_principal", None),
                         "_config", None) or {}
        puerto = chat_en_video.puerto_del_panel(config)
        resultado = aplicar_diseno.aplicar_diseno(
            self._gestor, self._registro, escena, diseno, puerto)
        return resultado, consultas_transmision.leer_filas(
            self._gestor, escena)

    def _diseno_aplicado(self, nombre, datos):
        resultado, filas = datos
        self.cargar(filas, self.fuente())
        anunciar(disenos_fabrica.resumen(
            nombre, resultado[0], sin_mover=resultado[1]))

    def _agregar_fuente(self, _event):
        escena_agregar_fuente.mostrar_menu(self, self.btn_agregar)

    def _releer_filas(self, escena, fuente):
        self._operaciones.en_hilo(
            lambda: consultas_transmision.leer_filas(self._gestor, escena),
            lambda filas: self._cargar_filas(filas, fuente))

    def _cargar_filas(self, filas, fuente):
        nombres = [fila.nombre for fila in filas]
        if fuente in nombres:
            self.cargar(filas, fuente)
        else:
            self.cargar(filas, nombres[0] if nombres else "")

    def _restaurar(self, event):
        if not self._operaciones.puede_correr():
            return
        escena, fuente = self._destino()
        self._operaciones.en_hilo(
            lambda: self._restaurar_y_leer(escena, fuente),
            lambda datos: self._restaurado(datos, fuente))

    def _restaurar_y_leer(self, escena, fuente):
        snap = consultas_transmision.restaurar(
            self._gestor, self._registro, escena, fuente)
        return snap, consultas_transmision.leer_filas(self._gestor, escena)

    def _restaurado(self, datos, fuente):
        _snap, filas = datos
        self.cargar(filas, fuente)
        anunciar(_("Cambios deshechos"))
