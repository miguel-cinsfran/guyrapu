# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana Administrar voces: catálogo, vista previa e instalación."""
from __future__ import annotations
import threading
import wx
from guyrapu.core import (config, diagnostico, paquetes_catalogo,
                          paquetes_instalacion, red, voces_disponibles)
from guyrapu.core.idioma import _, ngettext, pgettext
from guyrapu.ui import confirmar, paleta
from guyrapu.ui.accesibilidad import anunciar, entregar_intro, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta
from guyrapu.ui.ventana_espera import VentanaEspera
from guyrapu.voice import muestra_voz, sound_player as _snd
from guyrapu.voice.proveedores import PROVEEDORES
logger = diagnostico.obtener_logger(__name__)

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
        self._valores_idioma, self._valores_motor = [""], [""]
        self._catalogo, self._instalados = [], []
        self._entradas, self._filtradas = [], []
        self._crear_controles()
        paleta.pintar_ventana(self)
        self.Centre()
        self.Bind(wx.EVT_CLOSE, self._al_cerrar)
        self._recargar_instalados()
        self._rehacer_filtros()
        self._rehacer()
        self.lista_paquetes.SetFocus()
        self._leer_catalogo()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(fila_label(self, _("&Idioma:")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.cho_idioma = wx.Choice(self, name=_("Idioma"))
        self.cho_idioma.Bind(wx.EVT_CHOICE, lambda e: self._al_cambiar_filtro(True))
        vs.Add(self.cho_idioma, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(fila_label(self, _("&Motor de voz:")), 0, wx.LEFT | wx.RIGHT, 10)
        self.cho_motor = wx.Choice(self, name=_("Motor de voz"))
        self.cho_motor.Bind(wx.EVT_CHOICE, lambda e: self._al_cambiar_filtro(False))
        vs.Add(self.cho_motor, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(fila_label(self, _("&Paquetes de voces:")), 0,
               wx.LEFT | wx.RIGHT, 10)
        self.lista_paquetes = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name=_("Paquetes de voces"))
        nombre_accesible(self.lista_paquetes, _("Paquetes de voces"))
        self.lista_paquetes.Bind(wx.EVT_LISTBOX, self._al_elegir_paquete)
        self._paquetes = ListaConAcciones(self.lista_paquetes, [
            Accion("instalar", _("In&stalar"), lambda: self._accion("instalar")),
            Accion("actualizar", _("&Actualizar"),
                   lambda: self._accion("actualizar")),
            Accion("eliminar", pgettext("paquete de voces", "&Eliminar"), self._eliminar,
                   tecla="suprimir")], "")
        entregar_intro(self.lista_paquetes, self._al_intro_paquete)
        vs.Add(self.lista_paquetes, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(fila_label(self, _("De&talles:")), 0, wx.LEFT | wx.RIGHT, 10)
        self.txt_detalles = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL
            | wx.TE_RICH2, name=_("Detalles"))
        self.txt_detalles.SetMinSize((-1, 120))
        vs.Add(self.txt_detalles, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        for clave, etiqueta in (("instalar", _("In&stalar")),
                                ("actualizar", _("&Actualizar")),
                                ("eliminar", pgettext("paquete de voces", "&Eliminar"))):
            boton = wx.Button(self, label=etiqueta,
                              name=nombre_de_etiqueta(etiqueta))
            boton.Bind(wx.EVT_BUTTON,
                       lambda _e, clave=clave: self._paquetes.ejecutar(clave))
            setattr(self, "btn_" + clave, boton)
            fila.Add(boton, 0, wx.RIGHT, 6)
        vs.Add(fila, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._crear_voces(vs)
        self.SetSizer(vs)

    def _crear_voces(self, vs):
        vs.Add(fila_label(self, _("&Voces del paquete:")), 0,
               wx.LEFT | wx.RIGHT, 10)
        self.lista_voces = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name=_("Voces del paquete"))
        nombre_accesible(self.lista_voces, _("Voces del paquete"))
        self._lista_voces = ListaConAcciones(
            self.lista_voces,
            [Accion("previa", _("Vista p&revia de voz"), self._vista_previa,
                    tecla="intro")], _("No hay voces en este paquete."))
        vs.Add(self.lista_voces, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.btn_previa = wx.Button(
            self, label=_("Vista p&revia de voz"), name=_("Vista previa de voz"))
        self.btn_previa.Bind(
            wx.EVT_BUTTON, lambda _e: self._lista_voces.ejecutar("previa"))
        vs.Add(self.btn_previa, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.btn_cerrar = wx.Button(self, wx.ID_CANCEL, _("&Cerrar"),
                                    name=_("Cerrar"))
        self.btn_cerrar.Bind(wx.EVT_BUTTON, self._al_cerrar)
        vs.Add(self.btn_cerrar, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

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
        conservar = self._id_elegido()
        self._catalogo = paquetes
        self._cargando, self._fallo = False, False
        self._recargar_instalados()
        self._rehacer_filtros()
        self._rehacer(conservar=conservar, anunciar_conteo=True)

    def _catalogo_fallo(self, motivo):
        if not self._vivo:
            return
        conservar = self._id_elegido()
        self._catalogo, self._fallo, self._cargando = [], True, False
        self._recargar_instalados()
        self._rehacer_filtros()
        self._rehacer(conservar=conservar)
        self._error(_("No se pudo cargar la lista de paquetes de voces: "
                      "{motivo}. Se muestran solo los paquetes instalados.").format(
                          motivo=motivo))
        self.lista_paquetes.SetFocus()

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
        elegido = self._valor(self.cho_motor, self._valores_motor)
        opciones = voces_disponibles.opciones_motor(self._entradas)
        self._valores_motor = [valor for _texto, valor in opciones]
        self.cho_motor.Set([texto for texto, _valor in opciones])
        self.cho_motor.SetSelection(
            self._valores_motor.index(elegido)
            if elegido in self._valores_motor else 0)

    @staticmethod
    def _valor(control, valores):
        indice = control.GetSelection()
        return valores[indice] if 0 <= indice < len(valores) else ""

    def _filtrar_actual(self):
        return voces_disponibles.filtrar(
            self._entradas,
            self._valor(self.cho_idioma, self._valores_idioma),
            self._valor(self.cho_motor, self._valores_motor))

    def _rehacer(self, conservar=None, elegido=None, anunciar_conteo=False):
        self._filtradas = self._filtrar_actual()
        if elegido is None and conservar is not None:
            elegido = next(
                (indice for indice, entrada in enumerate(self._filtradas)
                 if voces_disponibles.identificador(entrada) == conservar), None)
        textos = [voces_disponibles.fila(entrada) for entrada in self._filtradas]
        self._paquetes.fijar(
            textos, elegido=elegido,
            vacio=voces_disponibles.texto_vacio(
                self._cargando, self._fallo,
                bool(self._valor(self.cho_idioma, self._valores_idioma)
                     or self._valor(self.cho_motor, self._valores_motor))))
        if anunciar_conteo:
            anunciar(ngettext(
                "{n} paquete de voces", "{n} paquetes de voces", len(textos)
            ).format(n=len(textos)))
        self._mostrar_seleccion()

    def _elegida(self):
        indice = self._paquetes.indice()
        if indice is None or not 0 <= indice < len(self._filtradas):
            return None
        return self._filtradas[indice]

    def _id_elegido(self):
        entrada = self._elegida()
        return voces_disponibles.identificador(entrada) if entrada else None

    def _mostrar_seleccion(self):
        entrada = self._elegida()
        if entrada is None:
            self.txt_detalles.SetValue("")
            self._lista_voces.fijar([])
            return
        self.txt_detalles.SetValue(voces_disponibles.detalles(entrada))
        self._lista_voces.fijar(voces_disponibles.filas_voces(entrada))

    def _al_elegir_paquete(self, evento):
        evento.Skip()
        self._mostrar_seleccion()

    def _al_cambiar_filtro(self, es_idioma):
        if es_idioma:
            self._idioma_tocado = True
        self._rehacer(conservar=self._id_elegido())

    def _al_intro_paquete(self, _evento):
        entrada = self._elegida()
        if entrada is None:
            self._paquetes.ejecutar("instalar")
        elif (entrada.instalado is not None
              and voces_disponibles.estado_codigo(entrada) == "actualizable"):
            self._accion("actualizar")
        else:
            self._accion("instalar")

    def _accion(self, accion):
        entrada = self._elegida()
        if entrada is None:
            return
        nombre = voces_disponibles.nombre(entrada)
        if accion == "instalar":
            if entrada.instalado is not None:
                anunciar(_("{nombre} ya está instalado.").format(nombre=nombre))
            elif entrada.catalogo is not None:
                self._empezar(entrada.catalogo, accion, nombre)
            return
        if entrada.instalado is None:
            anunciar(_("{nombre} no está instalado.").format(nombre=nombre))
        elif (entrada.catalogo is None
              or voces_disponibles.estado_codigo(entrada) != "actualizable"):
            anunciar(_("No hay actualización disponible para {nombre}.").format(
                nombre=nombre))
        else:
            self._empezar(entrada.catalogo, accion, nombre)

    def _empezar(self, paquete, accion, nombre):
        if self._espera is not None:
            return
        parada = threading.Event()
        titulo = (_("Instalar {nombre}") if accion == "instalar"
                  else _("Actualizar {nombre}")).format(nombre=nombre)
        espera = VentanaEspera(
            self, titulo, _("Descargando {nombre}.").format(nombre=nombre),
            parada=parada)
        self._espera = espera
        self._ultimo_porcentaje = None
        def aviso(porcentaje):
            wx.CallAfter(self._aviso_porcentaje, porcentaje, nombre)
        def trabajar():
            resultado = paquetes_instalacion.instalar(
                paquete, aviso, parada.is_set)
            wx.CallAfter(self._terminar_instalacion, resultado, accion, nombre)
        diagnostico.crear_hilo(trabajar, titulo).start()
        try:
            espera.ShowModal()
        finally:
            espera.Destroy()
            self._espera = None
        if self._vivo:
            self._recargar_instalados()
            self._rehacer_filtros()
            self._rehacer(conservar=paquete.get("id"))
            self.lista_paquetes.SetFocus()

    def _aviso_porcentaje(self, porcentaje, nombre):
        if porcentaje is None or porcentaje == self._ultimo_porcentaje:
            return
        if (self._ultimo_porcentaje is not None
                and porcentaje < self._ultimo_porcentaje + 10
                and porcentaje != 100):
            return
        self._ultimo_porcentaje = porcentaje
        if self._espera is not None:
            try:
                self._espera.estado(
                    _("Descargando {nombre}: {porcentaje} por ciento").format(
                        nombre=nombre, porcentaje=porcentaje))
            except RuntimeError as error:
                logger.debug("la espera ya no existe: %s", error)

    def _terminar_instalacion(self, resultado, accion, nombre):
        if self._espera is None:
            return
        try:
            if resultado.cancelada:
                self._espera.terminar(_("Instalación cancelada."))
            elif resultado.correcta:
                frase = (_("Actualización completada: {nombre}.")
                         if accion == "actualizar"
                         else _("Instalación completada: {nombre}."))
                self._espera.terminar(frase.format(nombre=nombre))
                _snd.reproducir("listo")
            else:
                self._espera.terminar(
                    _("No se pudo instalar {nombre}: {motivo}. Revisa la "
                      "conexión a internet y vuelve a intentarlo.").format(
                          nombre=nombre,
                          motivo=resultado.motivo or _("motivo desconocido")),
                    error=True)
        except RuntimeError as error:
            logger.debug("la espera ya no existe: %s", error)

    def _eliminar(self):
        entrada = self._elegida()
        if entrada is None:
            return
        nombre = voces_disponibles.nombre(entrada)
        if entrada.instalado is None:
            anunciar(_("{nombre} no está instalado.").format(nombre=nombre))
            return
        if not confirmar.preguntar(
                self,
                _("¿Eliminar {nombre}? Se liberan {tamano} del disco. Para "
                  "volver a usarlo, hay que instalarlo de nuevo.").format(
                      nombre=nombre, tamano=voces_disponibles.tamano(entrada)),
                _("Eliminar paquete de voces"),
                pgettext("paquete de voces", "&Eliminar"), _("&Cancelar"),
                predeterminado_si=False):
            return
        indice = self._paquetes.indice()
        resultado = paquetes_instalacion.borrar(
            voces_disponibles.identificador(entrada), "voz")
        if not resultado.correcta:
            self._error(_("No se pudo eliminar {nombre}: {motivo}.").format(
                nombre=nombre,
                motivo=resultado.motivo or _("motivo desconocido")))
            return
        anunciar(_("Paquete eliminado: {nombre}.").format(nombre=nombre))
        self._recargar_instalados()
        self._rehacer_filtros()
        restantes = self._filtrar_actual()
        identificador = voces_disponibles.identificador(entrada)
        if any(voces_disponibles.identificador(otra) == identificador
               for otra in restantes):
            self._rehacer(conservar=identificador)
        else:
            self._rehacer(elegido=min(
                indice if indice is not None else 0,
                max(0, len(restantes) - 1)))
        self.lista_paquetes.SetFocus()

    def _vista_previa(self):
        indice = self._lista_voces.indice()
        entrada = self._elegida()
        if indice is None or entrada is None:
            self._lista_voces.ejecutar("previa")
            return
        listado = voces_disponibles.voces(entrada)
        if not 0 <= indice < len(listado):
            return
        muestra = listado[indice].get("muestra")
        if not muestra:
            anunciar(_("Esta voz no tiene vista previa."))
            return
        try:
            muestra_voz.reproducir(muestra)
        except Exception as error:
            self._error(_("No se pudo reproducir la vista previa: {motivo}.").format(
                motivo=error))

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
