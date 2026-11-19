# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Libera las ventanas de primer nivel creadas en las pruebas.

En wx, el Destroy() de una ventana de primer nivel queda pendiente
hasta que corre el bucle de eventos, que en las pruebas no corre y los
objetos USER se acumulan hasta el tope de Windows. Por eso destruir
llama a wx.SafeYield() después del Destroy(), para que wx la libere en
el momento.
"""


_APP = None


def app_de_prueba():
    """Devuelve una sola wx.App sostenida hasta el final del proceso.

    unittest suelta cada prueba al terminarla y el App moría con ella.
    """
    global _APP
    import wx
    if _APP is None:
        _APP = wx.App.Get() or wx.App(False)
    return _APP


def armar_preferencias(config, *titulos):
    """Abre Preferencias en modo perezoso y arma solo las páginas pedidas.

    Los títulos son los visibles en la lista de categorías. Quien llama pone
    sus propios `mock.patch` alrededor y destruye el cuadro al terminar.
    """
    from guyrapu.ui import gui_preferencias
    app_de_prueba()
    dialogo = gui_preferencias.PreferenciasDialog(
        None, config, perezosa=True)
    try:
        for titulo in titulos:
            dialogo._libro_perezoso.construir(_indice(dialogo, titulo))
    except ValueError:
        destruir(dialogo)
        raise
    return dialogo


def _indice(dialogo, titulo):
    for i in range(dialogo.nb.GetPageCount()):
        if dialogo.nb.GetPageText(i) in (titulo, f"[¡{titulo}!]"):
            return i
    raise ValueError(f"No está la categoría {titulo}")


def pagina_por_titulo(dialogo, titulo):
    """Devuelve el panel real de una categoría, no el panel vacío del libro."""
    return dialogo._libro_perezoso._paneles[_indice(dialogo, titulo)]


def destruir(ventana) -> None:
    """Libera la ventana con Destroy y SafeYield; nunca lanza."""
    try:
        import wx
        if not ventana:
            return
        if isinstance(ventana, wx.App):
            ventana.Destroy()
            return
        for nombre in ("_timer", "_diagnostico_timer"):
            temporizador = getattr(ventana, nombre, None)
            if temporizador is not None:
                try:
                    temporizador.Stop()
                except Exception:
                    pass
        if hasattr(ventana, "_alive"):
            ventana._alive = False
        ventana.Destroy()
        wx.SafeYield()
    except Exception:
        pass
