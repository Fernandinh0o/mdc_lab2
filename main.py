"""Ejecutar con python main.py; no requiere servidor."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from agenda import Agenda, CAMPOS, reporte_pdf


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


if __name__ == '__main__':
    root = tk.Tk()
    Aplicacion(root)
    root.mainloop()
