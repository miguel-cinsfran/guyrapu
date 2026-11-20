# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Muestras de los cuadros que se abren desde la ventana Interacción.

Cada `armar(datos)` devuelve el cuadro ya construido, con ejemplos. Los
dobles y el aislamiento de archivos los pone quien llama, como en las
pruebas de cada cuadro.
"""

from __future__ import annotations

MUESTRAS = []


def _registrar(nombre, clase, variante, armar):
    MUESTRAS.append((nombre, clase, variante, armar))


def _medios(datos):
    """Un medio de ejemplo en la carpeta aislada, para los desplegables."""
    from guyrapu.core import paths
    from guyrapu.interaction import medios_guardados

    ruta = paths.carpeta_datos()
    ruta.mkdir(parents=True, exist_ok=True)
    (ruta / "aplauso.gif").write_bytes(b"GIF89a")
    medios_guardados.guardar(paths.medios(), [
        {"nombre": "aplauso.gif", "tipo": "imagen", "archivo": "aplauso.gif"}])


def _comando(datos):
    from guyrapu.ui import comando_cuadro

    ejemplo = {
        "nombre": "discord", "alias": ["dc"], "respuesta": "Hola",
        "destino": "video", "permiso": "todos", "nombres": [],
        "espera_general": 5.0, "espera_persona": 30.0, "activo": True,
        "estilo": "clasico", "segundos": 8,
    }
    return comando_cuadro.DialogoComando(None, ejemplo, ())


def _palabra(datos):
    from guyrapu.ui import comando_cuadro
    return comando_cuadro.DialogoPalabra(None, "gracias")


def _encuesta(datos):
    from guyrapu.ui import encuesta_cuadro
    return encuesta_cuadro.DialogoEncuesta(None, {
        "pregunta": "¿Qué les gustó más?",
        "opciones": ["La música", "El chat"], "segundos": 30})


def _estilo(datos):
    from guyrapu.obs import estilos_aviso
    from guyrapu.ui import estilo_cuadro

    estilo = dict(estilos_aviso.FABRICA[0], clave="mio", nombre="Mi estilo")
    return estilo_cuadro.DialogoEstilo(None, estilo, ())


def _tipos(datos):
    from guyrapu.ui import estilo_tipos_cuadro
    return estilo_tipos_cuadro.DialogoTipos(None, {"clasico", "neon"})


def _medio(datos):
    from guyrapu.ui import medio_cuadro
    return medio_cuadro.DialogoMedio(None, {
        "nombre": "Risa", "descripcion": "Una risa", "tipo": "sonido",
        "archivo": "risa.wav", "duracion": 3})


def _mensaje(datos):
    from guyrapu.ui import mensaje_automatico_cuadro
    return mensaje_automatico_cuadro.DialogoMensaje(None, {
        "texto": "¡Bienvenido al directo!", "cada": 60}, ())


def _meta(datos):
    _medios(datos)
    from guyrapu.ui import meta_cuadro
    return meta_cuadro.DialogoMeta(None, {
        "nombre": "Mil seguidores", "objetivo": 1000, "estilo": "clasico"}, ())


def _nombre(datos):
    from guyrapu.ui import mensaje_automatico_cuadro
    return mensaje_automatico_cuadro.DialogoNombre(None, "Saludo")


def _disparador(datos):
    _medios(datos)
    from guyrapu.ui import disparador_cuadro
    return disparador_cuadro.DialogoDisparador(None, {}, ())


_registrar("comando", "DialogoComando", "con_datos", _comando)
_registrar("palabra", "DialogoPalabra", "con_datos", _palabra)
_registrar("encuesta", "DialogoEncuesta", "con_datos", _encuesta)
_registrar("estilo", "DialogoEstilo", "con_datos", _estilo)
_registrar("tipos", "DialogoTipos", "con_datos", _tipos)
_registrar("medio", "DialogoMedio", "con_datos", _medio)
_registrar("mensaje", "DialogoMensaje", "con_datos", _mensaje)
_registrar("meta", "DialogoMeta", "con_datos", _meta)
_registrar("nombre", "DialogoNombre", "con_datos", _nombre)
_registrar("disparador", "DialogoDisparador", "con_datos", _disparador)
