#!/usr/bin/env python3
"""Genera los ficheros que enlaza la web a partir de los originales.

NO es un paso de compilación: esto se ejecuta a mano cuando cambian las
imágenes, y el resultado se commitea. GitHub Pages sirve ficheros estáticos y
no ejecuta nada, así que todo lo que la página pide tiene que existir en el
repo ya listo.

    python3 tools/genera_assets.py

Entra por  assets/fotos/ y assets/capturas/  y sale por  assets/web/.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN_FOTOS = RAIZ / "assets" / "fotos"
ORIGEN_CAPTURAS = RAIZ / "assets" / "capturas"
ORIGEN_MARCA = RAIZ / "assets" / "marca"
SALIDA = RAIZ / "assets" / "web"

# Fondo de marca. Se usa para aplanar los PNG con transparencia cuando el
# formato de destino no la admite (JPEG) y para los iconos, que en iOS NO
# pueden llevar canal alfa: si lo llevan, se pinta de negro.
FONDO = (11, 36, 51)  # #0B2433

# La portada se sirve en tres anchos. El original mide 1365 px, así que NO se
# amplía: pedirle más pixeles de los que tiene solo engorda el fichero.
ANCHOS_PORTADA = (640, 960, 1280)

# Las capturas se pintan como mucho a ~390 px de ancho en pantalla; con el
# triple para pantallas densas va sobrado.
ANCHOS_CAPTURA = (380, 560, 790)

CAPTURAS = {
    "01-diario.png": "cap-diario",
    "02-clima.png": "cap-clima",
    "03-comunidad.png": "cap-comunidad",
    "04-clubes.png": "cap-clubes",
    "05-salidas.png": "cap-salidas",
}


def aplanar(img: Image.Image) -> Image.Image:
    """Quita la transparencia componiendo sobre el azul de marca."""
    if img.mode not in ("RGBA", "LA", "P"):
        return img.convert("RGB")
    img = img.convert("RGBA")
    fondo = Image.new("RGBA", img.size, FONDO + (255,))
    return Image.alpha_composite(fondo, img).convert("RGB")


def redimensionar(img: Image.Image, ancho: int) -> Image.Image:
    if img.width == ancho:
        return img.copy()
    alto = round(img.height * ancho / img.width)
    return img.resize((ancho, alto), Image.LANCZOS)


def portada() -> None:
    src = ORIGEN_FOTOS / "portada-original.jpg"
    if not src.exists():
        print(f"  !! falta {src.name}")
        return
    img = Image.open(src).convert("RGB")
    for ancho in ANCHOS_PORTADA:
        if ancho > img.width:
            print(f"  ·  portada {ancho}: saltada (el original solo tiene {img.width} px)")
            continue
        dst = SALIDA / f"portada-{ancho}.webp"
        redimensionar(img, ancho).save(dst, "WEBP", quality=82, method=6)
        print(f"  ✓  {dst.name}  {dst.stat().st_size // 1024} KB")


def capturas() -> None:
    for fichero, base in CAPTURAS.items():
        src = ORIGEN_CAPTURAS / fichero
        if not src.exists():
            print(f"  !! falta {fichero}")
            continue
        img = Image.open(src)
        # Las capturas SÍ conservan la transparencia: el marco del móvil viene
        # recortado y tiene que flotar sobre el fondo de la sección, sea cual sea.
        img = img.convert("RGBA")
        for ancho in ANCHOS_CAPTURA:
            dst = SALIDA / f"{base}-{ancho}.webp"
            redimensionar(img, ancho).save(dst, "WEBP", quality=86, method=6)
            print(f"  ✓  {dst.name}  {dst.stat().st_size // 1024} KB")


def iconos() -> None:
    """Favicon, iconos de instalación y apple-touch.

    apple-touch-icon va OPACO y sin esquinas redondeadas: iOS redondea solo, y
    si le llega con alfa lo compone sobre negro.
    """
    src = ORIGEN_MARCA / "logo.png"
    if not src.exists():
        print("  !! falta marca/logo.png")
        return
    logo = Image.open(src).convert("RGBA")

    # Símbolo pequeño para la barra y el pie, con transparencia.
    redimensionar(logo, 56).save(SALIDA / "logo-simbolo-56.webp", "WEBP", quality=90, method=6)
    print("  ✓  logo-simbolo-56.webp")

    for tam in (192, 512):
        lienzo = Image.new("RGBA", (tam, tam), FONDO + (255,))
        margen = round(tam * 0.12)
        pieza = redimensionar(logo, tam - margen * 2)
        lienzo.paste(pieza, (margen, (tam - pieza.height) // 2), pieza)
        lienzo.convert("RGB").save(SALIDA / f"icon-{tam}.png", "PNG", optimize=True)
        print(f"  ✓  icon-{tam}.png")

    tam = 180
    lienzo = Image.new("RGBA", (tam, tam), FONDO + (255,))
    margen = round(tam * 0.12)
    pieza = redimensionar(logo, tam - margen * 2)
    lienzo.paste(pieza, (margen, (tam - pieza.height) // 2), pieza)
    lienzo.convert("RGB").save(SALIDA / "apple-touch-icon.png", "PNG", optimize=True)
    print("  ✓  apple-touch-icon.png (opaco, sin alfa)")

    # favicon.ico con los dos tamaños que siguen usándose de verdad.
    ico = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    pieza = redimensionar(logo, 64)
    ico.paste(pieza, (0, (64 - pieza.height) // 2), pieza)
    ico.save(RAIZ / "favicon.ico", "ICO", sizes=[(16, 16), (32, 32)])
    print("  ✓  favicon.ico")


def compartir() -> None:
    """Imagen de vista previa al compartir (1200x630).

    En España el reparto va por WhatsApp: sin esta imagen el enlace sale como
    una línea de texto gris y nadie lo abre. Va versionada en el nombre porque
    WhatsApp y Facebook cachean la anterior durante días.

    Sin degradados: la foto recortada, un velo plano y el logo con el nombre.
    """
    src = ORIGEN_FOTOS / "portada-original.jpg"
    if not src.exists():
        print("  !! falta la foto de portada")
        return
    ancho, alto = 1200, 630
    foto = Image.open(src).convert("RGB")

    # Cubrir y recortar por el centro.
    escala = max(ancho / foto.width, alto / foto.height)
    grande = foto.resize((round(foto.width * escala), round(foto.height * escala)), Image.LANCZOS)
    x = (grande.width - ancho) // 2
    y = (grande.height - alto) // 2
    lienzo = grande.crop((x, y, x + ancho, y + alto)).convert("RGBA")

    # Velo plano (no degradado) para que el logo se lea sobre cualquier zona.
    velo = Image.new("RGBA", (ancho, alto), FONDO + (150,))
    lienzo = Image.alpha_composite(lienzo, velo)

    # Barra inferior sólida, borde duro arriba: el lenguaje de la página.
    d = ImageDraw.Draw(lienzo)
    d.rectangle((0, alto - 96, ancho, alto), fill=FONDO + (255,))
    d.line((0, alto - 96, ancho, alto - 96), fill=(30, 72, 106, 255), width=2)

    logo = Image.open(ORIGEN_MARCA / "logo.png").convert("RGBA")
    pieza = redimensionar(logo, 300)
    lienzo.paste(pieza, ((ancho - pieza.width) // 2, (alto - 96 - pieza.height) // 2), pieza)

    dst = SALIDA / "og-spearovis-v1.jpg"
    lienzo.convert("RGB").save(dst, "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  ✓  {dst.name}  {dst.stat().st_size // 1024} KB  (1200x630)")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    print("Portada:")
    portada()
    print("Capturas:")
    capturas()
    print("Iconos:")
    iconos()
    print("Compartir:")
    compartir()
    total = sum(f.stat().st_size for f in SALIDA.iterdir() if f.is_file())
    print(f"\nTotal en assets/web: {total // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
