#!/usr/bin/env python3
"""Resumen diario por WhatsApp de entregas y levantamientos (app de Comodatos).

Lee la tabla de solicitudes de la base PostgreSQL (Neon), calcula el resumen del día con las mismas reglas de la app
y lo envía por WhatsApp (API de Meta o Twilio) a uno o varios números, y por correo a una o varias direcciones.

Uso:
    python resumen_diario.py                    # resumen de hoy (hora de Cancún) y envío
    python resumen_diario.py --probar           # solo muestra el mensaje, no envía nada
    python resumen_diario.py --fecha 2026-11-26 # resumen de otro día

Variables de entorno:
    DATABASE_URL        cadena de conexión de Neon
    WHATSAPP_PROVIDER   meta (por defecto) o twilio
    WHATSAPP_DESTINO    números que reciben el resumen, separados por coma (10 dígitos o con lada): 9981234567,9987654321
    EMAIL_DESTINOS      correos que reciben el resumen, separados por coma: ana@empresa.com,luis@empresa.com
    Correo: SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD, EMAIL_REMITENTE (por defecto SMTP_USER),
            SMTP_SEGURIDAD (starttls por defecto; ssl o ninguna)
    Si solo configuras un medio (WhatsApp o correo), se envía solo por ese.
    Meta:   WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_PLANTILLA (por defecto resumen_diario_comodatos), WHATSAPP_IDIOMA (es_MX)
    Twilio: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM (whatsapp:+14155238886),
            TWILIO_CONTENT_SID (opcional: plantilla aprobada; sin ella se envía texto libre)
    SALTAR_SIN_SERVICIOS  true (por defecto): si ese día no hubo servicios programados, no se envía nada
"""
import argparse
import html as _html
import json
import os
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage
from datetime import date, datetime, timedelta

import pandas as pd

# Mismas reglas que la app
STATUS_COMPLETADO = ["entregado", "transferido", "realizado", "levantado"]
REFERENCIA_CATORCENA_DEFECTO = date(2025, 12, 31)   # un miércoles
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ---------------------------------------------------------------- datos
def _fechas(serie):
    t = serie.astype(str).str.strip().str[:10]
    f = pd.to_datetime(t, errors="coerce", format="%Y-%m-%d")
    pend = f.isna() & t.ne("") & ~t.str.lower().isin(["nan", "nat", "none"])
    if pend.any():
        try:
            f.loc[pend] = pd.to_datetime(t[pend], errors="coerce", dayfirst=True, format="mixed")
        except Exception:
            pass
    return f


def _clasificar(df):
    d = df.copy()
    d["_f"] = _fechas(d["Fecha_Entregado"])
    est = d["Status"].astype(str).str.strip().str.lower()
    d["_completada"] = est.isin(STATUS_COMPLETADO)
    d["_cancelada"] = est == "cancelado"
    d["_pendiente"] = est == "pendiente"
    mov = d["Movimiento"].astype(str).str.lower()
    doc = d["Proyecto"].astype(str).str.strip().str.lower() == "documental"
    d["_tipo"] = ["Documentales" if es_doc else ("Levantamientos" if "levant" in m else ("Reubicaciones" if "reubic" in m else "Entregas"))
                  for m, es_doc in zip(mov, doc)]
    return d


