# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué respondió a un envío de prueba y cómo se cuenta.

Puro y sin wx. Única razón para cambiar: cómo se cuenta lo que respondió
a un registro del ensayo, en el orden en que la interfaz presenta cada parte.
"""

from __future__ import annotations

from guyrapu.core.idioma import N_, _

# Traductores: partes del resultado de un mensaje de prueba, en este orden.
COMANDO = N_("Respondió el comando {nombre}.")
ALERTA = N_("Respondió la alerta {nombre}.")
VOTO = N_("Voto contado en la encuesta {nombre}.")
PREGUNTA = N_("Pregunta agregada a la página Preguntas.")
META = N_("La meta {nombre} avanzó a {actual} de {objetivo}.")

# Traductores: resultado cuando nada respondió. {motivo} ya trae su punto.
NADA = N_("Nada respondió: {motivo}")
FILA = N_("{hora} {enviado}: {resultado}")

# Traductores: motivos de un mensaje que no respondió ninguna parte.
MOTIVO_MENSAJE = N_("ningún comando ni alerta usa ese mensaje.")
MOTIVO_EVENTO = N_("ninguna alerta usa ese evento.")
MOTIVO_ESPERA_COMANDO = N_(
    "el comando {nombre} está en espera, faltan {segundos} segundos.")
MOTIVO_PERMISO = N_("el comando {nombre} es solo para {permiso}.")
MOTIVO_PAUSA_COMANDO = N_("el comando {nombre} está en pausa.")
MOTIVO_PAUSA_GENERAL = N_("los comandos están en pausa.")
MOTIVO_ESPERA_ALERTA = N_(
    "la alerta {nombre} está en espera, faltan {segundos} segundos.")


def fila(hora, enviado, resultado):
    """La línea que se agrega a la lista de resultados."""
    return _(FILA).format(hora=hora, enviado=enviado, resultado=resultado)


def _numero(valor):
    numero = float(valor)
    return str(int(numero)) if numero.is_integer() else f"{numero:g}"


class InformeEnsayo:
    """Lo que anotaron las partes de un envío, listo para contarse."""

    def __init__(self):
        self._comandos = []
        self._alertas = []
        self._votos = []
        self._preguntas = 0
        self._metas = []
        self._motivos = []

    def comando(self, nombre):
        self._comandos.append(nombre)

    def alerta(self, nombre):
        self._alertas.append(nombre)

    def voto(self, nombre):
        self._votos.append(nombre)

    def pregunta(self):
        self._preguntas += 1

    def meta(self, nombre, actual, objetivo):
        self._metas.append((nombre, _numero(actual), objetivo))

    def motivo(self, texto):
        self._motivos.append(texto)

    @property
    def respondio(self):
        """Si alguna parte anotó una respuesta."""
        return bool(self._comandos or self._alertas or self._votos
                    or self._preguntas or self._metas)

    def _partes(self):
        partes = [_(COMANDO).format(nombre=nombre) for nombre in self._comandos]
        partes += [_(ALERTA).format(nombre=nombre) for nombre in self._alertas]
        partes += [_(VOTO).format(nombre=nombre) for nombre in self._votos]
        partes += [_(PREGUNTA)] * self._preguntas
        partes += [_(META).format(nombre=nombre, actual=actual,
                                 objetivo=objetivo)
                   for nombre, actual, objetivo in self._metas]
        return partes

    def texto(self, motivo_general=""):
        """La frase que se anuncia y se escribe en Resultados."""
        if self.respondio:
            return " ".join(self._partes())
        motivo = next((texto for texto in self._motivos if texto),
                      motivo_general)
        return _(NADA).format(motivo=motivo)
