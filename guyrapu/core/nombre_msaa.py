"""Anotación dinámica del nombre accesible de una ventana de Windows.

COM con ctypes puro: comtypes no forma parte del paquete. Cambia solo el
nombre que MSAA informa para la ventana, sin tocar el rol ni el estado que
da el control. Cualquier fallo devuelve False, se registra en depuración y
nunca llega a quien llamó.
"""

from __future__ import annotations

import ctypes
import uuid
from ctypes import wintypes

from guyrapu.core import diagnostico

logger = diagnostico.obtener_logger(__name__)

CLSCTX_INPROC_SERVER = 0x1
OBJID_CLIENT = 0xFFFFFFFC
CHILDID_SELF = 0

_VTABLE_RELEASE = 2
_VTABLE_SET_HWND_PROP_STR = 7
_VTABLE_CLEAR_HWND_PROPS = 9


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(texto: str) -> GUID:
    return GUID.from_buffer_copy(uuid.UUID(texto).bytes_le)


CLSID_ACC_PROP_SERVICES = _guid("B5F8350B-0548-48B1-A6EE-88BD00B4A5E7")
IID_IACC_PROPSERVICES = _guid("6E26E776-04F0-495D-80E4-3330352E3169")
PROPID_ACC_NAME = _guid("608D3DF8-8128-4AA7-A428-F55E49267291")

_servicios = None


def _llamar(interfaz, indice, tipos, *argumentos):
    vtable = ctypes.cast(
        interfaz, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    prototipo = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *tipos)
    funcion = prototipo(vtable[indice])
    return funcion(interfaz, *argumentos)


def _co_create_instance():
    ole32 = ctypes.WinDLL("ole32")
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    ole32.CoCreateInstance.restype = ctypes.c_long
    servicios = ctypes.c_void_p()
    resultado = ole32.CoCreateInstance(
        ctypes.byref(CLSID_ACC_PROP_SERVICES), None, CLSCTX_INPROC_SERVER,
        ctypes.byref(IID_IACC_PROPSERVICES), ctypes.byref(servicios))
    if resultado < 0 or not servicios:
        logger.debug("CoCreateInstance de AccPropServices falló: %#x",
                     resultado & 0xFFFFFFFF)
        return None
    return servicios


def _obtener_servicios():
    global _servicios
    if _servicios is None:
        _servicios = _co_create_instance()
    return _servicios


def poner(hwnd, nombre: str) -> bool:
    """Anota el nombre MSAA de la ventana. Devuelve False si no pudo."""
    try:
        servicios = _obtener_servicios()
        if not servicios:
            return False
        resultado = _llamar(
            servicios, _VTABLE_SET_HWND_PROP_STR,
            [wintypes.HWND, wintypes.DWORD, wintypes.DWORD, GUID,
             ctypes.c_wchar_p],
            hwnd, OBJID_CLIENT, CHILDID_SELF, PROPID_ACC_NAME, nombre)
        if resultado < 0:
            logger.debug("SetHwndPropStr del nombre accesible falló: %#x",
                         resultado & 0xFFFFFFFF)
            return False
        return True
    except Exception as exc:
        logger.debug("No se pudo anotar el nombre accesible: %s", exc)
        return False


def quitar(hwnd) -> bool:
    """Borra la anotación del nombre MSAA de la ventana."""
    try:
        servicios = _obtener_servicios()
        if not servicios:
            return False
        propiedades = (GUID * 1)(PROPID_ACC_NAME)
        resultado = _llamar(
            servicios, _VTABLE_CLEAR_HWND_PROPS,
            [wintypes.HWND, wintypes.DWORD, wintypes.DWORD,
             ctypes.POINTER(GUID), ctypes.c_long],
            hwnd, OBJID_CLIENT, CHILDID_SELF, propiedades, 1)
        if resultado < 0:
            logger.debug("ClearHwndProps del nombre accesible falló: %#x",
                         resultado & 0xFFFFFFFF)
            return False
        return True
    except Exception as exc:
        logger.debug("No se pudo borrar el nombre accesible: %s", exc)
        return False
