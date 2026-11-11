# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se dicen los espectadores del estado de sesión (lógica pura, sin wx).

Una sola razón para cambiar: cómo se nombran los espectadores de cada
plataforma y cómo se escriben sus números. `estado_sesion` lo usa para el
componente de espectadores de F2.
"""

from __future__ import annotations

from guyrapu.core.idioma import ngettext


def _fmt_num(n) -> str:
    """Miles con punto al estilo español: 30044 → «30.044»."""
    try:    return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError): return str(n)


def _espectadores_tiktok(cuenta: int, n: str, total: str, largo: bool) -> str:
    if largo:
        # Traductores: parte del estado F2 (espectadores TikTok). {n} son los de ahora y {total} el total.
        return ngettext("Espectador: {n} ahora, {total} en total",
                        "Espectadores: {n} ahora, {total} en total", cuenta).format(n=n, total=total)
    # Traductores: parte del estado F2 (espectadores TikTok). {n} son los de ahora y {total} el total.
    return ngettext("{n} espectador ahora, {total} en total",
                    "{n} espectadores ahora, {total} en total", cuenta).format(n=n, total=total)


def _espectadores_resto(cuenta: int, n: str, en_directo: bool, largo: bool) -> str:
    if en_directo and largo:
        # Traductores: parte del estado F2 (espectadores). {n} es el nº actual.
        return ngettext("Espectador: {n}", "Espectadores: {n}", cuenta).format(n=n)
    if en_directo:
        # Traductores: parte del estado F2 (espectadores). {n} es el nº actual.
        return ngettext("{n} espectador", "{n} espectadores", cuenta).format(n=n)
    if largo:
        # Traductores: parte del estado F2 (vistas). {n} es el nº total.
        return ngettext("Vista: {n}", "Vistas: {n}", cuenta).format(n=n)
    # Traductores: parte del estado F2 (vistas). {n} es el nº total.
    return ngettext("{n} vista", "{n} vistas", cuenta).format(n=n)


def _espectadores_youtube(s, largo: bool) -> str:
    n = _fmt_num(s.espectadores)
    cuenta = s.espectadores if isinstance(s.espectadores, int) else 2
    if largo:
        # Traductores: parte del estado F2 (espectadores en YouTube). {n} es el nº actual.
        return ngettext("Espectador en YouTube: {n}",
                        "Espectadores en YouTube: {n}", cuenta).format(n=n)
    # Traductores: parte del estado F2 (espectadores en YouTube). {n} es el nº actual.
    return ngettext("En YouTube, {n} espectador",
                    "En YouTube, {n} espectadores", cuenta).format(n=n)


def _espectadores_adicional(n_actual, total, largo: bool) -> str:
    n = _fmt_num(n_actual)
    cuenta = n_actual if isinstance(n_actual, int) else 2
    if total is not None:
        total_txt = _fmt_num(total)
        if largo:
            # Traductores: parte del estado F2 (espectadores del chat adicional). {n} son los de ahora y {total} el total.
            return ngettext("Espectador en TikTok: {n} ahora, {total} en total",
                            "Espectadores en TikTok: {n} ahora, {total} en total",
                            cuenta).format(n=n, total=total_txt)
        # Traductores: parte del estado F2 (espectadores del chat adicional). {n} son los de ahora y {total} el total.
        return ngettext("en TikTok, {n} espectador ahora, {total} en total",
                        "en TikTok, {n} espectadores ahora, {total} en total",
                        cuenta).format(n=n, total=total_txt)
    if largo:
        # Traductores: parte del estado F2 (espectadores del chat adicional). {n} es el nº actual.
        return ngettext("Espectador en TikTok: {n}",
                        "Espectadores en TikTok: {n}", cuenta).format(n=n)
    # Traductores: parte del estado F2 (espectadores del chat adicional). {n} es el nº actual.
    return ngettext("en TikTok, {n} espectador",
                    "en TikTok, {n} espectadores", cuenta).format(n=n)


def _render_espectadores(s, largo: bool) -> str:
    if s.espectadores_adicional is not None:
        partes = []
        if s.espectadores is not None:
            partes.append(_espectadores_youtube(s, largo))
        adicional = _espectadores_adicional(
            s.espectadores_adicional, s.espectadores_adicional_total, largo)
        if s.espectadores is None:
            adicional = adicional[0].upper() + adicional[1:]
        partes.append(adicional)
        return "\n".join(partes) if largo else "; ".join(partes)
    if s.espectadores is None:
        return ""
    n = _fmt_num(s.espectadores)
    # En un directo es el nº de espectadores AHORA; en un vídeo, las vistas
    # totales (números distintos, no confundir).
    cuenta = s.espectadores if isinstance(s.espectadores, int) else 2
    if s.tipo == "live_tiktok" and s.espectadores_total is not None:
        return _espectadores_tiktok(cuenta, n, _fmt_num(s.espectadores_total), largo)
    en_directo = s.tipo in ("live_youtube", "live_tiktok")
    return _espectadores_resto(cuenta, n, en_directo, largo)
