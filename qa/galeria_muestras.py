# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Muestras de las ventanas de la aplicación, armadas como en sus pruebas.

Cada `armar(datos)` devuelve una ventana de nivel superior ya construida,
con datos de ejemplo y sin red. Los dobles y el aislamiento de archivos
los deja `galeria.py` en `datos` antes de llamar.
"""

from __future__ import annotations

import logging
import queue
import threading
from types import SimpleNamespace
from unittest import mock

from galeria_muestras_interaccion import MUESTRAS as MUESTRAS_CUADROS

MUESTRAS = []
SIN_MUESTRA = {}
logger = logging.getLogger(__name__)


def _registrar(nombre, clase, variante, armar):
    MUESTRAS.append((nombre, clase, variante, armar))


def _sin_muestra(clase, motivo):
    SIN_MUESTRA[clase] = motivo


def _sembrar_interaccion():
    """Dos elementos en cada lista de la ventana Interacción."""
    from guyrapu.capture import programados
    from guyrapu.core import paths
    from guyrapu.interaction import (comandos_guardados,
                                     disparadores_guardados,
                                     encuestas_guardadas, filtro_publico,
                                     medios_guardados, metas_guardadas)
    from guyrapu.obs import estilos_aviso

    programados.guardar(paths.mensajes_programados(), [
        {"texto": "Bienvenido al directo"}, {"texto": "Sígueme en redes"}])
    comandos_guardados.guardar(paths.comandos(), [
        {"nombre": "discord"}, {"nombre": "saludo"}])
    encuestas_guardadas.guardar(paths.encuestas(), [
        {"pregunta": "¿Qué les gustó?"}, {"pregunta": "¿Seguimos?"}])
    disparadores_guardados.guardar(paths.disparadores(), [
        {"nombre": "Aplausos"}, {"nombre": "Suscripción"}])
    metas_guardadas.guardar(paths.metas(), [
        {"nombre": "Mil seguidores"}, {"nombre": "Diez mil seguidores"}])
    medios_guardados.guardar(paths.medios(), [
        {"nombre": "aplauso.gif", "tipo": "imagen", "archivo": "aplauso.gif"},
        {"nombre": "risa.wav", "tipo": "sonido", "archivo": "risa.wav"}])
    estilos_aviso.guardar_estilos(paths.estilos_avisos(), [
        {"clave": "uno", "nombre": "Estilo uno"},
        {"clave": "dos", "nombre": "Estilo dos"}])
    filtro_publico.guardar(paths.palabras_bloqueadas(), ["spam", "publicidad"])


def _padre_interaccion():
    import wx

    padre = wx.Frame(None)
    padre._config = {}
    padre.mi_programados_activo = mock.Mock()
    padre.programador = mock.Mock()
    preguntas = [SimpleNamespace(autor="Ana", plataforma="youtube",
                                 texto="¿Cómo va el directo?"),
                 SimpleNamespace(autor="Beto", plataforma="tiktok",
                                 texto="¿Qué música suena?")]
    cola = SimpleNamespace(pendientes=lambda: preguntas,
                           suscribir=lambda aviso: None,
                           desuscribir=lambda aviso: None,
                           vaciar=lambda: None)
    padre._preguntas_en_vivo = SimpleNamespace(cola=cola)
    return padre


def _principal(datos, con_chat=False):
    from guyrapu.ui import chat_vivo, gui

    config = {
        "atajos_raw": {}, "filtro_activo": "todos",
        "mostrar_botones_reproductor": False, "mostrar_metadatos": True,
        "mostrar_total_superchats": True, "overlay_activo": False,
        "programados_activo": False,
    }
    stats = SimpleNamespace(leidos=0, superchats=0, descartados=0)
    worker = SimpleNamespace(get_rate=lambda: 0, get_volume=lambda: 100)
    datos.pila.enter_context(mock.patch.object(gui.diagnostico, "crear_hilo"))
    frame = gui.VentanaPrincipal(None, config, queue.Queue(), stats, worker,
                                 threading.Event())
    if con_chat:
        frame._conectado = True
        datos.pila.enter_context(mock.patch.object(
            chat_vivo.wx, "CallLater", return_value=mock.Mock()))
        for autor, texto in (("Ana", "¡Hola a todos!"),
                             ("Beto", "Buen directo"),
                             ("Cris", "Gracias por venir")):
            frame.agregar_mensaje_chat(autor, texto, "20:15:00", "text",
                                       "", plataforma="youtube")
        datos.pila.enter_context(mock.patch.object(
            chat_vivo.wx.Window, "FindFocus", return_value=None))
        frame.chat_vivo.volcar()
    return frame


def _preferencias(datos):
    from guyrapu.ai import catalogo
    from guyrapu.core import config
    from guyrapu.ui import gui_preferencias, preferencias_ia, preferencias_ia_clave
    from guyrapu.voice import motores

    (datos.carpeta / "config.ini").write_text(config._CONFIG_FALLBACK,
                                              encoding="utf-8")
    datos.pila.enter_context(mock.patch.object(
        motores, "listar_voces", return_value=[]))
    datos.pila.enter_context(mock.patch.object(
        preferencias_ia_clave.claves, "leer", return_value=""))
    datos.pila.enter_context(mock.patch.object(
        preferencias_ia.catalogo, "cargar",
        return_value={"version": catalogo.VERSION, "fecha": None,
                      "proveedores": {}}))
    return gui_preferencias.PreferenciasDialog(None, {})


def _interaccion(datos):
    from guyrapu.ui import interaccion_ventana

    _sembrar_interaccion()
    return interaccion_ventana.VentanaInteraccion(_padre_interaccion())


def _musica(datos):
    from guyrapu.ui import musica_ventana
    from tests.test_musica_ventana import ControlFalso

    datos.pila.enter_context(mock.patch.object(
        musica_ventana.wx, "CallAfter", lambda *a, **k: None))
    datos.pila.enter_context(mock.patch.object(
        musica_ventana, "anunciar", mock.Mock()))
    return musica_ventana.VentanaMusica(None, ControlFalso())


def _obs(datos):
    from guyrapu.ui import obs_ventana
    from tests.test_gui_transmision import GestorFalso, PrincipalFalsa

    datos.pila.enter_context(mock.patch.object(
        obs_ventana.OperacionesObs, "en_hilo", lambda *a, **k: None))
    datos.pila.enter_context(mock.patch.object(
        obs_ventana.obs_lanzador, "asegurar_obs", lambda *a, **k: False))
    datos.pila.enter_context(mock.patch.object(
        obs_ventana.wx, "CallAfter", lambda *a, **k: None))
    datos.pila.enter_context(mock.patch.object(obs_ventana, "anunciar",
                                              mock.Mock()))
    return obs_ventana.VentanaObs(None, PrincipalFalsa(), gestor=GestorFalso())


def _ia(datos):
    from guyrapu.ui import ia_ventana

    datos.pila.enter_context(mock.patch.object(
        ia_ventana.diagnostico, "crear_hilo", mock.Mock()))
    datos.pila.enter_context(mock.patch.object(
        ia_ventana.wx, "CallAfter", lambda *a, **k: None))
    return ia_ventana.VentanaIA(None)


def _descargas(datos):
    from guyrapu.downloads import descargas
    from guyrapu.ui import (descargas_acciones, descargas_buscador,
                            descargas_listas, gui_descargas)

    for modulo, nombre in ((descargas_listas.historial_descargas, "cargar"),
                           (descargas_buscador.busquedas_recientes, "cargar")):
        datos.pila.enter_context(mock.patch.object(
            modulo, nombre, return_value=[]))
    for modulo in (descargas_listas.historial_descargas,
                   descargas_acciones.historial_descargas,
                   descargas_buscador.busquedas_recientes):
        datos.pila.enter_context(mock.patch.object(modulo, "guardar"))
    datos.pila.enter_context(mock.patch.object(
        gui_descargas.wx, "CallAfter", lambda *a, **k: None))
    descargas.reiniciar_gestor()
    datos.pila.callback(descargas.reiniciar_gestor)
    datos.pila.callback(setattr, gui_descargas, "_dialogo_activo", None)
    return gui_descargas.GestorDescargasDialog(None)


def _historial(datos):
    from guyrapu.ui import gui_historial

    ruta = datos.carpeta / "historial.json"
    ruta.write_text("[]", encoding="utf-8")
    datos.pila.enter_context(mock.patch.object(
        gui_historial.wx, "CallAfter", lambda *a, **k: None))
    return gui_historial.HistorialDialog(None, ruta, mock.Mock())


def _voces(datos):
    from guyrapu.ui import voces_ventana
    from tests.test_voces_ventana import _Instalados, _catalogo, HiloInmediato

    parches = (
        (voces_ventana.paquetes_instalacion, "instalados", _Instalados([])),
        (voces_ventana.red, "pedir_texto", _catalogo()),
        (voces_ventana.diagnostico, "crear_hilo", HiloInmediato),
        (voces_ventana.voces_disponibles, "idioma_actual", "es"),
    )
    for objeto, nombre, nuevo in parches:
        datos.pila.enter_context(mock.patch.object(objeto, nombre, nuevo))
    datos.pila.enter_context(mock.patch.object(
        voces_ventana.wx, "CallAfter",
        lambda funcion, *a, **k: funcion(*a, **k)))
    for objeto, nombre in ((voces_ventana.confirmar, "avisar"),
                           (voces_ventana._snd, "reproducir"),
                           (voces_ventana, "anunciar")):
        datos.pila.enter_context(mock.patch.object(objeto, nombre, mock.Mock()))
    return voces_ventana.VentanaVoces(None)


def _restream(datos):
    from guyrapu.ui import restream_ventana

    class CuentaFalsa:
        def conectada(self):
            return False

    datos.pila.enter_context(mock.patch.object(
        restream_ventana.wx, "CallAfter", lambda *a, **k: None))
    return restream_ventana.VentanaRestream(
        None, CuentaFalsa(), lambda: [("1", "Canal")],
        datos.carpeta / "perfiles.json", id_canal=lambda: "")


def _ensayo(datos):
    import wx
    from guyrapu.ui import ensayo_ventana

    frame = wx.Frame(None)
    datos.pila.callback(_destruir, frame)
    frame._ensayo = True
    frame._conectado = False
    frame.chat_vivo = mock.Mock()
    frame._capa_video = mock.Mock()
    frame._reiniciar_datos_sesion = mock.Mock()
    frame._encuesta_en_vivo = mock.Mock()
    frame._preguntas_en_vivo = mock.Mock()
    return ensayo_ventana.VentanaEnsayo(frame)


def _destruir(ventana):
    import wx
    try:
        ventana.Destroy()
        wx.SafeYield()
    except Exception as exc:
        logger.debug("No se pudo destruir la ventana: %s", exc)


def _acciones_chat(datos):
    import wx
    from guyrapu.ui import chat_acciones
    from guyrapu.ui.chat_vivo import ControladorChat

    padre = wx.Frame(None)
    datos.pila.callback(_destruir, padre)
    lista = wx.ListBox(padre)
    chat = ControladorChat(
        lista, 500, activo=lambda: True,
        autor_oculto=lambda autor: False,
        formatear=lambda *a: "", al_superchat=lambda monto: None)
    return padre, chat_acciones.AccionesChat(
        lista, chat, mock.Mock(), {}, lambda: None, padre)


def _buscar_chat(datos):
    from guyrapu.ui import chat_buscar

    padre, acciones = _acciones_chat(datos)
    return chat_buscar.CuadroBuscarChat(padre, acciones)


def _participacion(datos):
    from guyrapu.ui import chat_participacion

    padre, acciones = _acciones_chat(datos)
    return chat_participacion.VentanaParticipacion(padre, acciones)


_registrar("principal_desconectada", "VentanaPrincipal", "desconectada",
           lambda datos: _principal(datos))
_registrar("principal_con_chat", "VentanaPrincipal", "con_chat",
           lambda datos: _principal(datos, con_chat=True))
_registrar("preferencias", "PreferenciasDialog", "con_datos", _preferencias)
_registrar("interaccion", "VentanaInteraccion", "con_datos", _interaccion)
_registrar("musica", "VentanaMusica", "con_datos", _musica)
_registrar("obs", "VentanaObs", "sin_obs", _obs)
_registrar("ia", "VentanaIA", "con_datos", _ia)
_registrar("descargas", "GestorDescargasDialog", "con_datos", _descargas)
_registrar("historial", "HistorialDialog", "con_datos", _historial)
_registrar("voces", "VentanaVoces", "con_datos", _voces)
_registrar("restream", "VentanaRestream", "sin_cuenta", _restream)
_registrar("ensayo", "VentanaEnsayo", "con_datos", _ensayo)
_registrar("participacion", "VentanaParticipacion", "con_datos", _participacion)
_registrar("buscar_chat", "CuadroBuscarChat", "con_datos", _buscar_chat)

MUESTRAS.extend(MUESTRAS_CUADROS)

# Las que no se pueden armar fuera de la app sin tocar guyrapu/, y las bases
# de las que cuelgan otros cuadros. El motivo nunca puede quedar vacío.
_SIN_MUESTRA_TEXTO = {
    "DialogoActualizacion": "falta la muestra",
    "DialogoAgregarCaptura": "falta la muestra",
    "DialogoAjustesPerfil": "falta la muestra",
    "DialogoArchivo": "falta la muestra",
    "DialogoAsistentePerfiles": "falta la muestra",
    "DialogoBase": "base abstracta",
    "DialogoCapturarVentana": "falta la muestra",
    "DialogoDestinoBase": "base abstracta",
    "DialogoDestinoManual": "falta la muestra",
    "DialogoDirectoYoutube": "falta la muestra",
    "DialogoEditorLista": "falta la muestra",
    "DialogoEleccion": "falta la muestra",
    "DialogoElegirDestino": "falta la muestra",
    "DialogoEnlace": "falta la muestra",
    "DialogoEstado": "falta la muestra",
    "DialogoFormato": "falta la muestra",
    "DialogoJuego": "falta la muestra",
    "DialogoMetaDestino": "falta la muestra",
    "DialogoNombrePerfil": "falta la muestra",
    "DialogoPerfilRestream": "falta la muestra",
    "DialogoPruebaConexion": "falta la muestra",
    "DialogoPruebaEquipo": "falta la muestra",
    "DialogoRedactar": "falta la muestra",
    "DialogoResultadoPrueba": "falta la muestra",
    "DialogoResultadoPruebaConexion": "falta la muestra",
    "DialogoResumenAsistente": "falta la muestra",
    "DialogoTexto": "falta la muestra",
    "DialogoUsosPerfil": "falta la muestra",
    "DisenoEscenaDialog": "falta la muestra",
    "FiltrosMicrofonoDialog": "falta la muestra",
    "MicrofonoObsDialog": "falta la muestra",
    "PantallaCompleta": "falta la muestra",
    "TamanoFuenteDialog": "falta la muestra",
    "VentanaEspera": "falta la muestra",
}
for _clase, _motivo in _SIN_MUESTRA_TEXTO.items():
    _sin_muestra(_clase, _motivo)
