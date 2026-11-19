# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los pasos de interacción del directo real.

Prepara y restaura las cuatro colecciones de datos de la app y comprueba al
aire el comando, el disparador, la encuesta, las preguntas y la meta. Todo lo
que toca la app o el escritorio recibe adaptadores: acá solo se decide qué se
envía, qué se lee y qué se anota. No importa `directo_real.py` para no armar
un import circular.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from guyrapu.interaction import (comandos_guardados, disparadores_guardados,
                                 encuestas_guardadas, metas_guardadas)

_RUTA_QA = str(Path(__file__).resolve().parent)
if _RUTA_QA not in sys.path:
    sys.path.insert(0, _RUTA_QA)
from directo_chat import mensaje_en_respuesta  # noqa: E402

DATOS = ("comandos", "disparadores", "encuestas", "metas")
MARCA = "QA_DIRECTO_INTERACCION"
RESPUESTA_PRUEBA = MARCA + " respuesta del comando"
TARJETA_RISA = MARCA + " tarjeta de la risa"
PREGUNTA_ENCUESTA = MARCA + " encuesta"
OPCION_UNO = "Una opción"
OPCION_DOS = "Otra opción"
RESULTADO_UNO = "Ganó " + OPCION_UNO + " con 1 voto"
ANUNCIO_ENCUESTA = "Encuesta abierta"
ANUNCIO_META = "Meta cumplida"
NOMBRE_META = MARCA + " meta de superchats"
TEXTO_PREGUNTA = MARCA + " pregunta del público"
TEXTO_SUPERCHAT = MARCA + " superchat"
# De qa/sonda.py, que no se importa acá porque ese módulo carga wx.
VAR_ANUNCIOS = "GUYRAPU_QA_ANUNCIOS"
VAR_ORDENES = "GUYRAPU_QA_ORDENES"
VAR_RESULTADOS = "GUYRAPU_QA_RESULTADOS"
ARCHIVOS_SONDA = ("anuncios-sonda.jsonl", "ordenes.jsonl", "resultados.jsonl")


def coinciden(texto, fragmento) -> bool:
    return bool(fragmento) and str(fragmento).lower() in str(texto or "").lower()


def esperar_texto(leer, fragmento, segundos=30) -> tuple[bool, str]:
    fin = time.time() + segundos
    while True:
        try:
            visto = str(leer() or "")
        except Exception as exc:
            visto = f"error leyendo: {exc}"
        if coinciden(visto, fragmento):
            return (True, f"«{fragmento}» encontrado")
        if time.time() >= fin:
            return (False, f"sin «{fragmento}» en {segundos} s "
                           f"(visto: {visto[-120:]})")
        time.sleep(1)


def _poner(guardados, ruta, campo, datos, convertir=None):
    actuales = [d for d in guardados.cargar(ruta)
                if MARCA not in str(d.get(campo, ""))]
    actuales.append((convertir or guardados.normalizar)(datos))
    guardados.guardar(ruta, actuales)


class Datos:
    """Respaldo y vuelta atrás de las colecciones, archivo por archivo."""

    def __init__(self, rutas):
        self._rutas = dict(rutas)
        self._respaldos: dict[str, bytes | None] = {}

    def preparar(self) -> None:
        for clave in DATOS:
            ruta = Path(self._rutas[clave])
            self._respaldos[clave] = (ruta.read_bytes()
                                      if ruta.exists() else None)
        try:
            self._agregar()
        except Exception:
            self.restaurar()
            raise

    def _agregar(self) -> None:
        _poner(comandos_guardados, self._rutas["comandos"], "respuesta", {
            "nombre": "prueba", "respuesta": RESPUESTA_PRUEBA,
            "destino": "ambos"})
        _poner(disparadores_guardados, self._rutas["disparadores"], "nombre", {
            "nombre": "risa " + MARCA, "cuando": "comando",
            "comandos": ["!risa"], "tarjeta": TARJETA_RISA})
        _poner(encuestas_guardadas, self._rutas["encuestas"], "pregunta", {
            "pregunta": PREGUNTA_ENCUESTA,
            "opciones": [OPCION_UNO, OPCION_DOS], "destino": "chat"})
        _poner(metas_guardadas, self._rutas["metas"], "nombre", {
            "nombre": NOMBRE_META, "que_cuenta": "super_chat",
            "objetivo": 1, "activa": True, "en_video": True},
            lambda datos: metas_guardadas.desde_meta(
                metas_guardadas.a_meta(datos)))

    def restaurar(self) -> None:
        for clave in DATOS:
            ruta = Path(self._rutas[clave])
            contenido = self._respaldos.get(clave)
            if contenido is None:
                ruta.unlink(missing_ok=True)
            else:
                ruta.write_bytes(contenido)


