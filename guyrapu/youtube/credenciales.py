"""Almacén de credenciales de la YouTube Data API (gestionable desde la app).

A diferencia de config.ini, esto NO se edita a mano normalmente: la sección
de Configuración de la aplicación escribe aquí la API key, el cliente OAuth y
el token de sesión. El archivo va cifrado con DPAPI, atado a la cuenta de
Windows, y guardado junto al ejecutable.

El archivo `credenciales.json` está en .gitignore: contiene secretos del
usuario y nunca debe subirse al repositorio.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
from pathlib import Path

from guyrapu.core import archivos
from guyrapu.core import diagnostico
from guyrapu.core import dpapi
from guyrapu.core import paths

logger = diagnostico.obtener_logger(__name__)

NOMBRE_ARCHIVO = paths.NOMBRE_CREDENCIALES
_CAMPO_CIFRADO = "dpapi"

# guardar_campo es leer-modificar-escribir y lo llaman hilos de trabajo (el
# refresco del token OAuth, la GUI): sin candado, dos guardados cruzados
# pisarían el campo del otro. RLock porque guardar_campo llama a guardar.
_lock = threading.RLock()

# cargar se llama seguido (efectivas, hay_lectura, cada guardar_campo): el
# aviso de un archivo cifrado ilegible sale una sola vez por proceso. Un
# guardado bueno la limpia, para que un archivo que vuelve a quedar ilegible
# avise otra vez.
_aviso_ilegible = False

# Estructura por defecto. `token` guarda el JSON de las credenciales OAuth
# (lo serializa google-auth con Credentials.to_json()); None = sin sesión.
_DEFECTO = {
    "api_key": "",
    "oauth_client_id": "",
    "oauth_client_secret": "",
    "token": None,
    # Clave de ElevenLabs: es un secreto, va acá y nunca a config.ini.
    "elevenlabs_clave": "",
    # Tokens de Restream: son secretos, van acá y nunca a config.ini.
    "restream_token": None,
}


def ruta() -> Path:
    return paths.credenciales()


def _leer_archivo(ruta: Path) -> tuple[dict, str]:
    """Lee el archivo y devuelve el dict con su estado de lectura."""
    bruto = archivos.leer_json(ruta, None)
    if not isinstance(bruto, dict):
        return {}, "roto" if Path(ruta).exists() else "falta"
    if _CAMPO_CIFRADO not in bruto:
        return bruto, "texto"
    try:
        claro = dpapi.descifrar(base64.b64decode(bruto[_CAMPO_CIFRADO]))
        datos = json.loads(claro.decode("utf-8"))
    except Exception:
        return {}, "ilegible"
    if not isinstance(datos, dict):
        return {}, "ilegible"
    return datos, "cifrado"


def leer_archivo(ruta) -> dict:
    """Lee y descifra si hace falta. {} si falta, está roto o no se descifra."""
    try:
        return _leer_archivo(Path(ruta))[0]
    except Exception:
        return {}


def _avisar_ilegible() -> None:
    global _aviso_ilegible
    if _aviso_ilegible:
        return
    logger.warning(
        "Las credenciales guardadas no se pudieron leer en esta cuenta "
        "de Windows: se tratan como sesión cerrada.")
    _aviso_ilegible = True


def _limpiar_aviso() -> None:
    global _aviso_ilegible
    _aviso_ilegible = False


def cargar() -> dict:
    """Devuelve siempre un dict completo, aunque el archivo falte o esté roto."""
    with _lock:
        bruto, estado = _leer_archivo(ruta())
        if estado == "texto":
            guardar(bruto)
        elif estado == "ilegible":
            _avisar_ilegible()
    datos = dict(_DEFECTO)
    if isinstance(bruto, dict):
        for k in _DEFECTO:
            if k in bruto:
                datos[k] = bruto[k]
    return datos


def guardar(datos: dict) -> bool:
    """Cifra el dict completo y lo escribe. Devuelve True si se guardó."""
    limpio = {k: datos.get(k, _DEFECTO[k]) for k in _DEFECTO}
    try:
        contenido = json.dumps(limpio, ensure_ascii=False, indent=2)
        blob = dpapi.cifrar(contenido.encode("utf-8"))
        sobre = {_CAMPO_CIFRADO: base64.b64encode(blob).decode("ascii")}
    except Exception as exc:
        logger.error("No se pudo cifrar %s: %s", NOMBRE_ARCHIVO, exc)
        return False
    try:
        with _lock:
            archivos.escribir_json_atomico(ruta(), sobre)
            _limpiar_aviso()
        return True
    except Exception as exc:
        logger.error("No se pudo guardar %s: %s", NOMBRE_ARCHIVO, exc)
        return False


def guardar_campo(clave: str, valor) -> bool:
    """Actualiza una sola clave preservando el resto."""
    if clave not in _DEFECTO:
        logger.warning("credenciales: clave desconocida %r", clave)
        return False
    with _lock:
        datos = cargar()
        datos[clave] = valor
        return guardar(datos)


# Claves que aporta el cliente de Google de la app (sin token: la sesión
# es siempre de la persona, nunca compartida).
_CLAVES_APP = ("oauth_client_id", "oauth_client_secret", "api_key")


def cliente_app() -> dict:
    """Lee el cliente de Google que viaja con la app. Nunca lanza: si el
    archivo falta, está roto o no trae las claves, devuelve cadenas vacías."""
    datos = {k: "" for k in _CLAVES_APP}
    try:
        bruto = archivos.leer_json(paths.cliente_app(), None)
    except Exception:
        return datos
    if not isinstance(bruto, dict):
        return datos
    for k in _CLAVES_APP:
        valor = bruto.get(k, "")
        datos[k] = valor if isinstance(valor, str) else ""
    return datos


def efectivas(datos: dict | None = None) -> dict:
    """Mezcla las credenciales propias con las de la app, sin escribir nada.

    El ID y el secreto van juntos: solo se toman los de la app si los dos
    propios están vacíos (un ID propio con el secreto de la app no sirve).
    La API key va sola. El token no se toca nunca."""
    base = dict(datos) if datos is not None else cargar()
    for k, v in _DEFECTO.items():
        base.setdefault(k, v)
    try:
        app = cliente_app()
    except Exception:
        return base
    if not (base.get("oauth_client_id") or "").strip() \
            and not (base.get("oauth_client_secret") or "").strip():
        base["oauth_client_id"] = app["oauth_client_id"]
        base["oauth_client_secret"] = app["oauth_client_secret"]
    if not (base.get("api_key") or "").strip():
        base["api_key"] = app["api_key"]
    return base


def usa_cliente_de_la_app(datos: dict | None = None) -> bool:
    """¿Se está usando el cliente OAuth de la app (la persona no puso el suyo)?"""
    d = datos if datos is not None else cargar()
    if ((d.get("oauth_client_id") or "").strip()):
        return False
    try:
        app = cliente_app()
    except Exception:
        return False
    return bool((app.get("oauth_client_id") or "").strip())


def hay_lectura(datos: dict | None = None) -> bool:
    """¿Hay API key para leer comentarios (propia o de la app)?"""
    d = efectivas(datos)
    return bool((d.get("api_key") or "").strip())


def hay_oauth_configurado(datos: dict | None = None) -> bool:
    """¿Están puestos el client id y el secret del OAuth (propios o de la app)?"""
    d = efectivas(datos)
    return bool((d.get("oauth_client_id") or "").strip()
                and (d.get("oauth_client_secret") or "").strip())


def hay_sesion(datos: dict | None = None) -> bool:
    """¿Hay un token OAuth guardado (sesión iniciada)?"""
    d = datos if datos is not None else cargar()
    return bool(d.get("token"))


def cerrar_sesion() -> bool:
    """Borra solo el token, conservando API key y cliente OAuth."""
    return guardar_campo("token", None)
