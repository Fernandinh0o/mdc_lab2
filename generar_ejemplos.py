"""Genera entregables de demostración sin alterar los datos de la interfaz."""
from pathlib import Path
from agenda import Agenda, reporte_pdf


def generar():
    carpeta = Path(__file__).resolve().parent / 'ejemplos'
    agenda = Agenda(carpeta)
    if not agenda.cargar_indice():
        for identificador, nombre, ciudad in [(1, 'María López', 'Quetzaltenango'), (2, 'José Pérez', 'Guatemala'), (3, 'Ana García', 'Antigua Guatemala')]:
            agenda.guardar(dict(id=identificador, nombre=nombre, telefono=f'5555-000{identificador}', correo=f'contacto{identificador}@example.com', ciudad=ciudad))
    agenda.exportar(carpeta / 'contactos.json')
    reporte_pdf(carpeta / 'contactos.json', carpeta / 'reporte.pdf')
    original, zip_bytes = agenda.respaldo(carpeta / 'respaldo.zip')
    print(f'DAT: {agenda.archivo.stat().st_size} bytes; DAT + índice + hash: {original} bytes; ZIP: {zip_bytes} bytes.')


if __name__ == '__main__':
    generar()