class Pasos:
    """Comprobaciones al aire, con todo lo que lee o escribe por argumentos."""

    def __init__(self, anotar, enviar, respuesta, texto_video, leer_anuncios,
                 ruta_anuncios, abrir_encuesta, cerrar_encuesta,
                 leer_siguiente, orden, segundos=30):
        self.anotar = anotar
        self.enviar = enviar
        self.respuesta = respuesta
        self.texto_video = texto_video
        self.leer_anuncios = leer_anuncios
        self.ruta_anuncios = ruta_anuncios
        self.abrir_encuesta = abrir_encuesta
        self.cerrar_encuesta = cerrar_encuesta
        self.leer_siguiente = leer_siguiente
        self.orden = orden
        self.segundos = segundos

    def _comprobar(self, nombre, fragmento, leer) -> bool:
        bien, detalle = esperar_texto(leer, fragmento, self.segundos)
        self.anotar(nombre, bien, detalle)
        return bien

    def _anuncios(self, nombre, fragmento, marca=None) -> bool:
        if marca is None:
            marca = len(self.leer_anuncios(self.ruta_anuncios))

        def leer():
            return self.leer_anuncios(self.ruta_anuncios)[marca:]

        return self._comprobar(nombre, fragmento, leer)

    def _enviar(self, texto) -> bool:
        try:
            self.enviar(texto)
            return True
        except Exception as exc:
            self.anotar("enviar " + texto, False, str(exc))
            return False

    def _en_chat(self, fragmento):
        return lambda: (fragmento if mensaje_en_respuesta(
            self.respuesta(), fragmento) else "")

    def comando(self) -> bool:
        if not self._enviar("!prueba"):
            return False
        if not self._comprobar("comando !prueba en el chat",
                               RESPUESTA_PRUEBA, self._en_chat(RESPUESTA_PRUEBA)):
            return False
        return self._comprobar("comando !prueba en la tarjeta",
                               RESPUESTA_PRUEBA, self.texto_video)

    def disparador(self) -> bool:
        if not self._enviar("!risa"):
            return False
        return self._comprobar("disparador !risa en la tarjeta",
                               TARJETA_RISA, self.texto_video)

    def encuesta(self) -> bool:
        marca = len(self.leer_anuncios(self.ruta_anuncios))
        try:
            self.abrir_encuesta()
        except Exception as exc:
            self.anotar("encuesta abierta", False, f"no se pudo abrir: {exc}")
            return False
        if not self._anuncios("encuesta abierta", ANUNCIO_ENCUESTA, marca):
            return False
        if not self._enviar("!1"):
            return False
        ruta_chat = Path(self.ruta_anuncios).with_name("chat.txt")
        if not self._comprobar("voto !1 contado", "!1",
                               lambda: self.leer_anuncios(ruta_chat)):
            return False
        marca = len(self.leer_anuncios(self.ruta_anuncios))
        try:
            self.cerrar_encuesta()
        except Exception as exc:
            self.anotar("resultado de la encuesta", False,
                        f"no se pudo cerrar: {exc}")
            return False
        if not self._anuncios("resultado de la encuesta", RESULTADO_UNO, marca):
            return False
        return self._comprobar("resultado de la encuesta en el chat",
                               OPCION_UNO, self._en_chat(OPCION_UNO))

    def pregunta(self) -> bool:
        if not self._enviar("!pregunta " + TEXTO_PREGUNTA):
            return False
        marca = len(self.leer_anuncios(self.ruta_anuncios))
        try:
            self.leer_siguiente()
        except Exception as exc:
            self.anotar("leer siguiente pregunta", False,
                        f"no se pudo pedir: {exc}")
            return False
        return self._anuncios("leer siguiente pregunta", TEXTO_PREGUNTA, marca)

    def meta(self) -> bool:
        marca = len(self.leer_anuncios(self.ruta_anuncios))
        try:
            self.orden("agregar_mensaje_chat", "Miguel", TEXTO_SUPERCHAT,
                       "12:00", "superchat", "1", "",
                       plataforma="youtube")
        except Exception as exc:
            self.anotar("meta de superchat cumplida", False, str(exc))
            return False
        if not self._anuncios("meta de superchat cumplida", ANUNCIO_META,
                              marca):
            return False
        return self._comprobar("meta de superchat en la tarjeta",
                               NOMBRE_META, self.texto_video)

    def todos(self) -> bool:
        bienes = [paso() for paso in (self.comando, self.disparador,
                                      self.encuesta, self.pregunta, self.meta)]
        return all(bienes)


def _rotulo_limpio(texto) -> str:
    return (texto or "").replace("&", "").split("\t")[0].strip()


def _menu_item(principal, rotulo, segundos=20):
    from pywinauto import Desktop
    fin = time.time() + segundos
    while time.time() < fin:
        raices = [principal] + list(Desktop(backend="uia").windows())
        for raiz in raices:
            for control in raiz.descendants(control_type="MenuItem"):
                if rotulo.lower() in _rotulo_limpio(
                        control.window_text()).lower():
                    return control
        time.sleep(0.5)
    raise RuntimeError(f"no apareció la entrada de menú «{rotulo}»")


def _pulsar_menu(principal, rotulo) -> None:
    _menu_item(principal, "Interacción").click_input()
    _menu_item(principal, rotulo).click_input()


def _dialogo_interaccion(principal):
    for hijo in principal.descendants(control_type="Window"):
        if "Interacción" in (hijo.window_text() or ""):
            return hijo
    raise RuntimeError("no apareció la ventana «Interacción»")


