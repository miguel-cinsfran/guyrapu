# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro Diseño de escena: elegir, ajustar, guardar y eliminar diseños.

No habla con OBS: devuelve el diseño elegido y la pestaña Fuentes lo aplica.
Guardar y eliminar sí escriben el archivo de diseños propios.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _, ngettext
from guyrapu.obs import disenos_fabrica, disenos_guardados, obs_disposicion
from guyrapu.obs.disenos_escena import ESQUINAS, Diseno
from guyrapu.ui import paleta
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.disenos_nombres import buscar_guardado as _buscar_guardado
from guyrapu.ui.disenos_nombres import pedir_nombre as _pedir_nombre
from guyrapu.ui.preferencias_comun import (
    boton, fila_campo, lista_con_nombre, nombre_de_etiqueta)

_OPCIONES_AJUSTE = (("", N_("Automático")), ("ajustar", N_("Ajustar")),
                    ("llenar", N_("Llenar")))
_OPCIONES_ESQUINA = tuple(
    (nombre, N_(obs_disposicion.etiqueta_anclaje(nombre)))
    for nombre in ESQUINAS)
_OPCIONES_TAMANO = (
    ("chica", N_("Pequeño, un quinto del ancho")),
    ("mediana", N_("Mediano, un cuarto del ancho")),
    ("grande", N_("Grande, un tercio del ancho")))
_OPCIONES_REPARTO = (("mitades", N_("Mitad y mitad")),
                     ("dos_tercios", N_("Dos tercios y un tercio")),
                     ("a_la_medida", N_("A la medida de la primera fuente")))
_OPCIONES_CHAT = (
    ("ninguno", N_("Sin chat")),
    ("superpuesto", N_("Encima de la imagen")),
    ("franja", N_("En una franja a la derecha")))
_OPCIONES_CHAT_VERTICAL = _OPCIONES_CHAT[:2] + (
    ("franja", N_("En una franja inferior")),)
_ETIQUETAS_LUGAR = {
    "principal": (N_("&Fuente principal:"),
                  N_("Ajuste de la fuente principal")),
    "secundaria": (N_("Fuente en la &esquina:"),
                   N_("Ajuste de la fuente en la esquina")),
    "izquierda": (N_("Fuente a la &izquierda:"),
                  N_("Ajuste de la fuente a la izquierda")),
    "derecha": (N_("Fuente a la de&recha:"),
                N_("Ajuste de la fuente a la derecha")),
}
_ETIQUETAS_LUGAR_VERTICAL = {
    "izquierda": (N_("Fuente &superior:"),
                  N_("Ajuste de la fuente superior")),
    "derecha": (N_("Fuente &inferior:"),
                N_("Ajuste de la fuente inferior")),
}


