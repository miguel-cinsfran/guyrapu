# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Muestras de los cuadros de OBS, armadas como en sus pruebas.

Cada `armar(datos)` devuelve el cuadro ya construido, con datos de ejemplo
y sin red. Los dobles y el aislamiento de archivos los pone quien llama.
"""

from __future__ import annotations

MUESTRAS = []


def _registrar(nombre, clase, variante, armar):
    MUESTRAS.append((nombre, clase, variante, armar))


def _ajustes():
    from guyrapu.obs import ajustes_perfil

    return ajustes_perfil.AjustesPerfil(
        ancho_lienzo=1920, alto_lienzo=1080,
        ancho_salida=1280, alto_salida=720,
        fps=60, codificador="x264", preset="veryfast")


def _ajustes_perfil(datos):
    from guyrapu.obs import ajustes_perfil
    from guyrapu.ui import dialogo_ajustes_perfil

    return dialogo_ajustes_perfil.DialogoAjustesPerfil(
        None, ajustes_perfil.valores_iniciales(False, "x264"), "Casa",
        salidas=(("default", "Por defecto"), ("{usb}", "Micrófono USB")))


def _usos_perfil(datos):
    from guyrapu.ui import dialogo_usos_perfil

    config = {"perfil_horizontal": "Casa", "perfil_vertical": "Vertical",
              "perfil_grabar": "Grabación"}
    return dialogo_usos_perfil.DialogoUsosPerfil(None, "Casa", config)


def _asistente(datos):
    from guyrapu.ui import dialogo_asistente_perfiles

    return dialogo_asistente_perfiles.DialogoAsistentePerfiles(None)


def _resumen(datos):
    from guyrapu.obs import ajustes_perfil, asistente_perfiles
    from guyrapu.ui import dialogo_asistente_perfiles

    def perfil(nombre, uso):
        return asistente_perfiles.PerfilPreparado(
            nombre, uso, ajustes_perfil.valores_iniciales(
                uso == "perfil_vertical", "x264"))

    resultado = asistente_perfiles.ResultadoAsistente((
        perfil("Casa horizontal", "perfil_horizontal"),
        perfil("Casa grabación", "perfil_grabar")))
    texto = "\n".join(asistente_perfiles.lineas_resumen(resultado))
    return dialogo_asistente_perfiles.DialogoResumenAsistente(None, texto)


def _prueba_equipo(datos):
    from guyrapu.ui import dialogo_prueba_equipo

    return dialogo_prueba_equipo.DialogoPruebaEquipo(
        None, "Casa", _ajustes(), 48, vertical=True)


def _resultado_prueba(datos):
    from dataclasses import replace

    from guyrapu.obs import prueba_equipo
    from guyrapu.ui import dialogo_prueba_equipo

    original = _ajustes()
    pasos = (prueba_equipo.PasoEquipo(original, 1, 100, 1, 100),)
    ganador = replace(original, fps=30, ancho_salida=1280, alto_salida=720)
    resultado = prueba_equipo.ResultadoEquipo("Casa", original, ganador, pasos)
    return dialogo_prueba_equipo.DialogoResultadoPrueba(None, resultado)


def _prueba_conexion(datos):
    from guyrapu.ui import dialogo_prueba_conexion

    return dialogo_prueba_conexion.DialogoPruebaConexion(
        None, "Casa", 2500, 60)


def _resultado_conexion(datos):
    from guyrapu.obs import ajustes_perfil, prueba_conexion
    from guyrapu.ui import dialogo_prueba_conexion

    original = ajustes_perfil.AjustesPerfil(bitrate_video=2500)
    pasos = (prueba_conexion.PasoRed(2500, 5, 100),
             prueba_conexion.PasoRed(1300, 0, 100))
    resultado = prueba_conexion.ResultadoConexion(
        "Casa", original, 2500, 1300, None, pasos, False, ())
    return dialogo_prueba_conexion.DialogoResultadoPruebaConexion(
        None, resultado)


def _espera(datos):
    import threading

    from guyrapu.ui import ventana_espera

    cuadro = ventana_espera.VentanaEspera(
        None, "Probando la conexión", "Conectando con OBS…",
        threading.Event())
    cuadro.estado("Probando a 2500 kbps. Conectando con OBS…")
    return cuadro


def _capturar_ventana(datos):
    from guyrapu.ui import escena_captura_ventana

    opciones = (("Champions", "champions"), ("Calculadora", "calculadora"))
    return escena_captura_ventana.DialogoCapturarVentana(
        None, opciones, "champions")


def _eleccion(datos):
    from guyrapu.ui import escena_propiedades

    opciones = (("Monitor 1", "monitor1"), ("Monitor 2", "monitor2"))
    return escena_propiedades.DialogoEleccion(
        None, "Captura de pantalla", "DialogoPantalla", "&Pantalla:",
        opciones, "monitor1", "No hay pantallas para capturar.")


def _juego(datos):
    from guyrapu.ui import escena_propiedades

    ventanas = (("Champions", "champions"), ("Navegador", "navegador"))
    return escena_propiedades.DialogoJuego(
        None, ventanas, {"modo": "window", "ventana": "champions"})


def _archivo_escena(datos):
    from guyrapu.ui import escena_propiedades

    return escena_propiedades.DialogoArchivo(
        None, "imagen", {"archivo": "C:/Vídeos/cabecera.png"})


def _texto_escena(datos):
    from guyrapu.ui import escena_propiedades

    return escena_propiedades.DialogoTexto(
        None, {"texto": "Bienvenido al directo", "tamano": 72})


def _diseno(datos):
    from guyrapu.obs import disenos_escena
    from guyrapu.obs.fuente_chat import NOMBRE_FUENTE
    from guyrapu.ui import escena_disenos

    fuentes = [
        disenos_escena.Fuente("Juego", "otra", 1600, 900),
        disenos_escena.Fuente("Cámara", "camara", 1280, 720),
        disenos_escena.Fuente(NOMBRE_FUENTE, "chat", 460, 620),
    ]
    return escena_disenos.DisenoEscenaDialog(None, fuentes, [], False)


def _filtros(datos):
    from guyrapu.obs.filtros_microfono import Estado
    from guyrapu.ui import escena_filtros

    return escena_filtros.FiltrosMicrofonoDialog(
        None, "Mic/Aux", Estado(True, False, 6))


def _microfono(datos):
    from guyrapu.ui import gui_microfono

    fuentes = ("Mic/Aux", "Audio USB")
    pares = (("Predeterminado", "default"), ("Micrófono (USB)", "{usb}"))
    return gui_microfono.MicrofonoObsDialog(
        None, fuentes, "Mic/Aux", pares, "{usb}")


def _tamano_fuente(datos):
    from guyrapu.ui import escena_tamano

    return escena_tamano.TamanoFuenteDialog(None, 29, 69)


def _nombre_perfil(datos):
    from guyrapu.ui import obs_pagina_perfiles

    return obs_pagina_perfiles.DialogoNombrePerfil(
        None, con_orientacion=True, accion="C&rear")


_registrar("ajustes_perfil", "DialogoAjustesPerfil", "con_datos",
           _ajustes_perfil)
_registrar("usos_perfil", "DialogoUsosPerfil", "con_datos", _usos_perfil)
_registrar("asistente_perfiles", "DialogoAsistentePerfiles", "con_datos",
           _asistente)
_registrar("resumen_asistente", "DialogoResumenAsistente", "con_datos",
           _resumen)
_registrar("prueba_equipo", "DialogoPruebaEquipo", "con_datos",
           _prueba_equipo)
_registrar("resultado_prueba", "DialogoResultadoPrueba", "con_cambios",
           _resultado_prueba)
_registrar("prueba_conexion", "DialogoPruebaConexion", "con_datos",
           _prueba_conexion)
_registrar("resultado_conexion", "DialogoResultadoPruebaConexion",
           "con_cambios", _resultado_conexion)
_registrar("espera", "VentanaEspera", "con_datos", _espera)
_registrar("capturar_ventana", "DialogoCapturarVentana", "con_datos",
           _capturar_ventana)
_registrar("eleccion", "DialogoEleccion", "con_datos", _eleccion)
_registrar("juego", "DialogoJuego", "con_datos", _juego)
_registrar("archivo_escena", "DialogoArchivo", "con_datos", _archivo_escena)
_registrar("texto_escena", "DialogoTexto", "con_datos", _texto_escena)
_registrar("diseno_escena", "DisenoEscenaDialog", "con_datos", _diseno)
_registrar("filtros_microfono", "FiltrosMicrofonoDialog", "con_datos",
           _filtros)
_registrar("microfono_obs", "MicrofonoObsDialog", "con_datos", _microfono)
_registrar("tamano_fuente", "TamanoFuenteDialog", "con_datos",
           _tamano_fuente)
_registrar("nombre_perfil", "DialogoNombrePerfil", "con_orientacion",
           _nombre_perfil)
