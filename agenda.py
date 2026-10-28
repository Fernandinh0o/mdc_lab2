"""Persistencia de contactos en registros UTF-8 de exactamente 256 bytes."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import zipfile

CAMPOS = {'id': 10, 'nombre': 80, 'telefono': 25, 'correo': 90, 'ciudad': 50}
TAMANO = sum(CAMPOS.values()) + 1


def escribir_json(ruta, valor):
    ruta = Path(ruta)
    temporal = ruta.with_suffix(ruta.suffix + '.tmp')
    temporal.write_text(json.dumps(valor, ensure_ascii=False, indent=2), encoding='utf-8')
    temporal.replace(ruta)


def codificar(contacto):
    contacto = dict(contacto)
    numero = int(contacto['id'])
    if numero <= 0:
        raise ValueError('El ID debe ser un entero positivo.')
    contacto['id'] = str(numero)
    partes = []
    for campo, largo in CAMPOS.items():
        texto = str(contacto[campo]).strip()
        if not texto or any(ord(c) < 32 for c in texto):
            raise ValueError(f'{campo}: ingresa un valor sin saltos ni caracteres de control.')
        valor = texto.encode('utf-8')
        if len(valor) > largo:
            raise ValueError(f'{campo}: máximo {largo} bytes UTF-8 (las tildes pueden ocupar más de uno).')
        partes.append(valor.ljust(largo, b' '))
    return b''.join(partes) + b'\n'


def decodificar(datos):
    if len(datos) != TAMANO or datos[-1:] != b'\n':
        raise ValueError('Registro incompleto o corrupto.')
    contacto, posicion = {}, 0
    for campo, largo in CAMPOS.items():
        contacto[campo] = datos[posicion:posicion + largo].decode('utf-8').rstrip(' ')
        posicion += largo
    contacto['id'] = int(contacto['id'])
    if codificar(contacto) != datos:
        raise ValueError('Registro no canónico o corrupto.')
    return contacto


class Agenda:
    def __init__(self, directorio='datos'):
        self.directorio = Path(directorio)
        self.directorio.mkdir(parents=True, exist_ok=True)
        self.archivo = self.directorio / 'contactos.dat'
        self.indice = self.directorio / 'indice.json'
        self.hash_archivo = self.directorio / 'contactos.sha256'
        self.posicion = 0
        # Solo inicializar si los tres archivos son nuevos; nunca borrar evidencia.
        if not any(p.exists() for p in (self.archivo, self.indice, self.hash_archivo)):
            self.archivo.touch()
            escribir_json(self.indice, {})
            self.guardar_hash()

    def hash_actual(self):
        digest = hashlib.sha256()
        with self.archivo.open('rb') as archivo:
            for bloque in iter(lambda: archivo.read(65536), b''):
                digest.update(bloque)
        return digest.hexdigest()

    def guardar_hash(self):
        self.hash_archivo.write_text(self.hash_actual() + '\n', encoding='utf-8')

    def verificar_integridad(self):
        esperado = self.hash_archivo.read_text(encoding='utf-8').strip()
        return len(esperado) == 64 and esperado == self.hash_actual()

    def cargar_indice(self):
        indice = json.loads(self.indice.read_text(encoding='utf-8'))
        tamano = self.archivo.stat().st_size
        if tamano % TAMANO:
            raise ValueError('El tamaño del archivo no es múltiplo del registro.')
        if not isinstance(indice, dict) or len(indice) != tamano // TAMANO:
            raise ValueError('Índice incompleto o corrupto.')
        for clave, numero in indice.items():
            if not isinstance(clave, str) or not clave.isascii() or not clave.isdigit() or str(int(clave)) != clave or int(clave) <= 0:
                raise ValueError('ID inválido en el índice.')
            if type(numero) is not int or not 0 <= numero < len(indice):
                raise ValueError('Posición inválida en el índice.')
        if len(set(indice.values())) != len(indice):
            raise ValueError('Posiciones duplicadas en el índice.')
        return indice

    def buscar(self, identificador):
        clave = str(int(identificador))
        indice = self.cargar_indice()
        if clave not in indice:
            raise ValueError('No existe un contacto con ese ID.')
        with self.archivo.open('rb') as archivo:
            archivo.seek(indice[clave] * TAMANO)
            self.posicion = archivo.tell()
            contacto = decodificar(archivo.read(TAMANO))
        if str(contacto['id']) != clave:
            raise ValueError('El índice no corresponde al registro.')
        return contacto

    def guardar(self, contacto, modificar=False):
        registro = codificar(contacto)
        clave = str(int(contacto['id']))
        if not self.verificar_integridad():
            raise ValueError('Integridad incorrecta: restaura un respaldo antes de guardar.')
        indice = self.cargar_indice()
        if modificar:
            self.buscar(clave)
        elif clave in indice:
            raise ValueError('El ID ya existe.')
        numero = indice[clave] if modificar else len(indice)
        with self.archivo.open('r+b') as archivo:
            archivo.seek(numero * TAMANO)
            self.posicion = archivo.tell()
            archivo.write(registro)
            archivo.flush()
            os.fsync(archivo.fileno())
        if not modificar:
            indice[clave] = numero
            escribir_json(self.indice, indice)
        self.guardar_hash()

    def todos(self):
        indice = self.cargar_indice()
        resultado = []
        with self.archivo.open('rb') as archivo:
            for numero in range(len(indice)):
                contacto = decodificar(archivo.read(TAMANO))
                if indice.get(str(contacto['id'])) != numero:
                    raise ValueError('El índice no corresponde a los registros.')
                resultado.append(contacto)
        return resultado

    def exportar(self, destino):
        escribir_json(Path(destino), self.todos())

    def respaldo(self, destino):
        self.todos()
        if not self.verificar_integridad():
            raise ValueError('No se respalda un archivo con integridad incorrecta.')
        archivos = (self.archivo, self.indice, self.hash_archivo)
        with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as respaldo:
            for archivo in archivos:
                respaldo.write(archivo, archivo.name)
        return sum(p.stat().st_size for p in archivos), Path(destino).stat().st_size

    def informacion(self):
        info = self.archivo.stat()
        return (f'Archivo: {self.archivo.resolve()}\nTamaño: {info.st_size} bytes\n'
                f'Registro: {TAMANO} bytes\nRegistros: {info.st_size // TAMANO}\n'
                f'Modificación: {datetime.fromtimestamp(info.st_mtime).isoformat(sep=" ", timespec="seconds")}\n'
                f'Lectura: {os.access(self.archivo, os.R_OK)}\nEscritura: {os.access(self.archivo, os.W_OK)}')


def reporte_pdf(origen_json, destino):
    from fpdf import FPDF
    contactos = json.loads(Path(origen_json).read_text(encoding='utf-8'))
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Helvetica', size=12)
    def linea(texto):
        # Las fuentes básicas PDF soportan Latin-1; otros alfabetos se indican con ?.
        pdf.multi_cell(0, 7, str(texto).encode('latin-1', errors='replace').decode('latin-1'), new_x='LMARGIN', new_y='NEXT')
    linea('Agenda de contactos')
    linea('Generado: ' + datetime.now().isoformat(sep=' ', timespec='seconds'))
    for contacto in contactos:
        linea(' | '.join(f'{campo}: {contacto[campo]}' for campo in CAMPOS))
        pdf.ln(3)
    pdf.output(str(destino))
