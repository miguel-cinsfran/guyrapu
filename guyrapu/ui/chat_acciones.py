# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Acciones sobre la lista del chat.

Teclado, menú de la tecla Aplicaciones, copiar, releer, abrir enlace,
silenciar y ocultar autores, alias y filtro de mensajes. Única razón para
cambiar: qué se puede hacer con un mensaje de la lista del chat.
"""

from __future__ import annotations

import re
import webbrowser

import wx

from guyrapu.capture import alias, chat_adicional
from guyrapu.core import paths, sonidos_eventos
from guyrapu.core.config import guardar_opcion
from guyrapu.core.idioma import _
from guyrapu.translation.proveedores.base import Traduccion
from guyrapu.ui import confirmar, menu_moderacion
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.ui.chat_vivo import VACIO_CHAT, es_linea_vacia, filas_de_chat
from guyrapu.ui.gui_menu import FILTROS
from guyrapu.ui.lista_chat import texto_fila
from guyrapu.voice import sound_player as _snd

# Mapeo entre índice de FILTROS y clave persistida en config.ini.
_NOMBRES_FILTRO = ("todos", "texto", "superchat", "miembro", "avisos")
IDX_FILTRO     = {"todos": 0, "texto": 1, "superchat": 2, "miembro": 3, "avisos": 4}

_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)


def paso_filtro(indice: int, paso: int, cantidad: int) -> int:
    """Índice del filtro que queda al avanzar `paso` lugares, con vuelta."""
    return (indice + paso) % cantidad


class AccionesChat:
    """Lo que se puede hacer con un mensaje de la lista del chat."""

    def __init__(self, lb_chat, chat_vivo, cola, config, sesion, padre):
        self.lb_chat = lb_chat
        self.chat_vivo = chat_vivo
        self._cola = cola
        self._config = config
        self._sesion = sesion
        self._padre = padre
        self.fi_items = []

    def _bind_menu(self, item, fn, *args):
        """Difiere el anuncio hasta que el menú se cerró y volvió el foco."""
        menu, identificador = item
        menu.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(fn, *args), id=identificador)

    def _aplicar_filtro(self, idx: int):
        self.chat_vivo.filtro = FILTROS[idx][1] if idx < len(FILTROS) else None
        self.chat_vivo.reconstruir()
        from guyrapu.ui.gui import RUTA_CONFIG
        guardar_opcion(RUTA_CONFIG, "ui", "filtro_activo",
                       _NOMBRES_FILTRO[idx] if idx < len(_NOMBRES_FILTRO) else "todos")
        self._marcar_filtro()
        anunciar(_("Filtro: {filtro}. {n} mensajes").format(
            filtro=_(FILTROS[idx][0]),
            n=len(filas_de_chat(self.lb_chat))))

    def _indice_filtro(self) -> int:
        for indice, (_nombre, valor) in enumerate(FILTROS):
            if valor == self.chat_vivo.filtro:
                return indice
        return 0

    def cambiar_filtro(self, paso: int) -> None:
        """Elige el filtro anterior o siguiente, con vuelta en los extremos."""
        self._aplicar_filtro(paso_filtro(self._indice_filtro(), paso,
                                         len(FILTROS)))

    def abrir_busqueda(self) -> None:
        """Abre el cuadro que busca en los mensajes de la sesión."""
        from guyrapu.ui import chat_buscar
        chat_buscar.abrir(self._padre, self)

    def abrir_participacion(self) -> None:
        """Abre la ventana con la participación del directo conectado."""
        from guyrapu.ui import chat_participacion
        chat_participacion.abrir(self._padre, self)

    def enfocar_mensaje(self, mensaje) -> bool:
        """Lleva el foco al mensaje en la lista del chat.

        Si el filtro de tipo lo ocultaba, pasa a Todos y lo anuncia antes de
        enfocarlo. Devuelve False si el mensaje ya salió de la sesión.
        """
        modelo = self.chat_vivo.modelo
        indice = next((i for i, actual in enumerate(modelo.todos)
                       if actual is mensaje), None)
        if indice is None:
            anunciar(_("Ese mensaje ya no está en el chat."))
            return False
        if indice not in modelo.visibles:
            self._aplicar_filtro(0)
        fila = modelo.visibles.index(indice)
        self.lb_chat.SetSelection(fila)
        self.lb_chat.SetFirstItem(fila)
        self.lb_chat.SetFocus()
        return True

    def _on_chat_key(self, event):
        k = event.GetKeyCode()
        # La orilla suena sin consumir la tecla: NVDA sigue leyendo la fila.
        if sonidos_eventos.es_orilla(k, self.lb_chat.GetSelection(), self.lb_chat.GetCount()):
            _snd.reproducir("orilla")
        if k == ord('C') and event.ControlDown():
            self._copiar_mensaje()
        elif k == wx.WXK_WINDOWS_MENU:
            self._mostrar_menu_chat()
        else:
            # Enter se atiende en EVT_CHAR_HOOK porque wx no lo entrega aquí.
            event.Skip()

    def _on_chat_char_hook(self, event):
        if (event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER)
                and event.GetModifiers() == wx.MOD_NONE):
            # Solo Enter a secas: Alt+Enter es el acelerador de «Enviar mensaje»
            # y debe seguir hasta el menú.
            self._copiar_mensaje()
        else:
            event.Skip()

    def _fila_vacia_elegida(self):
        seleccion = self.lb_chat.GetSelection()
        if seleccion is None or seleccion == wx.NOT_FOUND:
            return False
        return es_linea_vacia(self.lb_chat.GetString(seleccion))

    def _on_chat_menu(self, event):
        self._mostrar_menu_chat()

    def _mostrar_menu_chat(self):
        registro_sel = self._get_selected_data()
        if registro_sel is None:
            return
        menu = wx.Menu()

        id_copiar   = wx.NewIdRef()
        id_copiar2  = wx.NewIdRef()
        id_releer   = wx.NewIdRef()
        id_link     = wx.NewIdRef()
        id_sil_tts  = wx.NewIdRef()
        id_sil_full = wx.NewIdRef()
        id_rehab    = wx.NewIdRef()
        id_alias    = wx.NewIdRef()

        menu.Append(id_copiar,  _("Copiar mensaje"))
        menu.Append(id_copiar2, _("Copiar todo (autor: mensaje, hora)"))
        menu.Append(id_releer,  _("Leer en voz alta"))
        self._agregar_entradas_traduccion(menu, registro_sel)
        menu.AppendSeparator()
        menu.Append(id_link,    _("Abrir enlace"))
        menu.AppendSeparator()

        autor = registro_sel.autor if registro_sel else ""
        autor_mostrado = alias.visible(autor) if autor else ""
        if autor:
            self._agregar_entradas_autor(menu, autor, autor_mostrado,
                                         id_rehab, id_sil_tts, id_sil_full, id_alias)

        menu_moderacion.agregar(menu, self._padre, registro_sel, autor_mostrado,
                                chat_adicional.activo())

        # Los handlers van sobre el propio menú (no sobre la ventana): así mueren
        # con él y no se acumulan bindings en cada apertura del menú contextual.
        self._bind_menu((menu, id_copiar), self._copiar_mensaje)
        self._bind_menu((menu, id_copiar2), self._copiar_todo)
        self._bind_menu((menu, id_releer), self._releer_mensaje)
        self._bind_menu((menu, id_link), self._abrir_enlace)
        self._bind_menu((menu, id_sil_tts), self._silenciar_autor, autor, False)
        self._bind_menu((menu, id_sil_full), self._silenciar_autor, autor, True)
        self._bind_menu((menu, id_rehab), self._rehabilitar_autor, autor)
        self._bind_menu((menu, id_alias), self._editar_alias_autor, autor)

        self.lb_chat.PopupMenu(menu)
        menu.Destroy()

    def _agregar_entradas_traduccion(self, menu, registro) -> None:
        """Suma al menú leer y copiar el original si el mensaje se tradujo."""
        if self._traduccion(registro) is None:
            return
        id_leer = wx.NewIdRef()
        id_copiar = wx.NewIdRef()
        menu.Append(id_leer, _("Leer mensaje original"))
        menu.Append(id_copiar, _("Copiar mensaje original"))
        self._bind_menu((menu, id_leer), self._leer_original)
        self._bind_menu((menu, id_copiar), self._copiar_original)

    def _agregar_entradas_autor(self, menu, autor, autor_mostrado,
                                id_rehab, id_sil_tts, id_sil_full, id_alias):
        if self._autor_esta_silenciado(autor):
            menu.Append(id_rehab, _("Dejar de silenciar a {autor}").format(autor=autor_mostrado))
        else:
            menu.Append(id_sil_tts,  _("Silenciar voz de {autor}").format(autor=autor_mostrado))
            menu.Append(id_sil_full, _("Ocultar y silenciar a {autor}").format(autor=autor_mostrado))
        if alias.clave(autor) not in alias.vigente():
            menu.Append(id_alias, _("Asignar &alias a {autor}…").format(autor=autor_mostrado))
        else:
            menu.Append(id_alias, _("Cambiar &alias de {autor}…").format(autor=autor_mostrado))

    def _editar_alias_autor(self, autor: str) -> None:
        mapa = alias.vigente()
        actual = mapa.get(alias.clave(autor), "")
        dialogo = wx.TextEntryDialog(
            self._padre, _("Alias para {autor}. Déjalo vacío para eliminarlo.").format(autor=autor),
            _("Alias del usuario"), value=actual)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return
            nuevo = dialogo.GetValue()
        finally:
            dialogo.Destroy()
            self.lb_chat.SetFocus()

        actualizado = alias.poner(mapa, autor, nuevo)
        alias.guardar(paths.alias(), actualizado)
        alias.usar(actualizado)
        self.chat_vivo.reconstruir()
        anunciar(_("Alias guardado, {nuevo}").format(nuevo=actualizado[alias.clave(autor)])
                  if nuevo.strip() else _("Alias eliminado"))

    def _traduccion(self, registro):
        """La traducción guardada de ese registro, o None."""
        if registro is None or self.chat_vivo is None:
            return None
        resultado = self.chat_vivo.traduccion(registro)
        return resultado if isinstance(resultado, Traduccion) else None

    def _texto_visible(self, registro) -> str:
        traduccion = self._traduccion(registro)
        return traduccion.texto if traduccion is not None else registro.texto

    def _copiar_mensaje(self):
        data = self._get_selected_data()
        if data is None:
            return
        self._clipboard_set(self._texto_visible(data))
        _snd.reproducir("copiar")
        anunciar(_("Mensaje copiado"))

    def _copiar_original(self):
        data = self._get_selected_data()
        if data is None:
            return
        self._clipboard_set(data.texto)
        _snd.reproducir("copiar")
        anunciar(_("Mensaje original copiado"))

    def _copiar_enlace_directo(self):
        texto, frase = chat_adicional.texto_enlace_directo(
            self._sesion().enlace_directo)
        if texto:
            self._clipboard_set(texto)
            _snd.reproducir("copiar")
        anunciar(frase)

    def _copiar_todo(self):
        data = self._get_selected_data()
        if data is None:
            return
        linea = f"{data.autor}: {self._texto_visible(data)}, {data.hora}"
        if data.monto:
            linea += f" [{data.monto}]"
        self._clipboard_set(linea)
        _snd.reproducir("copiar")
        anunciar(_("Línea copiada"))

    def _releer_mensaje(self):
        data = self._get_selected_data()
        if data is None:
            return
        from guyrapu.voice.tts_worker import construir_tts
        self._cola.put({"texto_tts": construir_tts(
                            data.autor, self._texto_visible(data), self._config),
                        "autor": data.autor})

    def _leer_original(self):
        data = self._get_selected_data()
        if data is None:
            return
        from guyrapu.voice.tts_worker import construir_tts
        self._cola.put({"texto_tts": construir_tts(
                            data.autor, data.texto, self._config),
                        "autor": data.autor})

    def _abrir_enlace(self):
        data = self._get_selected_data()
        if data is None:
            return
        urls = _URL_RE.findall(data.texto)
        if not urls:
            anunciar(_("No se encontró ningún enlace"))
            confirmar.avisar(self._padre, _("No se encontró ningún enlace en este mensaje."),
                             _("Sin enlace"), _("Aceptar"), icono=confirmar.ICON_INFORMATION)
            return
        webbrowser.open(urls[0])
        anunciar(_("Abriendo enlace"))

    def _silenciar_autor(self, autor: str, ocultar: bool) -> None:
        if not autor:
            return
        al = autor.lower().strip()
        self._config.setdefault("silenciados_runtime", set()).add(al)
        sil_oculto = self._config.setdefault("silenciados_ocultar", set())
        if ocultar:
            sil_oculto.add(al)
            self.chat_vivo.reconstruir()
        else:
            sil_oculto.discard(al)
        # Traductores: {autor} es el autor del mensaje.
        anunciar(_("{autor} silenciado").format(autor=autor))

    def _rehabilitar_autor(self, autor: str) -> None:
        if not autor:
            return
        al = autor.lower().strip()
        self._config.setdefault("silenciados_runtime", set()).discard(al)
        self._config.setdefault("silenciados_ocultar", set()).discard(al)
        self.chat_vivo.reconstruir()
        # Traductores: {autor} es el autor del mensaje.
        anunciar(_("{autor} ya no está silenciado").format(autor=autor))

    def _autor_esta_silenciado(self, autor: str) -> bool:
        return autor.lower().strip() in self._config.get("silenciados_runtime", set())

    def _autor_esta_oculto(self, autor: str) -> bool:
        return autor.lower().strip() in self._config.get("silenciados_ocultar", set())

    def _get_selected_data(self):
        idx = self.lb_chat.GetSelection()
        if idx == wx.NOT_FOUND:
            return None
        if self._fila_vacia_elegida():
            anunciar(_(VACIO_CHAT))
            return None
        return self.chat_vivo.modelo.dato_en_fila(idx)

    def _clipboard_set(self, text: str) -> None:
        from guyrapu.ui.gui import copiar_al_portapapeles
        copiar_al_portapapeles(text)

    def _marcar_filtro(self):
        idx = IDX_FILTRO.get(_NOMBRES_FILTRO[0] if self.chat_vivo.filtro is None else "", 0)
        # Buscar el índice cuyo valor coincide con el filtro del chat.
        for i, (_sin_uso, val) in enumerate(FILTROS):
            if val == self.chat_vivo.filtro:
                idx = i
                break
        if 0 <= idx < len(self.fi_items):
            self.fi_items[idx].Check(True)

    def _format_display(self, autor, msg, hora, tipo, monto):
        autor = alias.visible(autor)
        # Si "quitar emojis" está activo, también se ocultan en la lista (incluye
        # los shortcodes :nombre: de YouTube). Los marcadores 💲🎨⭐ se conservan.
        if self._config.get("limpiar_emojis", True):
            from guyrapu.voice.tts_worker import quitar_emojis
            msg = quitar_emojis(msg)
        return texto_fila(autor, msg, hora, tipo, monto)