def inicio_catorcena(fecha, ref):
    ref = ref - timedelta(days=(ref.weekday() - 2) % 7)
    return ref + timedelta(days=14 * ((fecha - ref).days // 14))


def _nombres_unicos(serie):
    """Un solo nombre por chofer aunque lo hayan escrito con otras mayúsculas o espacios."""
    limpio = serie.fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    limpio = limpio.where(~limpio.str.lower().isin(["", "nan", "none"]), "")
    mejor = {}
    for nombre, veces in limpio[limpio != ""].value_counts().items():
        mejor.setdefault(nombre.casefold(), nombre)
    return limpio.map(lambda v: mejor.get(v.casefold(), v) if v else "")


# ---------------------------------------------------------------- cálculo
def calcular_resumen(df, fecha, ref_catorcena=REFERENCIA_CATORCENA_DEFECTO):
    d = _clasificar(df)
    hoy = pd.Timestamp(fecha)
    dia = d[d["_f"] == hoy]
    ayer = d[d["_f"] == hoy - pd.Timedelta(days=1)]

    def contar(base, tipo, col):
        return int(base[(base["_tipo"] == tipo) & base[col]].shape[0])

    r = {"fecha": fecha, "programadas": int(len(dia))}
    for tipo, clave in (("Entregas", "ent"), ("Levantamientos", "lev")):
        r[f"{clave}_conc"] = contar(dia, tipo, "_completada")
        r[f"{clave}_canc"] = contar(dia, tipo, "_cancelada")
        r[f"{clave}_pend"] = contar(dia, tipo, "_pendiente")
    r["otros_conc"] = int(dia[dia["_tipo"].isin(["Reubicaciones", "Documentales"]) & dia["_completada"]].shape[0])
    r["conc"] = int(dia["_completada"].sum())
    r["canc"] = int(dia["_cancelada"].sum())
    r["pend"] = int(dia["_pendiente"].sum())
    base_cumpl = r["programadas"] - r["canc"]
    r["cumplimiento"] = round(r["conc"] / base_cumpl * 100) if base_cumpl > 0 else None
    r["base_cumpl"] = base_cumpl
    r["conc_ayer"] = int(ayer["_completada"].sum())
    r["dif_ayer"] = r["conc"] - r["conc_ayer"]
    ini = inicio_catorcena(fecha, ref_catorcena)
    fin = ini + timedelta(days=13)
    cat = d[(d["_f"] >= pd.Timestamp(ini)) & (d["_f"] <= pd.Timestamp(fin))]
    r["cat_ini"], r["cat_fin"] = ini, fin
    r["cat_conc"] = int(cat["_completada"].sum())
    r["cat_total"] = int(len(cat))
    r["atrasadas"] = int((d["_pendiente"] & (d["_f"] < hoy)).sum())
    ch = _nombres_unicos(dia["Ruta"]) if len(dia) else pd.Series(dtype=str)
    top = dia[dia["_completada"] & (ch != "")].assign(_ch=ch).groupby("_ch").size().sort_values(ascending=False) if len(dia) else pd.Series(dtype=int)
    r["top_choferes"] = [(n, int(v)) for n, v in top.head(3).items()]
    return r


# ---------------------------------------------------------------- mensajes
def _fecha_larga(f):
    return f"{DIAS[f.weekday()]} {f:%d/%m/%Y}"


def _servicios(n):
    return f"{n} servicio" + ("" if n == 1 else "s")


def valores_plantilla(r):
    """12 textos cortos, sin saltos de línea (las plantillas de WhatsApp no los permiten en las variables)."""
    cumpl = f"{r['cumplimiento']}% ({r['conc']} de {r['base_cumpl']} programadas)" if r["cumplimiento"] is not None else "sin servicios programados"
    if r["conc_ayer"] or r["conc"]:
        signo = "+" if r["dif_ayer"] > 0 else ""
        ayer = f"{signo}{r['dif_ayer']} (ayer {r['conc_ayer']} concretadas)"
    else:
        ayer = "sin servicios ayer ni hoy"
    cat = f"{r['cat_conc']} de {r['cat_total']} servicios ({r['cat_ini']:%d/%m} al {r['cat_fin']:%d/%m})"
    mejor = f"{r['top_choferes'][0][0]} ({_servicios(r['top_choferes'][0][1])})" if r["top_choferes"] else "sin datos"
    vals = [_fecha_larga(r["fecha"]), r["ent_conc"], r["ent_canc"], r["ent_pend"], r["lev_conc"], r["lev_canc"], r["lev_pend"],
            cumpl, ayer, cat, r["atrasadas"], mejor]
    return [re.sub(r"\s+", " ", str(v)).strip() for v in vals]


def texto_libre(r):
    v = valores_plantilla(r)
    lineas = [
        f"📊 *Resumen diario de Comodatos*", f"📅 {v[0]}", "",
        "📦 *ENTREGAS*", f"✅ Concretadas: {v[1]}", f"❌ Canceladas: {v[2]}", f"⏳ Pendientes: {v[3]}", "",
        "🔄 *LEVANTAMIENTOS*", f"✅ Concretados: {v[4]}", f"❌ Cancelados: {v[5]}", f"⏳ Pendientes: {v[6]}",
    ]
    if r["otros_conc"]:
        lineas += ["", f"🔁 Reubicaciones y documentales concretados: {r['otros_conc']}"]
    lineas += ["", f"📈 *Cumplimiento del día:* {v[7]}", f"↕️ *Contra ayer:* {v[8]}", f"🗓️ *Catorcena en curso:* {v[9]}",
               f"⚠️ *Pendientes atrasadas:* {v[10]}"]
    if r["top_choferes"]:
        lineas += ["", "🏆 *Choferes del día*"] + [f"{i}. {n}: {_servicios(c)}" for i, (n, c) in enumerate(r["top_choferes"], 1)]
    lineas += ["", "Mensaje automático de la app de Comodatos."]
    return "\n".join(lineas)


# ---------------------------------------------------------------- envío
def normalizar_destino(numero):
    digitos = re.sub(r"\D", "", str(numero))
    if len(digitos) == 10:
        digitos = "52" + digitos
    if len(digitos) < 11:
        raise ValueError("WHATSAPP_DESTINO no parece un número válido (usa 10 dígitos o con lada).")
    return digitos


def enviar_meta(r, destino, http):
    token, phone_id = os.environ["WHATSAPP_TOKEN"], os.environ["WHATSAPP_PHONE_ID"]
    cuerpo = {
        "messaging_product": "whatsapp", "to": destino, "type": "template",
        "template": {"name": os.environ.get("WHATSAPP_PLANTILLA", "resumen_diario_comodatos"),
                     "language": {"code": os.environ.get("WHATSAPP_IDIOMA", "es_MX")},
                     "components": [{"type": "body", "parameters": [{"type": "text", "text": t} for t in valores_plantilla(r)]}]},
    }
    return http.post(f"https://graph.facebook.com/v21.0/{phone_id}/messages", json=cuerpo,
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)


def enviar_twilio(r, destino, http):
    sid, token = os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]
    datos = {"From": os.environ["TWILIO_FROM"], "To": f"whatsapp:+{destino}"}
    content_sid = os.environ.get("TWILIO_CONTENT_SID", "").strip()
    if content_sid:
        datos["ContentSid"] = content_sid
        datos["ContentVariables"] = json.dumps({str(i): t for i, t in enumerate(valores_plantilla(r), 1)}, ensure_ascii=False)
    else:
        datos["Body"] = texto_libre(r)
    return http.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=datos, auth=(sid, token), timeout=30)