class DisenoEscenaDialog(wx.Dialog):
    """Elige un diseño, ajusta cada lugar y devuelve el diseño armado."""

    def __init__(self, padre, fuentes, guardados, vertical=False):
        super().__init__(padre, title=_("Aplicar diseño"),
                         name="DialogoDisenoEscena")
        self._fuentes = list(fuentes)
        self._guardados = list(guardados)
        self._vertical = vertical
        self._opciones_chat = (
            _OPCIONES_CHAT_VERTICAL if vertical else _OPCIONES_CHAT)
        self._fabrica = disenos_fabrica.FABRICA
        self._elegido = None
        self._clase = "pantalla_completa"
        self._nombres_fuente = [fuente.nombre for fuente in self._fuentes
                                if fuente.tipo != "chat"]
        self._lugares = {}
        self._opciones = {}
        self._crear_controles()
        self._rehacer_lista()
        self._cargar_diseno(0)
        paleta.pintar_ventana(self)
        self.Centre()
        self.cho_diseno.SetFocus()

    def diseno_elegido(self):
        return self._elegido

    def _crear_controles(self):
        caja = wx.BoxSizer(wx.VERTICAL)
        self.cho_diseno = lista_con_nombre(self, _("&Diseño:"))
        fila_campo(
            caja, wx.StaticText(self, label=_("&Diseño:")), self.cho_diseno)
        for lugar in ("principal", "secundaria", "izquierda", "derecha"):
            self._crear_lugar(caja, lugar, *self._etiquetas_lugar(lugar))
        self._crear_opciones(caja)
        self._crear_botones(caja)
        self.SetSizerAndFit(caja)
        self.cho_diseno.Bind(wx.EVT_CHOICE, self._al_elegir_diseno)
        self.cho_chat.Bind(wx.EVT_CHOICE, self._al_cambiar_chat)
        self.btn_aplicar.Bind(wx.EVT_BUTTON, self._al_aplicar)
        self.btn_guardar.Bind(wx.EVT_BUTTON, self._al_guardar)
        self.btn_eliminar.Bind(wx.EVT_BUTTON, self._al_eliminar)
        self.btn_cancelar.Bind(wx.EVT_BUTTON, self._al_cancelar)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)

    def _etiquetas_lugar(self, lugar):
        tabla = _ETIQUETAS_LUGAR_VERTICAL if self._vertical else _ETIQUETAS_LUGAR
        return tabla.get(lugar, _ETIQUETAS_LUGAR[lugar])

    def _crear_lugar(self, caja, lugar, etiqueta, nombre_ajuste):
        etiqueta = _(etiqueta)
        nombre_ajuste = _(nombre_ajuste)
        rotulo = wx.StaticText(self, label=etiqueta)
        control = lista_con_nombre(self, etiqueta, self._nombres_fuente)
        fila = fila_campo(caja, rotulo, control)
        rotulo_ajuste = wx.StaticText(self, label=_("Ajuste:"))
        ajuste = wx.Choice(
            self, choices=[_(texto) for _valor, texto in _OPCIONES_AJUSTE],
            name=nombre_ajuste)
        nombre_accesible(ajuste, nombre_ajuste)
        fila_ajuste = fila_campo(caja, rotulo_ajuste, ajuste)
        setattr(self, "cho_" + lugar, control)
        setattr(self, "cho_ajuste_" + lugar, ajuste)
        self._lugares[lugar] = (
            fila, rotulo, control, fila_ajuste, rotulo_ajuste, ajuste)

    def _crear_opciones(self, caja):
        self.cho_esquina = self._opcion(
            caja, "esquina", _("Es&quina:"), _OPCIONES_ESQUINA)
        self.cho_tamano = self._opcion(
            caja, "tamano", _("&Tamaño:"), _OPCIONES_TAMANO)
        self.cho_reparto = self._opcion(
            caja, "reparto", _("Re&parto:"), _OPCIONES_REPARTO)
        self.cho_chat = self._opcion(
            caja, "chat", _("&Chat:"), self._opciones_chat)
        self.cho_esquina_chat = self._opcion(
            caja, "esquina_chat", _("Esquina del c&hat:"), _OPCIONES_ESQUINA)

    def _opcion(self, caja, clave, etiqueta, opciones):
        rotulo = wx.StaticText(self, label=etiqueta)
        control = lista_con_nombre(
            self, etiqueta, [_(texto) for _valor, texto in opciones])
        fila = fila_campo(caja, rotulo, control)
        self._opciones[clave] = (fila, rotulo, control)
        return control

    def _crear_botones(self, caja):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_aplicar = boton(
            self, _("&Aceptar"), nombre_de_etiqueta(_("&Aceptar")), wx.ID_OK)
        self.btn_aplicar.SetDefault()
        self.btn_guardar = boton(
            self, _("&Guardar como…"),
            nombre_de_etiqueta(_("&Guardar como…")))
        self.btn_eliminar = boton(
            self, _("Eli&minar"), nombre_de_etiqueta(_("Eli&minar")))
        self.btn_cancelar = boton(
            self, _("Cance&lar"), nombre_de_etiqueta(_("Cance&lar")),
            wx.ID_CANCEL)
        for control in (self.btn_aplicar, self.btn_guardar, self.btn_eliminar,
                        self.btn_cancelar):
            fila.Add(control, 0, wx.RIGHT, 8)
        caja.Add(fila, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

    def _rehacer_lista(self, seleccion=0):
        nombres = [_(fabrica.nombre) for fabrica in self._fabrica]
        nombres.extend(nombre for nombre, _diseno in self._guardados)
        self.cho_diseno.Set(nombres)
        if nombres:
            self.cho_diseno.SetSelection(
                max(0, min(seleccion, len(nombres) - 1)))

    def _cargar_diseno(self, indice):
        if not 0 <= indice < len(self._fabrica) + len(self._guardados):
            return
        if indice < len(self._fabrica):
            fabrica = self._fabrica[indice]
            diseno = disenos_fabrica.completar(
                fabrica.diseno, fabrica.papeles, self._fuentes)
        else:
            _nombre, guardado = self._guardados[indice - len(self._fabrica)]
            papeles = {lugar: disenos_fabrica.PAPEL_PRINCIPAL
                       for lugar in disenos_fabrica.lugares(guardado.clase)}
            diseno = disenos_fabrica.completar(
                guardado, papeles, self._fuentes)
        self._clase = diseno.clase
        self._poner_en_controles(diseno)
        self._actualizar_visibilidad()

    def _poner_en_controles(self, diseno):
        for lugar, grupo in self._lugares.items():
            nombre = getattr(diseno, lugar, "")
            _seleccionar_fuente(grupo[2], nombre)
            _seleccionar_valor(
                grupo[5], diseno.modos.get(nombre, ""), _OPCIONES_AJUSTE)
        _seleccionar_valor(self.cho_esquina, diseno.esquina, _OPCIONES_ESQUINA)
        _seleccionar_valor(self.cho_tamano, diseno.tamano, _OPCIONES_TAMANO)
        _seleccionar_valor(
            self.cho_reparto, diseno.proporcion, _OPCIONES_REPARTO)
        _seleccionar_valor(self.cho_chat, diseno.chat, _OPCIONES_CHAT)
        _seleccionar_valor(
            self.cho_esquina_chat, diseno.esquina_chat, _OPCIONES_ESQUINA)

    def _actualizar_visibilidad(self):
        lugares = disenos_fabrica.lugares(self._clase)
        for nombre, grupo in self._lugares.items():
            visible = nombre in lugares
            self._mostrar_fila(grupo[0], grupo[1], grupo[2], visible)
            self._mostrar_fila(grupo[3], grupo[4], grupo[5], visible)
        imagen = self._clase == "imagen_en_imagen"
        self._mostrar_opcion("esquina", imagen)
        self._mostrar_opcion("tamano", imagen)
        self._mostrar_opcion("reparto", self._clase == "dividida")
        self._mostrar_opcion(
            "esquina_chat",
            _valor(self.cho_chat, _OPCIONES_CHAT) == "superpuesto")
        self.Layout()

    def _mostrar_fila(self, fila, rotulo, control, visible):
        for ventana in (rotulo, control):
            fila.Show(ventana, visible)
        if not visible and control.HasFocus():
            self.cho_diseno.SetFocus()

    def _mostrar_opcion(self, clave, visible):
        fila, rotulo, control = self._opciones[clave]
        self._mostrar_fila(fila, rotulo, control, visible)

    def _nombre_visible(self, indice):
        if not 0 <= indice < len(self._fabrica) + len(self._guardados):
            return ""
        if indice < len(self._fabrica):
            return _(self._fabrica[indice].nombre)
        return self._guardados[indice - len(self._fabrica)][0]

    def _diseno_actual(self):
        valores = {"principal": "", "secundaria": "", "izquierda": "",
                   "derecha": ""}
        modos = {}
        for lugar in disenos_fabrica.lugares(self._clase):
            control = self._lugares[lugar][2]
            nombre = control.GetStringSelection()
            valores[lugar] = nombre
            if nombre:
                modos[nombre] = _valor(
                    self._lugares[lugar][5], _OPCIONES_AJUSTE)
        return Diseno(
            clase=self._clase,
            **valores,
            esquina=(_valor(self.cho_esquina, _OPCIONES_ESQUINA)
                     if self._clase == "imagen_en_imagen"
                     else "inferior-derecha"),
            tamano=(_valor(self.cho_tamano, _OPCIONES_TAMANO)
                    if self._clase == "imagen_en_imagen" else "mediana"),
            proporcion=(_valor(self.cho_reparto, _OPCIONES_REPARTO)
                        if self._clase == "dividida" else "mitades"),
            chat=_valor(self.cho_chat, _OPCIONES_CHAT),
            esquina_chat=_valor(self.cho_esquina_chat, _OPCIONES_ESQUINA),
            modos=modos)

    def _al_elegir_diseno(self, _event):
        indice = self.cho_diseno.GetSelection()
        self._cargar_diseno(indice)
        aviso = self._aviso_de_fuentes(indice)
        if aviso is not None:
            anunciar(aviso)

    def _aviso_de_fuentes(self, indice):
        if not 0 <= indice < len(self._fabrica) + len(self._guardados):
            return None
        if indice < len(self._fabrica):
            fabrica = self._fabrica[indice]
            nombre = _(fabrica.nombre)
            clase = fabrica.diseno.clase
        else:
            nombre, guardado = self._guardados[indice - len(self._fabrica)]
            clase = guardado.clase
        if not disenos_fabrica.faltan_fuentes(clase, self._fuentes):
            return None
        pedidas = len(disenos_fabrica.lugares(clase))
        presentes = sum(1 for fuente in self._fuentes
                        if fuente.tipo != "chat")
        texto = ngettext("una fuente", "{n} fuentes", pedidas).format(
            n=pedidas)
        if presentes == 0:
            return _("{diseno} necesita {pedidas} y esta escena no tiene "
                     "ninguna. Agrega una con Agregar fuente.").format(
                         diseno=nombre, pedidas=texto)
        return _("{diseno} necesita {pedidas} y esta escena tiene {m}. "
                 "Agrega otra con Agregar fuente.").format(
                     diseno=nombre, pedidas=texto, m=presentes)

    def _al_cambiar_chat(self, event):
        self._actualizar_visibilidad()
        event.Skip()

    def _al_aplicar(self, _event):
        aviso = self._aviso_de_fuentes(self.cho_diseno.GetSelection())
        if aviso is not None:
            anunciar(aviso)
            return
        diseno = self._diseno_actual()
        problema = disenos_fabrica.motivo_para_no_aplicar(
            diseno, self._fuentes, self._vertical)
        if problema is not None:
            lugar, texto = problema
            anunciar(texto)
            self._enfocar(lugar)
            return
        self._elegido = (
            self._nombre_visible(self.cho_diseno.GetSelection()), diseno)
        self.EndModal(wx.ID_OK)

    def _al_guardar(self, _event):
        indice = self.cho_diseno.GetSelection()
        nombre = _pedir_nombre(
            self,
            self._nombre_visible(indice) if indice != wx.NOT_FOUND else "")
        if nombre is None:
            return
        nombre = nombre.strip()
        if not nombre:
            return
        if self._es_nombre_de_fabrica(nombre):
            anunciar(_("Ese nombre es de un diseño de fábrica. Elige otro."))
            return
        diseno = self._diseno_actual()
        self._guardados = disenos_guardados.guardar_diseno(nombre, diseno)
        self._rehacer_lista()
        guardado = _buscar_guardado(self._guardados, nombre)
        if guardado is None:
            guardado = len(self._guardados) - 1
        self.cho_diseno.SetSelection(len(self._fabrica) + guardado)
        self._clase = diseno.clase
        self._actualizar_visibilidad()
        anunciar(_("Diseño guardado: {nombre}").format(
            nombre=self._guardados[guardado][0]))

    def _al_eliminar(self, _event):
        indice = self.cho_diseno.GetSelection()
        if indice == wx.NOT_FOUND:
            return
        if indice < len(self._fabrica):
            anunciar(_("Los diseños de fábrica no se eliminan."))
            return
        nombre = self._guardados[indice - len(self._fabrica)][0]
        self._guardados = disenos_guardados.eliminar_diseno(nombre)
        self._rehacer_lista()
        self.cho_diseno.SetSelection(0)
        self._cargar_diseno(0)
        anunciar(_("Diseño eliminado: {nombre}").format(nombre=nombre))

    def _al_cancelar(self, _event):
        self.EndModal(wx.ID_CANCEL)

    def _al_tecla(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def _enfocar(self, lugar):
        self._lugares[lugar][2].SetFocus()

    def _es_nombre_de_fabrica(self, nombre):
        buscado = nombre.casefold()
        for fabrica in self._fabrica:
            if buscado in (fabrica.nombre.casefold(),
                           _(fabrica.nombre).casefold()):
                return True
        return False


def _seleccionar_fuente(control, nombre):
    if not control.SetStringSelection(nombre):
        control.SetSelection(wx.NOT_FOUND)


def _seleccionar_valor(control, valor, opciones):
    valores = [clave for clave, _texto in opciones]
    try:
        indice = valores.index(valor)
    except ValueError:
        indice = 0
    control.SetSelection(indice)


def _valor(control, opciones):
    indice = control.GetSelection()
    if 0 <= indice < len(opciones):
        return opciones[indice][0]
    return opciones[0][0]


def pedir_diseno(padre, fuentes, guardados, vertical=False):
    """Abre el cuadro y devuelve (nombre, Diseno), o None si se cancela."""
    dialogo = DisenoEscenaDialog(padre, fuentes, guardados, vertical)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return dialogo.diseno_elegido()
        return None
    finally:
        dialogo.Destroy()
