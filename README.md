# Laboratorio 2: Agenda de contactos con acceso aleatorio

Aplicación de escritorio Python/Tkinter. Todo el código de la aplicación, incluida la generación de ejemplos, está en `main.py`; no necesitas otros módulos propios. La carpeta `tests/` solo contiene pruebas de desarrollo. Incluye índice JSON, SHA-256, exportación JSON/PDF, ZIP y metadatos. Los contactos de ejemplo son ficticios.

## Ejecutar en Windows con Visual Studio

1. Clona `https://github.com/Fernandinh0o/mdc_lab2.git` usando **Git > Clonar repositorio**.
2. Instala Python 3.12 o posterior desde python.org, con Tcl/Tk. En Visual Studio instala la carga de trabajo **Desarrollo de Python** y abre la carpeta del repositorio. También funciona en Visual Studio Code con su extensión Python.
3. En una terminal situada en la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Selecciona `.venv` como intérprete. No hace falta activar PowerShell ni cambiar su política de ejecución. En Linux: `python3 -m venv .venv`, `.venv/bin/pip install -r requirements.txt`, `.venv/bin/python main.py`; requiere Tkinter del sistema y una sesión gráfica.

## Uso

- Agregar: llena los cinco campos con un ID positivo único.
- Buscar: escribe el ID y pulsa Buscar ID. La ventana muestra el desplazamiento obtenido con `tell()`.
- Modificar: busca primero, edita los campos y pulsa Modificar conservando el ID.
- Exportar JSON guarda todos los registros. Reporte PDF pide ese JSON como origen.
- Herramientas verifica SHA-256, genera ZIP y muestra metadatos/permisos.
- Ayuda es simulada, como pide el enunciado.

Los archivos propios se crean en `datos/`, junto al programa. No se sobreescriben los ejemplos. No ejecutes dos instancias simultáneamente: esta versión académica no implementa bloqueo entre procesos. Si ocurre un fallo entre la escritura del DAT y el índice/hash, la validación avisa; conserva los archivos para diagnóstico y restaura los tres desde un ZIP válido. No se regeneran índices ni hashes silenciosamente.

## Formato de archivo

| Campo | Bytes UTF-8 |
|---|---:|
| id | 10 |
| nombre | 80 |
| telefono | 25 |
| correo | 90 |
| ciudad | 50 |
| Salto de línea LF | 1 |
| **Total** | **256** |

Se codifica cada campo a UTF-8 y se rellena con espacios hasta su ancho en **bytes**, no en caracteres. Esto evita que las tildes desplacen los siguientes registros. Se rechazan campos demasiado largos; no se truncan secuencias UTF-8. Se usan modos binarios para impedir la traducción de LF a CRLF en Windows; el contenido sigue siendo texto UTF-8.

El índice asigna ID a número de registro, empezando por cero. `seek(numero * 256)` llega directamente al contacto y `tell()` informa su posición. Modificar escribe exactamente 256 bytes sin reescribir los demás registros. La carga del índice cuesta O(n); una vez cargado, localizar la clave cuesta O(1) promedio y la lectura del DAT es directa. Calcular SHA-256 después de una escritura sí recorre el DAT completo, tal como exige el laboratorio.

El hash verifica el DAT, no autentica al autor ni protege frente a alguien que modifique también el hash. El índice se valida estructuralmente y se contrasta con los registros al exportar/iniciar. El PDF usa Helvetica y soporta acentos latinos; caracteres ajenos a Latin-1 se representan como `?` solo en el PDF. DAT y JSON conservan Unicode.

## Pruebas y entregables

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py --generar-ejemplos
```

`ejemplos/` contiene DAT, índice, SHA-256, JSON exportado, reporte PDF y ZIP. El generador es repetible y no duplica IDs. `docs/informe.pdf` explica el diseño e incluye capturas reales de la interfaz y de una alteración detectada, tomadas en una pantalla virtual Linux. La apariencia en Windows puede variar.

Para reproducir la evidencia de integridad: agrega un contacto, cierra el programa, cambia una letra del nombre en `datos/contactos.dat` conservando el tamaño y vuelve a abrir. Debe aparecer la advertencia SHA-256. Restaura DAT, índice y hash de un respaldo anterior antes de guardar nuevos contactos. Los errores de archivos ausentes, permisos y corrupción se muestran como avisos; no se borran datos automáticamente.
