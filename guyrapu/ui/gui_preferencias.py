# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Diálogo de Preferencias por categorías (accesible).

Cada categoría se construye recién al elegirla. Guardar escribe solo las
construidas con `config.guardar_opciones` y actualiza la config en memoria.
"""

from __future__ import annotations

from functools import partial

import wx

from guyrapu.core import avisos_preferencias
from guyrapu.core import diagnostico
from guyrapu.core import config as cfg
from guyrapu.core import paths
from guyrapu.core.ini_tipado import separar_por_comas
from guyrapu.core.idioma import N_, _
from guyrapu.ui import atajos_captura, ayuda_manual, confirmar
from guyrapu.voice import sound_player as _snd
from guyrapu.ui.gui import _T, _tc, nombre_accesible
from guyrapu.ui.libro_perezoso import LibroPerezoso
from guyrapu.ui import paleta
from guyrapu.ui.preferencias_comun import (
    ajustar_ancho_categorias, crear_panel, fila_label)
from guyrapu.ui.preferencias_api import PaginaApi
from guyrapu.ui.preferencias_atajos import PaginaAtajos
from guyrapu.ui.preferencias_general import OPCIONES_GENERAL, PaginaGeneral, ofrecer_reinicio
from guyrapu.ui.preferencias_transmision import PaginaTransmision
from guyrapu.ui.preferencias_camara import PaginaCamara
from guyrapu.ui.preferencias_musica import OPCIONES_MUSICA, PaginaMusica
from guyrapu.ui.preferencias_descargas import PaginaDescargasPreferencias
from guyrapu.ui.preferencias_lectura import OPCIONES_LECTURA, PaginaLectura
from guyrapu.ui.preferencias_eventos import OPCIONES_EVENTOS, PaginaEventos
from guyrapu.ui.preferencias_ia import PaginaIA
from guyrapu.ui.preferencias_sonidos import PaginaSonidos
from guyrapu.ui.preferencias_voz import PaginaVoz
from guyrapu.ui.preferencias_interfaz import OPCIONES_INTERFAZ, PaginaInterfaz
from guyrapu.ui.preferencias_cola import OPCIONES_COLA, PaginaCola
from guyrapu.ui.preferencias_conexion import OPCIONES_CONEXION, PaginaConexion
from guyrapu.ui.preferencias_reproductor import OPCIONES_REPRODUCTOR, PaginaReproductor
from guyrapu.ui.preferencias_estado import PaginaEstado
from guyrapu.ui.preferencias_filtros import PaginaFiltros

logger = diagnostico.obtener_logger(__name__)

# Traductores: nombre de la categoría de Preferencias con la sesión de YouTube.
CATEGORIA_YOUTUBE = N_("YouTube")

# Opciones que se guardan y se cargan con el mismo molde (leer el control,
# escribir el texto en el ini y copiar el valor a la config en memoria; y al
# revés, volcar la config en el control). Lo que no sigue ese molde va a mano
# en `_on_guardar`. El último campo es el valor de fábrica de
# `config_predeterminada`, ya convertido al tipo de la fila: es el que se
# escribe en el control cuando la config no trae la clave o la trae ilegible.
# `tests/test_preferencias_tabla.py` lo compara con el de fábrica para que no
# se separen.
_OPCIONES_SIMPLES = (
    OPCIONES_INTERFAZ
    + OPCIONES_REPRODUCTOR
) + OPCIONES_GENERAL + OPCIONES_LECTURA + OPCIONES_EVENTOS + (
    OPCIONES_COLA
    + OPCIONES_CONEXION
    + (
        ("chk_buscar_actualizaciones", "actualizaciones", "buscar_al_iniciar", "buscar_actualizaciones_al_iniciar", bool, True),
        ("chk_confirmar_salida", "ui", "confirmar_salida", "confirmar_salida", bool, True),
        ("chk_sonido_inicio", "ui", "sonido_inicio", "sonido_inicio", bool, True),
        ("chk_registro_detallado", "diagnostico", "registro_detallado", "registro_detallado", bool, True),
        ("sp_puerto_overlay", "overlay", "puerto", "overlay_puerto", int, 8730),
        ("chk_avisar_sobrecarga", "transmision", "avisar_sobrecarga", "avisar_sobrecarga", bool, True),
        ("chk_titulo_estado_obs", "transmision", "titulo_estado_obs", "titulo_estado_obs", bool, False),
    )
) + OPCIONES_MUSICA


class PreferenciasDialog(wx.Dialog):

    def __init__(self, parent, config: dict, perezosa: bool = False):
        # Redimensionable: quien ve poco puede agrandarlo; las páginas se
        # desplazan solas si no caben.
        super().__init__(parent, title=_("Preferencias"), size=(720, 600),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                         name="DialogoPreferencias")
        self._config = config
        self._ruta = paths.config_ini()
        self._cambios = False
        self._pendientes = []
        self._filas_cargadas = set()
        self.avisos = []
        self._build_ui(perezosa)
        ayuda_manual.enlazar(self, "preferencias")
        self._ajustar_minimo()
        paleta.pintar_ventana(self)
        self.Centre()

    def _build_ui(self, perezosa):
        panel = wx.Panel(self, name="PanelPreferencias")
        vs = wx.BoxSizer(wx.VERTICAL)

        # La lista se anuncia sola al recorrerla, a diferencia de las pestañas.
        self.nb = wx.Listbook(panel, name=_("Categorías de preferencias"))
        self.lista_categorias = self.nb.GetListView()
        # Traductores: nombre accesible de la lista de categorías.
        nombre_accesible(self.lista_categorias, _("Categorías"))
        _tc(self.lista_categorias, bg=_T.surface)
        self._libro_perezoso = LibroPerezoso(
            self.nb, self._entradas(), perezosa)
        ajustar_ancho_categorias(self.nb, self.lista_categorias)
        # Mínimo explícito: si no, el libro pide el «mejor tamaño» de la página
        # más alta (Atajos, más de 1200 px) y el sizer lo desbordaría en vez
        # de dejar que la página se desplace.
        self.nb.SetMinSize((320, 240))
        vs.Add(self.nb, 1, wx.EXPAND | wx.ALL, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        btn_guardar = wx.Button(panel, wx.ID_OK, _("&Guardar"), name="GuardarPreferencias")
        btn_cancelar = wx.Button(panel, wx.ID_CANCEL, _("&Cancelar"), name="CancelarPreferencias")
        paleta.tema.boton_principal(btn_guardar)
        for b in (btn_guardar, btn_cancelar):
            row.Add(b, 0, wx.RIGHT, 6)
        vs.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(vs)
        btn_guardar.Bind(wx.EVT_BUTTON, self._on_guardar)
        self._cargar_opciones_simples()
        self._perezoso = perezosa
        self.lista_categorias.SetFocus()

    def _entradas(self):
        def externa(atributo, clase, argumentos=()):
            return self._envolver(
                partial(self._pagina_de, atributo, clase, argumentos))
        return (
            (_("General"), externa("pagina_general", PaginaGeneral, (self,))),
            (_("Interfaz"), externa("pagina_interfaz", PaginaInterfaz)),
            (_("Sonidos"), externa("pagina_sonidos", PaginaSonidos)),
            (_("Atajos"), externa("pagina_atajos", PaginaAtajos, (self, self._config))),
            (_("Voces"), externa("pagina_voz", PaginaVoz, (self, self._config))),
            (_("Lectura"), externa("pagina_lectura", PaginaLectura,
                                   (self._config, fila_label, crear_panel))),
            (_("Cola de lectura"), externa("pagina_cola", PaginaCola,
                                           (self._config,))),
            (_("Eventos del directo"), externa("pagina_eventos", PaginaEventos,
                                                (self._config, fila_label, crear_panel))),
            (_("Filtros"), externa("pagina_filtros", PaginaFiltros, (self._config,))),
            (_("Estado (F2)"), externa("pagina_estado", PaginaEstado, (self._config,))),
            (_("Conexión"), externa("pagina_conexion", PaginaConexion)),
            (_(CATEGORIA_YOUTUBE), externa("pagina_api", PaginaApi, (self,))),
            (_("Reproductor"), externa("pagina_reproductor", PaginaReproductor)),
            (_("Música"), externa("pagina_musica", PaginaMusica, (self, self._config))),
            (_("Descargas"), externa("pagina_descargas", PaginaDescargasPreferencias)),
            (_("Inteligencia artificial"), externa("pagina_ia", PaginaIA, (self, self._ruta))),
            (_("OBS"), externa("pagina_transmision", PaginaTransmision,
                               (self, self._config))),
            (_("Cámara"), externa("pagina_camara", PaginaCamara, (self, self._config))),
        )

    def _envolver(self, fabrica):
        def armar(parent):
            panel = fabrica(parent)
            if getattr(self, "_perezoso", False):
                self._cargar_opciones_simples()
                wx.CallAfter(self._ajustar_minimo)
            return panel
        return armar

    def _cargar_opciones_simples(self):
        """Vuelca la config en los controles de la tabla. El valor por
        defecto de cada fila es el de fábrica, y se usa tanto si la config no
        trae la clave como si el valor no se puede convertir al tipo."""
        for atributo, _seccion, _clave, en_memoria, tipo, por_defecto in _OPCIONES_SIMPLES:
            if atributo in self._filas_cargadas or not hasattr(self, atributo):
                continue
            control = getattr(self, atributo)
            try:
                valor = tipo(self._config.get(en_memoria, por_defecto))
            except (TypeError, ValueError):
                valor = por_defecto
            control.SetValue(valor)
            self._filas_cargadas.add(atributo)

    def _paginas(self):
        return (self.nb.GetPage(i) for i in range(self.nb.GetPageCount()))

    def _ajustar_minimo(self):
        """Ancho mínimo del diálogo: el que deja a la página más ancha entera
        (más la barra de desplazamiento). No hay desplazamiento horizontal,
        así que más angosto se cortarían controles."""
        try:
            self.Layout()
            visible = self.nb.GetPage(0).GetClientSize().width
            necesario = max(p.GetSizer().GetMinSize().width
                            for i, p in enumerate(self._paginas())
                            if self._libro_perezoso.construida(i))
            barra = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
            # Solo agranda: una página construida después puede pedir más ancho.
            ancho = max(self.GetSize().width - visible + necesario + barra,
                        self.GetMinSize().width)
            alto = 480
            self.SetMinSize((ancho, alto))
            actual = self.GetSize()
            if actual.width < ancho or actual.height < alto:
                self.SetSize((max(actual.width, ancho), max(actual.height, alto)))
        except Exception as exc:
            logger.debug("mínimo del diálogo de preferencias: %s", exc)

    def _pagina_de(self, atributo, clase, argumentos, parent):
        # La página vive en su módulo (composición); el diálogo conserva
        # los atributos públicos de los controles para las pruebas y la tabla.
        pagina = clase(*argumentos)
        setattr(self, atributo, pagina)
        panel = pagina.construir(parent)
        for nombre in tuple(f[0] for f in _OPCIONES_SIMPLES) + (
                "cho_tema", "rb_formato", "rb_estrategia",
                "txt_palabras", "txt_usuarios"):
            if hasattr(pagina, nombre):
                setattr(self, nombre, getattr(pagina, nombre))
        return panel

    def _set(self, seccion, clave, valor):
        self._pendientes.append((seccion, clave, valor))
        self._cambios = True

    def _volcar_controles(self, c):
        """Vuelca los controles y las páginas en la config y en los pendientes.

        Devuelve si el motor de voz elegido no está disponible."""
        for atributo, seccion, clave, en_memoria, tipo, _por_defecto in _OPCIONES_SIMPLES:
            if not hasattr(self, atributo):
                continue
            control = getattr(self, atributo)
            valor = control.GetValue() if tipo in (bool, str) else int(control.GetValue())
            texto = ("true" if valor else "false") if tipo is bool else str(valor)
            self._set(seccion, clave, texto)
            c[en_memoria] = valor

        if hasattr(self, "pagina_sonidos") and self.pagina_sonidos.tema_cambiado():
            self._cambios = True
        motor_no_disponible = False
        if hasattr(self, "pagina_voz"):
            motor_no_disponible = self.pagina_voz.guardar(self._set, c)
        # Lectura: la página calcula el valor en cambios(); se aplica con el
        # _set de hoy, igual que los demás controles manuales de abajo.
        if hasattr(self, "pagina_lectura"):
            formato = self.pagina_lectura.cambios()[0][2]
            self._set("lectura", "formato_prefijo", formato)
            c["formato_prefijo"] = formato
        # Se guarda la clave, no la etiqueta, porque config.ini solo admite estas claves.
        if hasattr(self, "rb_estrategia"):
            estrategia = ("todas", "limite")[self.rb_estrategia.GetSelection()]
            self._set("cola", "estrategia", estrategia)
            c["estrategia"] = estrategia
        for nombre in ("pagina_transmision", "pagina_camara", "pagina_musica",
                       "pagina_estado"):
            pagina = getattr(self, nombre, None)
            if pagina is not None:
                pagina.guardar(self._set, c)
        if hasattr(self, "pagina_descargas"):
            self.pagina_descargas.guardar()

        self._volcar_controles_manuales(c)

        # Los atajos ya vienen validados desde la captura (área + conflicto), así
        # que aquí solo se guardan; no hace falta revalidar por escritura.
        if hasattr(self, "pagina_atajos"):
            self.pagina_atajos.guardar(self._set, c)
        if hasattr(self, "pagina_ia"):
            self._pendientes.extend(self.pagina_ia._cambios_ia())
        if hasattr(self, "pagina_general"):
            self._pendientes.extend(self.pagina_general.cambios_canal())
        return motor_no_disponible

    def _volcar_controles_manuales(self, c):
        if hasattr(self, "txt_palabras"):
            palabras = self.txt_palabras.GetValue().strip()
            self._set("filtros", "palabras_silenciadas", palabras)
            c["palabras_silenciadas"] = separar_por_comas(palabras)
            usuarios = self.txt_usuarios.GetValue().strip()
            self._set("filtros", "usuarios_silenciados", usuarios)
            c["usuarios_silenciados"] = separar_por_comas(usuarios)

    def _on_guardar(self, event):
        c = self._config
        self._pendientes = []
        self._fallo_guardado = False
        registro_detallado_inicial = bool(c.get("registro_detallado", True))
        puerto_anterior = int(c.get("overlay_puerto", 8730))
        motor_no_disponible = self._volcar_controles(c)

        if hasattr(self, "pagina_sonidos") and not self.pagina_sonidos.guardar():
            self._fallo_guardado = True
        if not cfg.guardar_opciones(self._ruta, self._pendientes):
            self._fallo_guardado = True

        _snd.reproducir("error" if self._fallo_guardado else "copiar")

        self.avisos = avisos_preferencias.avisos_al_guardar(
            self._fallo_guardado,
            motor_no_disponible,
            c.get("registro_detallado", True) != registro_detallado_inicial,
            (c.get("overlay_puerto", 8730) != puerto_anterior
             and c.get("overlay_activo", False)))
        self.EndModal(wx.ID_OK)

    def hubo_cambios(self) -> bool:
        return self._cambios


_ETIQUETAS_ATAJO = atajos_captura.ETIQUETAS
_mostrar_atajo = atajos_captura.mostrar_atajo
etiqueta_de_accion = atajos_captura.etiqueta_de_accion


def abrir_preferencias(parent, config: dict, pagina=None, avisos=None) -> bool:
    """Devuelve True si se guardaron cambios (para aplicarlos en caliente).

    Si `pagina` coincide con una pestaña (p. ej. "YouTube"), esa queda elegida;
    sin `pagina`, igual. Una lista en `avisos` suma sus avisos para que la
    ventana principal los diga al recuperar el foco.
    """
    idioma_previo = config.get("idioma")
    dlg = PreferenciasDialog(parent, config, perezosa=True)
    try:
        if pagina:
            try:
                for i in range(dlg.nb.GetPageCount()):
                    if dlg.nb.GetPageText(i) == _(pagina):
                        dlg.nb.SetSelection(i)
                        break
            except Exception as exc:
                logger.debug("abrir_preferencias: no se pudo elegir página: %s", exc)
        res = dlg.ShowModal()
        if res == wx.ID_OK and avisos is not None:
            avisos.extend(dlg.avisos)
    finally:
        dlg.Destroy()
    if res == wx.ID_OK and config.get("idioma") != idioma_previo:
        ofrecer_reinicio(parent)
    return res == wx.ID_OK and dlg.hubo_cambios()


def ofrecer_iniciar_sesion(parent, config) -> bool:
    """Ofrece abrir Preferencias en la pestaña de sesión tras caducar el token.

    Devuelve lo que devuelva `abrir_preferencias` si el usuario acepta, o
    False si no quiere.
    """
    if not confirmar.preguntar(
            parent, _("Tu sesión de YouTube caducó. ¿Abrir Preferencias para "
                      "volver a iniciar sesión?"),
            _("Sesión caducada"), _("&Abrir Preferencias"), _("Ahora &no"), predeterminado_si=True):
        return False
    return abrir_preferencias(parent, config, pagina=CATEGORIA_YOUTUBE)
