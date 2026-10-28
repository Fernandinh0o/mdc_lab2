import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from agenda import Agenda, TAMANO, reporte_pdf


def contacto(i):
    return dict(id=i, nombre='María López', telefono='5555-1234', correo='maria@example.com', ciudad='Quetzaltenango')


class PruebasAgenda(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name)
        self.agenda = Agenda(self.ruta)

    def test_acceso_y_modificacion_local(self):
        for i in range(1, 4):
            self.agenda.guardar(contacto(i))
        antes = self.agenda.archivo.read_bytes()
        self.assertEqual(len(antes), 3 * TAMANO)
        editado = self.agenda.buscar(2)
        self.assertEqual(self.agenda.posicion, TAMANO)
        editado['nombre'] = 'José Pérez'
        self.agenda.guardar(editado, modificar=True)
        despues = self.agenda.archivo.read_bytes()
        self.assertEqual(antes[:TAMANO], despues[:TAMANO])
        self.assertEqual(antes[2*TAMANO:], despues[2*TAMANO:])
        self.assertEqual(len(antes), len(despues))
        self.assertEqual(self.agenda.buscar(2)['nombre'], 'José Pérez')
        self.assertTrue(self.agenda.verificar_integridad())

    def test_validaciones(self):
        self.agenda.guardar(contacto(1))
        with self.assertRaises(ValueError): self.agenda.guardar(contacto(1))
        with self.assertRaises(ValueError): self.agenda.buscar(99)
        largo = contacto(2)
        largo['nombre'] = 'á' * 41
        with self.assertRaises(ValueError): self.agenda.guardar(largo)

    def test_alteracion_y_reinicio(self):
        self.agenda.guardar(contacto(1))
        datos = bytearray(self.agenda.archivo.read_bytes())
        datos[10] = ord('X')
        self.agenda.archivo.write_bytes(datos)
        reiniciada = Agenda(self.ruta)
        self.assertFalse(reiniciada.verificar_integridad())
        with self.assertRaises(ValueError): reiniciada.guardar(contacto(2))

    def test_archivos_faltantes_y_corruptos(self):
        self.agenda.indice.write_text('{', encoding='utf-8')
        with self.assertRaises(ValueError): self.agenda.buscar(1)
        self.agenda.indice.unlink()
        with self.assertRaises(OSError): self.agenda.buscar(1)
        self.assertFalse(self.agenda.indice.exists())

    def test_exportacion_y_respaldo(self):
        self.agenda.guardar(contacto(1))
        origen = self.ruta / 'exportado.json'
        self.agenda.exportar(origen)
        self.assertEqual(json.loads(origen.read_text(encoding='utf-8'))[0]['nombre'], 'María López')
        destino = self.ruta / 'reporte.pdf'
        reporte_pdf(origen, destino)
        self.assertTrue(destino.read_bytes().startswith(b'%PDF-'))
        respaldo = self.ruta / 'respaldo.zip'
        self.agenda.respaldo(respaldo)
        with zipfile.ZipFile(respaldo) as archivo:
            self.assertIsNone(archivo.testzip())
            self.assertEqual(archivo.read('contactos.dat'), self.agenda.archivo.read_bytes())


if __name__ == '__main__':
    unittest.main()
