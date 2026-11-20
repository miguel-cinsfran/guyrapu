# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las ventanas de prueba del carril: una limpia y una trampa por regla.

Cada trampa viola a propósito una sola regla de `reglas.py`, y la limpia
cumple todas. Las sondas comparan clases de lista y formas de poner el
nombre para medir qué lee NVDA al llegar a ellas con Tab. No se registran
en la app ni se alcanzan desde ella.

La tabla `VENTANAS` declara el primer control y las acciones de cada una, que
es lo que lee `recorrido.py`. El módulo se puede importar sin wx: las
ventanas se construyen recién en `construir`.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def _comando(nombre):
    return [sys.executable, str(Path(__file__).resolve()),
            "--ventana", nombre]


def _datos(nombre, regla, primero, acciones=(), titulo=""):
    return {
        "nombre": nombre,
        "titulo": titulo or f"Ventana de prueba {nombre}",
        "regla": regla,
        "comando": _comando(nombre),
        "primero": primero,
        "acciones": list(acciones),
    }


def _sonda(nombre):
    datos = _datos(nombre, None, "Antes")
    datos["sonda"] = True
    return datos


VENTANAS = {
    "limpia": _datos(
        "limpia", None, "Nombre completo",
        [{"control": "Anunciar", "gesto": "space"},
         {"control": "Mover foco", "gesto": "space"}],
        titulo="Ventana limpia del carril"),
    "sin_nombre": _datos("sin_nombre", "sin_nombre", "Antes"),
    "rol_contenedor": _datos(
        "rol_contenedor", "rol_contenedor", "Zona de prueba"),
    "nombre_repetido": _datos(
        "nombre_repetido", "nombre_repetido", "Siguiente"),
    "ingles": _datos("ingles", "ingles", "Cancel"),
    "atajo_repetido": _datos(
        "atajo_repetido", "atajo_repetido", "Activar"),
    "paso_mudo": _datos(
        "paso_mudo", "paso_mudo", "Mudo",
        [{"control": "Mudo", "gesto": "space"}]),
    "foco_perdido": _datos(
        "foco_perdido", "foco_perdido", "Deshabilitar",
        [{"control": "Deshabilitar", "gesto": "space"}]),
    "recorrido": _datos("recorrido", "recorrido", "Entrada"),
    "sonda_lista_box": _sonda("sonda_lista_box"),
    "sonda_lista_box_nombre": _sonda("sonda_lista_box_nombre"),
    "sonda_lista_box_pieza": _sonda("sonda_lista_box_pieza"),
    "sonda_lista_box_ayuda": _sonda("sonda_lista_box_ayuda"),
    "sonda_lista_box_msaa": _sonda("sonda_lista_box_msaa"),
    "sonda_lista_vista": _sonda("sonda_lista_vista"),
    "sonda_categorias": _sonda("sonda_categorias"),
}


def _anunciar() -> None:
    from guyrapu.voice.lector import Lector

    Lector().speak("Anuncio de prueba")


def nombre_accesible(control, nombre) -> None:
    """El nombre accesible de la app, con su anotación MSAA."""
    from guyrapu.ui.accesibilidad import nombre_accesible as poner

    poner(control, nombre)


def _construir_sin_nombre(wx, panel, caja, marco):
    campo = wx.TextCtrl(panel)
    nombre_accesible(campo, "Antes")
    caja.Add(campo, 0, wx.EXPAND | wx.ALL, 6)
    boton = wx.BitmapButton(panel, bitmap=wx.Bitmap(16, 16))
    boton.SetName("")
    caja.Add(boton, 0, wx.ALL, 6)
    return campo


def _construir_rol_contenedor(wx, panel, caja, marco):
    class PanelConFoco(wx.Window):

        def AcceptsFocus(self):
            return True

        def AcceptsFocusFromKeyboard(self):
            return True

    zona = PanelConFoco(panel, size=(200, 40))
    nombre_accesible(zona, "Zona de prueba")
    zona.SetCanFocus(True)
    caja.Add(zona, 0, wx.EXPAND | wx.ALL, 6)
    boton = wx.Button(panel, label="Siguiente")
    nombre_accesible(boton, "Siguiente")
    caja.Add(boton, 0, wx.ALL, 6)
    return zona


def _construir_nombre_repetido(wx, panel, caja, marco):
    boton = wx.Button(panel, label="Siguiente")
    nombre_accesible(boton, "Siguiente")
    caja.Add(boton, 0, wx.ALL, 6)
    cuadro = wx.StaticBox(panel, label="Volumen")
    nombre_accesible(cuadro, "Volumen")
    grupo = wx.StaticBoxSizer(cuadro, wx.VERTICAL)
    deslizador = wx.Slider(cuadro, value=50, minValue=0, maxValue=100)
    nombre_accesible(deslizador, "Volumen")
    grupo.Add(deslizador, 0, wx.EXPAND | wx.ALL, 6)
    caja.Add(grupo, 0, wx.EXPAND | wx.ALL, 6)
    return boton


