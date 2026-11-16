# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los avisos de una descarga sobre su ítem (lógica pura)."""

import unittest
from unittest import mock

from guyrapu.downloads import avisos_item
from guyrapu.downloads.avisos_item import AvisosItem, INTERVALO_VELOCIDAD_S
from guyrapu.downloads.descargas import ItemDescarga


class TestAvisosItem(unittest.TestCase):

    def test_la_velocidad_se_frena_al_intervalo(self):
        item = ItemDescarga("x", "https://youtu.be/abc", "video")
        avisos = AvisosItem(item, item.id, mock.Mock(), mock.Mock(), mock.Mock())
        with mock.patch.object(
                avisos_item.time, "monotonic",
                side_effect=[10.0,
                             10.0 + INTERVALO_VELOCIDAD_S / 2,
                             10.0 + INTERVALO_VELOCIDAD_S]):
            avisos.progreso(10, 1000, 10, "primero")
            self.assertEqual((item.velocidad, item.eta), (1000, 10))
            avisos.progreso(20, 2000, 20, "segundo")
            self.assertEqual((item.velocidad, item.eta), (1000, 10))
            avisos.progreso(30, 3000, 30, "tercero")
            self.assertEqual((item.velocidad, item.eta), (3000, 30))


if __name__ == "__main__":
    unittest.main()
