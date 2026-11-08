# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La página con movimiento que se graba durante la prueba del equipo.

Su única razón para cambiar es qué imagen se usa para medir. Una cuadrícula
de mosaicos que se desplaza, 1500 círculos y textos que se mueven cubren
todo el lienzo y exigen al codificador sin el costo de un ruido aleatorio
por píxel, que haría bajar de más al equipo y falsearía la medición.
"""

from __future__ import annotations

import base64

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Prueba del equipo</title>
<style>
html, body { margin: 0; overflow: hidden; background: #000; }
canvas { display: block; }
</style>
</head>
<body>
<canvas id="lienzo"></canvas>
<script>
var lienzo = document.getElementById("lienzo");
var ctx = lienzo.getContext("2d");

function ajustar() {
    lienzo.width = window.innerWidth;
    lienzo.height = window.innerHeight;
}
ajustar();
window.addEventListener("resize", ajustar);

var CIRCULOS = 1500;
var particulas = [];
for (var i = 0; i < CIRCULOS; i += 1) {
    particulas.push({
        x: Math.random(),
        y: Math.random(),
        vx: (Math.random() - 0.5) * 0.004,
        vy: (Math.random() - 0.5) * 0.004,
        radio: 2 + Math.random() * 10,
        tono: Math.random() * 360
    });
}

var cuadro = 0;
function dibujar() {
    cuadro += 1;
    var ancho = lienzo.width;
    var alto = lienzo.height;
    var lado = 40;
    var desplazamiento = (cuadro * 3) % lado;

    for (var gy = -lado; gy < alto; gy += lado) {
        for (var gx = -lado; gx < ancho; gx += lado) {
            ctx.fillStyle = "hsl(" + ((gx + gy + cuadro * 2) % 360) +
                ",60%," + (30 + ((gx * 7 + gy * 3) % 25)) + "%)";
            ctx.fillRect(gx + desplazamiento, gy + desplazamiento,
                         lado - 2, lado - 2);
        }
    }

    for (var j = 0; j < particulas.length; j += 1) {
        var p = particulas[j];
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > 1) { p.vx = -p.vx; }
        if (p.y < 0 || p.y > 1) { p.vy = -p.vy; }
        ctx.fillStyle = "hsl(" + ((p.tono + cuadro) % 360) + ",90%,60%)";
        ctx.beginPath();
        ctx.arc(p.x * ancho, p.y * alto, p.radio, 0, 6.283);
        ctx.fill();
    }

    ctx.fillStyle = "#fff";
    ctx.font = "28px sans-serif";
    for (var k = 0; k < 12; k += 1) {
        ctx.fillText("Guyrapu " + (cuadro + k * 37),
                     (cuadro * 5 + k * 160) % ancho, 60 + k * 80);
    }
    window.requestAnimationFrame(dibujar);
}
window.requestAnimationFrame(dibujar);
</script>
</body>
</html>
"""


def url() -> str:
    """La página como URL de datos, sin escribir ningún archivo."""
    codificado = base64.b64encode(HTML.encode("utf-8")).decode("ascii")
    return "data:text/html;base64," + codificado
