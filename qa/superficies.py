# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué superficie del banco recorre cada módulo de interfaz.

Los `gui*.py` no se listan: se descubren en `superficies_sin_escenario`.
`SIN_ESCENARIO` reúne los que dibujan interfaz y no abren ventana propia.
"""

from __future__ import annotations

SUPERFICIES = {
    "gui.py": "principal",
    "gui_cierre.py": "principal",
    "gui_construccion.py": "principal",
    "gui_sesion.py": "principal",
    "capa_video.py": "principal",
    "chat_acciones.py": "principal",
    "chat_buscar.py": "menu_chat",
    "chat_participacion.py": "menu_chat",
    "confirmar_salida.py": "principal",
    "titulo_ventana.py": "principal",
    "gui_actualizacion.py": "actualizaciones",
    "gui_actualizar_app.py": "actualizaciones",
    "gui_actualizar_ytdlp.py": "actualizaciones",
    "gui_aplicar_preferencias.py": "preferencias",
    "gui_comentarios.py": "comentarios",
    "gui_descargas.py": "descargas",
    "descargas_buscador.py": "descargas",
    "buscador_filtros.py": "descargas",
    "buscador_acciones.py": "descargas",
    "buscador_escucha.py": "descargas",
    "elegir_formato.py": "descargas",
    "buscador_contenido.py": "descargas",
    "buscador_tandas.py": "descargas",
    "barra_progreso.py": "descargas",
    "descargas_listas.py": "descargas",
    "descargas_acciones.py": "descargas",
    "aviso_progreso.py": "descargas",
    "gui_directo_huerfano.py": "directo_sin_imagen",
    "gui_directo_youtube.py": "transmitir_destino",
    "miniatura_directo.py": "transmitir_destino",
    "gui_elegir_destino.py": "transmitir_destino",
    "gui_envio_chat.py": "redactar",
    "gui_estado.py": "principal",
    "dialogo_estado.py": "principal",
    "gui_historial.py": "historial",
    "gui_grabaciones.py": "grabacion",
    "obs_ventana.py": "escena",
    "obs_pagina_grabacion.py": "grabacion",
    "obs_pagina_general.py": "escena",
    "obs_pagina_perfiles.py": "escena",
    "dialogo_nombre_perfil_obs.py": "escena",
    "dialogo_ajustes_perfil.py": "escena",
    "dialogo_usos_perfil.py": "escena",
    "dialogo_asistente_perfiles.py": "escena",
    "dialogo_prueba_equipo.py": "escena",
    "dialogo_prueba_conexion.py": "escena",
    "ventana_espera.py": "escena",
    "restream_ventana.py": "restream",
    "restream_pagina_perfiles.py": "restream",
    "restream_pagina_destinos.py": "restream",
    "restream_pagina_cuenta.py": "restream",
    "restream_pagina_eventos.py": "restream",
    "restream_menus.py": "restream",
    "recientes_inicio.py": "principal",
    "gui_menu.py": "menus",
    "menu_obs.py": "menus",
    "menu_interaccion.py": "menus",
    "interaccion_ventana.py": "mensajes_automaticos",
    "mensajes_automaticos_ventana.py": "mensajes_automaticos",
    "estilos_ventana.py": "estilos",
    "comandos_ventana.py": "comandos",
    "encuestas_ventana.py": "comandos",
    "disparadores_ventana.py": "comandos",
    "metas_ventana.py": "comandos",
    "medios_ventana.py": "comandos",
    "palabras_bloqueadas_ventana.py": "mensajes_automaticos",
    "menu_reproductor.py": "menus",
    "menu_transmision.py": "menus",
    "menu_moderacion.py": "menu_chat",
    "gui_microfono.py": "microfono",
    "guia_encuadre.py": "encuadre",
    "gui_musica.py": "musica",
    "controles_medios.py": "musica",
    "musica_desde_fuera.py": "musica",
    "musica_dialogo_enlace.py": "musica",
    "musica_colecciones.py": "musica",
    "musica_editor_lista.py": "musica",
    "musica_filtros.py": "musica",
    "musica_menus.py": "musica",
    "musica_ventana.py": "musica",
    "musica_ventana_acciones.py": "musica",
    "musica_ventana_igualando.py": "musica",
    "ia_ventana.py": "ia",
    "ia_agregar_captura.py": "ia",
    "ia_consulta_rapida.py": "ia",
    "ia_privacidad.py": "ia",
    "gui_transmision.py": "transmision",
    "escena_pagina_escena.py": "escena",
    "escena_pagina_fuentes.py": "escena",
    "escena_agregar_fuente.py": "escena",
    "escena_propiedades.py": "escena",
    "escena_menu_fuente.py": "escena",
    "escena_menu_escena.py": "escena",
    "escena_version_vertical.py": "escena",
    "escena_edicion_fuente.py": "escena",
    "escena_captura_ventana.py": "escena",
    "escena_pagina_audio.py": "escena",
    "escena_escucha.py": "escena",
    "escena_tamano.py": "escena",
    "escena_filtros.py": "escena",
    "escena_disenos.py": "escena",
    "disenos_nombres.py": "escena",
    "control_grabacion.py": "transmision",
    "directo_panel.py": "transmision",
    "mover_con_flechas.py": "escena",
    "confirmar_transmision.py": "transmision",
    "gui_transmitir.py": "transmitir_destino",
    "inicio_youtube.py": "transmitir_destino",
    "gui_preferencias.py": "preferencias",
    "libro_perezoso.py": "preferencias",
    "gui_redactar.py": "redactar",
    "reproductor.py": "reproductor",
    "pantalla_completa.py": "reproductor",
    "iconos.py": "reproductor",
    "boton_directo.py": "principal",
    "camara_atajos.py": "principal",
    "escena_atajos.py": "principal",
    "accesibilidad.py": "principal",
    "preferencias_comun.py": "preferencias",
    "preferencias_api.py": "preferencias",
    "preferencias_atajos.py": "preferencias",
    "preferencias_general.py": "preferencias",
    "preferencias_musica.py": "preferencias",
    "preferencias_descargas.py": "preferencias",
    "preferencias_sonidos.py": "preferencias",
    "preferencias_ia.py": "preferencias",
    "preferencias_ia_clave.py": "preferencias",
    "preferencias_ia_lista.py": "preferencias",
    "preferencias_lectura.py": "preferencias",
    "preferencias_eventos.py": "preferencias",
    "preferencias_transmision.py": "preferencias",
    "preferencias_camara.py": "preferencias",
    "preferencias_voz.py": "preferencias",
    "preferencias_voz_eleven.py": "preferencias",
    "preferencias_voz_secundaria.py": "preferencias",
    "voces_ventana.py": "preferencias",
    "paleta.py": "actualizaciones",
}

# Módulos que dibujan interfaz sin escena a propósito: cada uno lleva su
# motivo como valor y no cuenta como huérfano en `superficies_sin_escenario()`.
SIN_ESCENARIO: dict[str, str] = {
    "ajuste_tono.py": "comando del menú Voz que ajusta el tono; no abre ventana.",
    "lista_acciones.py": (
        "da teclas y menú a una lista; la recorren los escenarios de las "
        "ventanas que la usen."),
    "lista_ctrl.py": (
        "traduce a un wx.ListCtrl lo que pide la pieza de listas; la "
        "recorren los escenarios de las ventanas que la usen."),
    "probar_aviso.py": (
        "es el comando Probar de las páginas de estilos y mensajes "
        "automáticos; no abre ventana propia."),
    "operaciones_obs.py": "opera sobre OBS en un hilo para las ventanas; no abre una propia.",
    "comandos_grabacion.py": "comandos del menú OBS que actúan sobre OBS; no abren ventana.",
    "comandos_clips.py": "comanda el búfer de clips del menú OBS; no abre ventana.",
    "comandos_en_vivo.py": (
        "atiende los comandos del chat y no abre ventana propia."),
    "disparadores_en_vivo.py": (
        "atiende los disparadores del chat y no abre ventana propia."),
    "encuesta_en_vivo.py": (
        "atiende la encuesta abierta de la sesión y no abre ventana propia."),
    "comando_cerrar_obs.py": (
        "comando del menú OBS y del panel que cierra OBS; no abre ventana."),
    "comando_directo.py": (
        "comando del botón y del panel que transmite y finaliza el directo; "
        "no abre ventana propia."),
    "cortina_captura.py": (
        "ofrece cambiar el método de captura antes de transmitir; el cuadro "
        "lo cubren las pruebas con wx y no abre una ventana propia."),
    "comando_en_directo.py": (
        "comandos del menú Interacción que actúan sobre la cola del vídeo; "
        "no abren ventana propia."),
    "interaccion_atajos.py": (
        "registra los atajos globales de lo que sale en el vídeo; no abre "
        "ventana propia."),
    "restream_perfil.py": "El banco no tiene cuenta ni canales; el diálogo lo cubren las pruebas con wx.",
    "restream_dialogos_destino.py": "El banco no tiene cuenta ni canales; los cuadros los cubren las pruebas con wx.",
    "agregar_camara.py": (
        "El banco no tiene cámara de Windows; el flujo lo cubren las pruebas "
        "con wx y la prueba contra OBS real."),
    "confirmar.py": "Envuelve los cuadros nativos de Windows; no abre una ventana propia.",
    "tecla_escape.py": "Atiende teclas y no abre ventana propia.",
    "mensaje_automatico_cuadro.py": (
        "el cuadro lo cubren las pruebas con wx; el banco audita la "
        "ventana que lo abre."),
    "estilo_cuadro.py": (
        "el cuadro lo cubren las pruebas con wx; el banco audita la "
        "ventana que lo abre."),
    "estilo_tipos_cuadro.py": (
        "el cuadro lo cubren las pruebas con wx; el banco audita la "
        "ventana que lo abre."),
    "estilo_opciones.py": (
        "arma los desplegables de un estilo; los recorren las pruebas y el "
        "escenario de la ventana que los usa."),
    "comando_cuadro.py": (
        "el cuadro lo cubren las pruebas con wx; el banco audita la "
        "ventana que lo abre."),
    "encuesta_cuadro.py": (
        "el cuadro lo cubren las pruebas con wx; el banco audita la "
        "ventana que lo abre."),
    "disparador_cuadro.py": (
        "el cuadro lo cubren las pruebas con wx; el banco audita la "
        "ventana que lo abre."),
    "meta_cuadro.py": (
        "el cuadro lo cubren las pruebas con wx; el banco audita la "
        "ventana que lo abre."),
    "medio_cuadro.py": (
        "el cuadro lo cubren las pruebas con wx; el banco audita la "
        "ventana que lo abre."),
    "medio_descripcion_ia.py": (
        "lo cubren las pruebas con wx y usa la espera común; no abre una "
        "ventana propia."),
    "menu_habilitado.py": "Prende y apaga elementos de menú y no abre ventana propia.",
    "ayuda_manual.py": (
        "Atiende F1 y arma la página de redirección; no abre ventana propia."),
    "aviso_importante.py": "Envuelve los cuadros de aviso de Windows; no abre una ventana propia.",
    "espera_sonora.py": "Suena la espera de otra ventana y no abre ventana propia.",
    "estado_relevo.py": "Guarda el estado del relevo en curso; no abre una ventana propia.",
}
