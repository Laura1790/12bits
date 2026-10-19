# Cómo poner 12 BITS en un servidor

Esta app es **Python (Flask)** con base de datos **SQLite** y **subida de imágenes**.
Eso define qué hosting sirve y cuál no.

## ¿Sirve Cloudflare? ¿Sirve HostGator?

- **Cloudflare NO puede alojar esta app.** Cloudflare (Pages/Workers) ejecuta
  JavaScript en el borde, no un proceso Python permanente con SQLite. Lo que sí
  conviene usar de Cloudflare es lo **gratis y útil**: tu dominio, el DNS y el
  HTTPS/SSL, poniéndolo **por delante** del servidor que de verdad corre Python.

- **HostGator compartido (cPanel barato) NO es recomendable.** Está pensado para
  PHP/MySQL. Tiene "Setup Python App", pero se lleva mal con un proceso que
  consulta cada 2,5 s, con SQLite y con archivos subidos. Puede fallar o quedar
  inestable.

- **HostGator VPS/dedicado SÍ sirve**, porque es un Linux completo. Requiere
  configurarlo a mano (ver opción C).

**Recomendación:** usa un hosting de aplicaciones Python. El más fácil es
**Render** (opción A). Si ya pagas HostGator, usa su **VPS** (opción C) y, si
quieres, pon **Cloudflare delante** para el dominio y el HTTPS.

La app necesita: 1 proceso permanente, **disco persistente** (para que la base
de datos y las imágenes no se borren al reiniciar) y **un solo worker** (por SQLite).

---

## Opción A — Render (la más fácil, recomendada)

1. Sube esta carpeta a un repositorio de GitHub.
2. En render.com: **New → Web Service** y conecta ese repo.
3. Render detecta el archivo `render.yaml` incluido y configura solo:
   - Instalación: `pip install -r requirements.txt`
   - Arranque: `gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT app:app`
   - Variable secreta `BITS_ADMIN_KEY` generada automáticamente.
   - Disco persistente de 1 GB montado en `/var/data` (ahí vive la base de datos).
4. Deploy. Te da una URL `https://...onrender.com` con HTTPS ya listo.
5. Entra al panel del facilitador en: `https://TU-URL/facilitador?key=TU_CLAVE`
   (la clave está en Render → tu servicio → Environment → `BITS_ADMIN_KEY`).

> El plan gratuito de Render "duerme" tras inactividad y **no incluye disco
> persistente**: para talleres reales usa el plan de pago más bajo (Starter).

Railway funciona igual de fácil con los mismos comandos.

---

## Opción B — Dominio propio con Cloudflare

Cloudflare no aloja la app, pero sí le da un dominio bonito y HTTPS:

1. Despliega primero en Render (opción A) o en un VPS (opción C).
2. En Cloudflare, en tu dominio, crea un registro **CNAME** (o A) que apunte al
   host de Render/VPS. Activa el proxy (nube naranja) para HTTPS.
3. Listo: tus participantes entran por `https://12bits.tudominio.com`.

---

## Opción C — HostGator VPS (o cualquier VPS Linux)

En un VPS con acceso SSH:

```bash
# 1. Instalar Python y subir esta carpeta al servidor
sudo apt update && sudo apt install -y python3-pip python3-venv
cd /ruta/12bits_app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Fijar una clave secreta y arrancar con gunicorn
export BITS_ADMIN_KEY="pon-aqui-una-clave-larga-y-privada"
export BITS_DB="/ruta/12bits_app/12bits.sqlite"   # en disco permanente
gunicorn -w 1 --threads 8 -b 0.0.0.0:8000 app:app
```

Para que quede permanente y con HTTPS:
- Crea un servicio **systemd** que ejecute ese comando de gunicorn al arrancar.
- Pon **nginx** delante en el puerto 80/443 haciendo *proxy* a `127.0.0.1:8000`.
- Saca el certificado HTTPS con **Let's Encrypt (certbot)** o pon Cloudflare delante.

En HostGator compartido (sin VPS) esto normalmente **no** se puede hacer.

---

## Puntos importantes para cualquier servidor

- **Clave del facilitador:** define siempre `BITS_ADMIN_KEY` (larga y privada).
  Si no la defines, la app genera una nueva en cada reinicio y perderás el acceso.
- **Arranca con gunicorn, no con `python app.py`.** `python app.py` es solo para
  pruebas locales en un computador.
- **Un solo worker** (`-w 1`): SQLite no admite varios procesos escribiendo a la vez.
- **Disco persistente** obligatorio para `12bits.sqlite` y `static/uploads`, o
  perderás sesiones e imágenes en cada reinicio.
- **HTTPS** es necesario para que los celulares escaneen el QR sin problemas.
