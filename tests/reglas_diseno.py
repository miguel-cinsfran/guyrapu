# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Detectores de armado visual escrito a mano en la interfaz.

Cuentan bordes, tamaños, letras y colores puestos con números o texto en
guyrapu/ui/. Las piezas comunes son las dueñas y el resto queda pendiente.
"""

from __future__ import annotations

import ast

from tests.reglas_detectores import Hallazgo

PIEZAS = (
    "guyrapu/ui/formulario.py",
    "guyrapu/ui/pagina_de_lista.py",
    "guyrapu/ui/botonera.py",
    "guyrapu/ui/deslizador.py",
    "guyrapu/ui/paleta.py",
    "guyrapu/ui/tema.py",
)

MOTIVO = "falta pasar a las piezas comunes"

_POSICION_BORDE = {"Add": 3, "Insert": 4}
_METODOS_TAMANO = ("SetSize", "SetMinSize", "SetMaxSize", "SetInitialSize")


def _ui(archivo: str) -> bool:
    return archivo.startswith("guyrapu/ui/")


def _numeros(nodo: ast.expr) -> list[int | float]:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)):
        if not isinstance(nodo.value, bool):
            return [nodo.value]
    if isinstance(nodo, (ast.Tuple, ast.List)):
        return [valor for elemento in nodo.elts
                for valor in _numeros(elemento)]
    return []


def _destino(nodo: ast.expr) -> str | None:
    if isinstance(nodo, ast.Attribute):
        return nodo.attr
    if isinstance(nodo, ast.Name):
        return nodo.id
    return None


def _es_wx(nodo: ast.expr, nombre: str) -> bool:
    return (isinstance(nodo, ast.Attribute) and nodo.attr == nombre
            and isinstance(nodo.value, ast.Name) and nodo.value.id == "wx")


def _borde_de(llamada: ast.Call) -> ast.expr | None:
    posicion = _POSICION_BORDE.get(_destino(llamada.func))
    if posicion is not None and len(llamada.args) > posicion:
        return llamada.args[posicion]
    for palabra in llamada.keywords:
        if palabra.arg == "border":
            return palabra.value
    return None


def _numero_local(nodo: ast.stmt) -> bool:
    if not isinstance(nodo, ast.Assign):
        return False
    if not any(isinstance(destino, ast.Name) for destino in nodo.targets):
        return False
    return bool(_numeros(nodo.value))


def _unicos(hallazgos: list[Hallazgo]) -> list[Hallazgo]:
    vistos: set[int] = set()
    resultado = []
    for hallazgo in sorted(hallazgos, key=lambda hallazgo: hallazgo.linea):
        if hallazgo.linea not in vistos:
            vistos.add(hallazgo.linea)
            resultado.append(hallazgo)
    return resultado


def detectar_bordes(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            borde = _borde_de(nodo)
            if borde is not None and any(valor != 0
                                         for valor in _numeros(borde)):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
        if _numero_local(nodo):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return _unicos(hallazgos)


def detectar_tamanos(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            valores = [*nodo.args, *(kw.value for kw in nodo.keywords)]
            if (_destino(nodo.func) in _METODOS_TAMANO
                    or _es_wx(nodo.func, "Size")):
                if any(valor != -1 for arg in valores
                       for valor in _numeros(arg)):
                    hallazgos.append(Hallazgo(archivo, nodo.lineno))
            elif any(kw.arg == "size" and any(valor != -1
                                              for valor in _numeros(kw.value))
                     for kw in nodo.keywords):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
        if _numero_local(nodo):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return _unicos(hallazgos)


def detectar_fuentes(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if _es_wx(nodo.func, "Font"):
            if (nodo.args and _numeros(nodo.args[0])) or any(
                    kw.arg == "pointSize" and _numeros(kw.value)
                    for kw in nodo.keywords):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
        elif (_destino(nodo.func) == "SetPointSize"
              and any(_numeros(arg) for arg in nodo.args)):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return _unicos(hallazgos)


def _literal_color(nodo: ast.expr) -> bool:
    if isinstance(nodo, (ast.Tuple, ast.List)):
        return any(_literal_color(elemento) for elemento in nodo.elts)
    if isinstance(nodo, ast.Constant):
        return (isinstance(nodo.value, (int, float, str))
                and not isinstance(nodo.value, bool))
    return False


def _tupla_o_texto(nodo: ast.expr) -> bool:
    if isinstance(nodo, ast.Tuple):
        return any(_literal_color(elemento) for elemento in nodo.elts)
    return isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)


def detectar_colores(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if _es_wx(nodo.func, "Colour"):
            if any(_literal_color(arg) for arg in nodo.args):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
        elif (_destino(nodo.func) in ("SetForegroundColour",
                                      "SetBackgroundColour")
              and nodo.args and _tupla_o_texto(nodo.args[0])):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return _unicos(hallazgos)


PENDIENTES_BORDES: dict[str, tuple[int, str]] = {
    "guyrapu/ui/gui_preferencias.py": (31, MOTIVO),
    "guyrapu/ui/preferencias_musica.py": (21, MOTIVO),
    "guyrapu/ui/preferencias_ia.py": (20, MOTIVO),
    "guyrapu/ui/preferencias_descargas.py": (16, MOTIVO),
    "guyrapu/ui/preferencias_lectura.py": (16, MOTIVO),
    "guyrapu/ui/preferencias_voz.py": (16, MOTIVO),
    "guyrapu/ui/preferencias_transmision.py": (15, MOTIVO),
    "guyrapu/ui/preferencias_voz_secundaria.py": (14, MOTIVO),
    "guyrapu/ui/descargas_buscador.py": (13, MOTIVO),
    "guyrapu/ui/gui_descargas.py": (13, MOTIVO),
    "guyrapu/ui/voces_ventana.py": (13, MOTIVO),
    "guyrapu/ui/gui_construccion.py": (12, MOTIVO),
    "guyrapu/ui/musica_ventana.py": (12, MOTIVO),
    "guyrapu/ui/gui.py": (11, MOTIVO),
    "guyrapu/ui/preferencias_general.py": (10, MOTIVO),
    "guyrapu/ui/escena_pagina_audio.py": (9, MOTIVO),
    "guyrapu/ui/gui_comentarios.py": (9, MOTIVO),
    "guyrapu/ui/obs_ventana.py": (8, MOTIVO),
    "guyrapu/ui/preferencias_camara.py": (8, MOTIVO),
    "guyrapu/ui/preferencias_voz_eleven.py": (8, MOTIVO),
    "guyrapu/ui/chat_participacion.py": (7, MOTIVO),
    "guyrapu/ui/preferencias_api.py": (7, MOTIVO),
    "guyrapu/ui/musica_filtros.py": (6, MOTIVO),
    "guyrapu/ui/restream_pagina_eventos.py": (6, MOTIVO),
    "guyrapu/ui/chat_buscar.py": (5, MOTIVO),
    "guyrapu/ui/descargas_listas.py": (5, MOTIVO),
    "guyrapu/ui/encuadre_camara.py": (5, MOTIVO),
    "guyrapu/ui/escena_pagina_escena.py": (5, MOTIVO),
    "guyrapu/ui/gui_historial.py": (5, MOTIVO),
    "guyrapu/ui/preferencias_comun.py": (5, MOTIVO),
    "guyrapu/ui/preferencias_ia_clave.py": (5, MOTIVO),
    "guyrapu/ui/preferencias_sonidos.py": (5, MOTIVO),
    "guyrapu/ui/teclado_altgr.py": (5, MOTIVO),
    "guyrapu/ui/escena_pagina_fuentes.py": (4, MOTIVO),
    "guyrapu/ui/escena_propiedades.py": (4, MOTIVO),
    "guyrapu/ui/ia_ventana.py": (4, MOTIVO),
    "guyrapu/ui/obs_pagina_general.py": (4, MOTIVO),
    "guyrapu/ui/preferencias_atajos.py": (4, MOTIVO),
    "guyrapu/ui/recientes_inicio.py": (4, MOTIVO),
    "guyrapu/ui/barra_estado.py": (3, MOTIVO),
    "guyrapu/ui/barra_progreso.py": (3, MOTIVO),
    "guyrapu/ui/encuesta_en_vivo.py": (3, MOTIVO),
    "guyrapu/ui/gui_directo_youtube.py": (3, MOTIVO),
    "guyrapu/ui/gui_transmision.py": (3, MOTIVO),
    "guyrapu/ui/musica_sonoridad.py": (3, MOTIVO),
    "guyrapu/ui/musica_ventana_igualando.py": (3, MOTIVO),
    "guyrapu/ui/obs_pagina_grabacion.py": (3, MOTIVO),
    "guyrapu/ui/restream_pagina_perfiles.py": (3, MOTIVO),
    "guyrapu/ui/ajuste_tono.py": (2, MOTIVO),
    "guyrapu/ui/atajos_globales.py": (2, MOTIVO),
    "guyrapu/ui/buscador_filtros.py": (2, MOTIVO),
    "guyrapu/ui/escena_agregar_fuente.py": (2, MOTIVO),
    "guyrapu/ui/gui_redactar.py": (2, MOTIVO),
    "guyrapu/ui/guia_encuadre.py": (2, MOTIVO),
    "guyrapu/ui/ia_agregar_captura.py": (2, MOTIVO),
    "guyrapu/ui/interaccion_ventana.py": (2, MOTIVO),
    "guyrapu/ui/lista_acciones.py": (2, MOTIVO),
    "guyrapu/ui/lista_chat.py": (2, MOTIVO),
    "guyrapu/ui/meta_cuadro.py": (2, MOTIVO),
    "guyrapu/ui/metas_en_vivo.py": (2, MOTIVO),
    "guyrapu/ui/obs_pagina_perfiles.py": (2, MOTIVO),
    "guyrapu/ui/preferencias_eventos.py": (2, MOTIVO),
    "guyrapu/ui/restream_pagina_cuenta.py": (2, MOTIVO),
    "guyrapu/ui/restream_pagina_destinos.py": (2, MOTIVO),
    "guyrapu/ui/restream_perfil.py": (2, MOTIVO),
    "guyrapu/ui/restream_ventana.py": (2, MOTIVO),
    "guyrapu/ui/aviso_progreso.py": (1, MOTIVO),
    "guyrapu/ui/botonera_atajos.py": (1, MOTIVO),
    "guyrapu/ui/busqueda_lista.py": (1, MOTIVO),
    "guyrapu/ui/busqueda_teclado.py": (1, MOTIVO),
    "guyrapu/ui/camara_atajos.py": (1, MOTIVO),
    "guyrapu/ui/capa_video.py": (1, MOTIVO),
    "guyrapu/ui/chat_recientes.py": (1, MOTIVO),
    "guyrapu/ui/chat_vivo.py": (1, MOTIVO),
    "guyrapu/ui/clave_elevenlabs.py": (1, MOTIVO),
    "guyrapu/ui/comandos_en_vivo.py": (1, MOTIVO),
    "guyrapu/ui/disparador_cuadro.py": (1, MOTIVO),
    "guyrapu/ui/encuesta_cuadro.py": (1, MOTIVO),
    "guyrapu/ui/escena_atajos.py": (1, MOTIVO),
    "guyrapu/ui/escena_disenos.py": (1, MOTIVO),
    "guyrapu/ui/espera_sonora.py": (1, MOTIVO),
    "guyrapu/ui/gui_grabaciones.py": (1, MOTIVO),
    "guyrapu/ui/interaccion_atajos.py": (1, MOTIVO),
    "guyrapu/ui/medio_descripcion_ia.py": (1, MOTIVO),
    "guyrapu/ui/medios_ventana.py": (1, MOTIVO),
    "guyrapu/ui/menu_reproductor.py": (1, MOTIVO),
    "guyrapu/ui/musica_cola.py": (1, MOTIVO),
    "guyrapu/ui/musica_editor_lista.py": (1, MOTIVO),
    "guyrapu/ui/preferencias_ia_lista.py": (1, MOTIVO),
    "guyrapu/ui/preguntas_en_vivo.py": (1, MOTIVO),
    "guyrapu/ui/prueba_voz.py": (1, MOTIVO),
    "guyrapu/ui/teclas_wx.py": (1, MOTIVO),
    "guyrapu/ui/voces_instalacion.py": (1, MOTIVO),
}

PENDIENTES_TAMANOS: dict[str, tuple[int, str]] = {
    "guyrapu/ui/gui.py": (12, MOTIVO),
    "guyrapu/ui/obs_ventana.py": (8, MOTIVO),
    "guyrapu/ui/gui_descargas.py": (7, MOTIVO),
    "guyrapu/ui/encuadre_camara.py": (5, MOTIVO),
    "guyrapu/ui/teclado_altgr.py": (5, MOTIVO),
    "guyrapu/ui/gui_directo_youtube.py": (4, MOTIVO),
    "guyrapu/ui/barra_estado.py": (3, MOTIVO),
    "guyrapu/ui/barra_progreso.py": (3, MOTIVO),
    "guyrapu/ui/encuesta_en_vivo.py": (3, MOTIVO),
    "guyrapu/ui/escena_propiedades.py": (3, MOTIVO),
    "guyrapu/ui/gui_preferencias.py": (3, MOTIVO),
    "guyrapu/ui/musica_sonoridad.py": (3, MOTIVO),
    "guyrapu/ui/preferencias_transmision.py": (3, MOTIVO),
    "guyrapu/ui/ajuste_tono.py": (2, MOTIVO),
    "guyrapu/ui/atajos_globales.py": (2, MOTIVO),
    "guyrapu/ui/dialogo_asistente_perfiles.py": (2, MOTIVO),
    "guyrapu/ui/dialogo_prueba_conexion.py": (2, MOTIVO),
    "guyrapu/ui/dialogo_prueba_equipo.py": (2, MOTIVO),
    "guyrapu/ui/encuesta_cuadro.py": (2, MOTIVO),
    "guyrapu/ui/escena_agregar_fuente.py": (2, MOTIVO),
    "guyrapu/ui/escena_pagina_audio.py": (2, MOTIVO),
    "guyrapu/ui/gui_construccion.py": (2, MOTIVO),
    "guyrapu/ui/gui_microfono.py": (2, MOTIVO),
    "guyrapu/ui/guia_encuadre.py": (2, MOTIVO),
    "guyrapu/ui/ia_agregar_captura.py": (2, MOTIVO),
    "guyrapu/ui/ia_ventana.py": (2, MOTIVO),
    "guyrapu/ui/lista_acciones.py": (2, MOTIVO),
    "guyrapu/ui/lista_chat.py": (2, MOTIVO),
    "guyrapu/ui/meta_cuadro.py": (2, MOTIVO),
    "guyrapu/ui/metas_en_vivo.py": (2, MOTIVO),
    "guyrapu/ui/musica_editor_lista.py": (2, MOTIVO),
    "guyrapu/ui/musica_filtros.py": (2, MOTIVO),
    "guyrapu/ui/musica_ventana.py": (2, MOTIVO),
    "guyrapu/ui/preferencias_comun.py": (2, MOTIVO),
    "guyrapu/ui/preferencias_descargas.py": (2, MOTIVO),
    "guyrapu/ui/voces_ventana.py": (2, MOTIVO),
    "guyrapu/ui/aviso_progreso.py": (1, MOTIVO),
    "guyrapu/ui/botonera_atajos.py": (1, MOTIVO),
    "guyrapu/ui/busqueda_lista.py": (1, MOTIVO),
    "guyrapu/ui/busqueda_teclado.py": (1, MOTIVO),
    "guyrapu/ui/camara_atajos.py": (1, MOTIVO),
    "guyrapu/ui/capa_video.py": (1, MOTIVO),
    "guyrapu/ui/chat_buscar.py": (1, MOTIVO),
    "guyrapu/ui/chat_participacion.py": (1, MOTIVO),
    "guyrapu/ui/chat_recientes.py": (1, MOTIVO),
    "guyrapu/ui/chat_vivo.py": (1, MOTIVO),
    "guyrapu/ui/clave_elevenlabs.py": (1, MOTIVO),
    "guyrapu/ui/comandos_en_vivo.py": (1, MOTIVO),
    "guyrapu/ui/descargas_buscador.py": (1, MOTIVO),
    "guyrapu/ui/disparador_cuadro.py": (1, MOTIVO),
    "guyrapu/ui/ensayo_ventana.py": (1, MOTIVO),
    "guyrapu/ui/escena_atajos.py": (1, MOTIVO),
    "guyrapu/ui/escena_disenos.py": (1, MOTIVO),
    "guyrapu/ui/escena_pagina_escena.py": (1, MOTIVO),
    "guyrapu/ui/escena_pagina_fuentes.py": (1, MOTIVO),
    "guyrapu/ui/espera_sonora.py": (1, MOTIVO),
    "guyrapu/ui/gui_actualizacion.py": (1, MOTIVO),
    "guyrapu/ui/gui_comentarios.py": (1, MOTIVO),
    "guyrapu/ui/gui_historial.py": (1, MOTIVO),
    "guyrapu/ui/interaccion_atajos.py": (1, MOTIVO),
    "guyrapu/ui/interaccion_ventana.py": (1, MOTIVO),
    "guyrapu/ui/medio_descripcion_ia.py": (1, MOTIVO),
    "guyrapu/ui/medios_ventana.py": (1, MOTIVO),
    "guyrapu/ui/menu_reproductor.py": (1, MOTIVO),
    "guyrapu/ui/musica_cola.py": (1, MOTIVO),
    "guyrapu/ui/musica_ventana_igualando.py": (1, MOTIVO),
    "guyrapu/ui/obs_pagina_general.py": (1, MOTIVO),
    "guyrapu/ui/preferencias_eventos.py": (1, MOTIVO),
    "guyrapu/ui/preferencias_ia.py": (1, MOTIVO),
    "guyrapu/ui/preferencias_ia_lista.py": (1, MOTIVO),
    "guyrapu/ui/preferencias_lectura.py": (1, MOTIVO),
    "guyrapu/ui/preferencias_musica.py": (1, MOTIVO),
    "guyrapu/ui/preferencias_sonidos.py": (1, MOTIVO),
    "guyrapu/ui/preferencias_voz.py": (1, MOTIVO),
    "guyrapu/ui/preguntas_en_vivo.py": (1, MOTIVO),
    "guyrapu/ui/prueba_voz.py": (1, MOTIVO),
    "guyrapu/ui/recientes_inicio.py": (1, MOTIVO),
    "guyrapu/ui/restream_pagina_perfiles.py": (1, MOTIVO),
    "guyrapu/ui/restream_perfil.py": (1, MOTIVO),
    "guyrapu/ui/restream_ventana.py": (1, MOTIVO),
    "guyrapu/ui/teclas_wx.py": (1, MOTIVO),
    "guyrapu/ui/ventana_espera.py": (1, MOTIVO),
    "guyrapu/ui/voces_instalacion.py": (1, MOTIVO),
}

PENDIENTES_FUENTES: dict[str, tuple[int, str]] = {}
PENDIENTES_COLORES: dict[str, tuple[int, str]] = {}