def _elegir_item(raiz, nombres_lista, texto) -> None:
    lista = next((c for c in raiz.descendants()
                  if c.window_text() in nombres_lista), None)
    if lista is None:
        raise RuntimeError(f"no apareció la lista «{nombres_lista[0]}»")
    for item in lista.descendants(control_type="ListItem"):
        if texto.lower() in (item.window_text() or "").lower():
            item.select()
            return
    raise RuntimeError(f"no apareció «{texto}» en «{nombres_lista[0]}»")


def _abrir_encuesta(principal, control) -> None:
    _pulsar_menu(principal, "Abrir Interacción")
    ventana = _dialogo_interaccion(principal)
    _elegir_item(ventana, ("Páginas de interacción",), "Encuestas")
    _elegir_item(ventana, ("ListaEncuestas", "Encuestas guardadas"), MARCA)
    control(ventana, "Iniciar", "Button").invoke()
    control(ventana, "Cerrar", "Button").invoke()


class Interaccion:
    """Prepara, conduce y restaura la interacción del directo real."""

    def __init__(self, activo, tmpdir, anotar):
        self.activo = bool(activo)
        self._tmpdir = tmpdir
        self._anotar = anotar
        self._datos = None
        self._id_orden = 0

    def _ruta(self, nombre) -> str:
        return os.path.join(self._tmpdir, nombre)

    @property
    def arranque(self) -> str:
        if not self.activo:
            return "import main\nmain.main()"
        return ("import sys\n"
                "sys.path.insert(0, os.path.join(REPO, 'qa'))\n"
                "import sonda as _qa_sonda\n"
                "_qa_sonda.arrancar_aplicacion("
                "os.path.join(REPO, 'main.py'))")

    def entorno(self) -> dict:
        if not self.activo:
            return {}
        return {clave: self._ruta(nombre) for clave, nombre in zip(
            (VAR_ANUNCIOS, VAR_ORDENES, VAR_RESULTADOS), ARCHIVOS_SONDA)}

    def preparar(self) -> None:
        if not self.activo:
            return
        from guyrapu.core import paths
        self._datos = Datos({clave: str(getattr(paths, clave)()) for clave in DATOS})
        self._datos.preparar()
        try:
            for nombre in ARCHIVOS_SONDA:
                open(self._ruta(nombre), "w").close()
            self._anotar("datos de interacción preparados", True,
                         "comando, disparador, encuesta y meta de prueba agregados")
        except Exception:
            self.restaurar()
            raise

    def restaurar(self) -> None:
        if self._datos is not None:
            self._datos.restaurar()
            self._datos = None

    def respuesta(self, cliente, id_chat):
        return cliente._escritura().liveChatMessages().list(
            liveChatId=id_chat, part="snippet", maxResults=200).execute()

    def orden(self, metodo, *args, **kwargs) -> dict:
        self._id_orden += 1
        id_orden = self._id_orden
        orden = {"id": id_orden, "op": "llamar", "metodo": metodo,
                 "args": list(args), "kwargs": kwargs}
        with open(self._ruta(ARCHIVOS_SONDA[1]), "a", encoding="utf-8") as f:
            f.write(json.dumps(orden, ensure_ascii=False) + "\n")
        limite = time.time() + 30
        while time.time() < limite:
            try:
                lineas = Path(self._ruta(ARCHIVOS_SONDA[2])).read_text(
                    encoding="utf-8").splitlines()
            except OSError:
                lineas = []
            for linea in lineas:
                try:
                    resultado = json.loads(linea)
                except ValueError:
                    continue
                if resultado.get("id") != id_orden:
                    continue
                if not resultado.get("ok"):
                    raise RuntimeError(f"la sonda rechazó {metodo}: "
                                       f"{resultado.get('error')}")
                return resultado
            time.sleep(0.05)
        raise TimeoutError(f"la orden {metodo!r} no contestó en 30 s")

    def pasar(self, cliente, id_chat, gestor_obs, leer_anuncios,
              ruta_anuncios, principal, control) -> None:
        if not self.activo:
            return
        from guyrapu.obs import escena_guyrapu

        def texto_video():
            datos = gestor_obs._pedir(
                "GetInputSettings", {"inputName": escena_guyrapu.TEXTO})
            return " ".join(str(datos.get("inputSettings", {})
                                .get("text", "") or "").split())

        pasos = Pasos(
            anotar=self._anotar,
            enviar=lambda texto: cliente.enviar_mensaje_live(id_chat, texto),
            respuesta=lambda: self.respuesta(cliente, id_chat),
            texto_video=texto_video, leer_anuncios=leer_anuncios,
            ruta_anuncios=ruta_anuncios,
            abrir_encuesta=lambda: _abrir_encuesta(principal, control),
            cerrar_encuesta=lambda: _pulsar_menu(principal, "Cerrar encuesta"),
            leer_siguiente=lambda: _pulsar_menu(
                principal, "Leer siguiente pregunta"),
            orden=self.orden)
        pasos.todos()