# ---------------------------------------------------------------- varios destinatarios
def lista_valores(texto):
    """Separa por coma, punto y coma o salto de línea y quita repetidos."""
    vistos, res = set(), []
    for v in re.split(r"[,;\n]+", str(texto or "")):
        v = v.strip()
        if v and v.lower() not in vistos:
            vistos.add(v.lower())
            res.append(v)
    return res


def enviar_whatsapp_a_todos(r, destinos, proveedor, http):
    """Envía a cada número; si uno falla, sigue con los demás. Devuelve la lista de errores."""
    errores = []
    for crudo in destinos:
        try:
            num = normalizar_destino(crudo)
            resp = enviar_twilio(r, num, http) if proveedor == "twilio" else enviar_meta(r, num, http)
            if resp.status_code >= 300:
                errores.append(f"WhatsApp ...{num[-4:]}: HTTP {resp.status_code} {resp.text[:200]}")
            else:
                print(f"WhatsApp ...{num[-4:]}: enviado (HTTP {resp.status_code})")
        except Exception as e:
            errores.append(f"WhatsApp {str(crudo)[-4:]}: {type(e).__name__}: {e}")
    return errores


# ---------------------------------------------------------------- correo
def asunto_correo(r):
    return f"Resumen diario de Comodatos · {_fecha_larga(r['fecha'])}"


