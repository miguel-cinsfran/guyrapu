# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Música del diálogo de Preferencias.

Dueña de sus controles y de su guardado propio. El diálogo la construye
por composición y copia solo los controles que lee su tabla de opciones
simples.
"""

from __future__ import annotations

import wx

from guyrapu.core import diagnostico, musica_decir
from guyrapu.core import config as cfg
from guyrapu.core.idioma import _
from guyrapu.music import atenuacion
from guyrapu.ui import formulario, opciones_musica
from guyrapu.ui.accesibilidad import ContadorAccesible, anunciar, nombre_accesible
from guyrapu.ui.deslizador import deslizador_accesible
from guyrapu.ui.tema import _T, _tc
from guyrapu.ui.gui_descargas import nombrar_selector_carpeta
from guyrapu.ui.preferencias_comun import EleccionTexto, crear_panel, fila_label


# Filas de música de `_OPCIONES_SIMPLES` en `gui_preferencias`: misma tabla, mismo orden.
OPCIONES_MUSICA = (
    ("chk_musica_aleatorio", "musica", "aleatorio", "musica_aleatorio", bool, False),
    ("chk_musica_repetir", "musica", "repetir", "musica_repetir", str, "no"),
    ("chk_musica_retomar", "musica", "retomar", "musica_retomar", bool, True),
    ("sp_musica_cruce", "musica", "cruce", "musica_cruce", int, 6),
    ("cho_musica_decir", "musica", "decir", "musica_decir", str, "titulo"),
    ("chk_musica_decir_pausa", "musica", "decir_pausa", "musica_decir_pausa", bool, True),
    ("sp_musica_volumen", "musica", "volumen", "musica_volumen", int, 50),
    ("chk_musica_normalizar", "musica", "normalizar", "musica_normalizar", bool, True),
    ("chk_musica_preguntar_igualar", "musica", "preguntar_igualar", "musica_preguntar_igualar", bool, True),
) + tuple(
    (f"chk_musica_atenuar_{fuente.id}", "musica", f"atenuar_{fuente.id}",
     f"musica_atenuar_{fuente.id}", bool, fuente.fabrica)
    for fuente in atenuacion.FUENTES
) + (
    ("sp_musica_volumen_atenuado", "musica", "volumen_atenuado",
     "musica_volumen_atenuado", int, atenuacion.VOLUMEN_FABRICA),
    ("chk_musica_atajos_globales", "musica", "atajos_globales", "musica_atajos_globales", bool, False),
    ("chk_musica_teclas_multimedia", "musica", "teclas_multimedia",
     "musica_teclas_multimedia", bool, True),
)


class PaginaMusica:
    """Página Música: carpeta, orden, repetición, aviso, volumen, igualación y salida."""

    def __init__(self, ventana, config):
        self._ventana = ventana
        self._config = config

    def construir(self, parent):
        p = crear_panel(parent, "PagMusica")
        vs = wx.BoxSizer(wx.VERTICAL)
        self._musica_carpeta(p, vs)
        self._musica_orden(p, vs)
        self._musica_anuncios(p, vs)
        self._musica_audio(p, vs)
        self._musica_atajos(p, vs)
        formulario.armar_pagina(p, vs)
        return p

    def _musica_carpeta(self, p, vs):
        rotulo = fila_label(p, _("Carpeta de &música:"))
        carpeta = str(self._config.get("musica_carpeta", "") or "")
        self.dir_musica_carpeta = wx.DirPickerCtrl(
            p, path=carpeta, name=_("Carpeta de música"),
            message=_("Elige la carpeta de música"))
        nombrar_selector_carpeta(self.dir_musica_carpeta)
        # La función nombra el campo para las descargas; acá el campo es la
        # carpeta de música.
        if hasattr(self.dir_musica_carpeta, "GetTextCtrl"):
            nombre_accesible(self.dir_musica_carpeta.GetTextCtrl(),
                             _("Carpeta de música"))
        formulario.agregar_fila(vs, rotulo, self.dir_musica_carpeta)

    def _musica_orden(self, p, vs):
        self.chk_musica_aleatorio = wx.CheckBox(
            p, label=_("Orden &aleatorio"),
            name="MusicaAleatorio")
        self.chk_musica_aleatorio.SetForegroundColour(_T.text)
        formulario.agregar_casillas(vs, (self.chk_musica_aleatorio,))

        rotulo = fila_label(p, _("&Repetir:"))
        # Traductores: opción de no repetir la música.
        self.chk_musica_repetir = EleccionTexto(
            p, (("no", _("No")), ("todo", _("Toda la cola")),
                 ("tema", _("Esta canción"))),
            normalizar=cfg.normalizar_repetir, name=_("Repetir la música"))
        _tc(self.chk_musica_repetir)
        formulario.agregar_fila(vs, rotulo, self.chk_musica_repetir)

        self.chk_musica_retomar = wx.CheckBox(
            p, label=_("Recordar ú&ltima lista al abrir"),
            name="MusicaRetomar")
        self.chk_musica_retomar.SetForegroundColour(_T.text)
        formulario.agregar_casillas(vs, (self.chk_musica_retomar,))

        rotulo = fila_label(p, _("&Fundido entre canciones, en segundos:"))
        self.sp_musica_cruce = ContadorAccesible(
            p, min=0, max=12,
            name=_("Fundido entre canciones, en segundos"))
        formulario.agregar_fila(vs, rotulo, self.sp_musica_cruce, numerico=True)

    def _musica_anuncios(self, p, vs):
        rotulo = fila_label(p, _("Anunciar al cambiar &de canción:"))
        # Traductores: no decir nada al cambiar de canción.
        self.cho_musica_decir = EleccionTexto(
            p, (("nada", _("Nada")), ("titulo", _("El título")),
                ("titulo_artista", _("El título y el artista")), ("artista", _("Solo el artista"))),
            normalizar=musica_decir.normalizar, name=_("Anunciar al cambiar de canción"))
        _tc(self.cho_musica_decir)
        formulario.agregar_fila(vs, rotulo, self.cho_musica_decir)
        self.chk_musica_decir_pausa = wx.CheckBox(
            p, label=_("A&nunciar pausa, reanudación y vuelta al comienzo"),
            name="MusicaDecirPausa")
        self.chk_musica_decir_pausa.SetForegroundColour(_T.text)
        formulario.agregar_casillas(vs, (self.chk_musica_decir_pausa,))

    def _musica_audio(self, p, vs):
        rotulo = fila_label(p, _("&Volumen de la música:"))
        self.sp_musica_volumen = deslizador_accesible(
            p, minimo=0, maximo=100, inicial=0, paso=1,
            nombre=_("Volumen de la música"))
        formulario.agregar_fila(vs, rotulo, self.sp_musica_volumen,
                                expandir=False)

        self._casilla_igualar(p, vs)
        self._atenuacion(p, vs)

        # Al abrir no se consulta VLC: la lista se arma solo con la salida
        # guardada (o la predeterminada) y se completa con el botón.
        rotulo = fila_label(p, _("Salida de a&udio de la música:"))
        etiquetas, identificadores, seleccion = opciones_musica.opciones_salida(
            str(self._config.get("musica_salida", "") or ""),
            str(self._config.get("musica_salida_nombre", "") or ""), [])
        self._musica_salidas_ids = identificadores
        self.cho_musica_salida = wx.Choice(
            p, choices=etiquetas, name=_("Salida de audio de la música"))
        self.cho_musica_salida.SetSelection(seleccion)
        formulario.agregar_fila(vs, rotulo, self.cho_musica_salida)

        self.btn_buscar_salidas = wx.Button(
            p, label=_("&Buscar salidas de audio"),
            name=_("Buscar salidas de audio"))
        formulario.agregar_fila(vs, None, self.btn_buscar_salidas,
                                expandir=False)
        self.btn_buscar_salidas.Bind(wx.EVT_BUTTON, self._buscar_salidas)

    def _casilla_igualar(self, p, vs):
        self.chk_musica_normalizar = wx.CheckBox(
            p, label=_("&Igualar volumen de las canciones"),
            name=_("Igualar volumen de las canciones"))
        self.chk_musica_normalizar.SetForegroundColour(_T.text)

        self.chk_musica_preguntar_igualar = wx.CheckBox(
            p, label=_("Pr&eguntar al abrir Música si igualar el volumen"),
            name=_("Preguntar al abrir Música si igualar el volumen"))
        self.chk_musica_preguntar_igualar.SetForegroundColour(_T.text)
        formulario.agregar_casillas(vs, (
            self.chk_musica_normalizar, self.chk_musica_preguntar_igualar))

    def _atenuacion(self, p, vs):
        rotulo = fila_label(p, _("V&olumen de la música al bajarla:"))
        self.sp_musica_volumen_atenuado = deslizador_accesible(
            p, minimo=0, maximo=100, inicial=atenuacion.VOLUMEN_FABRICA,
            paso=1, nombre=_("Volumen de la música al bajarla"))
        formulario.agregar_fila(
            vs, rotulo, self.sp_musica_volumen_atenuado, expandir=False)

        casillas = []
        for fuente in atenuacion.FUENTES:
            nombre = _(fuente.rotulo)
            casilla = wx.CheckBox(
                p, label=nombre, name=nombre.replace("&", ""))
            casilla.SetForegroundColour(_T.text)
            setattr(self, f"chk_musica_atenuar_{fuente.id}", casilla)
            casillas.append(casilla)
        formulario.agregar_casillas(vs, casillas)

    def _musica_atajos(self, p, vs):
        self.chk_musica_atajos_globales = wx.CheckBox(
            p, label=_("Usar atajos de música en cualquier a&plicación"),
            name="MusicaAtajosGlobales")
        self.chk_musica_atajos_globales.SetForegroundColour(_T.text)

        self.chk_musica_teclas_multimedia = wx.CheckBox(
            p, label=_("Usar &teclas multimedia del teclado"),
            name=_("Usar teclas multimedia del teclado"))
        self.chk_musica_teclas_multimedia.SetForegroundColour(_T.text)
        formulario.agregar_casillas(vs, (
            self.chk_musica_atajos_globales,
            self.chk_musica_teclas_multimedia))

    def _buscar_salidas(self, event):
        # Consultar libVLC puede tardar, por eso nunca corre en la interfaz.
        def consultar():
            try:
                from guyrapu.music import consultas_vlc
                salidas = consultas_vlc.salidas_audio()
            except Exception:
                salidas = []
            wx.CallAfter(self._salidas_encontradas, salidas)

        diagnostico.crear_hilo(consultar, "SalidasAudioPrefs").start()

    def _salidas_encontradas(self, salidas):
        if not self._ventana:   # el diálogo pudo cerrarse mientras libVLC respondía
            return
        elegida = self.cho_musica_salida.GetSelection()
        if 0 <= elegida < len(self._musica_salidas_ids):
            elegida_id = self._musica_salidas_ids[elegida]
        else:
            elegida_id = ""
        elegida_nombre = ("" if not elegida_id
                          else self.cho_musica_salida.GetStringSelection())
        etiquetas, identificadores, seleccion = opciones_musica.opciones_salida(
            elegida_id, elegida_nombre, salidas or [])
        self._musica_salidas_ids = identificadores
        self.cho_musica_salida.Set(etiquetas)
        self.cho_musica_salida.SetSelection(seleccion)
        cantidad = len({ident for ident, _nombre in (salidas or []) if ident})
        if cantidad == 1:
            anunciar(_("Se encontró 1 salida de audio"))
        elif cantidad:
            anunciar(_("Se encontraron {cantidad} salidas de audio").format(
                cantidad=cantidad))
        else:
            anunciar(_("No se encontraron salidas de audio"))

    def guardar(self, fijar, en_memoria):
        # La carpeta se guarda codificada igual que la lee el cargador; la
        # salida guarda su id y su nombre para no perderla.
        carpeta_musica = self.dir_musica_carpeta.GetPath()
        fijar("musica", "carpeta", cfg.codificar_texto_ini(carpeta_musica))
        en_memoria["musica_carpeta"] = carpeta_musica
        elegida_musica = self.cho_musica_salida.GetSelection()
        if 0 <= elegida_musica < len(self._musica_salidas_ids):
            salida_musica = self._musica_salidas_ids[elegida_musica]
        else:
            salida_musica = ""
        nombre_salida = ("" if not salida_musica
                         else self.cho_musica_salida.GetStringSelection())
        fijar("musica", "salida", salida_musica)
        en_memoria["musica_salida"] = salida_musica
        fijar("musica", "salida_nombre", cfg.codificar_texto_ini(nombre_salida))
        en_memoria["musica_salida_nombre"] = nombre_salida
