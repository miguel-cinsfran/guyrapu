# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Libro de wx que arma cada página recién la primera vez que se elige.

Las páginas caras de Preferencias (voces, eventos, inteligencia artificial)
solo se pagan cuando el usuario las mira. Sin pereza se construyen todas al
crear, que es lo que esperan las pruebas de cada página.
"""

from __future__ import annotations

import wx


class LibroPerezoso:
    """Envoltorio de un libro de wx con construcción diferida de páginas.

    Cada entrada es un título y una función que recibe la página vacía como
    padre y devuelve el panel real. Con pereza, el libro guarda un panel
    vacío con el título y el panel real se agrega dentro la primera vez que
    esa página queda elegida, sin mover el foco ni anunciar nada.
    """

    def __init__(self, libro, entradas, perezoso):
        self._libro = libro
        self._entradas = tuple(entradas)
        self._paneles = [None] * len(self._entradas)
        if not perezoso:
            for indice, (titulo, fabrica) in enumerate(self._entradas):
                self._paneles[indice] = fabrica(libro)
                libro.AddPage(self._paneles[indice], titulo)
            return
        for titulo, _fabrica in self._entradas:
            vacio = wx.Panel(libro)
            vacio.SetSizer(wx.BoxSizer(wx.VERTICAL))
            libro.AddPage(vacio, titulo)
        libro.Bind(wx.EVT_LISTBOOK_PAGE_CHANGED, self._al_cambiar)
        self.construir(libro.GetSelection())

    def _al_cambiar(self, evento):
        self.construir(evento.GetSelection())
        evento.Skip()

    def construida(self, indice) -> bool:
        """Si la página de ese índice ya tiene su panel real."""
        return (0 <= indice < len(self._paneles)
                and self._paneles[indice] is not None)

    def construir(self, indice) -> None:
        """Construye la página si todavía no lo está. Repetirlo no hace nada."""
        if not (0 <= indice < len(self._entradas)) or self.construida(indice):
            return
        vacio = self._libro.GetPage(indice)
        panel = self._entradas[indice][1](vacio)
        vacio.GetSizer().Add(panel, 1, wx.EXPAND)
        vacio.Layout()
        self._libro.Layout()
        self._paneles[indice] = panel