def _construir_ingles(wx, panel, caja, marco):
    boton = wx.Button(panel, label="Cancel")
    nombre_accesible(boton, "Cancel")
    caja.Add(boton, 0, wx.ALL, 6)
    return boton


def _construir_atajo_repetido(wx, panel, caja, marco):
    activar = wx.CheckBox(panel, label="&Activar")
    nombre_accesible(activar, "Activar")
    caja.Add(activar, 0, wx.ALL, 6)
    aplicar = wx.CheckBox(panel, label="&Aplicar")
    nombre_accesible(aplicar, "Aplicar")
    caja.Add(aplicar, 0, wx.ALL, 6)
    return activar


def _construir_paso_mudo(wx, panel, caja, marco):
    boton = wx.Button(panel, label="Mudo")
    nombre_accesible(boton, "Mudo")
    boton.Bind(wx.EVT_BUTTON, lambda evento: None)
    caja.Add(boton, 0, wx.ALL, 6)
    return boton


def _construir_foco_perdido(wx, panel, caja, marco):
    boton = wx.Button(panel, label="Deshabilitar")
    nombre_accesible(boton, "Deshabilitar")
    boton.Bind(wx.EVT_BUTTON, lambda evento: boton.Disable())
    caja.Add(boton, 0, wx.ALL, 6)
    return boton


def _construir_recorrido(wx, panel, caja, marco):
    entrada = wx.Button(panel, label="Entrada")
    nombre_accesible(entrada, "Entrada")
    caja.Add(entrada, 0, wx.ALL, 6)
    campo = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_TAB)
    nombre_accesible(campo, "Campo con Tab")
    caja.Add(campo, 1, wx.EXPAND | wx.ALL, 6)
    return entrada


def _construir_limpia(wx, panel, caja, marco):
    nombre = wx.TextCtrl(panel)
    nombre_accesible(nombre, "Nombre completo")
    caja.Add(nombre, 0, wx.EXPAND | wx.ALL, 6)
    imagen = wx.BitmapButton(panel, bitmap=wx.Bitmap(16, 16))
    nombre_accesible(imagen, "Imagen")
    caja.Add(imagen, 0, wx.ALL, 6)
    cuadro = wx.StaticBox(panel, label="Audio")
    nombre_accesible(cuadro, "Audio")
    grupo = wx.StaticBoxSizer(cuadro, wx.VERTICAL)
    nivel = wx.Slider(cuadro, value=50, minValue=0, maxValue=100)
    nombre_accesible(nivel, "Nivel")
    grupo.Add(nivel, 0, wx.EXPAND | wx.ALL, 6)
    caja.Add(grupo, 0, wx.EXPAND | wx.ALL, 6)
    activar = wx.CheckBox(panel, label="&Activar")
    nombre_accesible(activar, "Activar")
    caja.Add(activar, 0, wx.ALL, 6)
    mostrar = wx.CheckBox(panel, label="&Mostrar")
    nombre_accesible(mostrar, "Mostrar")
    caja.Add(mostrar, 0, wx.ALL, 6)
    anunciar = wx.Button(panel, label="Anunciar")
    nombre_accesible(anunciar, "Anunciar")
    anunciar.Bind(wx.EVT_BUTTON, lambda evento: _anunciar())
    caja.Add(anunciar, 0, wx.ALL, 6)
    mover = wx.Button(panel, label="Mover foco")
    nombre_accesible(mover, "Mover foco")
    destino = wx.TextCtrl(panel)
    nombre_accesible(destino, "Destino")
    caja.Add(destino, 0, wx.EXPAND | wx.ALL, 6)

    def mover_foco(evento):
        destino.SetFocus()
        mover.Disable()

    mover.Bind(wx.EVT_BUTTON, mover_foco)
    caja.Add(mover, 0, wx.ALL, 6)
    libre = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
    nombre_accesible(libre, "Campo libre")
    caja.Add(libre, 1, wx.EXPAND | wx.ALL, 6)
    return nombre


def _boton_antes(wx, panel, caja):
    boton = wx.Button(panel, label="Antes")
    nombre_accesible(boton, "Antes")
    caja.Add(boton, 0, wx.ALL, 6)
    return boton


def _construir_sonda_lista_box(wx, panel, caja, marco):
    antes = _boton_antes(wx, panel, caja)
    lista = wx.ListBox(panel, choices=["Uno", "Dos", "Tres"],
                       name="Lista de sonda")
    lista.SetSelection(0)
    caja.Add(lista, 0, wx.EXPAND | wx.ALL, 6)
    return antes


def _construir_sonda_lista_box_nombre(wx, panel, caja, marco):
    antes = _boton_antes(wx, panel, caja)
    lista = wx.ListBox(panel, choices=["Uno", "Dos", "Tres"])
    nombre_accesible(lista, "Lista de sonda")
    lista.SetSelection(0)
    caja.Add(lista, 0, wx.EXPAND | wx.ALL, 6)
    return antes


