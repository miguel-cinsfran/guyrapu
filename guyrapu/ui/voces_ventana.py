# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana Administrar voces: motores, búsqueda, voces e instalación."""
from __future__ import annotations
import wx
from guyrapu.core import (config, diagnostico, lista_voces, paquetes_catalogo,
                          paquetes_instalacion, red, voces_disponibles)
from guyrapu.core.idioma import _, ngettext, pgettext
from guyrapu.music import anuncios as anuncios_musica
from guyrapu.ui import (ayuda_manual, confirmar, paleta, tecla_escape,
                        voces_instalacion)
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta
from guyrapu.ui.ventana_espera import VentanaEspera
from guyrapu.voice import muestra_voz, sound_player as _snd
from guyrapu.voice.proveedores import PROVEEDORES
logger = diagnostico.obtener_logger(__name__)

class ListaVocesConAcciones(ListaConAcciones):
    """En una lista múltiple wx rechaza GetSelection: solo da GetSelections."""

    def __init__(self, lista, acciones, texto_vacio):
        super().__init__(lista, acciones, texto_vacio)
        self._lista_multiple = lista

    def indice(self):
        elegidas = self._lista_multiple.GetSelections()
        return elegidas[0] if elegidas else None

    def indices(self):
        return list(self._lista_multiple.GetSelections())


def abrir(padre, al_cerrar=None):
    """Muestra la ventana y, al cerrarla, avisa a quien la abrió."""
    dialogo = VentanaVoces(padre)
    try:
        dialogo.ShowModal()
    finally:
        dialogo.Destroy()
    if al_cerrar is not None:
        al_cerrar()


