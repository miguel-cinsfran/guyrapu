# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Diálogo de Preferencias por categorías (accesible).

Cada categoría se construye recién al elegirla. Guardar escribe solo las
construidas con `config.guardar_opciones` y actualiza la config en memoria.
La configuración de API/OAuth sigue en su propio diálogo (Herramientas).
"""

from __future__ import annotations

from functools import partial

import wx

from guyrapu.core import diagnostico
from guyrapu.core import config as cfg
from guyrapu.core import paths
from guyrapu.core.ini_tipado import separar_por_comas
from guyrapu.core.idioma import N_, _
from guyrapu.ui import atajos_captura, confirmar
from guyrapu.capture import estado_sesion
from guyrapu.voice import sound_player as _snd
from guyrapu.ui.gui import ContadorAccesible, _T, _tc, nombre_accesible
from guyrapu.ui.libro_perezoso import LibroPerezoso
from guyrapu.ui import paleta
from guyrapu.ui.preferencias_comun import (
    ANCHO_NOTA, ajustar_ancho_categorias, crear_panel, fila_label)
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
from guyrapu.ui.preferencias_programados import PaginaProgramados
from guyrapu.ui.preferencias_sonidos import PaginaSonidos
from guyrapu.ui.preferencias_voz import PaginaVoz

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
    ("chk_programados", "programados", "activo", "programados_activo", bool, False),
    ("sp_fuente", "ui", "tamanio_fuente_chat", "tamanio_fuente_chat", int, 12),
    ("chk_total_sc", "ui", "mostrar_total_superchats", "mostrar_total_superchats", bool, True),
    ("chk_autoplay", "ui", "autoplay_reproductor", "autoplay_reproductor", bool, True),
    ("chk_solo_audio", "ui", "reproductor_solo_audio", "reproductor_solo_audio", bool, True),
    ("chk_metadatos", "ui", "mostrar_metadatos", "mostrar_metadatos", bool, True),
    ("chk_botones_rep", "ui", "mostrar_botones_reproductor", "mostrar_botones_reproductor", bool, True),
    ("sp_cache_video", "ui", "cache_video_mb", "cache_video_mb", int, 1024),
) + OPCIONES_GENERAL + OPCIONES_LECTURA + OPCIONES_EVENTOS + (
    ("sp_cola_maxima", "cola", "tamanio_maximo", "tamanio_maximo", int, 15),
    ("sp_umbral_nombre", "cola", "umbral_solo_nombre", "umbral_solo_nombre", int, 0),
    ("chk_reconectar", "reconexion", "reconectar", "reconectar", bool, True),
    ("sp_espera_reconexion", "reconexion", "espera_entre_intentos", "espera_entre_intentos", int, 15),
    ("sp_max_intentos", "reconexion", "max_intentos", "max_intentos", int, 20),
    ("chk_buscar_actualizaciones", "actualizaciones", "buscar_al_iniciar", "buscar_actualizaciones_al_iniciar", bool, True),
    ("chk_confirmar_salida", "ui", "confirmar_salida", "confirmar_salida", bool, True),
    ("chk_sonido_inicio", "ui", "sonido_inicio", "sonido_inicio", bool, True),
    ("chk_registro_detallado", "diagnostico", "registro_detallado", "registro_detallado", bool, True),
    ("sp_puerto_overlay", "overlay", "puerto", "overlay_puerto", int, 8730),
    ("chk_avisar_sobrecarga", "transmision", "avisar_sobrecarga", "avisar_sobrecarga", bool, True),
    ("chk_titulo_estado_obs", "transmision", "titulo_estado_obs", "titulo_estado_obs", bool, False),
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
            (_("Interfaz"), self._envolver(self._pag_interfaz)),
            (_("Sonidos"), externa("pagina_sonidos", PaginaSonidos)),
            (_("Atajos"), externa("pagina_atajos", PaginaAtajos, (self, self._config))),
            (_("Voces"), externa("pagina_voz", PaginaVoz, (self, self._config))),
            (_("Lectura"), externa("pagina_lectura", PaginaLectura,
                                   (self._config, fila_label, crear_panel))),
            (_("Cola de lectura"), self._envolver(self._pag_cola)),
            (_("Eventos del directo"), externa("pagina_eventos", PaginaEventos,
                                                (self._config, fila_label, crear_panel))),
            (_("Filtros"), self._envolver(self._pag_filtros)),
            (_("Estado (F2)"), self._envolver(self._pag_estado)),
            (_("Mensajes automáticos"), externa("pagina_programados", PaginaProgramados)),
            (_("Conexión"), self._envolver(self._pag_conexion)),
            (_(CATEGORIA_YOUTUBE), externa("pagina_api", PaginaApi, (self,))),
            (_("Reproductor"), self._envolver(self._pag_reproductor)),
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

    def _pag_interfaz(self, parent):
        p = crear_panel(parent, "PagInterfaz")
        vs = wx.BoxSizer(wx.VERTICAL)

        vs.Add(fila_label(p, _("Tamaño de &letra del chat (8 a 24):")),
               0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.sp_fuente = ContadorAccesible(p, min=8, max=24, name=_("Tamaño de letra del chat"))
        vs.Add(self.sp_fuente, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.chk_total_sc = wx.CheckBox(p, label=_("Mostrar total de &Super Chats en la barra de estado"),
                                         name="MostrarTotalSuperChats")
        vs.Add(self.chk_total_sc, 0, wx.ALL, 10)

        self.chk_metadatos = wx.CheckBox(p, label=_("Mostrar pestaña de &información del vídeo"),
                                          name="MostrarMetadatos")
        vs.Add(self.chk_metadatos, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        p.SetSizer(vs)
        return p

    def _pag_cola(self, parent):
        p = crear_panel(parent, "PagCola")
        vs = wx.BoxSizer(wx.VERTICAL)

        self.rb_estrategia = wx.RadioBox(
            p, label=_("&Estrategia de la cola"), majorDimension=1,
            choices=[_("Leer todos los mensajes"),
                     _("Descartar los más antiguos si se acumulan")],
            style=wx.RA_SPECIFY_COLS, name=_("Estrategia de la cola"))
        self.rb_estrategia.SetSelection(
            0 if self._config.get("estrategia", "limite") == "todas" else 1)
        vs.Add(self.rb_estrategia, 0, wx.ALL, 10)

        vs.Add(fila_label(p, _("Tamaño &máximo de la cola:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.sp_cola_maxima = ContadorAccesible(
            p, min=1, max=500,
            name=_("Tamaño máximo de la cola"))
        vs.Add(self.sp_cola_maxima, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        vs.Add(fila_label(p, _("Leer solo el &nombre desde esta cantidad de mensajes en cola:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.sp_umbral_nombre = ContadorAccesible(p, min=0, max=500,
            name=_("Leer solo el nombre desde esta cantidad de mensajes en cola"))
        vs.Add(self.sp_umbral_nombre, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(wx.StaticText(p, label=_("Con 0, esta opción queda desactivada.")),
               0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        p.SetSizer(vs)
        return p

    def _pag_conexion(self, parent):
        p = crear_panel(parent, "PagConexion")
        vs = wx.BoxSizer(wx.VERTICAL)

        self.chk_reconectar = wx.CheckBox(
            p, label=_("&Reconectar automáticamente"),
            name=_("Reconectar automáticamente"))
        vs.Add(self.chk_reconectar, 0, wx.ALL, 10)

        vs.Add(fila_label(p, _("&Espera máxima entre intentos, en segundos:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.sp_espera_reconexion = ContadorAccesible(
            p, min=1, max=300,
            name=_("Espera máxima entre intentos, en segundos"))
        vs.Add(self.sp_espera_reconexion, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        vs.Add(fila_label(p, _("Número máximo de &intentos:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.sp_max_intentos = ContadorAccesible(
            p, min=0, max=100,
            name=_("Número máximo de intentos"))
        vs.Add(self.sp_max_intentos, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        p.SetSizer(vs)
        return p

    def _pag_reproductor(self, parent):
        p = crear_panel(parent, "PagReproductor")
        vs = wx.BoxSizer(wx.VERTICAL)

        self.chk_autoplay = wx.CheckBox(p, label=_("&Reproducir audio automáticamente al conectar"),
                                         name="AutoplayReproductor")
        vs.Add(self.chk_autoplay, 0, wx.ALL, 10)

        self.chk_solo_audio = wx.CheckBox(
            p, label=_("Reproducir &solo el audio, sin imagen"),
            name="SoloAudioReproductor")
        vs.Add(self.chk_solo_audio, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.chk_botones_rep = wx.CheckBox(p, label=_("Mostrar &botones del reproductor"),
                                            name="MostrarBotonesReproductor")
        vs.Add(self.chk_botones_rep, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        etiqueta_cache = wx.StaticText(
            p, label=_("&Tamaño máximo de la caché de vídeo, en megabytes:"))
        self.sp_cache_video = wx.SpinCtrl(
            p, min=0, max=20000,
            name=_("Tamaño máximo de la caché de vídeo en megabytes"))
        vs.Add(etiqueta_cache, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        vs.Add(self.sp_cache_video, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        p.SetSizer(vs)
        return p

    def _pagina_de(self, atributo, clase, argumentos, parent):
        # La página vive en su módulo (composición); el diálogo conserva
        # los atributos públicos de los controles para las pruebas y la tabla.
        pagina = clase(*argumentos)
        setattr(self, atributo, pagina)
        panel = pagina.construir(parent)
        for nombre in tuple(f[0] for f in _OPCIONES_SIMPLES) + ("cho_tema", "rb_formato"):
            if hasattr(pagina, nombre):
                setattr(self, nombre, getattr(pagina, nombre))
        return panel

    def _pag_estado(self, parent):
        """Una casilla por componente del anuncio de estado (tecla F2). Sin
        colores en las casillas: en Windows eso rompe su rol accesible."""
        p = crear_panel(parent, "PagEstado")
        vs = wx.BoxSizer(wx.VERTICAL)

        nota = wx.StaticText(p, name="NotaEstado", label=_(
            "Elige qué dice la tecla F2 (estado de sesión). Marca lo que quieras "
            "oír; por defecto, los datos del vídeo y del chat. El orden en que se "
            "dice es fijo."))
        nota.SetForegroundColour(_T.dim)
        nota.Wrap(ANCHO_NOTA)
        vs.Add(nota, 0, wx.ALL, 10)

        activos = self._config.get("estado_toggles") or estado_sesion.ACTIVOS_DEFECTO
        self._chk_estado: dict = {}
        for comp in estado_sesion.COMPONENTES:
            chk = wx.CheckBox(p, label=estado_sesion.etiqueta(comp),
                              name=f"EstadoComponente_{comp}")
            chk.SetValue(comp in activos)
            self._chk_estado[comp] = chk
            vs.Add(chk, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        p.SetSizer(vs)
        return p

    def _pag_filtros(self, parent):
        p = crear_panel(parent, "PagFiltros")
        vs = wx.BoxSizer(wx.VERTICAL)

        vs.Add(fila_label(p, _("&Palabras silenciadas (separadas por comas):")),
               0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.txt_palabras = wx.TextCtrl(
            p, value=", ".join(self._config.get("palabras_silenciadas", [])),
            name=_("Palabras silenciadas"))
        vs.Add(self.txt_palabras, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        vs.Add(fila_label(p, _("&Usuarios silenciados (separados por comas):")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.txt_usuarios = wx.TextCtrl(
            p, value=", ".join(self._config.get("usuarios_silenciados", [])),
            name=_("Usuarios silenciados"))
        vs.Add(self.txt_usuarios, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        nota = wx.StaticText(p, label=_(
            "Estos filtros ocultan y no leen los mensajes que contengan esas "
            "palabras o de esos usuarios. Se aplican a partir del próximo mensaje."),
            name="NotaFiltros")
        nota.SetForegroundColour(_T.dim)
        nota.Wrap(ANCHO_NOTA)
        vs.Add(nota, 0, wx.ALL, 10)

        p.SetSizer(vs)
        return p

    def _set(self, seccion, clave, valor):
        self._pendientes.append((seccion, clave, valor))
        self._cambios = True

    def _on_guardar(self, event):
        c = self._config
        self._pendientes = []
        self._fallo_guardado = False
        registro_detallado_inicial = bool(c.get("registro_detallado", True))
        puerto_anterior = int(c.get("overlay_puerto", 8730))
        # Los atajos ya vienen validados desde la captura (área + conflicto), así
        # que aquí solo se guardan; no hace falta revalidar por escritura.

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
        for nombre in ("pagina_transmision", "pagina_camara", "pagina_musica"):
            pagina = getattr(self, nombre, None)
            if pagina is not None:
                pagina.guardar(self._set, c)
        if hasattr(self, "pagina_descargas"):
            self.pagina_descargas.guardar()

        if hasattr(self, "_chk_estado"):
            activos = set()
            for comp, chk in self._chk_estado.items():
                on = chk.GetValue()
                self._set("estado", comp, "true" if on else "false")
                if on:
                    activos.add(comp)
            c["estado_toggles"] = activos

        if hasattr(self, "txt_palabras"):
            palabras = self.txt_palabras.GetValue().strip()
            self._set("filtros", "palabras_silenciadas", palabras)
            c["palabras_silenciadas"] = separar_por_comas(palabras)
            usuarios = self.txt_usuarios.GetValue().strip()
            self._set("filtros", "usuarios_silenciados", usuarios)
            c["usuarios_silenciados"] = separar_por_comas(usuarios)

        if hasattr(self, "pagina_atajos"):
            self.pagina_atajos.guardar(self._set, c)
        if hasattr(self, "pagina_ia"):
            self._pendientes.extend(self.pagina_ia._cambios_ia())
        if hasattr(self, "pagina_general"):
            self._pendientes.extend(self.pagina_general.cambios_canal())
        if hasattr(self, "pagina_sonidos") and not self.pagina_sonidos.guardar():
            self._fallo_guardado = True
        if not cfg.guardar_opciones(self._ruta, self._pendientes):
            self._fallo_guardado = True

        _snd.reproducir("error" if self._fallo_guardado else "copiar")

        # Los avisos se juntan acá y los dice la ventana principal una sola vez,
        # ya con el foco de vuelta en ella: anunciarlos antes de cerrar hacía que
        # el cambio de foco los cortara entre sí.
        guardado = _("Preferencias guardadas.")
        fallo = _("Las preferencias se aplicaron, pero no se pudieron guardar "
                  "en el disco. Se perderán al cerrar la aplicación.")
        self.avisos = [guardado if not self._fallo_guardado else fallo]
        if motor_no_disponible:
            self.avisos.append(_("El motor elegido no está disponible, se conserva el anterior."))
        if c.get("registro_detallado", True) != registro_detallado_inicial:
            self.avisos.append(_("El cambio del registro detallado se aplica al reiniciar "
                                 "la aplicación."))
        # El servidor del panel ya escucha en el puerto viejo; no se reinicia
        # solo, así que se avisa dónde se aplica.
        if (c.get("overlay_puerto", 8730) != puerto_anterior
                and c.get("overlay_activo", False)):
            self.avisos.append(_("El puerto del chat en el vídeo se aplica al desactivarlo y "
                                 "volver a activarlo desde el panel de transmisión."))
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
    dlg = PreferenciasDialog(parent, config)
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
            _("Sesión caducada"), _("&Abrir Preferencias"), _("Ahora &no")):
        return False
    return abrir_preferencias(parent, config, pagina=CATEGORIA_YOUTUBE)