def html_correo(r):
    e = _html.escape
    v = valores_plantilla(r)

    def tarjeta(titulo, conc, canc, pend, color):
        return (f'<td width="50%" valign="top" style="padding:6px;">'
                f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E5E7EB;border-radius:10px;border-top:4px solid {color};">'
                f'<tr><td style="padding:12px 14px;font-weight:700;color:#111827;font-size:15px;">{e(titulo)}</td></tr>'
                f'<tr><td style="padding:0 14px 12px 14px;font-size:14px;color:#374151;line-height:1.9;">'
                f'<span style="color:#15803D;">✅ Concretadas:</span> <b style="font-size:18px;color:#111827;">{conc}</b><br>'
                f'<span style="color:#B91C1C;">❌ Canceladas:</span> <b style="font-size:18px;color:#111827;">{canc}</b><br>'
                f'<span style="color:#B45309;">⏳ Pendientes:</span> <b style="font-size:18px;color:#111827;">{pend}</b>'
                f'</td></tr></table></td>')

    def fila(etiqueta, valor):
        return (f'<tr><td style="padding:8px 14px;border-bottom:1px solid #F3F4F6;color:#6B7280;font-size:13px;">{e(etiqueta)}</td>'
                f'<td style="padding:8px 14px;border-bottom:1px solid #F3F4F6;color:#111827;font-size:14px;font-weight:600;" align="right">{e(str(valor))}</td></tr>')

    choferes = "".join(f"<li>{e(n)}: {e(_servicios(c))}</li>" for n, c in r["top_choferes"])
    otros = (f'<p style="margin:10px 6px 0 6px;color:#374151;font-size:13px;">🔁 Reubicaciones y documentales concretados: <b>{r["otros_conc"]}</b></p>'
             if r["otros_conc"] else "")
    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#F3F4F6;font-family:Segoe UI,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:16px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#FFFFFF;border-radius:12px;overflow:hidden;">
