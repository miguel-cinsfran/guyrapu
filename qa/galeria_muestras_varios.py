# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Muestras de los cuadros sueltos, armadas como en sus pruebas.

Cada `armar(datos)` devuelve el cuadro ya construido, con datos de ejemplo
y sin red. Los dobles y el aislamiento de archivos los pone quien llama.
"""

from __future__ import annotations

MUESTRAS = []


def _registrar(nombre, clase, variante, armar):
    MUESTRAS.append((nombre, clase, variante, armar))


def _actualizacion(datos):
    from guyrapu.ui import gui_actualizacion

    cuadro = gui_actualizacion.DialogoActualizacion(
        None, "Hay una versión nueva")
    cuadro.estado("Descargando la versión 1.2.3…")
    cuadro.notas("Versión 1.2.3\nCorrige la lectura del chat y mejora la voz.")
    cuadro.progreso(65)
    cuadro.ofrecer_accion("&Descargar", lambda: None)
    return cuadro


def _agregar_captura(datos):
    from unittest import mock

    from guyrapu.ui import ia_agregar_captura as agregar
    from tests.test_ia_agregar_captura import ClienteDoble

    def hilo_directo(target, _nombre, **_opciones):
        target()
        return mock.Mock()

    datos.pila.enter_context(mock.patch.object(
        agregar.diagnostico, "crear_hilo", side_effect=hilo_directo))
    datos.pila.enter_context(mock.patch.object(
        agregar.wx, "CallAfter",
        side_effect=lambda funcion, *a, **k: funcion(*a, **k)))
    return agregar.DialogoAgregarCaptura(None, ClienteDoble())


def _elegir_destino(datos):
    from unittest import mock

    from guyrapu.restream.perfiles import Perfil
    from guyrapu.ui import gui_elegir_destino as elegir

    datos.pila.enter_context(mock.patch.object(
        elegir.ganchos, "cargar_perfiles", return_value=[]))
    perfiles = [Perfil(nombre="Canal", canales=(1,), orientacion="vertical")]
    return elegir.DialogoElegirDestino(
        None, destino="YouTube", usuario="amigo", perfiles=perfiles)


def _editor_lista(datos):
    from guyrapu.music.modelo import Tema
    from guyrapu.ui import musica_editor_lista

    temas = (Tema("C:/Musica/rock.mp3", "Rock", artista="Ana"),
             Tema("C:/Musica/jazz.mp3", "Jazz", artista="Beto"))
    return musica_editor_lista.DialogoEditorLista(
        None, "Mía", temas, (temas[0],))


def _enlace(datos):
    from guyrapu.ui import musica_dialogo_enlace

    return musica_dialogo_enlace.DialogoEnlace(None)


def _estado(datos):
    from guyrapu.ui import dialogo_estado

    lineas = ["YouTube: 12 mensajes leídos", "TikTok: 4 mensajes leídos",
              "Superchats: 3"]
    return dialogo_estado.DialogoEstado(None, lineas)


def _formato(datos):
    from guyrapu.downloads import formatos_reales
    from guyrapu.ui import elegir_formato

    opciones = [
        formatos_reales.OpcionFormato(
            etiqueta="1080p, MP4, 100 MB", selector="299+140",
            contenedor="mp4", tamano=100000000),
        formatos_reales.OpcionFormato(
            etiqueta="720p, MP4, 50 MB", selector="22+140",
            contenedor="mp4", tamano=50000000),
        formatos_reales.OpcionFormato(
            etiqueta="Solo audio, M4A, 128 kbps, 5 MB", selector="140",
            contenedor="m4a", tamano=5000000),
    ]
    return elegir_formato.DialogoFormato(None, opciones)


def _redactar(datos):
    from guyrapu.ui import gui_redactar

    cuadro = gui_redactar.DialogoRedactar(
        None, "&Comentario:", 200, lambda texto: None)
    cuadro.panel.texto.SetValue("¡Bienvenido al directo!")
    return cuadro


_registrar("actualizacion", "DialogoActualizacion", "con_datos",
           _actualizacion)
_registrar("agregar_captura", "DialogoAgregarCaptura", "con_datos",
           _agregar_captura)
_registrar("elegir_destino", "DialogoElegirDestino", "con_datos",
           _elegir_destino)
_registrar("editor_lista", "DialogoEditorLista", "con_datos", _editor_lista)
_registrar("enlace", "DialogoEnlace", "con_datos", _enlace)
_registrar("estado", "DialogoEstado", "con_datos", _estado)
_registrar("formato", "DialogoFormato", "con_datos", _formato)
_registrar("redactar", "DialogoRedactar", "con_datos", _redactar)
