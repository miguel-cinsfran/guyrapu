# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana para pedir los datos del directo de YouTube antes de transmitir.

Modal pequeña como `DialogoRedactar`: título, descripción, privacidad y las
opciones del directo (latencia, hecho para niños, rebobinar, categoría,
etiquetas y miniatura), que se recuerdan para la próxima vez. Pura salvo wx.
"""

from __future__ import annotations

from datetime import datetime

import wx

from guyrapu.capture import redaccion
from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import obs_prevuelo
from guyrapu.ui import ayuda_manual, formulario, miniatura_directo, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.espera_sonora import EsperaSonora
from guyrapu.youtube import youtube_api
from guyrapu.youtube.emision import (
    CATEGORIAS,
    ETIQUETAS_LATENCIA,
    ETIQUETAS_PRIVACIDAD,
    LATENCIA_INICIAL,
    LATENCIAS,
    PRIVACIDAD_INICIAL,
    PRIVACIDADES,
    EmisionError,
    anuncio_listas,
    opciones_lista,
    resultado_directo,
    titulo_por_defecto,
)

# Traductores: motivo de Cargar listas mientras se cargan las listas.
_MOTIVO_CARGANDO_LISTAS = N_("Cargando las listas")
# Traductores: motivo de Cargar listas sin sesión de YouTube.
_MOTIVO_SIN_SESION = N_("Sin sesión de YouTube")


def ancho_con_barra(ancho, alto_necesario, alto_maximo, ancho_barra):
    """Ancho con margen para la barra vertical si el contenido no cabe."""
    if alto_necesario > alto_maximo:
        return ancho + ancho_barra
    return ancho


class DialogoDirectoYoutube(wx.Dialog):
    def __init__(self, padre, titulo="", descripcion="",
                 privacidad=PRIVACIDAD_INICIAL, revision=None,
                 latencia=LATENCIA_INICIAL, ninos=False, dvr=True,
                 categoria="", etiquetas="", miniatura="", lista="",
                 lista_titulo="", cargar_listas=None, solo_titulo=False,
                 titulo_ventana=""):
        super().__init__(padre, title=titulo_ventana or _("Directo de YouTube"),
                         name="DialogoDirectoYoutube")
        if privacidad not in PRIVACIDADES:
            privacidad = PRIVACIDAD_INICIAL
        if latencia not in LATENCIAS:
            latencia = LATENCIA_INICIAL
        if not (titulo or "").strip():
            titulo = titulo_por_defecto(datetime.now())
        self._datos = None
        self._miniatura = (miniatura or "").strip()
        self._cargar_listas = cargar_listas

        vs = wx.BoxSizer(wx.VERTICAL)
        zona = wx.ScrolledWindow(
            self, style=wx.TAB_TRAVERSAL | wx.VSCROLL)
        zona.SetScrollRate(0, 20)
        self.zona_desplazamiento = zona
        contenido = wx.BoxSizer(wx.VERTICAL)
        self._contenido_datos(zona, contenido, titulo, descripcion,
                              privacidad, latencia, solo_titulo)
        if not solo_titulo:
            self._contenido_opciones(zona, contenido, ninos, dvr, categoria,
                                     etiquetas)
            self._contenido_cierre(zona, contenido, lista, lista_titulo,
                                   revision)

        zona.SetSizer(contenido)
        vs.Add(zona, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
               formulario.MARGEN)

        pie = self._crear_pie(vs)

        self.txt_titulo.SetMinSize((420, -1))
        self._ajustar_tamano(vs, zona, pie)
        self.btn_crear.Bind(wx.EVT_BUTTON, self._al_crear)
        if not solo_titulo:
            self._enlazar_opciones()
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        if revision is not None and obs_prevuelo.problemas_de(revision):
            self.btn_cancelar.SetDefault()
            self.btn_cancelar.SetFocus()
        else:
            self.btn_crear.SetDefault()
            self.txt_titulo.SetFocus()
        paleta.pintar_ventana(self)

    def _crear_pie(self, vs):
        self.btn_crear = wx.Button(self, wx.ID_OK, _("&Transmitir"),
                                   name=_("Transmitir"))
        self.btn_cancelar = wx.Button(self, wx.ID_CANCEL, _("C&ancelar"),
                                      name=_("Cancelar"))
        pie = wx.BoxSizer(wx.VERTICAL)
        formulario.agregar_pie(pie, [self.btn_crear, self.btn_cancelar])
        vs.Add(pie, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
               formulario.MARGEN)
        return pie

    def _ajustar_tamano(self, vs, zona, pie):
        self.SetSizer(vs)
        self.Fit()
        ancho = max(formulario.ANCHO_MINIMO, self.GetSize().width)
        delta = self.GetSize().height - self.GetClientSize().height
        alto_contenido = zona.GetSizer().GetMinSize().height
        alto_pie = pie.GetMinSize().height + formulario.MARGEN
        try:
            indice = wx.Display.GetFromWindow(self)
            if indice == wx.NOT_FOUND:
                indice = 0
            alto_area = wx.Display(indice).GetClientArea().height
        except Exception:
            alto_area = 700
        alto_maximo = min(700, alto_area)
        piso = min(300, alto_maximo)
        try:
            ancho_barra = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
        except Exception:
            ancho_barra = 0
        ancho = ancho_con_barra(
            ancho, alto_contenido + alto_pie + delta, alto_maximo,
            ancho_barra)
        zona.FitInside()
        self.SetSize((ancho, max(min(alto_contenido + alto_pie + delta,
                                     alto_maximo), piso)))
        self.SetMinSize((ancho, piso))
        self.Layout()

    def _contenido_datos(self, zona, contenido, titulo, descripcion,
                           privacidad, latencia, solo_titulo=False):
        rotulo_titulo = wx.StaticText(zona, label=_("Título:"))
        self.txt_titulo = wx.TextCtrl(
            zona, value=titulo, name=_("Título del directo"))
        self.txt_titulo.SetMaxLength(100)
        self.txt_titulo.SelectAll()
        nombre_accesible(self.txt_titulo, _("Título del directo"))
        formulario.agregar_fila(contenido, rotulo_titulo, self.txt_titulo)

        rotulo_descripcion = wx.StaticText(
            zona, label=_("Descripción, opcional:"))
        self.txt_descripcion = wx.TextCtrl(
            zona, value=descripcion or "", style=wx.TE_MULTILINE,
            name=_("Descripción del directo"))
        self.txt_descripcion.SetMinSize(
            (-1, 3 * self.txt_descripcion.GetCharHeight() + 12))
        nombre_accesible(self.txt_descripcion, _("Descripción del directo"))
        formulario.agregar_fila(contenido, rotulo_descripcion,
                                self.txt_descripcion)
        if solo_titulo:
            return

        rotulo_privacidad = wx.StaticText(zona, label=_("Privacidad:"))
        self.cho_privacidad = wx.Choice(
            zona, choices=[_(ETIQUETAS_PRIVACIDAD[p])
                           for p in PRIVACIDADES],
            name=_("Privacidad"))
        self.cho_privacidad.SetSelection(PRIVACIDADES.index(privacidad))
        nombre_accesible(self.cho_privacidad, _("Privacidad"))
        formulario.agregar_fila(contenido, rotulo_privacidad,
                                self.cho_privacidad)

        rotulo_latencia = wx.StaticText(zona, label=_("&Latencia:"))
        self.cho_latencia = wx.Choice(
            zona, choices=[_(ETIQUETAS_LATENCIA[latencia])
                           for latencia in LATENCIAS],
            name=_("Latencia"))
        self.cho_latencia.SetSelection(LATENCIAS.index(latencia))
        nombre_accesible(self.cho_latencia, _("Latencia"))
        formulario.agregar_fila(contenido, rotulo_latencia, self.cho_latencia)

    def _contenido_opciones(self, zona, contenido, ninos, dvr, categoria,
                            etiquetas):
        self.chk_ninos = wx.CheckBox(
            zona, label=_("Creado para &niños (YouTube desactiva el chat)"),
            name=_("Creado para niños"))
        self.chk_ninos.SetValue(bool(ninos))
        nombre_accesible(self.chk_ninos, _("Creado para niños"))

        self.chk_dvr = wx.CheckBox(
            zona, label=_("Permitir re&bobinar el directo"),
            name=_("Permitir rebobinar"))
        self.chk_dvr.SetValue(bool(dvr))
        nombre_accesible(self.chk_dvr, _("Permitir rebobinar"))
        formulario.agregar_casillas(contenido, [self.chk_ninos, self.chk_dvr])

        rotulo_categoria = wx.StaticText(zona, label=_("Cate&goría:"))
        self.cho_categoria = wx.Choice(
            zona, choices=[_(texto) for _id, texto in CATEGORIAS],
            name=_("Categoría"))
        ids = [identificador for identificador, _texto in CATEGORIAS]
        self.cho_categoria.SetSelection(
            ids.index(categoria) if categoria in ids else 0)
        nombre_accesible(self.cho_categoria, _("Categoría"))
        formulario.agregar_fila(contenido, rotulo_categoria, self.cho_categoria)

        rotulo_etiquetas = wx.StaticText(
            zona, label=_("&Etiquetas, separadas por comas:"))
        self.txt_etiquetas = wx.TextCtrl(
            zona, value=etiquetas or "", name=_("Etiquetas"))
        nombre_accesible(self.txt_etiquetas, _("Etiquetas"))
        formulario.agregar_fila(contenido, rotulo_etiquetas, self.txt_etiquetas)

    def _contenido_cierre(self, zona, contenido, lista, lista_titulo,
                          revision):
        rotulo_miniatura = wx.StaticText(zona, label=_("Miniatura:"))
        self.txt_miniatura = wx.TextCtrl(
            zona, value=miniatura_directo.texto_miniatura(self._miniatura),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL,
            name=_("Miniatura"))
        self.txt_miniatura.SetMinSize(
            (-1, self.txt_miniatura.GetCharHeight() + 12))
        nombre_accesible(self.txt_miniatura, _("Miniatura"))
        formulario.agregar_fila(contenido, rotulo_miniatura, self.txt_miniatura)

        fila_miniatura = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_elegir_miniatura = wx.Button(
            zona, label=_("Elegir &miniatura…"), name=_("Elegir miniatura"))
        self.btn_quitar_miniatura = wx.Button(
            zona, label=_("El&iminar miniatura"), name=_("Eliminar miniatura"))
        fila_miniatura.Add(self.btn_elegir_miniatura, 0, wx.RIGHT, formulario.ENTRE_BOTONES)
        fila_miniatura.Add(self.btn_quitar_miniatura, 0)
        formulario.agregar_bloque(contenido, fila_miniatura, junto=True)

        self._opciones_lista, seleccion_lista = opciones_lista(
            None, lista, lista_titulo)
        rotulo_lista = wx.StaticText(zona, label=_("Lista de re&producción:"))
        self.cho_lista = wx.Choice(
            zona, choices=[texto for _id, texto in self._opciones_lista],
            name=_("Lista de reproducción"))
        self.cho_lista.SetSelection(seleccion_lista)
        nombre_accesible(self.cho_lista, _("Lista de reproducción"))
        formulario.agregar_fila(contenido, rotulo_lista, self.cho_lista)
        self.btn_cargar_listas = wx.Button(
            zona, label=_("Ca&rgar listas"), name=_("Cargar listas"))
        formulario.agregar_bloque(contenido, self.btn_cargar_listas, junto=True)

        from guyrapu.obs import obs_prevuelo
        texto_revision = (obs_prevuelo.frase_revision(revision)
                          if revision is not None else "")
        rotulo_revision = wx.StaticText(zona, label=_("Revisión de OBS:"))
        self.txt_revision = wx.TextCtrl(
            zona, value=texto_revision,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            name=_("Revisión de OBS"))
        self.txt_revision.SetMinSize(
            (-1, 3 * self.txt_revision.GetCharHeight() + 12))
        nombre_accesible(self.txt_revision, _("Revisión de OBS"))
        formulario.agregar_fila(contenido, rotulo_revision, self.txt_revision)

    def _enlazar_opciones(self):
        self.btn_elegir_miniatura.Bind(
            wx.EVT_BUTTON,
            lambda _event: miniatura_directo.elegir_miniatura(self))
        self.btn_quitar_miniatura.Bind(
            wx.EVT_BUTTON,
            lambda _event: miniatura_directo.quitar_miniatura(self))
        self.btn_cargar_listas.Bind(wx.EVT_BUTTON, self._al_cargar_listas)
        self._fijar_motivo(_MOTIVO_SIN_SESION if self._cargar_listas is None else "")

    def _fijar_motivo(self, motivo) -> None:
        self._motivo = motivo
        self.btn_cargar_listas.SetLabel(redaccion.etiqueta_con_motivo(_("Ca&rgar listas"), _(motivo) if motivo else ""))

    @property
    def datos(self):
        return self._datos

    def _privacidad_elegida(self) -> str:
        return PRIVACIDADES[self.cho_privacidad.GetSelection()]

    def _latencia_elegida(self) -> str:
        return LATENCIAS[self.cho_latencia.GetSelection()]

    def _categoria_elegida(self) -> str:
        return CATEGORIAS[self.cho_categoria.GetSelection()][0]

    def _opcion_lista_elegida(self) -> tuple[str, str]:
        indice = self.cho_lista.GetSelection()
        if indice < 0 or indice >= len(self._opciones_lista):
            return "", ""
        return self._opciones_lista[indice]

    def _espera_listas(self):
        if not hasattr(self, "_espera"):
            self._espera = EsperaSonora(self)
        return self._espera

    def _al_cargar_listas(self, _event) -> None:
        if self._motivo:
            return anunciar(f"{_(self._motivo)}.")
        self._fijar_motivo(_MOTIVO_CARGANDO_LISTAS)
        self._espera_listas().empezar()
        anunciar(_("Cargando las listas."))

        def _traer():
            try:
                listas = self._cargar_listas()
            except Exception as exc:
                wx.CallAfter(self._listas_fallo, exc)
                return
            wx.CallAfter(self._listas_ok, listas)

        diagnostico.crear_hilo(_traer, "ListasYouTube").start()

    def _listas_ok(self, listas) -> None:
        if not self:
            return
        self._fijar_motivo("")
        id_elegido, titulo_elegido = self._opcion_lista_elegida()
        self._opciones_lista, seleccion = opciones_lista(
            listas, id_elegido, titulo_elegido)
        self.cho_lista.SetItems([texto for _id, texto in self._opciones_lista])
        self.cho_lista.SetSelection(seleccion)
        self._espera_listas().terminar("listo")
        anunciar(anuncio_listas(len(listas)))

    def _listas_fallo(self, exc) -> None:
        if not self:
            return
        self._fijar_motivo("")
        self._espera_listas().terminar("error")
        anunciar(_("No se pudieron cargar las listas: {detalle}").format(
            detalle=youtube_api.mensaje_error_api(exc)))

    def _valores_directo(self) -> tuple:
        if not hasattr(self, "cho_privacidad"):
            return (self.txt_titulo.GetValue(),
                    self.txt_descripcion.GetValue(),
                    PRIVACIDAD_INICIAL)
        return (self.txt_titulo.GetValue(),
                self.txt_descripcion.GetValue(),
                self._privacidad_elegida(),
                self._latencia_elegida(),
                self.chk_ninos.GetValue(),
                self.chk_dvr.GetValue(),
                self._categoria_elegida(),
                self.txt_etiquetas.GetValue(),
                self._miniatura,
                *self._opcion_lista_elegida())

    def _al_crear(self, _event) -> None:
        try:
            self._datos = resultado_directo(*self._valores_directo())
        except EmisionError as exc:
            anunciar(str(exc))
            self.txt_titulo.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def _al_tecla(self, event) -> None:
        if not ayuda_manual.atender_f1(self, event, "transmitir"):
            tecla_escape.cancelar_si_escape(self, event)


def pedir_datos_directo(padre, titulo="", descripcion="",
                        privacidad=PRIVACIDAD_INICIAL, revision=None,
                        latencia=LATENCIA_INICIAL, ninos=False, dvr=True,
                        categoria="", etiquetas="", miniatura="", lista="",
                        lista_titulo="", cargar_listas=None,
                        solo_titulo=False, titulo_ventana=""):
    """Pide los datos del directo. Devuelve el dict o None si se cancela."""
    dialogo = DialogoDirectoYoutube(
        padre, titulo, descripcion, privacidad, revision, latencia,
        ninos, dvr, categoria, etiquetas, miniatura, lista, lista_titulo,
        cargar_listas, solo_titulo, titulo_ventana)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return dialogo.datos
        return None
    finally:
        dialogo.Destroy()