class VentanaVoces(wx.Dialog):

    def __init__(self, padre):
        super().__init__(padre, title=_("Administrar voces"),
                         name="VentanaVoces", size=(820, 700))
        self._vivo = True
        self._espera = None
        self._idioma_tocado = False
        self._cargando, self._fallo = True, False
        self._valores_idioma = [""]
        self._catalogo, self._instalados = [], []
        self._entradas, self._por_idioma = [], []
        self._motores, self._filtradas = [], []
        self._motor, self._buscado = "", ""
        self._crear_controles()
        ayuda_manual.enlazar(self, "voces")
        paleta.pintar_ventana(self)
        self.Centre()
        self.Bind(wx.EVT_CLOSE, self._al_cerrar)
        self._recargar_instalados()
        self._rehacer_filtros()
        self._rehacer()
        self.lista_motores.SetFocus()
        self._leer_catalogo()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(fila_label(self, _("&Idioma:")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.cho_idioma = wx.Choice(self, name=_("Idioma"))
        self.cho_idioma.Bind(wx.EVT_CHOICE, self._al_cambiar_idioma)
        vs.Add(self.cho_idioma, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(fila_label(self, _("&Motor de voz:")), 0, wx.LEFT | wx.RIGHT, 10)
        self.lista_motores = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name=_("Motor de voz"))
        nombre_accesible(self.lista_motores, _("Motor de voz"))
        self.lista_motores.Bind(wx.EVT_LISTBOX, self._al_elegir_motor)
        self._motores_pieza = ListaConAcciones(
            self.lista_motores, (),
            _("No hay motores de voz para este idioma."))
        vs.Add(self.lista_motores, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(fila_label(self, _("&Buscar voz:")), 0, wx.LEFT | wx.RIGHT, 10)
        self.txt_buscar = wx.TextCtrl(self, name=_("Buscar voz"))
        nombre_accesible(self.txt_buscar, _("Buscar voz"))
        self.txt_buscar.Bind(wx.EVT_TEXT, self._al_buscar)
        self.txt_buscar.Bind(wx.EVT_KEY_DOWN, self._tecla_buscar)
        vs.Add(self.txt_buscar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(fila_label(self, _("&Voces:")), 0, wx.LEFT | wx.RIGHT, 10)
        self.lista_voces = wx.ListBox(
            self, style=wx.LB_EXTENDED | wx.LB_HSCROLL, name=_("Voces"))
        nombre_accesible(self.lista_voces, _("Voces"))
        self._voces = ListaVocesConAcciones(
            self.lista_voces, self._acciones_voces(),
            _("No hay voces que coincidan con la búsqueda."))
        vs.Add(self.lista_voces, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(fila_label(self, _("De&talles:")), 0, wx.LEFT | wx.RIGHT, 10)
        self.txt_detalles = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL
            | wx.TE_RICH2, name=_("Detalles"))
        self.txt_detalles.SetMinSize((-1, 120))
        vs.Add(self.txt_detalles, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._crear_botones(vs)
        self.SetSizer(vs)

    def _crear_botones(self, vs):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        for clave, etiqueta in (
                ("instalar", _("In&stalar")),
                ("actualizar", _("&Actualizar")),
                ("eliminar", pgettext("paquete de voces", "&Eliminar")),
                ("previa", _("Vista p&revia de voz"))):
            boton = wx.Button(self, label=etiqueta,
                              name=nombre_de_etiqueta(etiqueta))
            boton.Bind(wx.EVT_BUTTON,
                       lambda _e, clave=clave: self._voces.ejecutar(clave))
            setattr(self, "btn_" + clave, boton)
            fila.Add(boton, 0, wx.RIGHT, 6)
        vs.Add(fila, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.btn_cerrar = wx.Button(self, wx.ID_CANCEL, _("&Cerrar"),
                                     name=_("Cerrar"))
        self.btn_cerrar.Bind(wx.EVT_BUTTON, self._al_cerrar)
        vs.Add(self.btn_cerrar, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

    def _acciones_voces(self):
        return (
            Accion("instalar", _("In&stalar"),
                   lambda: self._accion_voces("instalar"), varios=True),
            Accion("actualizar", _("&Actualizar"),
                   lambda: self._accion_voces("actualizar"), varios=True),
            Accion("eliminar", pgettext("paquete de voces", "&Eliminar"),
                   self._eliminar_voces, tecla="suprimir", varios=True),
            Accion("previa", _("Vista p&revia de voz"), self._vista_previa,
                   tecla="intro", motivo=self._motivo_previa),
        )

    def _motivo_previa(self):
        if len(self.lista_voces.GetSelections()) > 1:
            return _("Elige un solo elemento para esta acción")
        return ""

    def _leer_catalogo(self):
        def trabajar():
            try:
                texto = red.pedir_texto(paquetes_catalogo.URL_CATALOGO)
                paquetes, descartes = paquetes_catalogo.leer(
                    texto, config.APP_VERSION, {"voz"},
                    tuple(proveedor.id for proveedor in PROVEEDORES))
            except Exception as error:
                wx.CallAfter(self._catalogo_fallo, str(error))
                return
            for motivo in descartes:
                logger.info("paquete de voces descartado: %s", motivo)
            wx.CallAfter(self._catalogo_listo, paquetes)
        diagnostico.crear_hilo(trabajar, "CatalogoVoces").start()

    def _catalogo_listo(self, paquetes):
        if not self._vivo:
            return
        self._catalogo = paquetes
        self._cargando, self._fallo = False, False
        self._recargar_instalados()
        self._rehacer_filtros()
        self._rehacer(anunciar_conteo=True)

    def _catalogo_fallo(self, motivo):
        if not self._vivo:
            return
        self._catalogo, self._fallo, self._cargando = [], True, False
        self._recargar_instalados()
        self._rehacer_filtros()
        self._rehacer()
        self._error(_("No se pudo cargar la lista de paquetes de voces: "
                      "{motivo}. Se muestran solo los paquetes instalados.").format(
                          motivo=motivo))
        self.lista_motores.SetFocus()

    def _recargar_instalados(self):
        self._instalados = paquetes_instalacion.instalados("voz")
        self._entradas = voces_disponibles.ordenar(
            voces_disponibles.reunir(self._catalogo, self._instalados))

    def _rehacer_filtros(self):
        elegido = self._valor(self.cho_idioma, self._valores_idioma)
        opciones = voces_disponibles.opciones_idioma(self._entradas)
        self._valores_idioma = [valor for _texto, valor in opciones]
        self.cho_idioma.Set([texto for texto, _valor in opciones])
        if not self._idioma_tocado:
            elegido = voces_disponibles.idioma_inicial(self._entradas)
        self.cho_idioma.SetSelection(
            self._valores_idioma.index(elegido)
            if elegido in self._valores_idioma else 0)

    @staticmethod
    def _valor(control, valores):
        indice = control.GetSelection()
        return valores[indice] if 0 <= indice < len(valores) else ""

    def _idioma(self):
        return self._valor(self.cho_idioma, self._valores_idioma)

    def _rehacer(self, conservar=None, elegido=None, anunciar_conteo=False):
        if conservar is None:
            fila = self._voz_elegida()
            conservar = self._clave(fila) if fila is not None else None
        self._por_idioma = voces_disponibles.filtrar(self._entradas, self._idioma())
        self._motores = lista_voces.filas_motores(self._por_idioma)
        if not any(motor == self._motor for _texto, motor in self._motores):
            self._motor = self._motores[0][1] if self._motores else ""
        seleccion = next((indice for indice, (_texto, motor)
                          in enumerate(self._motores) if motor == self._motor), None)
        self._motores_pieza.fijar(
            [texto for texto, _motor in self._motores], elegido=seleccion,
            vacio=voces_disponibles.texto_vacio(
                self._cargando, self._fallo, bool(self._idioma())))
        self._filtradas = lista_voces.filas_voces(
            self._por_idioma, self._motor, self._buscado)
        elegida = next((indice for indice, fila in enumerate(self._filtradas)
                        if self._clave(fila) == conservar), None)
        self._voces.fijar(
            [fila.texto for fila in self._filtradas],
            elegido=elegida if elegida is not None else elegido,
            vacio=self._texto_vacio_voces())
        if anunciar_conteo:
            anunciar(ngettext("{n} voz", "{n} voces",
                              len(self._filtradas)).format(n=len(self._filtradas)))
        self._mostrar_seleccion()

    def _texto_vacio_voces(self):
        if self._buscado:
            return _("No hay voces que coincidan con la búsqueda.")
        return voces_disponibles.texto_vacio(
            self._cargando, self._fallo, bool(self._idioma()))

    @staticmethod
    def _clave(fila):
        return (voces_disponibles.identificador(fila.paquete), fila.indice)

    def _voz_elegida(self):
        indice = self._voces.indice()
        if indice is None or not 0 <= indice < len(self._filtradas):
            return None
        return self._filtradas[indice]

    def _paquetes_elegidos(self):
        elegidos, vistos = [], set()
        for indice in self.lista_voces.GetSelections():
            if not 0 <= indice < len(self._filtradas):
                continue
            paquete = self._filtradas[indice].paquete
            clave = voces_disponibles.identificador(paquete)
            if clave not in vistos:
                vistos.add(clave)
                elegidos.append(paquete)
        return elegidos

    def _mostrar_seleccion(self):
        fila = self._voz_elegida()
        self.txt_detalles.SetValue(
            voces_disponibles.detalles(fila.paquete, fila.indice) if fila is not None else "")

    def _al_cambiar_idioma(self, _evento=None):
        self._idioma_tocado = True
        self._motor = ""
        self._rehacer()

    def _al_elegir_motor(self, evento):
        evento.Skip()
        indice = self._motores_pieza.indice()
        self._motor = self._motores[indice][1] if (
            indice is not None and 0 <= indice < len(self._motores)) else ""
        self._rehacer()

    def _al_buscar(self, _evento):
        self._buscado = self.txt_buscar.GetValue()
        self._rehacer()

    def _tecla_buscar(self, evento):
        codigo = evento.GetKeyCode()
        if tecla_escape.es_escape(codigo):
            if self._buscado:
                self.txt_buscar.ChangeValue("")
                self._buscado = ""
                self._rehacer()
                anunciar(_(anuncios_musica.TEXTO_BUSQUEDA_BORRADA))
            else:
                self._al_cerrar()
            return
        if codigo == wx.WXK_DOWN:
            self.lista_voces.SetFocus()
            if self._voces.indice() is None and self._filtradas:
                self.lista_voces.SetSelection(0)
            return
        evento.Skip()

    def _accion_voces(self, accion):
        paquetes = []
        for entrada in self._paquetes_elegidos():
            nombre = voces_disponibles.nombre(entrada)
            if accion == "instalar":
                if entrada.instalado is not None:
                    anunciar(_("{nombre} ya está instalado.").format(nombre=nombre))
                    continue
                if entrada.catalogo is None:
                    continue
            else:
                if entrada.instalado is None:
                    anunciar(_("{nombre} no está instalado.").format(nombre=nombre))
                    continue
                if (entrada.catalogo is None
                        or voces_disponibles.estado_codigo(entrada) != "actualizable"):
                    anunciar(_("No hay actualización disponible para {nombre}.").format(
                        nombre=nombre))
                    continue
            paquetes.append(entrada)
        if paquetes:
            self._empezar(paquetes, accion)
        self._rehacer()
        self.lista_voces.SetFocus()

    def _eliminar_voces(self):
        paquetes = self._paquetes_elegidos()
        if not paquetes:
            return
        indice = self._voces.indice()
        if voces_instalacion.eliminar(
                self, paquetes, indice, self._anunciar, self._error,
                self._rehacer_tras_eliminar):
            self._rehacer()
            self.lista_voces.SetFocus()

    def _rehacer_tras_eliminar(self, _entrada, _indice):
        self._recargar_instalados()
        self._rehacer_filtros()

    def _empezar(self, paquetes, accion):
        if self._espera is not None:
            return
        self._ultimo_porcentaje = None
        voces_instalacion.empezar(
            paquetes, accion, self._crear_espera, self._poner_espera,
            self._aviso_porcentaje, self._preparar_paquete,
            self._terminar_instalacion)
        if self._vivo:
            self._recargar_instalados()
            self._rehacer_filtros()
            self._rehacer()

    def _poner_espera(self, espera):
        self._espera = espera

    def _preparar_paquete(self):
        self._ultimo_porcentaje = None

    def _aviso_porcentaje(self, porcentaje, nombre):
        self._ultimo_porcentaje = voces_instalacion.aviso_porcentaje(
            self._espera, self._ultimo_porcentaje, porcentaje, nombre)

    def _terminar_instalacion(self, texto, sonido):
        voces_instalacion.terminar_instalacion(self._espera, texto, sonido)

    def _vista_previa(self):
        fila = self._voz_elegida()
        if fila is None:
            self._voces.ejecutar("previa")
            return
        listado = voces_disponibles.voces(fila.paquete)
        if not 0 <= fila.indice < len(listado):
            return
        muestra = listado[fila.indice].get("muestra")
        if not muestra:
            anunciar(_("Esta voz no tiene vista previa."))
            return
        try:
            muestra_voz.reproducir(muestra)
        except Exception as error:
            self._error(_("No se pudo reproducir la vista previa: {motivo}.").format(
                motivo=error))

    def _anunciar(self, texto):
        anunciar(texto)

    def _crear_espera(self, titulo, texto, parada):
        return VentanaEspera(self, titulo, texto, parada=parada)

    def _error(self, texto):
        _snd.reproducir("error")
        confirmar.avisar(self, texto, _("Administrar voces"), _("Aceptar"),
                         icono=confirmar.ICON_ERROR)

    def _al_cerrar(self, _evento=None):
        self._vivo = False
        muestra_voz.detener()
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Destroy()
