# 12 BITS · Aplicación web para talleres

Aplicación web con tres roles: facilitador (panel protegido por clave), participante (solo su pista y tablero), e integrador (modificación del tablero, tres intentos). 12 pistas originales incluidas.

## Requisitos
Python 3.10+ y acceso a internet **una sola vez** para instalar dependencias.

## Ejecutar en un computador
```bash
cd 12bits_app
python -m pip install -r requirements.txt
python app.py
```
El terminal imprime la URL secreta del facilitador. Abrirla en el navegador.

El facilitador puede crear una sesión. El QR de cada sesión apunta a `http://SERVIDOR/s/CODIGO`.

## Probar con varios celulares en la misma red Wi-Fi

1. El computador y los celulares deben usar la misma red Wi-Fi, y permitir conexiones entrantes al puerto 5000.
2. Identifica la IP **local** del computador; por ejemplo, `192.168.1.25`.
3. En lugar de abrir `localhost:5000` en el computador, abre `http://192.168.1.25:5000/facilitador?key=CLAVE` (sustituye dirección y clave). Así, el QR incorpora la IP accesible a los celulares.
4. Abre una sesión y proyecta el QR. Cada persona registra su nombre desde su celular.
5. El facilitador selecciona al integrador, inicia el desafío y observa los cambios del tablero.

No uses `localhost` en la URL del facilitador si deseas escanear el QR desde otros dispositivos; en un celular, localhost apunta al propio celular. Una red corporativa puede restringir conexiones entre dispositivos. Si ocurre, usa un hosting HTTPS.

## Publicarla en internet

La carpeta se puede desplegar en servicios compatibles con Python como Render, Railway u otro servidor WSGI. Comando de instalación: `pip install -r requirements.txt`. Comando de inicio: `python app.py`. Configura `PORT` conforme al hosting y establece una variable secreta `BITS_ADMIN_KEY` (larga y privada).

**Persistencia:** se guarda en SQLite (`12bits.sqlite`) y los archivos en `static/uploads`. En hosting con almacenamiento efímero hay que configurar disco persistente, o migrar SQLite a una base de datos persistente. Por defecto se recomienda un único proceso para evitar complicaciones operativas de SQLite.

**Protección del facilitador:** su panel requiere `?key=...`; no compartas esta URL ni la contraseña de acceso. El QR de participante solo contiene la URL `/s/CODIGO`. Este diseño cubre una primera prueba controlada, no una autenticación corporativa de producción.

## Qué incluye
- Creación de sesiones desde el panel del facilitador.
- QR SVG generado por el propio servidor (sin servicio externo de QR).
- Asignación atómica de las 12 primeras pistas sin repetición; luego asignaciones aleatorias.
- Vista previa de las 12 pistas reservada al facilitador.
- Imágenes JPG/PNG/WebP configurables para personas, países y pistas.
- Visualización individual de pistas y tablero compartido.
- Designación del integrador solo por el facilitador.
- Tablero sincronizado mediante consulta cada 2,5 segundos.
- Máximo tres envíos de respuesta.
- Revelación de la solución al finalizar.

## Límite de las personalizaciones
La solución de referencia está fijada para el contenido original. Cambiar nombres de países, pistas o condiciones lógicas puede invalidar la solución. En esta versión no hay solucionador automático para nuevos acertijos; para usar una variante personalizada, verifica la solución y adapta la matriz de referencia del archivo `app.py`.
