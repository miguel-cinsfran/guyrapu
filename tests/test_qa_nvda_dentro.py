# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las piezas que corren dentro de NVDA, con NVDA de mentira.

Se cargan los módulos de `qa/nvda/dentro/` por ruta y con módulos falsos en
`sys.modules`: el entorno de pruebas no tiene la API de NVDA y estas piezas
solo se pueden importar dentro de NVDA. Lo que se prueba es la lógica pura:
el formato de los eventos, la clave de las órdenes, el retrato del foco y
las notificaciones del sintetizador.
"""

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

BASE = Path(__file__).resolve().parent.parent / "qa" / "nvda" / "dentro"


class AccionFalsa:

    def __init__(self):
        self.manejadores = []

    def register(self, manejador):
        self.manejadores.append(manejador)

    def unregister(self, manejador):
        self.manejadores.remove(manejador)

    def notify(self, **datos):
        for manejador in list(self.manejadores):
            manejador(**datos)


class DecisorFalso(AccionFalsa):

    def decide(self, **datos):
        for manejador in list(self.manejadores):
            if not manejador(**datos):
                return False
        return True


class GlobalPluginFalso:

    def __init__(self):
        self.terminado = False

    def terminate(self):
        self.terminado = True


class SynthDriverFalso:

    def __init__(self):
        pass


class IndexCommandFalso:

    def __init__(self, indice):
        self.index = indice


class GestorFalso:

    def __init__(self):
        self.gestos = []

    def emulateGesture(self, gesto):
        self.gestos.append(gesto)


class RelojFalso:

    def __init__(self, ahora=0.0):
        self.ahora = ahora
        self._programados = []

    def monotonic(self):
        return self.ahora

    def sleep(self, segundos):
        self.ahora += segundos
        self._disparar()

    def programar(self, cuando, funcion):
        self._programados.append((cuando, funcion))

    def _disparar(self):
        pendientes = sorted(self._programados, key=lambda par: par[0])
        self._programados = []
        for cuando, funcion in pendientes:
            if cuando <= self.ahora:
                funcion()
            else:
                self._programados.append((cuando, funcion))


def _modulos_falsos(carpeta, gestor):
    speech = types.ModuleType("speech")
    extensions = types.ModuleType("speech.extensions")
    extensions.pre_speech = AccionFalsa()
    extensions.speechCanceled = AccionFalsa()
    commands = types.ModuleType("speech.commands")
    commands.IndexCommand = IndexCommandFalso
    speech.extensions = extensions
    speech.commands = commands
    control = types.ModuleType("controlTypes")
    control.OutputReason = types.SimpleNamespace(FOCUS="foco")
    control.processAndLabelStates = lambda *a, **k: ["marcada"]
    config = types.ModuleType("config")
    config.WritePaths = types.SimpleNamespace(configDir=str(carpeta))
    api = types.ModuleType("api")
    api.getFocusObject = lambda: None
    api.getForegroundObject = lambda: None
    global_plugins = types.ModuleType("globalPluginHandler")
    global_plugins.GlobalPlugin = GlobalPluginFalso
    input_core = types.ModuleType("inputCore")
    input_core.manager = gestor
    teclado = types.ModuleType("keyboardHandler")
    teclado.KeyboardInputGesture = types.SimpleNamespace(
        fromName=lambda nombre: ("gesto", nombre))
    nvwave = types.ModuleType("nvwave")
    nvwave.decide_playWaveFile = DecisorFalso()
    queue = types.ModuleType("queueHandler")
    queue.eventQueue = object()
    queue.queueFunction = lambda cola, funcion, *a: funcion(*a)
    tones = types.ModuleType("tones")
    tones.decide_beep = DecisorFalso()
    version = types.ModuleType("versionInfo")
    version.version = "2026.3.1"
    watchdog = types.ModuleType("watchdog")
    watchdog.isCoreAsleep = lambda: True
    synth = types.ModuleType("synthDriverHandler")
    synth.SynthDriver = SynthDriverFalso
    synth.synthIndexReached = AccionFalsa()
    synth.synthDoneSpeaking = AccionFalsa()
    return {
        "speech": speech,
        "speech.extensions": extensions,
        "speech.commands": commands,
        "controlTypes": control,
        "config": config,
        "api": api,
        "globalPluginHandler": global_plugins,
        "inputCore": input_core,
        "keyboardHandler": teclado,
        "nvwave": nvwave,
        "queueHandler": queue,
        "tones": tones,
        "versionInfo": version,
        "watchdog": watchdog,
        "synthDriverHandler": synth,
    }


def _cargar(ruta, nombre):
    especificacion = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


class TestComplemento(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.gestor = GestorFalso()
        falsos = _modulos_falsos(self.carpeta.name, self.gestor)
        ruta = BASE / "globalPlugins" / "carril_guyrapu.py"
        with mock.patch.dict(sys.modules, falsos):
            self.modulo = _cargar(ruta, "carril_guyrapu_prueba")
        self.plugin = self.modulo.GlobalPlugin()

    def tearDown(self):
        self.plugin.terminate()
        self.carpeta.cleanup()

    def test_una_orden_sin_clave_se_ignora(self):
        self.assertTrue(self.modulo.clave_valida(
            {"clave": "abc", "orden": "marca"}, "abc"))
        self.assertFalse(self.modulo.clave_valida(
            {"clave": "otra", "orden": "marca"}, "abc"))
        self.assertFalse(self.modulo.clave_valida(None, "abc"))

    def test_la_orden_sin_clave_queda_anotada(self):
        self.plugin._rechazo()
        evento = self.plugin._eventos.desde(0)[-1]
        self.assertEqual(evento["tipo"], "orden")
        self.assertFalse(evento["aceptada"])

    def test_guarda_cada_frase_unida(self):
        self.plugin._al_hablar(speechSequence=["Hola", "mundo"])
        evento = self.plugin._eventos.desde(0)[-1]
        self.assertEqual(evento["tipo"], "habla")
        self.assertEqual(evento["texto"], "Hola mundo")

    def test_guarda_las_partes_del_habla_sin_quitar_el_texto(self):
        self.plugin._al_hablar(
            speechSequence=["Hola", IndexCommandFalso(1), "mundo"])
        evento = self.plugin._eventos.desde(0)[-1]
        self.assertEqual(evento["texto"], "Hola mundo")
        self.assertEqual(evento["partes"], ["Hola", "mundo"])

    def test_guarda_los_pitidos_y_los_deja_sonar(self):
        self.assertTrue(self.plugin._al_pitar(hz=440, length=10))
        evento = self.plugin._eventos.desde(0)[-1]
        self.assertEqual(evento["tipo"], "pitido")
        self.assertEqual(evento["hz"], 440)

    def test_guarda_el_foco_y_sigue_la_cadena(self):
        llamadas = []
        objeto = types.SimpleNamespace(
            name="Aceptar", role=types.SimpleNamespace(
                displayString="botón"), states=set(), value="",
            description="confirma", keyboardShortcut="alt+a")
        self.plugin.event_gainFocus(objeto, lambda: llamadas.append(True))
        self.assertEqual(llamadas, [True])
        evento = self.plugin._eventos.desde(0)[-1]
        self.assertEqual(evento["tipo"], "foco")
        self.assertEqual(evento["nombre"], "Aceptar")
        self.assertEqual(evento["rol_texto"], "botón")

    def test_el_foco_guarda_rol_nombre_hwnd_y_pid(self):
        objeto = types.SimpleNamespace(
            name="Aceptar", role=types.SimpleNamespace(
                name="PANE", displayString="panel"), states=set(), value="",
            description="", keyboardShortcut="", windowHandle=42,
            processID=7)
        self.plugin.event_gainFocus(objeto, lambda: None)
        evento = self.plugin._eventos.desde(0)[-1]
        self.assertEqual(evento["rol_nombre"], "PANE")
        self.assertEqual(evento["hwnd"], 42)
        self.assertEqual(evento["pid"], 7)

    def test_la_respuesta_de_foco_trae_el_primer_plano(self):
        enfocado = types.SimpleNamespace(
            name="Aceptar", role=types.SimpleNamespace(
                name="PUSH_BUTTON", displayString="botón"), states=set(),
            value="", description="", keyboardShortcut="", windowHandle=42,
            processID=7)
        primer_plano = types.SimpleNamespace(name="Ventana del carril",
                                             processID=7)
        with (
            mock.patch.object(self.modulo.api, "getFocusObject",
                              return_value=enfocado),
            mock.patch.object(self.modulo.api, "getForegroundObject",
                              return_value=primer_plano),
        ):
            respuesta = self.plugin._atender({"orden": "foco"})
        self.assertEqual(respuesta["foco"]["nombre"], "Aceptar")
        self.assertEqual(respuesta["primer_plano"],
                         {"pid": 7, "nombre": "Ventana del carril"})

    def test_version_responde_sin_tocar_la_interfaz(self):
        self.assertEqual(self.plugin._atender({"orden": "version"}),
                         {"ok": True, "version": "2026.3.1"})

    def test_la_tecla_dice_la_hora_en_que_se_mando(self):
        respuesta = self.plugin._atender(
            {"orden": "tecla", "gesto": "tab", "silencio_ms": 0,
             "tope_ms": 100})
        self.assertTrue(respuesta["ok"])
        self.assertIsInstance(respuesta["hora"], float)

    def test_cada_evento_va_al_jsonl_con_indice_hora_y_tipo(self):
        self.plugin._al_hablar(speechSequence=["uno"])
        self.plugin._al_hablar(speechSequence=["dos"])
        ruta = Path(self.carpeta.name) / "eventos.jsonl"
        lineas = ruta.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lineas), 2)
        primero, segundo = (json.loads(linea) for linea in lineas)
        self.assertEqual(primero["indice"], 0)
        self.assertEqual(segundo["indice"], 1)
        self.assertIsInstance(primero["hora"], float)
        self.assertEqual(primero["tipo"], "habla")
        self.assertIn("speechCanceled", primero)

    def test_desde_devuelve_lo_posterior_a_una_marca(self):
        self.plugin._al_hablar(speechSequence=["uno"])
        marca = self.plugin._eventos.marca()
        self.plugin._al_hablar(speechSequence=["dos"])
        posteriores = self.plugin._eventos.desde(marca)
        self.assertEqual([e["texto"] for e in posteriores], ["dos"])

    def _usar_reloj(self, ahora, ultima_habla):
        reloj = RelojFalso(ahora)
        self.plugin._eventos._reloj = reloj.monotonic
        self.plugin._eventos._inicio = 0.0
        self.plugin._eventos._ultima_habla = ultima_habla
        return reloj

    def test_la_espera_no_vuelve_antes_de_la_frase_de_la_tecla(self):
        reloj = self._usar_reloj(0.468, 0.0)
        oido = []

        def al_mandar():
            oido.append(True)
            self.plugin._al_hablar(speechSequence=["Aceptar, botón"])

        reloj.programar(0.499, al_mandar)
        with mock.patch.object(self.modulo, "time", reloj):
            respuesta = self.plugin._atender(
                {"orden": "tecla", "gesto": "tab", "tope_ms": 5000})
        self.assertTrue(respuesta["ok"])
        self.assertFalse(respuesta["agotado"])
        self.assertEqual(oido, [True])
        self.assertGreaterEqual(reloj.ahora, 0.898)

    def test_sin_habla_despues_de_la_tecla_espera_1500_ms(self):
        reloj = self._usar_reloj(0.1, 0.0)
        with mock.patch.object(self.modulo, "time", reloj):
            respuesta = self.plugin._atender(
                {"orden": "tecla", "gesto": "tab", "tope_ms": 5000})
        self.assertTrue(respuesta["ok"])
        self.assertFalse(respuesta["agotado"])
        self.assertGreaterEqual(reloj.ahora, 1.599)
        self.assertLessEqual(reloj.ahora, 1.7)

    def _esperar(self, frase, indice, plazo_s, reloj=None):
        pedido = {"orden": "esperar_frase", "frase": frase,
                  "indice": indice, "plazo_s": plazo_s}
        if reloj is None:
            return self.plugin._atender(pedido)
        with mock.patch.object(self.modulo, "time", reloj):
            return self.plugin._atender(pedido)

    def test_esperar_frase_oye_la_frase_y_devuelve_los_eventos(self):
        self.plugin._al_hablar(speechSequence=["otra cosa"])
        marca = self.plugin._eventos.marca()
        self.plugin._al_hablar(speechSequence=["El historial está vacío."])
        respuesta = self._esperar("historial ESTÁ vacío", marca, 0.5)
        self.assertTrue(respuesta["oida"])
        self.assertEqual([e["texto"] for e in respuesta["eventos"]],
                         ["El historial está vacío."])

    def test_esperar_frase_no_oida_al_vencer_el_plazo(self):
        reloj = self._usar_reloj(0.0, 0.0)
        respuesta = self._esperar("el historial está vacío", 0, 0.4, reloj)
        self.assertFalse(respuesta["oida"])

    def test_esperar_frase_no_cuenta_lo_dicho_antes_de_la_marca(self):
        self.plugin._al_hablar(speechSequence=["El historial está vacío."])
        marca = self.plugin._eventos.marca()
        self.plugin._al_hablar(speechSequence=["otra cosa"])
        reloj = self._usar_reloj(0.0, 0.0)
        respuesta = self._esperar("el historial está vacío", marca, 0.4,
                                  reloj)
        self.assertFalse(respuesta["oida"])


class TestEspia(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        falsos = _modulos_falsos(self.carpeta.name, GestorFalso())
        ruta = BASE / "synthDrivers" / "espia_guyrapu.py"
        with mock.patch.dict(sys.modules, falsos):
            self.modulo = _cargar(ruta, "espia_guyrapu_prueba")

    def tearDown(self):
        self.carpeta.cleanup()

    def test_notifica_cada_indice_y_el_fin(self):
        secuencia = ["hola", IndexCommandFalso(1), "mundo",
                     IndexCommandFalso(2)]
        indices = []
        fines = []
        cortado = self.modulo.notificar_secuencia(
            secuencia, lambda: False, indices.append, lambda: fines.append(1))
        self.assertFalse(cortado)
        self.assertEqual(indices, [1, 2])
        self.assertEqual(len(fines), 1)

    def test_cancelado_no_notifica_ni_indices_ni_fin(self):
        secuencia = [IndexCommandFalso(1)]
        avisos = []
        cortado = self.modulo.notificar_secuencia(
            secuencia, lambda: True, avisos.append, lambda: avisos.append(1))
        self.assertTrue(cortado)
        self.assertEqual(avisos, [])

    def test_declara_las_dos_notificaciones_y_no_suena(self):
        self.assertTrue(self.modulo.SynthDriver.check())
        declaradas = self.modulo.SynthDriver.supportedNotifications
        self.assertEqual(len(declaradas), 2)


class TestEventosSueltos(unittest.TestCase):

    def setUp(self):
        falsos = _modulos_falsos(tempfile.gettempdir(), GestorFalso())
        with mock.patch.dict(sys.modules, falsos):
            self.modulo = _cargar(
                BASE / "globalPlugins" / "carril_guyrapu.py",
                "carril_eventos_prueba")

    def test_el_formato_del_evento_lleva_indice_hora_tipo_y_cancelacion(self):
        lector = self.modulo.LectorEventos()
        primero = lector.agregar("pitido", hz=440)
        lector.marcar_cancelado()
        segundo = lector.agregar("cancelado")
        self.assertEqual(primero["indice"], 0)
        self.assertEqual(segundo["indice"], 1)
        self.assertEqual(primero["tipo"], "pitido")
        self.assertFalse(primero["speechCanceled"])
        self.assertTrue(segundo["speechCanceled"])
        self.assertIsInstance(segundo["hora"], float)

    def test_ultima_habla_avanza_con_cada_frase(self):
        tiempos = iter([0.0, 1.0, 1.0, 1.0, 2.0])
        lector = self.modulo.LectorEventos(reloj=lambda: next(tiempos))
        antes = lector.ultima_habla()
        lector.agregar("habla", texto="hola")
        self.assertGreater(lector.ultima_habla(), antes)
