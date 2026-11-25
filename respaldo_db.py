#!/usr/bin/env python3
"""Respaldo de la base PostgreSQL (Neon) de la app de Comodatos.

Genera un ZIP con un CSV por tabla y las imágenes de los modelos.
Uso:   DATABASE_URL="postgresql://..." python respaldo_db.py [carpeta_de_salida]
Si falta la base o los datos parecen vacíos, termina con error para que no se guarde un respaldo vacío sin aviso.
"""
import io
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

TABLAS = ["inventario", "solicitudes", "levantamientos", "historial", "especificaciones", "horas_extras", "configuracion"]


def motor(url):
    u = url.strip()
    for pref in ("postgresql://", "postgres://"):
        if u.startswith(pref):
            u = "postgresql+psycopg2://" + u[len(pref):]
            break
    return create_engine(u, pool_pre_ping=True)


def main():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        sys.exit("ERROR: falta la variable de entorno DATABASE_URL.")
    salida = Path(sys.argv[1] if len(sys.argv) > 1 else "respaldos")
    salida.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now(timezone.utc)
    destino = salida / f"respaldo_comodatos_{ahora:%Y%m%d_%H%M}.zip"

    resumen, problemas = [], []
    eng = motor(url)
    with eng.connect() as con, zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre in TABLAS:
            try:
                df = pd.read_sql(text(f"SELECT * FROM {nombre} ORDER BY id"), con)
            except Exception as e:   # la tabla no existe o no se pudo leer
                problemas.append(f"{nombre}: {type(e).__name__}")
                resumen.append(f"{nombre}: NO SE PUDO LEER")
                con.rollback()
                continue
            z.writestr(f"{nombre}.csv", df.to_csv(index=False))
            resumen.append(f"{nombre}: {len(df)} filas")
            if nombre in ("inventario", "solicitudes") and df.empty:
                problemas.append(f"{nombre}: la tabla está vacía")
        n_img = 0
        try:
            for nombre_img, contenido in con.execute(text("SELECT nombre, contenido FROM imagenes_modelos")).fetchall():
                z.writestr(f"imagenes_modelos/{nombre_img}", bytes(contenido))
                n_img += 1
        except Exception as e:
            problemas.append(f"imagenes_modelos: {type(e).__name__}")
        resumen.append(f"imagenes_modelos: {n_img} archivos")
        z.writestr("LEEME.txt", f"Respaldo de la app de Comodatos\nGenerado (UTC): {ahora:%Y-%m-%d %H:%M:%S}\n\n" + "\n".join(resumen) + "\n")

    print("\n".join(resumen))
    print(f"Archivo: {destino} ({destino.stat().st_size / 1024:.0f} KB)")
    if problemas:
        sys.exit("ATENCIÓN: " + "; ".join(problemas))


if __name__ == "__main__":
    main()