<tr><td style="background:#D95F00;padding:18px 20px;color:#FFFFFF;">
<div style="font-size:20px;font-weight:700;">📊 Resumen diario de Comodatos</div>
<div style="font-size:14px;opacity:.95;margin-top:4px;">📅 {e(v[0])}</div></td></tr>
<tr><td style="padding:14px 10px 4px 10px;"><table width="100%" cellpadding="0" cellspacing="0"><tr>
{tarjeta("📦 Entregas", r["ent_conc"], r["ent_canc"], r["ent_pend"], "#D95F00")}
{tarjeta("🔄 Levantamientos", r["lev_conc"], r["lev_canc"], r["lev_pend"], "#2563EB")}
</tr></table>{otros}</td></tr>
<tr><td style="padding:10px 10px 4px 10px;"><table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E5E7EB;border-radius:10px;">
{fila("📈 Cumplimiento del día", v[7])}{fila("↕️ Contra ayer", v[8])}{fila("🗓️ Catorcena en curso", v[9])}{fila("⚠️ Pendientes atrasadas", v[10])}
</table></td></tr>
{f'<tr><td style="padding:10px 20px 0 20px;"><div style="font-weight:700;color:#111827;font-size:14px;">🏆 Choferes del día</div><ul style="margin:6px 0 0 18px;padding:0;color:#374151;font-size:14px;line-height:1.7;">{choferes}</ul></td></tr>' if choferes else ""}
<tr><td style="padding:16px 20px;color:#9CA3AF;font-size:12px;">Cumplimiento = concretadas ÷ (programadas − canceladas). Mensaje automático de la app de Comodatos.</td></tr>
</table></td></tr></table></body></html>"""


def construir_correo(r, remitente, destinatario):
    msg = EmailMessage()
    msg["Subject"] = asunto_correo(r)
    msg["From"] = remitente
    msg["To"] = destinatario
    msg.set_content(texto_libre(r).replace("*", ""))
    msg.add_alternative(html_correo(r), subtype="html")
    return msg


def enviar_correos(r, destinos, config=None):
    """Un correo por destinatario (nadie ve las direcciones de los demás). Devuelve la lista de errores."""
    c = config or os.environ
    host, puerto = c.get("SMTP_HOST", "").strip(), int(c.get("SMTP_PORT", "587") or 587)
    usuario, clave = c.get("SMTP_USER", "").strip(), c.get("SMTP_PASSWORD", "")
    remitente = c.get("EMAIL_REMITENTE", "").strip() or usuario
    seguridad = (c.get("SMTP_SEGURIDAD", "starttls") or "starttls").strip().lower()
    if not host or not remitente:
        return ["Correo: faltan SMTP_HOST y SMTP_USER (o EMAIL_REMITENTE)."]
    errores = []
    try:
        srv = smtplib.SMTP_SSL(host, puerto, timeout=30, context=ssl.create_default_context()) if seguridad == "ssl" else smtplib.SMTP(host, puerto, timeout=30)
        with srv:
            if seguridad == "starttls":
                srv.starttls(context=ssl.create_default_context())
            if usuario:
                srv.login(usuario, clave)
            for dest in destinos:
                try:
                    srv.send_message(construir_correo(r, remitente, dest))
                    print(f"Correo a {dest}: enviado")
                except Exception as e:
                    errores.append(f"Correo a {dest}: {type(e).__name__}: {e}")
    except Exception as e:
        errores.append(f"Correo (conexión): {type(e).__name__}: {e}")
    return errores


# ---------------------------------------------------------------- base de datos
def leer_datos(url):
    from sqlalchemy import create_engine, text
    u = url.strip()
    for pref in ("postgresql://", "postgres://"):
        if u.startswith(pref):
            u = "postgresql+psycopg2://" + u[len(pref):]
            break
    eng = create_engine(u, pool_pre_ping=True)
    cols = ", ".join(f'"{c}"' for c in ("Fecha_Entregado", "Status", "Proyecto", "Movimiento", "Ruta"))
    with eng.connect() as con:
        df = pd.read_sql(text(f"SELECT {cols} FROM solicitudes"), con)
        try:
            ref = con.execute(text("SELECT \"Valor\" FROM configuracion WHERE \"Clave\" = 'catorcena_referencia' ORDER BY id DESC LIMIT 1")).scalar()
            ref = datetime.strptime(str(ref), "%Y-%m-%d").date()
        except Exception:
            ref = REFERENCIA_CATORCENA_DEFECTO
    return df, ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", help="AAAA-MM-DD (por defecto hoy, hora de Cancún)")
    ap.add_argument("--probar", action="store_true", help="solo muestra el mensaje")
    args = ap.parse_args()
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        sys.exit("ERROR: falta DATABASE_URL.")
    if args.fecha:
        fecha = datetime.strptime(args.fecha, "%Y-%m-%d").date()
    else:
        from datetime import timezone
        fecha = (datetime.now(timezone.utc) - timedelta(hours=5)).date()   # hora de Cancún (UTC-5, sin horario de verano)
    df, ref = leer_datos(url)
    r = calcular_resumen(df, fecha, ref)
    print(texto_libre(r))
    if r["programadas"] == 0 and os.environ.get("SALTAR_SIN_SERVICIOS", "true").lower() != "false":
        print("\nNo hubo servicios programados ese día: no se envía mensaje.")
        return
    destinos_wa = lista_valores(os.environ.get("WHATSAPP_DESTINO", ""))
    destinos_mail = lista_valores(os.environ.get("EMAIL_DESTINOS", ""))
    if args.probar:
        print(f"\nAsunto del correo: {asunto_correo(r)}")
        with open("resumen_preview.html", "w", encoding="utf-8") as f:
            f.write(html_correo(r))
        print("Vista previa del correo guardada en resumen_preview.html")
        print(f"Destinos configurados: {len(destinos_wa)} de WhatsApp, {len(destinos_mail)} de correo.")
        print("\n(Modo prueba: no se envió nada.)")
        return
    if not destinos_wa and not destinos_mail:
        sys.exit("ERROR: no hay destinos. Configura WHATSAPP_DESTINO y/o EMAIL_DESTINOS.")
    errores = []
    if destinos_wa:
        import requests
        proveedor = os.environ.get("WHATSAPP_PROVIDER", "meta").strip().lower() or "meta"
        errores += enviar_whatsapp_a_todos(r, destinos_wa, proveedor, requests)
    if destinos_mail:
        errores += enviar_correos(r, destinos_mail)
    if errores:
        sys.exit("ATENCIÓN, hubo errores:\n- " + "\n- ".join(errores))


if __name__ == "__main__":
    main()
