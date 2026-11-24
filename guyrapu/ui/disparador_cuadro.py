# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro que edita un disparador y el que cambia solo su nombre.

Recoge los datos y valida: no guarda. La colección y el disco los maneja la
ventana de disparadores.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.interaction import comandos, disparadores, disparadores_guardados
from guyrapu.interaction import estilo_elegido, medios_guardados
from guyrapu.obs import estilos_aviso
from guyrapu.ui import formulario, paleta, seccion_contenido, tecla_escape
from guyrapu.ui.accesibilidad import ContadorAccesible, anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

TITULO_AGREGAR = N_("Agregar alerta")
TITULO_EDITAR = N_("Editar alerta")
AYUDA_TARJETA = N_(
    "Puedes usar {usuario}, {cantidad}, {regalo}, {texto} y {contador}.")


def _eventos():
    return [_(disparadores.NOMBRES_EVENTOS[clave])
            for clave in disparadores.EVENTOS_DE_ALERTA]


def _permisos():
    return [_("Todos"), _("Solo moderadores"), _("Una lista de nombres")]


def _destinos():
    return [_("Vídeo"), _("Chat"), _("Chat y vídeo")]


def _medios():
    return medios_guardados.cargar(paths.medios())


def _numero(valor) -> str:
    numero = float(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:g}"


