"""Agenda del Laboratorio 2: toda la aplicación en un solo archivo.

Ejecutar: python main.py
Generar entregables ficticios: python main.py --generar-ejemplos
Dependencia externa: pip install fpdf2==2.8.7
"""
import argparse
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

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


class Aplicacion:
    def __init__(self, root):
        self.root = root
        root.title('Laboratorio 2 - Agenda de contactos')
        root.geometry('680x440')
        self.agenda = None
        self.valores = {campo: tk.StringVar() for campo in CAMPOS}
        panel = ttk.Frame(root, padding=20)
        panel.pack(fill='both', expand=True)
        for fila, (campo, variable) in enumerate(self.valores.items()):
            ttk.Label(panel, text=f'{campo.capitalize()} ({CAMPOS[campo]} bytes máx.)').grid(row=fila, column=0, sticky='w', pady=6)
            ttk.Entry(panel, textvariable=variable, width=48).grid(row=fila, column=1, sticky='ew')
        botones = ttk.Frame(panel)
        botones.grid(row=5, column=0, columnspan=2, pady=15)
        for texto, funcion in [('Agregar', self.agregar), ('Buscar ID', self.buscar), ('Modificar', self.modificar), ('Limpiar', self.limpiar)]:
            ttk.Button(botones, text=texto, command=lambda f=funcion: self.ejecutar(f)).pack(side='left', padx=4)
        self.estado = tk.StringVar(value='Listo. Usa el campo ID para buscar.')
        ttk.Label(panel, textvariable=self.estado, wraplength=620).grid(row=6, column=0, columnspan=2)
        barra = tk.Menu(root)
        root.config(menu=barra)
        for titulo, opciones in [('Contactos', [('Agregar', self.agregar), ('Buscar por ID', self.buscar), ('Modificar', self.modificar)]), ('Exportar', [('JSON', self.exportar), ('Reporte PDF desde JSON', self.pdf)]), ('Herramientas', [('Verificar integridad', self.integridad), ('Crear respaldo ZIP', self.respaldo), ('Información del archivo', self.informacion)]), ('Ayuda', [('Acerca de', self.ayuda)])]:
            menu = tk.Menu(barra, tearoff=False)
            barra.add_cascade(label=titulo, menu=menu)
            for texto, funcion in opciones:
                menu.add_command(label=texto, command=lambda f=funcion: self.ejecutar(f))
        self.ejecutar(self.iniciar)

    def ejecutar(self, funcion):
        try:
            funcion()
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            self.estado.set('Operación no completada.')
            messagebox.showerror('Error', str(error), parent=self.root)

    def iniciar(self):
        self.agenda = Agenda(Path(__file__).resolve().parent / 'datos')
        self.integridad()
        self.agenda.todos()

    def contacto(self):
        return {campo: variable.get() for campo, variable in self.valores.items()}

    def agregar(self):
        self.agenda.guardar(self.contacto())
        self.estado.set(f'Contacto agregado. seek()/tell(): byte {self.agenda.posicion}.')

    def modificar(self):
        self.agenda.guardar(self.contacto(), modificar=True)
        self.estado.set(f'Registro modificado en el lugar. tell(): byte {self.agenda.posicion}. El ID no cambia.')

    def buscar(self):
        contacto = self.agenda.buscar(self.valores['id'].get())
        for campo, variable in self.valores.items():
            variable.set(contacto[campo])
        self.estado.set(f'Encontrado usando el índice. seek()/tell(): byte {self.agenda.posicion}.')

    def limpiar(self):
        for variable in self.valores.values():
            variable.set('')

    def exportar(self):
        destino = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if destino:
            self.agenda.exportar(destino)
            self.estado.set('JSON exportado correctamente.')

    def pdf(self):
        origen = filedialog.askopenfilename(title='Selecciona el JSON exportado', filetypes=[('JSON', '*.json')])
        if origen:
            destino = filedialog.asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF', '*.pdf')])
            if destino:
                reporte_pdf(origen, destino)
                self.estado.set('Reporte PDF generado desde JSON.')

    def integridad(self):
        if self.agenda.verificar_integridad():
            messagebox.showinfo('Integridad', 'SHA-256 coincide: archivo íntegro.')
        else:
            messagebox.showwarning('Integridad', 'SHA-256 NO coincide. El archivo fue alterado fuera de la aplicación. Se bloquearán las escrituras; restaura los tres archivos de un respaldo.')

    def respaldo(self):
        destino = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[('ZIP', '*.zip')])
        if destino:
            original, comprimido = self.agenda.respaldo(destino)
            messagebox.showinfo('Respaldo', f'Archivos originales: {original} bytes\nZIP completo: {comprimido} bytes (incluye cabeceras).')

    def informacion(self):
        messagebox.showinfo('Información del archivo', self.agenda.informacion())

    def ayuda(self):
        messagebox.showinfo('Ayuda (simulada)', 'Agenda - Laboratorio 2\nAgregar: todos los campos. Buscar: solo ID.\nModificar conserva el ID. Consulta README.md para detalles.')



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
    parser = argparse.ArgumentParser(description='Agenda de contactos - Laboratorio 2')
    parser.add_argument('--generar-ejemplos', action='store_true', help='Generar entregables ficticios sin abrir la interfaz')
    opciones = parser.parse_args()
    if opciones.generar_ejemplos:
        generar()
    else:
        root = tk.Tk()
        Aplicacion(root)
        root.mainloop()
