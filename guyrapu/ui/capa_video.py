# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ejecutar en OBS lo que la cola ordena y devolverle el resultado.

El cliente de OBS, la escena y el animador se usan solo desde el hilo que
atiende cada orden. Los resultados vuelven al hilo de la interfaz con
`wx.CallAfter`, que es donde vive la cola.
"""

from __future__ import annotations

import time

import wx

from guyrapu.core import diagnostico, paths
from guyrapu.core.idioma import _
from guyrapu.interaction import ajustes_interaccion
from guyrapu.interaction.cola_pantalla import ColaPantalla, Pieza
from guyrapu.obs import animador as animador_obs
from guyrapu.obs import escena_guyrapu, estilos_aviso, medio_obs, obs_cliente
from guyrapu.obs import ordenes_animador, revision_tarjeta
from guyrapu.ui.accesibilidad import anunciar, anunciar_con_sonido


logger = diagnostico.obtener_logger(__name__)


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {}) or {}


class CapaVideo:
    """La tarjeta de Guyrapu en el vídeo, alimentada por una cola."""

    INTERVALO = 250

    def __init__(self, frame, *, cliente=None, escena=None, animador=None,
                 medio=None, reloj=time.monotonic):
        self.cola = ColaPantalla()
        self._cliente = cliente or obs_cliente.ClienteObs(
            obs_cliente.leer_ajustes())
        self._escena = escena or escena_guyrapu.EscenaGuyrapu(self._cliente)
        self._medio = medio or medio_obs.MedioObs(self._cliente)
        self._animador = animador or animador_obs.Animador()
        self._reloj = reloj
        self._preparado = False
        self._primera = True
        self._elemento = None
        self._ancho = 0
        self._alto = 0
        self._ocupado = False
        self._falla_avisada = False
        self._pausado = False
        self._silenciado = False
        self._panico = False
        self._en_cola = 0
        self._visible = None
        self._mostrando = False
        self._timer = wx.Timer(frame)
        frame.Bind(wx.EVT_TIMER, self._atender, self._timer)
        self._timer.Start(self.INTERVALO)

    def agregar(self, mensaje):
        """Suma el mensaje a la cola como una pieza del vídeo."""
        pieza = Pieza(
            tipo="mensaje",
            texto=str(mensaje.get("texto", "")),
            segundos=mensaje.get("segundos_pantalla", 10),
            datos={"estilo": mensaje.get("estilo", "clasico"),
                   "nombre": mensaje.get("nombre", "")},
        )
        return self._agregar(pieza)

    def agregar_comando(self, respuesta):
        """Suma la respuesta de un comando a la cola como pieza propia."""
        pieza = Pieza(
            tipo="comando",
            texto=respuesta.texto,
            segundos=respuesta.segundos,
            datos={"estilo": respuesta.estilo, "nombre": respuesta.nombre},
        )
        return self._agregar(pieza)

    def _agregar(self, pieza) -> bool:
        agregada = self.cola.agregar(pieza)
        if agregada:
            self._en_cola += 1
        return agregada

    def agregar_pieza(self, pieza) -> bool:
        """Suma una pieza ya armada, como la encuesta terminada."""
        return self._agregar(pieza)

    def fijar_encuesta(self, pieza):
        """Deja la encuesta fija en el vídeo."""
        self.cola.fijar_encuesta(pieza)

    def poner_al_dia_encuesta(self, pieza) -> bool:
        """Cambia el texto de la encuesta que ya se ve, sin ocultarla."""
        return self.cola.poner_al_dia_encuesta(pieza)

    def quitar_encuesta(self):
        """Saca la encuesta fija del vídeo."""
        self.cola.fijar_encuesta(None)

    def describir(self) -> str:
        """La frase de F2 sobre lo que hay en el vídeo."""
        return self.cola.describir()

    def estado(self) -> dict:
        """Pausa, silencio y pánico vigentes, para las casillas del menú."""
        return {"pausado": self._pausado,
                "silenciado": self._silenciado,
                "panico": self._panico}

    def pausar(self):
        self.cola.pausar()
        self._pausado = True

    def reanudar(self):
        self.cola.reanudar()
        self._pausado = False

    def saltar(self) -> bool:
        """Omite lo que se ve; dice si había algo en el vídeo."""
        habia = self._visible is not None or self._mostrando
        self.cola.saltar()
        return habia

    def vaciar(self) -> bool:
        """Vacía lo pendiente; dice si había algo en la cola."""
        habia = self._en_cola > 0
        self.cola.vaciar()
        self._en_cola = 0
        return habia

    def silenciar(self, activo):
        self.cola.silenciar(activo)
        self._silenciado = bool(activo)

    def panico(self, activo):
        self.cola.panico(activo)
        self._panico = bool(activo)
        if activo:
            self._en_cola = 0

    def probar(self, texto, estilo, al_terminar):
        """Arma la tarjeta en la escena propia y devuelve la revisión.

        No la saca al aire. `al_terminar` recibe la frase y si es un error,
        en el hilo de la interfaz.
        """
        if self._ocupado:
            wx.CallAfter(al_terminar, _("La cola del vídeo está ocupada. "
                                        "Prueba en unos segundos."), True)
            return
        if not self.cola.libre():
            wx.CallAfter(al_terminar, _("Hay algo en el vídeo. Prueba cuando "
                                        "termine."), True)
            return
        self._ocupado = True
        diagnostico.crear_hilo(
            self._trabajo_probar, "CapaVideoPrueba",
            args=(texto, estilo, al_terminar)).start()

    def _trabajo_probar(self, texto, estilo, al_terminar):
        try:
            frase, error = self._revisar(texto, estilo)
        except Exception as fallo:
            logger.debug("no se pudo probar la tarjeta: %s", fallo)
            frase, error = obs_cliente.mensaje_de_fallo_obs(fallo), True
        wx.CallAfter(self._termino_probar, al_terminar, frase, error)

    def _revisar(self, texto, estilo):
        if not self._cliente.conectado:
            try:
                self._cliente.conectar()
            except obs_cliente.ObsError as fallo:
                return obs_cliente.mensaje_de_fallo_obs(fallo), True
        if self._escena.en_el_programa():
            return _("La escena de Guyrapu está en la escena que sale al "
                     "aire. Quítala de esa escena en OBS y vuelve a "
                     "probar."), True
        self._asegurar()
        tarjeta = self._escena.armar(texto, estilo)
        return revision_tarjeta.revisar(
            tarjeta, self._ancho, self._alto, estilo), False

    def _termino_probar(self, al_terminar, frase, error):
        self._ocupado = False
        al_terminar(frase, error)

    def _atender(self, event):
        if self._ocupado:
            return
        ordenes = self.cola.ordenes(self._reloj())
        if not ordenes:
            return
        self._ocupado = True
        self._mostrando = ordenes[0].accion == "mostrar"
        diagnostico.crear_hilo(
            self._trabajo, "CapaVideo", args=(ordenes[0],)).start()

    def _trabajo(self, orden):
        try:
            if orden.accion == "mostrar":
                self._mostrar(orden.pieza)
            elif orden.accion == "actualizar":
                self._actualizar(orden.pieza)
            else:
                self._ocultar(orden.pieza)
        except Exception as error:
            logger.debug("no se pudo %s en el vídeo: %s",
                         orden.accion, error)
            self._preparado = False
            self._primera = True
            if orden.accion == "ocultar":
                try:
                    self._ocultar(orden.pieza)
                except Exception as segundo:
                    logger.debug("no se pudo quitar la escena: %s", segundo)
            wx.CallAfter(self._fallo, orden.pieza)
        else:
            if orden.accion == "mostrar":
                wx.CallAfter(self._mostrada, orden)
            elif orden.accion == "actualizar":
                wx.CallAfter(self._actualizada, orden.pieza)
            else:
                wx.CallAfter(self._oculta, orden.pieza)

    def _mostrar(self, pieza):
        usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        estilo = estilos_aviso.buscar_para(
            pieza.datos.get("estilo", ""), pieza.tipo, usuario, por_tipo)
        self._asegurar()
        medio = pieza.datos.get("medio")
        if medio:
            volumen = ajustes_interaccion.cargar_volumen(paths.interaccion())
            ganancia = ajustes_interaccion.ganancia_total(
                medio.get("ganancia_db"), volumen)
            self._medio.armar(medio["ruta"], medio["tipo"], ganancia)
        if medio and not (pieza.texto or "").strip():
            self._escena.mostrar_sin_tarjeta()
            return
        if not self._animar(ordenes_animador.ocultar_antes(
                self._elemento, self._ancho)):
            raise RuntimeError("OBS no ocultó la tarjeta antes de mostrarla")
        self._escena.mostrar(pieza.texto, estilo)
        if not self._animar(ordenes_animador.entrada(
                self._elemento, estilo, self._ancho, self._alto)):
            raise RuntimeError("OBS no terminó la entrada de la tarjeta")

    def _actualizar(self, pieza):
        usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        estilo = estilos_aviso.buscar_para(
            pieza.datos.get("estilo", ""), pieza.tipo, usuario, por_tipo)
        self._asegurar()
        self._escena.mostrar(pieza.texto, estilo)

    def _ocultar(self, pieza):
        if not self._preparado:
            self._cliente.conectar()
            self._escena.ocultar()
            self._soltar(pieza)
            return
        usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        estilo = estilos_aviso.buscar_para(
            pieza.datos.get("estilo", ""), pieza.tipo, usuario, por_tipo)
        if not self._animar(ordenes_animador.salida(
                self._elemento, estilo, self._ancho, self._alto)):
            raise RuntimeError("OBS no terminó la salida de la tarjeta")
        self._escena.ocultar()
        self._soltar(pieza)

    def _soltar(self, pieza):
        if pieza.datos.get("medio"):
            self._medio.soltar()

    def _asegurar(self):
        if self._preparado:
            return
        self._cliente.conectar()
        self._escena.preparar()
        identificador = _datos(self._cliente.pedir(
            "GetSceneItemId", {
                "sceneName": escena_guyrapu.ESCENA,
                "sourceName": escena_guyrapu.TARJETA}))
        lienzo = _datos(self._cliente.pedir("GetVideoSettings"))
        self._elemento = identificador.get("sceneItemId")
        self._ancho = int(lienzo.get("baseWidth") or 0)
        self._alto = int(lienzo.get("baseHeight") or 0)
        self._preparado = True

    def _animar(self, orden) -> bool:
        cuadros = orden.get("cuadros") or ()
        duracion = float(cuadros[-1][0]) / 1000.0 if cuadros else 0.0
        tope = duracion + 3.0 + (10.0 if self._primera else 0.0)
        self._primera = False
        return self._animador.animar(orden, tope)

    def _mostrada(self, orden):
        pieza = orden.pieza
        self.cola.mostrada(pieza, self._reloj())
        self._visible = pieza
        self._mostrando = False
        if self._en_cola > 0:
            self._en_cola -= 1
        self._ocupado = False
        self._falla_avisada = False
        # La respuesta de un comando, la tarjeta de un disparador y la de una
        # meta no se anuncian: el chat ya se lee como hoy. La encuesta ya se
        # anunció al abrirse y al cerrarse.
        if pieza.tipo in ("comando", "encuesta", "disparador", "meta"):
            return
        nombre = str(pieza.datos.get("nombre") or pieza.texto)
        # Traductores: aviso al confirmarse una tarjeta en el vídeo. {nombre} es el nombre del mensaje automático.
        frase = _("En el vídeo: {nombre}.").format(nombre=nombre)
        if orden.con_sonido:
            anunciar_con_sonido(frase, "aviso")
        else:
            anunciar(frase)

    def _actualizada(self, pieza):
        self.cola.actualizada(pieza, self._reloj())
        self._ocupado = False
        self._falla_avisada = False

    def _oculta(self, pieza):
        self.cola.oculta(pieza, self._reloj())
        self._visible = None
        self._ocupado = False

    def _fallo(self, pieza):
        self.cola.fallo(pieza, self._reloj())
        self._mostrando = False
        self._ocupado = False
        if self._falla_avisada:
            return
        self._falla_avisada = True
        # Traductores: aviso cuando una tarjeta no se pudo mostrar y se reintenta.
        anunciar_con_sonido(
            _("No se pudo mostrar en el vídeo. Se vuelve a intentar en unos "
              "segundos."), "espera")
