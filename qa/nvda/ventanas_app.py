# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las ventanas de la aplicación que recorre el carril de NVDA.

Cada entrada dice cómo abrirla por el menú, el título que se espera y el
primer control que toma el foco. Las que llevan `pagina` se abren por la
ventana Interacción y hay que elegir esa página en su lista. Sumar otra
ventana es agregar una entrada.
"""

from __future__ import annotations

from guyrapu.core.idioma import _

# Los nombres de las categorías de Preferencias, en el orden de la app.
PAGINAS_PREFERENCIAS = (
    _("General"),
    _("Interfaz"),
    _("Sonidos"),
    _("Atajos"),
    _("Voces"),
    _("Lectura"),
    _("Cola de lectura"),
    _("Eventos del directo"),
    _("Filtros"),
    _("Estado (F2)"),
    _("Conexión"),
    _("YouTube"),
    _("Reproductor"),
    _("Música"),
    _("Descargas"),
    _("Inteligencia artificial"),
    _("OBS"),
    _("Cámara"),
)

# En una lista, el primero es el elemento seleccionado, no la lista. Los
# primeros de Atajos, Cola de lectura y Lectura salen de los valores de
# fábrica: el carril abre la app con una carpeta de datos aislada y vacía.
VENTANAS = (
    {
        "nombre": "preferencias",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "General",
    },
    {
        "nombre": "interaccion",
        "menu": "Interacción > Mensajes automáticos",
        "titulo": "Interacción",
        "primero": "No hay mensajes automáticos. Usa Agregar para crear uno.",
    },
    {
        "nombre": "comandos",
        "menu": "Interacción > Comandos del chat…",
        "titulo": "Interacción",
        "primero": "No hay comandos. Usa Agregar para crear uno.",
    },
    {
        "nombre": "estilos",
        "menu": "Interacción > Estilos del vídeo…",
        "titulo": "Interacción",
        "primero": ("Clásico (de fábrica), predeterminado de mensajes "
                    "automáticos, comandos, disparadores, encuestas, metas y "
                    "preguntas"),
    },
    {
        "nombre": "historial",
        "menu": "Archivo > Historial de directos…",
        "titulo": "Historial de directos",
        "primero": "No hay entradas de YouTube.",
        "acciones": [
            {"control": "Conectar (el historial está vacío)",
             "espera": "el historial está vacío"},
            {"control": "Eliminar (el historial está vacío)",
             "espera": "el historial está vacío"},
        ],
    },
    {
        "nombre": "descargas",
        "menu": "Herramientas > Administrador de descargas…",
        "titulo": "Administrador de descargas",
        # El foco cae en la edición interna del combo y NVDA no le pone nombre.
        "primero": "",
    },
    {
        "nombre": "palabras",
        "menu": "Interacción > Abrir Interacción…",
        "titulo": "Interacción",
        "primero": "No hay palabras bloqueadas. Usa Agregar para escribir una.",
        "pagina": "Palabras bloqueadas",
    },
    {
        "nombre": "encuestas",
        "menu": "Interacción > Abrir Interacción…",
        "titulo": "Interacción",
        "primero": "No hay encuestas. Usa Agregar para crear una.",
        "pagina": "Encuestas",
    },
    {
        "nombre": "preguntas",
        "menu": "Interacción > Abrir Interacción…",
        "titulo": "Interacción",
        "primero": ("No hay preguntas. El público las hace con el comando "
                    "pregunta y el texto."),
        "pagina": "Preguntas",
    },
    {
        "nombre": "medios",
        "menu": "Interacción > Abrir Interacción…",
        "titulo": "Interacción",
        "primero": "No hay medios. Usa Agregar para crear uno.",
        "pagina": "Medios",
    },
    {
        "nombre": "preferencias_interfaz",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Tamaño de letra del chat (8 a 24):",
        "pagina": "Interfaz",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_sonidos",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Tema de sonido:",
        "pagina": "Sonidos",
        "paginas": PAGINAS_PREFERENCIAS,
        "acciones": [
            {"control": "Acción completada; Familia: Completado",
             "gesto": "upArrow"},
        ],
    },
    {
        "nombre": "preferencias_atajos",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Reproducir o pausar: Ctrl+P",
        "pagina": "Atajos",
        "paginas": PAGINAS_PREFERENCIAS,
        "tope": 90,
        "acciones": [
            {"control": "Bajar velocidad de la voz: F9 (fija)",
             "espera": "Este atajo es fijo"},
        ],
    },
    {
        "nombre": "preferencias_voces",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Motor de voz:",
        "pagina": "Voces",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_lectura",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Nombre y mensaje",
        "pagina": "Lectura",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_cola_de_lectura",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Descartar los más antiguos si se acumulan",
        "pagina": "Cola de lectura",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_eventos_del_directo",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Super Chats y regalos:",
        "pagina": "Eventos del directo",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_filtros",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Palabras silenciadas (separadas por comas):",
        "pagina": "Filtros",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_estado_f2",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Estado de conexión y tipo",
        "pagina": "Estado (F2)",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_conexion",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Reconectar automáticamente",
        "pagina": "Conexión",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_youtube",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Clave de API:",
        "pagina": "YouTube",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_reproductor",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Reproducir audio automáticamente al conectar",
        "pagina": "Reproductor",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_musica",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Carpeta de música",
        "pagina": "Música",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_descargas",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Carpeta de descargas",
        "pagina": "Descargas",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_inteligencia_artificial",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Proveedor:",
        "pagina": "Inteligencia artificial",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_obs",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Avisar si OBS se sobrecarga",
        "pagina": "OBS",
        "paginas": PAGINAS_PREFERENCIAS,
    },
    {
        "nombre": "preferencias_camara",
        "menu": "Herramientas > Preferencias",
        "titulo": "Preferencias",
        "primero": "Avisar si el rostro sale del encuadre",
        "pagina": "Cámara",
        "paginas": PAGINAS_PREFERENCIAS,
    },
)