class DialogoDisparador(wx.Dialog):
    """Cuándo, qué, aspecto, permiso y esperas de un disparador."""

    def __init__(self, padre, datos, otros):
        super().__init__(
            padre,
            title=_(TITULO_EDITAR if datos else TITULO_AGREGAR),
            name="DialogoDisparador")
        self._otros = [disparadores_guardados.a_disparador(otro)
                       for otro in otros]
        self._usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        self._por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        self._estilos = estilos_aviso.todos(self._usuario)
        self._medios = _medios()
        self._crear_controles(datos)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self.txt_nombre.SetFocus()

    def _crear_controles(self, datos):
        panel = wx.Panel(self, name="PanelDisparador")
        contenido = wx.BoxSizer(wx.VERTICAL)
        izquierda = wx.BoxSizer(wx.VERTICAL)
        derecha = wx.BoxSizer(wx.VERTICAL)
        self._crear_cuando(panel, izquierda)
        self._crear_contenido(panel, derecha)
        self._crear_alcance(panel, derecha)
        self._crear_aviso(panel, derecha)
        formulario.columnas(contenido, izquierda, derecha)
        self.btn_aceptar = wx.Button(
            panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._aceptar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        formulario.agregar_pie(
            contenido, [self.btn_aceptar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, contenido)
        self._nombrar_etiquetas(panel)
        self._cargar(datos)

    def _nombrar_etiquetas(self, panel):
        # NVDA omite un texto estático del texto del diálogo cuando el control
        # siguiente se nombra igual. Sin esto lee todos los rótulos seguidos.
        hijos = list(panel.GetChildren())
        for indice, hijo in enumerate(hijos[:-1]):
            if (isinstance(hijo, wx.StaticText)
                    and not isinstance(hijos[indice + 1], wx.Button)):
                # El foco de un contador es su edición interna, que NVDA
                # nombra con el rótulo y sus dos puntos: debe seguir igual.
                if isinstance(hijos[indice + 1], ContadorAccesible):
                    continue
                nombre_accesible(hijo, hijos[indice + 1].GetName())

    def _crear_cuando(self, panel, columna):
        vs = formulario.agregar_seccion(
            columna, panel, _(formulario.SECCION_CUANDO))
        rotulo = fila_label(panel, _("&Nombre:"))
        self.txt_nombre = self._campo(panel, _("&Nombre:"))
        formulario.agregar_fila(vs, rotulo, self.txt_nombre)
        rotulo = fila_label(panel, _("E&vento:"))
        self.cho_evento = self._eleccion(panel, _("E&vento:"), _eventos())
        formulario.agregar_fila(vs, rotulo, self.cho_evento)
        rotulo = fila_label(panel, _("Cantidad mín&ima:"))
        self.txt_minimo = self._campo(panel, _("Cantidad mín&ima:"))
        formulario.agregar_fila(vs, rotulo, self.txt_minimo)
        rotulo = fila_label(panel, _("Nom&bre del regalo:"))
        self.txt_regalo = self._campo(
            panel, _("Nom&bre del regalo:"),
            _("Déjalo vacío para cualquier regalo. Escribe el nombre tal "
              "como lo lee Guyrapu."))
        formulario.agregar_fila(vs, rotulo, self.txt_regalo)

    def _crear_contenido(self, panel, columna):
        self._contenido = seccion_contenido.SeccionContenido(
            panel, columna,
            ("texto", "mostrar_en", "medio", "segundos", "estilo"),
            ayuda=_(AYUDA_TARJETA), destinos=_destinos(),
            medios=self._nombres_de_medios(),
            estilos=estilo_elegido.opciones(
                self._usuario, self._por_tipo, "disparador"))
        self.txt_tarjeta = self._contenido.txt_texto
        self.cho_destino = self._contenido.cho_destino
        self.cho_medio = self._contenido.cho_medio
        self.sp_segundos = self._contenido.sp_segundos
        self.cho_estilo = self._contenido.cho_estilo

    def _crear_alcance(self, panel, columna):
        vs = formulario.agregar_seccion(
            columna, panel, _(formulario.SECCION_ALCANCE))
        rotulo = fila_label(panel, _("Pe&rmiso:"))
        self.cho_permiso = self._eleccion(
            panel, _("Pe&rmiso:"), _permisos())
        formulario.agregar_fila(vs, rotulo, self.cho_permiso)
        rotulo = fila_label(panel, _("Nombres &permitidos:"))
        self.txt_nombres = self._campo(panel, _("Nombres &permitidos:"))
        formulario.agregar_fila(vs, rotulo, self.txt_nombres)
        rotulo = fila_label(panel, _("Espera &general (segundos):"))
        self.sp_espera = self._contador(
            panel, _("Espera &general (segundos):"), 0, 3600, 5)
        formulario.agregar_fila(vs, rotulo, self.sp_espera, numerico=True)
        rotulo = fila_label(panel, _("Espera por pers&ona (segundos):"))
        self.sp_persona = self._contador(
            panel, _("Espera por pers&ona (segundos):"), 0, 3600, 30)
        formulario.agregar_fila(vs, rotulo, self.sp_persona, numerico=True)

    def _crear_aviso(self, panel, columna):
        etiqueta = _("Avisar cuando se m&uestra en el vídeo")
        self.chk_avisar = wx.CheckBox(
            panel, label=etiqueta, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(self.chk_avisar, self.chk_avisar.GetName())
        formulario.agregar_casillas(columna, (self.chk_avisar,))

    def _nombres_de_medios(self):
        return [str(medio.get("nombre", "")) for medio in self._medios]

    def _campo(self, panel, etiqueta, ayuda=""):
        nombre = nombre_de_etiqueta(etiqueta)
        campo = wx.TextCtrl(panel, name=nombre)
        nombre_accesible(campo, f"{nombre}. {ayuda}" if ayuda else nombre)
        return campo

    def _eleccion(self, panel, etiqueta, opciones):
        eleccion = wx.Choice(
            panel, choices=opciones, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(eleccion, eleccion.GetName())
        return eleccion

    def _contador(self, panel, etiqueta, minimo, maximo, inicial):
        nombre = nombre_de_etiqueta(etiqueta)
        control = ContadorAccesible(
            panel, min=minimo, max=maximo, initial=inicial, name=nombre)
        nombre_accesible(control, nombre)
        return control

    def _cargar(self, datos):
        disparador = disparadores_guardados.a_disparador(datos or {})
        self._activo = disparador.activo
        self.txt_nombre.SetValue(disparador.nombre)
        self._elegir_evento(disparador.evento)
        self.txt_minimo.SetValue(
            "" if disparador.minimo is None
            else _numero(disparador.minimo))
        self.txt_regalo.SetValue(disparador.regalo)
        self._contenido.poner({
            "texto": disparador.tarjeta,
            "mostrar_en": comandos.DESTINOS.index(disparador.destino),
            "medio": disparador.medio,
            "segundos": disparador.segundos,
        })
        self._elegir_estilo(disparador.estilo if datos else "")
        self.cho_permiso.SetSelection(
            comandos.PERMISOS.index(disparador.permiso))
        self.txt_nombres.SetValue(", ".join(disparador.nombres))
        self.sp_espera.SetValue(int(disparador.espera_general))
        self.sp_persona.SetValue(int(disparador.espera_persona))
        self.chk_avisar.SetValue(disparador.avisar)

    def _elegir_evento(self, clave):
        try:
            indice = disparadores.EVENTOS_DE_ALERTA.index(clave)
        except ValueError:
            indice = 0
        self.cho_evento.SetSelection(indice)

    def _elegir_estilo(self, clave):
        self._contenido.poner(
            {"estilo": estilo_elegido.indice_de(clave, self._estilos)})

    def _minimo_de_campo(self):
        texto = self.txt_minimo.GetValue().strip()
        if not texto:
            return None
        try:
            return float(texto.replace(",", "."))
        except ValueError:
            return None

    def _medio_elegido(self):
        indice = self.cho_medio.GetSelection()
        if indice <= 0:
            return ""
        return self._nombres_de_medios()[indice - 1]

    def _disparador_de_campos(self):
        evento = disparadores.EVENTOS_DE_ALERTA[
            self.cho_evento.GetSelection()]
        return disparadores.Disparador(
            nombre=self.txt_nombre.GetValue(),
            cuando="evento",
            evento=evento,
            minimo=self._minimo_de_campo(),
            regalo=(self.txt_regalo.GetValue().strip()
                    if evento == "superchat" else ""),
            medio=self._medio_elegido(),
            destino=comandos.DESTINOS[self.cho_destino.GetSelection()],
            tarjeta=self.txt_tarjeta.GetValue(),
            estilo=estilo_elegido.clave_de(
                self.cho_estilo.GetSelection(), self._estilos),
            segundos=self.sp_segundos.GetValue(),
            permiso=comandos.PERMISOS[self.cho_permiso.GetSelection()],
            nombres=comandos.separar_nombres(self.txt_nombres.GetValue()),
            espera_general=float(self.sp_espera.GetValue()),
            espera_persona=float(self.sp_persona.GetValue()),
            activo=self._activo,
            avisar=self.chk_avisar.GetValue(),
        )

    def _aceptar(self, _evento):
        disparador = self._disparador_de_campos()
        error = disparadores.validar(disparador, self._otros)
        if error:
            anunciar(error)
            self._campo_del_error(disparador).SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def _campo_del_error(self, disparador):
        campos = {
            "nombre": self.txt_nombre,
            "evento": self.cho_evento,
            "minimo": self.txt_minimo,
            "tarjeta": self.txt_tarjeta,
        }
        campo, _mensaje = disparadores.error_y_campo(
            disparador, self._otros)
        return campos.get(campo, self.txt_nombre)

    def datos(self) -> dict:
        """El disparador tal como se guarda."""
        return disparadores_guardados.desde_disparador(
            self._disparador_de_campos())

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


class DialogoNombre(wx.Dialog):
    """Pide un nombre, sin validarlo: el bucle de la ventana lo repite."""

    def __init__(self, padre, nombre):
        super().__init__(padre, title=_("Cambiar nombre"),
                         name="DialogoNombreDisparador")
        panel = wx.Panel(self, name="PanelNombreDisparador")
        caja = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Nombre:"))
        self.txt_nombre = wx.TextCtrl(
            panel, name=nombre_de_etiqueta(_("&Nombre:")))
        nombre_accesible(self.txt_nombre, self.txt_nombre.GetName())
        self.txt_nombre.SetValue(nombre)
        formulario.agregar_fila(caja, rotulo, self.txt_nombre)
        self.btn_aceptar = wx.Button(
            panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        formulario.agregar_pie(caja, [self.btn_aceptar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, caja)
        self.Centre()
        paleta.pintar_ventana(self)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.txt_nombre.SetFocus()

    def nombre(self) -> str:
        return self.txt_nombre.GetValue().strip()

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


def abrir(padre, datos=None, otros=()):
    """Abre el cuadro y devuelve los datos del disparador, o None."""
    dialogo = DialogoDisparador(padre, datos or {}, otros)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.datos()
    finally:
        dialogo.Destroy()


def pedir_nombre(padre, nombre) -> str | None:
    """Abre el cuadro del nombre y devuelve el texto, o None."""
    dialogo = DialogoNombre(padre, nombre)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.nombre()
    finally:
        dialogo.Destroy()