def _construir_sonda_lista_box_pieza(wx, panel, caja, marco):
    from guyrapu.ui.lista_acciones import Accion, ListaConAcciones

    antes = _boton_antes(wx, panel, caja)
    lista = wx.ListBox(panel, style=wx.LB_SINGLE | wx.LB_HSCROLL,
                       name="ListaSonda")
    nombre_accesible(lista, "Lista de sonda")
    acciones = (Accion("editar", "&Editar", lambda: None, tecla="intro"),)
    pieza = ListaConAcciones(lista, acciones, "No hay elementos.")
    pieza.fijar(["Uno", "Dos", "Tres"], 0)
    caja.Add(lista, 0, wx.EXPAND | wx.ALL, 6)
    return antes


def _construir_sonda_lista_box_ayuda(wx, panel, caja, marco):
    from guyrapu.ui.accesibilidad import nombre_accesible as poner

    antes = _boton_antes(wx, panel, caja)
    lista = wx.ListBox(panel, choices=["Uno", "Dos", "Tres"])
    poner(lista, "Lista de sonda", msaa=False)
    lista.SetSelection(0)
    caja.Add(lista, 0, wx.EXPAND | wx.ALL, 6)
    return antes


def _construir_sonda_lista_box_msaa(wx, panel, caja, marco):
    from guyrapu.core import nombre_msaa

    antes = _boton_antes(wx, panel, caja)
    lista = wx.ListBox(panel, choices=["Uno", "Dos", "Tres"])
    lista.SetName("Lista de sonda")
    nombre_msaa.poner(lista.GetHandle(), "Lista de sonda")
    lista.SetSelection(0)
    caja.Add(lista, 0, wx.EXPAND | wx.ALL, 6)
    return antes


def _construir_sonda_lista_vista(wx, panel, caja, marco):
    antes = _boton_antes(wx, panel, caja)
    lista = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    lista.InsertColumn(0, "Elemento")
    for indice, texto in enumerate(("Uno", "Dos", "Tres")):
        lista.InsertItem(indice, texto)
    estado = wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
    lista.SetItemState(0, estado, estado)
    nombre_accesible(lista, "Lista de sonda")
    caja.Add(lista, 0, wx.EXPAND | wx.ALL, 6)
    return antes


def _construir_sonda_categorias(wx, panel, caja, marco):
    antes = _boton_antes(wx, panel, caja)
    libro = wx.Listbook(panel)
    nombre_accesible(libro.GetListView(), "Lista de sonda")
    for texto in ("Uno", "Dos", "Tres"):
        pagina = wx.Panel(libro)
        boton = wx.Button(pagina, label=texto)
        nombre_accesible(boton, texto)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(boton, 0, wx.ALL, 6)
        pagina.SetSizer(sizer)
        libro.AddPage(pagina, texto)
    libro.SetSelection(0)
    caja.Add(libro, 1, wx.EXPAND | wx.ALL, 6)
    return antes


_CONSTRUCTORES = {
    "limpia": _construir_limpia,
    "sin_nombre": _construir_sin_nombre,
    "rol_contenedor": _construir_rol_contenedor,
    "nombre_repetido": _construir_nombre_repetido,
    "ingles": _construir_ingles,
    "atajo_repetido": _construir_atajo_repetido,
    "paso_mudo": _construir_paso_mudo,
    "foco_perdido": _construir_foco_perdido,
    "recorrido": _construir_recorrido,
    "sonda_lista_box": _construir_sonda_lista_box,
    "sonda_lista_box_nombre": _construir_sonda_lista_box_nombre,
    "sonda_lista_box_pieza": _construir_sonda_lista_box_pieza,
    "sonda_lista_box_ayuda": _construir_sonda_lista_box_ayuda,
    "sonda_lista_box_msaa": _construir_sonda_lista_box_msaa,
    "sonda_lista_vista": _construir_sonda_lista_vista,
    "sonda_categorias": _construir_sonda_categorias,
}


def construir(nombre):
    """Arma la ventana pedida, sin mostrarla, y deja listo su primer control."""
    import wx

    datos = VENTANAS[nombre]
    marco = wx.Frame(None, title=datos["titulo"])
    panel = wx.Panel(marco)
    caja = wx.BoxSizer(wx.VERTICAL)
    primero = _CONSTRUCTORES[nombre](wx, panel, caja, marco)
    panel.SetSizer(caja)
    marco.Fit()
    marco.Centre()
    marco.primero = primero

    def al_mostrar(evento):
        if evento.IsShown():
            primero.SetFocus()

    marco.Bind(wx.EVT_SHOW, al_mostrar)
    return marco


def main(argv=None) -> int:
    import wx

    analizador = argparse.ArgumentParser(
        description="Ventanas de prueba del carril de NVDA.")
    analizador.add_argument("--ventana", required=True,
                            choices=sorted(VENTANAS))
    analizador.add_argument("--pid-file")
    args = analizador.parse_args(argv)
    if args.pid_file:
        Path(args.pid_file).write_text(str(os.getpid()), encoding="utf-8")
    app = wx.App(False)
    marco = construir(args.ventana)
    marco.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
