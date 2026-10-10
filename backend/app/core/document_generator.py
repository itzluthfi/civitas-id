import os
import io
import base64
import tempfile
from typing import Dict, Any, Tuple
import qrcode
import barcode
from barcode.writer import ImageWriter
from playwright.async_api import async_playwright
from . import university_resolver as uni

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

SIGNATURE_DEAN_SVG = """<svg width="180" height="75" viewBox="0 0 220 90" xmlns="http://www.w3.org/2000/svg">
  <path d="M 25,65 Q 40,15 50,55 T 70,35 Q 95,20 115,55 T 145,45 Q 175,25 205,50 M 45,50 Q 100,48 185,48" 
        fill="none" stroke="#002244" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" opacity="0.92"/>
</svg>"""

SIGNATURE_KAPRODI_SVG = """<svg width="170" height="70" viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg">
  <path d="M 30,50 Q 45,20 60,52 T 85,38 Q 110,18 130,50 T 165,40" 
        fill="none" stroke="#002244" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" opacity="0.92"/>
</svg>"""

def _resolve_logo_src(clean_pt: str, acronym: str) -> str:
    # Generate vector university crest dynamically
    crest_svg = uni.generate_university_crest_svg(acronym, clean_pt)
    b64_svg = base64.b64encode(crest_svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64_svg}"

def _generate_qr_b64(url: str, box_size: int = 12) -> str:
    qr = qrcode.QRCode(version=3, box_size=box_size, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="#002b49", back_color="white")
    buf = io.BytesIO()
    img_qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def _generate_barcode_b64(value: str) -> str:
    code128 = barcode.get_barcode_class("code128")
    bar = code128(value.replace(".", ""), writer=ImageWriter())
    buf = io.BytesIO()
    bar.write(buf)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

async def _render_document(html: str, output_format: str = "pdf", viewport_w: int = 1200, viewport_h: int = 1697, device_scale_factor: int = 2) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html)
        temp_path = f.name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = await browser.new_context(
                viewport={"width": viewport_w, "height": viewport_h},
                device_scale_factor=device_scale_factor
            )
            page = await context.new_page()
            await page.goto(f"file:///{temp_path}", wait_until="networkidle")
            
            if output_format == "pdf":
                pdf_bytes = await page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
                await browser.close()
                return pdf_bytes
            else:
                png_bytes = await page.screenshot(full_page=True)
                await browser.close()
                return png_bytes
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ==============================================================================
# 1. SKMA STANDAR INDONESIA (100% DINAMIS)
# ==============================================================================
async def generate_skma_standard(data: Dict[str, Any], output_format: str = "pdf") -> bytes:
    clean_pt = uni.clean_text(data.get("nama_pt", "Perguruan Tinggi"))
    clean_prodi = uni.clean_text(data.get("prodi", "Program Studi"))
    kode_pt = uni.clean_text(data.get("kode_pt", "000000"))
    acronym = uni.resolve_acronym(clean_pt, data.get("sinkatan_pt", ""))
    city = uni.extract_city(clean_pt)
    faculty_id, _ = uni.resolve_faculty(clean_prodi, clean_pt)
    dean = uni.get_dean_info(clean_pt, clean_prodi)
    
    verify_url = data.get("verify_url", "https://pddikti.kemdiktisaintek.go.id")
    qr_b64 = _generate_qr_b64(verify_url, box_size=12)
    logo_src = _resolve_logo_src(clean_pt, acronym)
    
    # Generate dynamic stamp
    stamp_svg = uni.generate_dynamic_stamp_svg(clean_pt, city, acronym)
    stamp_b64 = base64.b64encode(stamp_svg.encode("utf-8")).decode("utf-8")
    sig_b64 = base64.b64encode(SIGNATURE_DEAN_SVG.encode("utf-8")).decode("utf-8")

    is_negeri = any(k in clean_pt.lower() for k in ["negeri", "universitas indonesia", "institut teknologi bandung", "universitas gadjah mada", "institut teknologi sepuluh nopember", "universitas airlangga", "universitas brawijaya", "universitas diponegoro", "universitas padjadjaran", "uin ", "iain "])
    kop_yayasan = "KEMENTERIAN PENDIDIKAN TINGGI, SAINS, DAN TEKNOLOGI" if is_negeri else "LEMBAGA LAYANAN PENDIDIKAN TINGGI (LLDIKTI)"
    nomor_surat = f"{kode_pt.strip() or '084'}/BAAK/{acronym}/X/2026"

    html = f"""<!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <title>Surat Keterangan Mahasiswa Aktif</title>
        <style>
            @page {{ size: A4 portrait; margin: 0; }}
            * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            body {{
                margin: 0;
                padding: 22mm 25mm 20mm 25mm;
                font-family: 'Times New Roman', Times, serif;
                font-size: 11.5pt;
                line-height: 1.45;
                color: #111;
                background-color: #fff;
            }}
            .kop-surat {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding-bottom: 8px;
                border-bottom: 3.5px solid #002b49;
                position: relative;
            }}
            .kop-surat::after {{
                content: '';
                position: absolute;
                bottom: -5px;
                left: 0;
                right: 0;
                height: 1px;
                background-color: #002b49;
            }}
            .kop-logo {{ width: 85px; height: auto; max-height: 85px; object-fit: contain; flex-shrink: 0; }}
            .kop-text {{ flex-grow: 1; text-align: center; padding: 0 10px; }}
            .kop-yayasan {{ font-size: 10pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #1a1a1a; }}
            .kop-kampus {{ font-size: 14pt; font-weight: bold; color: #002b49; text-transform: uppercase; letter-spacing: 0.8px; margin: 2px 0; }}
            .kop-fakultas {{ font-size: 11pt; font-weight: bold; color: #1a1a1a; text-transform: uppercase; margin-bottom: 2px; }}
            .kop-alamat {{ font-size: 8.5pt; color: #333; line-height: 1.25; }}
            .judul-blok {{ text-align: center; margin-top: 18px; margin-bottom: 18px; }}
            .judul-surat {{ font-size: 13.5pt; font-weight: bold; text-decoration: underline; text-transform: uppercase; letter-spacing: 1px; color: #002b49; margin-bottom: 3px; }}
            .nomor-surat {{ font-size: 10.5pt; color: #222; }}
            .paragraf {{ text-align: justify; margin-bottom: 12px; }}
            .data-table {{ width: 100%; margin-left: 20px; margin-bottom: 14px; border-collapse: collapse; }}
            .data-table td {{ padding: 3px 0; vertical-align: top; font-size: 11pt; }}
            .data-label {{ width: 220px; color: #222; }}
            .data-separator {{ width: 20px; text-align: center; }}
            .data-val {{ font-weight: bold; color: #002b49; }}
            .signature-block {{
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
                margin-top: 25px;
                page-break-inside: avoid;
            }}
            .qr-panel {{
                width: 48%;
                display: flex;
                align-items: center;
                gap: 12px;
                border: 1.2px solid #cbd5e1;
                border-radius: 6px;
                padding: 10px;
                background-color: #f8fafc;
            }}
            .qr-image {{ width: 110px; height: 110px; border-radius: 4px; }}
            .qr-desc {{ font-size: 8pt; color: #334155; line-height: 1.35; }}
            .signature-box {{ width: 45%; text-align: left; position: relative; }}
            .sig-space {{ height: 75px; position: relative; display: flex; align-items: center; }}
            .stempel {{ position: absolute; left: -25px; top: -10px; width: 115px; height: 115px; pointer-events: none; opacity: 0.86; }}
            .sig-img {{ position: absolute; left: 10px; top: 5px; width: 140px; }}
            .pejabat-nama {{ font-weight: bold; text-decoration: underline; color: #002b49; font-size: 11pt; }}
            .pejabat-nip {{ font-size: 9.5pt; color: #333; }}
        </style>
    </head>
    <body>
        <div class="kop-surat">
            <img class="kop-logo" src="{logo_src}" alt="Logo">
            <div class="kop-text">
                <div class="kop-yayasan">{kop_yayasan}</div>
                <div class="kop-kampus">{clean_pt}</div>
                <div class="kop-fakultas">{faculty_id}</div>
                <div class="kop-alamat">Pangkalan Data Pendidikan Tinggi | Kode PT: {kode_pt} | {city}, Indonesia</div>
            </div>
        </div>
        <div class="judul-blok">
            <div class="judul-surat">Surat Keterangan Mahasiswa Aktif</div>
            <div class="nomor-surat">Nomor: {nomor_surat}</div>
        </div>
        <div class="paragraf">
            {dean['title_id']} {clean_pt} dengan ini menerangkan dengan sebenarnya bahwa:
        </div>
        <table class="data-table">
            <tr><td class="data-label">Nama Mahasiswa</td><td class="data-separator">:</td><td class="data-val">{data.get('nama')}</td></tr>
            <tr><td class="data-label">Nomor Induk Mahasiswa (NIM)</td><td class="data-separator">:</td><td class="data-val">{data.get('nim')}</td></tr>
            <tr><td class="data-label">Program Studi</td><td class="data-separator">:</td><td class="data-val">{clean_prodi} (Jenjang {data.get('jenjang', 'Sarjana')})</td></tr>
            <tr><td class="data-label">Status Keaktifan</td><td class="data-separator">:</td><td class="data-val">{data.get('status_saat_ini', 'Aktif')}</td></tr>
        </table>
        <div class="paragraf">
            Adalah benar mahasiswa aktif pada Tahun Akademik berjalan dan tercatat secara sah pada pangkalan data universitas.
        </div>
        <div class="paragraf">
            Surat keterangan ini diterbitkan secara sah untuk dipergunakan sebagaimana mestinya.
        </div>
        <div class="signature-block">
            <div class="qr-panel">
                <img class="qr-image" src="data:image/png;base64,{qr_b64}" alt="QR">
                <div class="qr-desc">
                    <strong style="color: #002b49; font-size: 8.5pt; display: block;">VERIFIKASI DIGITAL</strong>
                    Pindai untuk memverifikasi keabsahan dokumen dan status mahasiswa secara daring.
                </div>
            </div>
            <div class="signature-box">
                <div>{city}, 10 Oktober 2026</div>
                <div style="font-weight: bold; margin-bottom: 2px;">{dean['title_id']}</div>
                <div class="sig-space">
                    <img class="sig-img" src="data:image/svg+xml;base64,{sig_b64}" alt="TTD">
                    <img class="stempel" src="data:image/svg+xml;base64,{stamp_b64}" alt="Stempel">
                </div>
                <div class="pejabat-nama">{dean['name']}</div>
                <div class="pejabat-nip">{dean['nip']}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _render_document(html, output_format)

# ==============================================================================
# 2. SKMA BILINGUAL (ENGLISH - INDONESIA, 100% DINAMIS)
# ==============================================================================
async def generate_skma_bilingual(data: Dict[str, Any], output_format: str = "pdf") -> bytes:
    clean_pt = uni.clean_text(data.get("nama_pt", "Perguruan Tinggi"))
    clean_prodi = uni.clean_text(data.get("prodi", "Program Studi"))
    kode_pt = uni.clean_text(data.get("kode_pt", "000000"))
    acronym = uni.resolve_acronym(clean_pt, data.get("sinkatan_pt", ""))
    city = uni.extract_city(clean_pt)
    _, faculty_en = uni.resolve_faculty(clean_prodi, clean_pt)
    dean = uni.get_dean_info(clean_pt, clean_prodi)

    verify_url = data.get("verify_url", "https://pddikti.kemdiktisaintek.go.id")
    qr_b64 = _generate_qr_b64(verify_url, box_size=12)
    logo_src = _resolve_logo_src(clean_pt, acronym)
    
    stamp_svg = uni.generate_dynamic_stamp_svg(clean_pt, city, acronym)
    stamp_b64 = base64.b64encode(stamp_svg.encode("utf-8")).decode("utf-8")
    sig_b64 = base64.b64encode(SIGNATURE_DEAN_SVG.encode("utf-8")).decode("utf-8")

    nomor_surat = f"{kode_pt.strip() or '084'}/BAAK/{acronym}/EN-ID/X/2026"

    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Student Enrollment Certificate / Surat Keterangan Mahasiswa Aktif</title>
        <style>
            @page {{ size: A4 portrait; margin: 0; }}
            * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            body {{
                margin: 0;
                padding: 18mm 22mm 16mm 22mm;
                font-family: 'Times New Roman', Times, serif;
                font-size: 10pt;
                line-height: 1.35;
                color: #111;
                background-color: #fff;
            }}
            .kop-surat {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding-bottom: 6px;
                border-bottom: 3px solid #002b49;
                position: relative;
            }}
            .kop-logo {{ width: 80px; height: auto; max-height: 80px; object-fit: contain; flex-shrink: 0; }}
            .kop-text {{ flex-grow: 1; text-align: center; }}
            .kop-kampus-en {{ font-size: 13.5pt; font-weight: bold; color: #002b49; text-transform: uppercase; }}
            .kop-fakultas-en {{ font-size: 10pt; font-weight: bold; color: #222; text-transform: uppercase; }}
            .kop-alamat {{ font-size: 8pt; color: #444; }}
            .judul-blok {{ text-align: center; margin: 12px 0; }}
            .judul-en {{ font-size: 12.5pt; font-weight: bold; text-decoration: underline; color: #002b49; text-transform: uppercase; }}
            .judul-id {{ font-size: 9.5pt; font-style: italic; color: #555; text-transform: uppercase; margin-top: 1px; }}
            .nomor {{ font-size: 9.5pt; margin-top: 3px; }}
            .data-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 9.5pt; }}
            .data-table td {{ padding: 3px 2px; vertical-align: top; }}
            .lbl-en {{ font-weight: bold; color: #1e293b; }}
            .lbl-id {{ font-style: italic; font-size: 8pt; color: #64748b; }}
            .val {{ font-weight: bold; color: #002b49; }}
            .signature-block {{ display: flex; justify-content: space-between; align-items: flex-end; margin-top: 20px; }}
            .qr-panel {{ width: 48%; display: flex; align-items: center; gap: 10px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; background: #f8fafc; }}
            .qr-image {{ width: 100px; height: 100px; }}
            .qr-desc {{ font-size: 7.5pt; color: #334155; line-height: 1.35; }}
            .signature-box {{ width: 45%; text-align: left; position: relative; }}
            .sig-space {{ height: 70px; position: relative; }}
            .stempel {{ position: absolute; left: -20px; top: -10px; width: 110px; height: 110px; opacity: 0.86; }}
            .sig-img {{ position: absolute; left: 10px; top: 5px; width: 135px; }}
            .pejabat-nama {{ font-weight: bold; text-decoration: underline; color: #002b49; font-size: 10pt; }}
            .pejabat-nip {{ font-size: 8.5pt; color: #333; }}
        </style>
    </head>
    <body>
        <div class="kop-surat">
            <img class="kop-logo" src="{logo_src}" alt="Logo">
            <div class="kop-text">
                <div class="kop-kampus-en">{clean_pt}</div>
                <div class="kop-fakultas-en">{faculty_en}</div>
                <div class="kop-alamat">Higher Education Registry | Inst. Code: {kode_pt} | {city}, Indonesia</div>
            </div>
        </div>
        <div class="judul-blok">
            <div class="judul-en">Certificate of Student Enrollment</div>
            <div class="judul-id">Surat Keterangan Mahasiswa Aktif</div>
            <div class="nomor">Ref. No: {nomor_surat}</div>
        </div>
        <div>
            This is to certify that the individual named below is a currently enrolled, active bona fide student in good standing at {clean_pt}:
        </div>
        <table class="data-table">
            <tr><td style="width: 220px;"><div class="lbl-en">Full Name</div><div class="lbl-id">Nama Mahasiswa</div></td><td>:</td><td class="val">{data.get('nama')}</td></tr>
            <tr><td><div class="lbl-en">Student Identification Number</div><div class="lbl-id">NIM / NPM</div></td><td>:</td><td class="val">{data.get('nim')}</td></tr>
            <tr><td><div class="lbl-en">Degree & Major</div><div class="lbl-id">Jenjang & Program Studi</div></td><td>:</td><td class="val">{clean_prodi} ({data.get('jenjang', 'Bachelor / Sarjana')})</td></tr>
            <tr><td><div class="lbl-en">Enrollment Status</div><div class="lbl-id">Status Keaktifan</div></td><td>:</td><td class="val">{data.get('status_saat_ini', 'Active')}</td></tr>
        </table>
        <div>
            This certificate is officially issued to serve for academic verification, educational discount privileges, student developer programs, and scholarship eligibility.
        </div>
        <div class="signature-block">
            <div class="qr-panel">
                <img class="qr-image" src="data:image/png;base64,{qr_b64}" alt="QR">
                <div class="qr-desc">
                    <strong style="color: #002b49; font-size: 8pt; display: block;">DIGITAL DOCUMENT VERIFICATION</strong>
                    Scan this QR code to verify the authentic student enrollment status directly online.
                </div>
            </div>
            <div class="signature-box">
                <div>{city}, 10 October 2026</div>
                <div style="font-weight: bold; margin-bottom: 2px;">{dean['title_en']}</div>
                <div class="sig-space">
                    <img class="sig-img" src="data:image/svg+xml;base64,{sig_b64}" alt="TTD">
                    <img class="stempel" src="data:image/svg+xml;base64,{stamp_b64}" alt="Stempel">
                </div>
                <div class="pejabat-nama">{dean['name']}</div>
                <div class="pejabat-nip">{dean['nip']}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _render_document(html, output_format)

# ==============================================================================
# 3. KTM DIGITAL CR80 (100% DINAMIS)
# ==============================================================================
async def generate_ktm_digital(data: Dict[str, Any], output_format: str = "pdf") -> bytes:
    clean_pt = uni.clean_text(data.get("nama_pt", "Perguruan Tinggi"))
    clean_prodi = uni.clean_text(data.get("prodi", "Program Studi"))
    kode_pt = uni.clean_text(data.get("kode_pt", "000000"))
    acronym = uni.resolve_acronym(clean_pt, data.get("sinkatan_pt", ""))
    city = uni.extract_city(clean_pt)

    verify_url = data.get("verify_url", "https://pddikti.kemdiktisaintek.go.id")
    qr_b64 = _generate_qr_b64(verify_url, box_size=10)
    barcode_b64 = _generate_barcode_b64(data.get("nim", "1203230028"))
    logo_src = _resolve_logo_src(clean_pt, acronym)

    photo_b64 = data.get("photo_base64")
    if photo_b64:
        photo_box_html = f'<img src="{photo_b64}" style="width: 100%; height: 100%; object-fit: cover;" alt="Pas Foto">'
    else:
        jk = (data.get("jenis_kelamin") or "").upper()
        if jk == "P":
            photo_box_html = """
                <div class="cf-avatar" style="background: linear-gradient(180deg, #334155, #1e293b); width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                    <svg width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.8">
                        <path d="M12 14c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5z"/>
                        <path d="M5.5 21a6.5 6.5 0 0 1 13 0"/>
                    </svg>
                    <span style="font-size: 12px; color: #cbd5e1; margin-top: 8px; font-weight: 800; letter-spacing: 1px;">PAS FOTO</span>
                </div>
            """
        else:
            photo_box_html = """
                <div class="cf-avatar" style="background: linear-gradient(180deg, #1e293b, #0f172a); width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                    <svg width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.8">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                    </svg>
                    <span style="font-size: 12px; color: #cbd5e1; margin-top: 8px; font-weight: 800; letter-spacing: 1px;">PAS FOTO</span>
                </div>
            """

    html = f"""<!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <title>Kartu Tanda Mahasiswa Digital</title>
        <style>
            @page {{ size: 900px 1260px; margin: 0; }}
            * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; }}
            body {{
                margin: 0;
                padding: 30px;
                background-color: #0b1120;
                display: flex;
                flex-direction: column;
                gap: 30px;
                align-items: center;
                justify-content: center;
                width: 960px;
            }}
            .card {{
                width: 900px;
                height: 568px;
                border-radius: 28px;
                overflow: hidden;
                position: relative;
                box-shadow: 0 25px 50px -12px rgba(0,0,0,0.7);
                flex-shrink: 0;
            }}
            .card-front {{
                background: linear-gradient(135deg, #021526 0%, #032b49 50%, #044b7f 100%);
                color: #ffffff;
                padding: 32px 38px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }}
            .cf-header {{ display: flex; align-items: center; gap: 20px; border-bottom: 2px solid rgba(255,255,255,0.22); padding-bottom: 18px; }}
            .cf-logo {{ width: 76px; height: 76px; object-fit: contain; }}
            .cf-instansi h1 {{ font-size: 24px; margin: 0; font-weight: 800; color: #facc15; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.25; }}
            .cf-instansi p {{ font-size: 13.5px; margin: 4px 0 0 0; color: #e2e8f0; font-weight: 600; letter-spacing: 1px; }}
            .cf-body {{ display: flex; gap: 30px; align-items: center; margin: 12px 0; }}
            .cf-photo-box {{
                width: 200px; height: 260px; border: 3.5px solid #facc15; border-radius: 18px; overflow: hidden; background: #1e293b;
                display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 8px 16px rgba(0,0,0,0.4);
            }}
            .cf-data {{ flex-grow: 1; display: flex; flex-direction: column; gap: 12px; }}
            .cf-label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 1px; }}
            .cf-val-name {{ font-size: 24px; font-weight: 800; color: #ffffff; text-transform: uppercase; letter-spacing: 0.5px; }}
            .cf-val-npm {{ font-size: 26px; font-weight: 900; color: #facc15; letter-spacing: 1.5px; font-family: monospace; }}
            .cf-val {{ font-size: 17px; font-weight: 700; color: #f1f5f9; }}
            .cf-footer {{ display: flex; justify-content: space-between; align-items: flex-end; border-top: 2px solid rgba(255,255,255,0.18); padding-top: 16px; }}
            .cf-chip-group {{ display: flex; align-items: center; gap: 16px; }}
            .cf-chip {{ width: 72px; height: 52px; background: linear-gradient(135deg, #d4af37, #fde047, #a16207); border-radius: 10px; border: 1.5px solid rgba(255,255,255,0.4); }}
            .cf-nfc-icon {{ width: 30px; height: 30px; opacity: 0.85; }}
            .cf-card-type {{ font-size: 14px; font-weight: 800; color: #f1f5f9; letter-spacing: 2px; text-transform: uppercase; border: 1.5px solid rgba(255,255,255,0.25); padding: 6px 18px; border-radius: 20px; }}
            
            .card-back {{ background: #ffffff; color: #1e293b; padding: 0 38px 28px 38px; display: flex; flex-direction: column; justify-content: space-between; }}
            .cb-strip {{ margin: 0 -38px; height: 64px; background: #020617; }}
            .cb-content {{ margin-top: 20px; display: flex; justify-content: space-between; align-items: center; gap: 24px; }}
            .cb-rules {{ flex-grow: 1; font-size: 13.5px; color: #334155; line-height: 1.55; }}
            .cb-rules strong {{ font-size: 14.5px; color: #002b49; display: block; margin-bottom: 6px; }}
            .cb-rules ol {{ padding-left: 20px; margin: 4px 0; }}
            .cb-rules li {{ margin-bottom: 4px; }}
            .cb-qr-box {{ display: flex; flex-direction: column; align-items: center; flex-shrink: 0; border: 2px solid #cbd5e1; padding: 8px; border-radius: 14px; background: #f8fafc; }}
            .cb-qr {{ width: 140px; height: 140px; }}
            .cb-qr-label {{ font-size: 11px; font-weight: 800; color: #002b49; margin-top: 4px; letter-spacing: 0.5px; }}
            .cb-footer {{ display: flex; justify-content: space-between; align-items: center; border-top: 2px solid #e2e8f0; padding-top: 14px; margin-top: 10px; }}
            .cb-barcode {{ height: 50px; max-width: 280px; object-fit: contain; }}
            .cb-address {{ font-size: 12.5px; color: #64748b; text-align: right; line-height: 1.4; }}
        </style>
    </head>
    <body>
        <div class="card card-front">
            <div class="cf-header">
                <img class="cf-logo" src="{logo_src}" alt="Logo">
                <div class="cf-instansi">
                    <h1>{clean_pt}</h1>
                    <p>KARTU TANDA MAHASISWA DIGITAL (KTM)</p>
                </div>
            </div>
            <div class="cf-body">
                <div class="cf-photo-box">
                    {photo_box_html}
                </div>
                <div class="cf-data">
                    <div><span class="cf-label">Nama Lengkap</span><div class="cf-val-name">{data.get('nama')}</div></div>
                    <div><span class="cf-label">Nomor Induk Mahasiswa (NIM)</span><div class="cf-val-npm">{data.get('nim')}</div></div>
                    <div><span class="cf-label">Program Studi & Jenjang</span><div class="cf-val">{clean_prodi} ({data.get('jenjang', 'S-1')})</div></div>
                </div>
            </div>
            <div class="cf-footer">
                <div class="cf-chip-group">
                    <div class="cf-chip"></div>
                    <svg class="cf-nfc-icon" viewBox="0 0 24 24" fill="none" stroke="#f1f5f9" stroke-width="2.2" stroke-linecap="round">
                        <path d="M6 8a9 9 0 0 1 0 8"/>
                        <path d="M9 10a5 5 0 0 1 0 4"/>
                        <path d="M12 12a1 1 0 0 1 0 0.1"/>
                    </svg>
                </div>
                <div class="cf-card-type">STUDENT CARD</div>
            </div>
        </div>
        <div class="card card-back">
            <div class="cb-strip"></div>
            <div class="cb-content">
                <div class="cb-rules">
                    <strong>KETENTUAN KARTU IDENTITAS MAHASISWA:</strong>
                    <ol>
                        <li>Kartu Tanda Mahasiswa (KTM) ini merupakan identitas resmi civitas akademika {clean_pt}.</li>
                        <li>Dilarang menyalahgunakan identitas atau memindahtangankan kartu ini kepada pihak lain.</li>
                        <li>Wajib dibawa selama beraktivitas di lingkungan kampus.</li>
                    </ol>
                </div>
                <div class="cb-qr-box">
                    <img class="cb-qr" src="data:image/png;base64,{qr_b64}" alt="QR">
                    <div class="cb-qr-label">VERIFIKASI</div>
                </div>
            </div>
            <div class="cb-footer">
                <img class="cb-barcode" src="data:image/png;base64,{barcode_b64}" alt="Barcode">
                <div class="cb-address">
                    <strong style="color: #002b49;">{clean_pt}</strong><br>
                    {city}, Indonesia | Kode PT: {kode_pt}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _render_document(html, output_format, viewport_w=960, viewport_h=1260, device_scale_factor=2)

# ==============================================================================
# 4. TRANSKRIP AKADEMIK SEMENTARA (100% DINAMIS)
# ==============================================================================
async def generate_transcript(data: Dict[str, Any], output_format: str = "pdf") -> bytes:
    clean_pt = uni.clean_text(data.get("nama_pt", "Perguruan Tinggi"))
    clean_prodi = uni.clean_text(data.get("prodi", "Program Studi"))
    kode_pt = uni.clean_text(data.get("kode_pt", "000000"))
    acronym = uni.resolve_acronym(clean_pt, data.get("sinkatan_pt", ""))
    city = uni.extract_city(clean_pt)
    faculty_id, _ = uni.resolve_faculty(clean_prodi, clean_pt)
    dean = uni.get_dean_info(clean_pt, clean_prodi)

    verify_url = data.get("verify_url", "https://pddikti.kemdiktisaintek.go.id")
    qr_b64 = _generate_qr_b64(verify_url, box_size=11)
    logo_src = _resolve_logo_src(clean_pt, acronym)
    
    stamp_svg = uni.generate_dynamic_stamp_svg(clean_pt, city, acronym)
    stamp_b64 = base64.b64encode(stamp_svg.encode("utf-8")).decode("utf-8")
    sig_dean_b64 = base64.b64encode(SIGNATURE_DEAN_SVG.encode("utf-8")).decode("utf-8")
    sig_kaprodi_b64 = base64.b64encode(SIGNATURE_KAPRODI_SVG.encode("utf-8")).decode("utf-8")

    courses = [
        ("IF1101", "Algoritma & Pemrograman", 3, "A", 4.0),
        ("IF1102", "Logika Informatika", 3, "A", 4.0),
        ("IF1103", "Matematika Diskrit", 3, "A", 4.0),
        ("IF1104", "Pengantar Teknologi Informasi", 2, "A", 4.0),
        ("KU1101", "Kalkulus I", 3, "B+", 3.5),
        ("KU1102", "Bahasa Indonesia", 2, "A", 4.0),
        ("KU1103", "Pendidikan Agama", 2, "A", 4.0),
        ("IF1201", "Struktur Data & Algoritma", 3, "A", 4.0),
        ("IF1202", "Pemrograman Berorientasi Objek", 3, "A", 4.0),
        ("IF1203", "Arsitektur & Organisasi Komputer", 3, "A", 4.0),
        ("IF1204", "Aljabar Linier & Matriks", 3, "A", 4.0),
        ("KU1201", "Kalkulus II", 3, "A", 4.0),
        ("KU1202", "Bahasa Inggris Komunikasi", 2, "A", 4.0),
        ("KU1203", "Pendidikan Kewarganegaraan", 2, "A", 4.0),
        ("IF2101", "Sistem Basis Data", 3, "A", 4.0),
        ("IF2102", "Komunikasi Data & Jaringan Komputer", 3, "A", 4.0),
        ("IF2103", "Rekayasa Perangkat Lunak", 3, "A", 4.0),
        ("IF2104", "Sistem Operasi", 3, "A", 4.0),
        ("IF2105", "Teori Bahasa & Otomata", 3, "A", 4.0),
        ("KU2101", "Probabilitas & Statistika Terapan", 3, "A", 4.0),
        ("IF2201", "Kecerdasan Buatan (AI)", 3, "A", 4.0),
        ("IF2202", "Pemrograman Web & Arsitektur API", 3, "A", 4.0),
        ("IF2203", "Analisis & Desain Algoritma", 3, "A", 4.0),
        ("IF2204", "Keamanan Siber & Informasi", 3, "A", 4.0),
        ("IF2205", "Interaksi Manusia & Komputer", 3, "A", 4.0),
        ("IF2206", "Manajemen Proyek Perangkat Lunak", 3, "A", 4.0),
        ("IF3101", "Machine Learning & Sains Data", 3, "A", 4.0),
        ("IF3102", "Komputasi Awan (Cloud Computing)", 3, "A", 4.0),
        ("IF3103", "Pengembangan Aplikasi Bergerak", 3, "A", 4.0),
        ("IF3104", "Pengolahan Citra Digital", 3, "A", 4.0),
        ("KU3101", "Metodologi Penelitian Ilmiah", 2, "A", 4.0),
        ("KU3102", "Etika Profesi & Hukum Siber", 2, "A", 4.0),
    ]
    total_sks = sum(c[2] for c in courses)
    total_bobot = sum(c[2] * c[4] for c in courses)
    ipk = total_bobot / total_sks
    col1 = courses[:16]
    col2 = courses[16:]

    def render_rows(items):
        r = ""
        for code, name, sks, grade, _ in items:
            r += f"""<tr>
                <td style="font-family: monospace; font-size: 7.5pt; text-align: center;">{code}</td>
                <td style="font-size: 7.8pt;">{name}</td>
                <td style="text-align: center; font-size: 7.8pt;">{sks}</td>
                <td style="text-align: center; font-weight: bold; font-size: 7.8pt;">{grade}</td>
            </tr>"""
        return r

    html = f"""<!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <title>Transkrip Akademik Sementara</title>
        <style>
            @page {{ size: A4 portrait; margin: 0; }}
            * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            body {{
                margin: 0;
                padding: 16mm 20mm 15mm 20mm;
                font-family: 'Times New Roman', Times, serif;
                font-size: 10.5pt;
                line-height: 1.35;
                color: #111;
                background-color: #fff;
            }}
            .kop-container {{ display: flex; align-items: center; padding-bottom: 6px; }}
            .kop-logo {{ width: 72px; height: auto; max-height: 72px; object-fit: contain; margin-right: 12px; flex-shrink: 0; }}
            .kop-text {{ flex-grow: 1; text-align: center; }}
            .kop-instansi {{ font-size: 9.5pt; font-weight: bold; text-transform: uppercase; color: #1a1a1a; }}
            .kop-pt {{ font-size: 13.5pt; font-weight: bold; color: #002b49; text-transform: uppercase; }}
            .kop-fakultas {{ font-size: 10pt; font-weight: bold; color: #222; text-transform: uppercase; }}
            .kop-alamat {{ font-size: 8pt; color: #444; line-height: 1.25; }}
            .kop-divider {{ margin-top: 4px; margin-bottom: 14px; border-top: 2px solid #002b49; border-bottom: 0.8px solid #002b49; height: 3px; }}
            .doc-title-block {{ text-align: center; margin-bottom: 12px; }}
            .doc-title {{ font-size: 12.5pt; font-weight: bold; text-decoration: underline; text-transform: uppercase; color: #002b49; }}
            .doc-sub {{ font-size: 9pt; font-style: italic; color: #555; text-transform: uppercase; margin-top: 1px; }}
            .table-bio {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 9.5pt; }}
            .table-bio td {{ padding: 2px 4px; vertical-align: top; }}
            .col-label {{ width: 180px; color: #333; }}
            .transcript-grid {{ display: flex; gap: 12px; margin-bottom: 12px; }}
            .transcript-col {{ width: 50%; }}
            .table-courses {{ width: 100%; border-collapse: collapse; border: 0.8px solid #334155; }}
            .table-courses th {{ background-color: #002b49; color: #ffffff; font-size: 7.5pt; padding: 4px 3px; text-align: center; border: 0.8px solid #002b49; text-transform: uppercase; }}
            .table-courses td {{ border: 0.5px solid #cbd5e1; padding: 2.5px 4px; }}
            .table-courses tr:nth-child(even) {{ background-color: #f8fafc; }}
            .summary-box {{ display: flex; justify-content: space-between; align-items: center; border: 1.2px solid #002b49; border-radius: 4px; padding: 6px 14px; background-color: #f0f7ff; margin-bottom: 16px; font-size: 9.5pt; }}
            .summary-box strong {{ color: #002b49; font-size: 10pt; }}
            .ttd-row {{ display: flex; justify-content: space-between; align-items: flex-end; margin-top: 12px; }}
            .qr-side {{ width: 38%; display: flex; align-items: center; gap: 10px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 8px; background: #f8fafc; }}
            .qr-side img {{ width: 85px; height: 85px; border-radius: 3px; }}
            .qr-side-text {{ font-size: 7.5pt; color: #334155; line-height: 1.35; }}
            .ttd-side {{ width: 58%; display: flex; justify-content: space-between; position: relative; }}
            .ttd-person {{ width: 48%; text-align: left; font-size: 9pt; position: relative; }}
            .ttd-space {{ height: 50px; position: relative; display: flex; align-items: center; }}
            .ttd-stempel {{ position: absolute; left: -15px; top: -10px; width: 95px; height: 95px; pointer-events: none; opacity: 0.86; }}
            .ttd-sig {{ position: absolute; left: 10px; top: 0; width: 110px; }}
            .ttd-name {{ font-weight: bold; text-decoration: underline; color: #002b49; font-size: 9.5pt; }}
            .ttd-nip {{ font-size: 8.5pt; color: #475569; }}
            .footer-legal {{ border-top: 0.5px solid #cbd5e1; padding-top: 4px; font-size: 7pt; color: #64748b; text-align: center; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="kop-container">
            <img class="kop-logo" src="{logo_src}" alt="Logo">
            <div class="kop-text">
                <div class="kop-instansi">Kementerian Pendidikan Tinggi, Sains, dan Teknologi</div>
                <div class="kop-pt">{clean_pt}</div>
                <div class="kop-fakultas">{faculty_id}</div>
                <div class="kop-alamat">Sistem Informasi Akademik | Kode PT: {kode_pt} | {city}, Indonesia</div>
            </div>
        </div>
        <div class="kop-divider"></div>
        <div class="doc-title-block">
            <div class="doc-title">TRANSKRIP AKADEMIK SEMENTARA</div>
            <div class="doc-sub">UNOFFICIAL CUMULATIVE ACADEMIC TRANSCRIPT</div>
        </div>
        <table class="table-bio">
            <tr>
                <td class="col-label">Nama Mahasiswa</td><td>: <strong>{data.get('nama')}</strong></td>
                <td class="col-label" style="padding-left: 20px;">Program Studi</td><td>: <strong>{clean_prodi} ({data.get('jenjang', 'S-1')})</strong></td>
            </tr>
            <tr>
                <td class="col-label">NPM / NIM</td><td>: <strong>{data.get('nim')}</strong></td>
                <td class="col-label" style="padding-left: 20px;">Jenjang / Fakultas</td><td>: <strong>{data.get('jenjang', 'Sarjana')} / {acronym}</strong></td>
            </tr>
            <tr>
                <td class="col-label">Status Akademik</td><td>: <strong>{data.get('status_saat_ini', 'Aktif')}</strong></td>
                <td class="col-label" style="padding-left: 20px;">Tahun Akademik</td><td>: <strong>2025/2026</strong></td>
            </tr>
        </table>
        <div class="transcript-grid">
            <div class="transcript-col"><table class="table-courses"><thead><tr><th style="width: 50px;">Kode</th><th>Mata Kuliah</th><th style="width: 32px;">SKS</th><th style="width: 32px;">Nilai</th></tr></thead><tbody>{render_rows(col1)}</tbody></table></div>
            <div class="transcript-col"><table class="table-courses"><thead><tr><th style="width: 50px;">Kode</th><th>Mata Kuliah</th><th style="width: 32px;">SKS</th><th style="width: 32px;">Nilai</th></tr></thead><tbody>{render_rows(col2)}</tbody></table></div>
        </div>
        <div class="summary-box">
            <div>Total SKS Ditempuh: <strong>{total_sks} SKS</strong></div>
            <div>Indeks Prestasi Kumulatif (IPK): <strong>{ipk:.2f} / 4.00</strong></div>
            <div>Predikat: <strong>DENGAN PUJIAN (CUM LAUDE)</strong></div>
        </div>
        <div class="ttd-row">
            <div class="qr-side">
                <img src="data:image/png;base64,{qr_b64}" alt="QR">
                <div class="qr-side-text">
                    <strong style="color: #002b49; display: block; font-size: 8pt;">VERIFIKASI DIGITAL</strong>
                    Pindai untuk memvalidasi catatan keaktifan resmi mahasiswa secara daring.
                </div>
            </div>
            <div class="ttd-side">
                <div class="ttd-person">
                    <div>Mengetahui,</div>
                    <div style="font-weight: bold; margin-bottom: 2px;">Ketua Program Studi,</div>
                    <div class="ttd-space"><img class="ttd-sig" src="data:image/svg+xml;base64,{sig_kaprodi_b64}" alt="TTD"></div>
                    <div class="ttd-name">Dr. Budi Setiawan, M.Kom.</div>
                    <div class="ttd-nip">NIP/NIDN: 0721038101</div>
                </div>
                <div class="ttd-person">
                    <div>{city}, 10 Oktober 2026</div>
                    <div style="font-weight: bold; margin-bottom: 2px;">{dean['title_id']}</div>
                    <div class="ttd-space">
                        <img class="ttd-sig" src="data:image/svg+xml;base64,{sig_dean_b64}" alt="TTD">
                        <img class="ttd-stempel" src="data:image/svg+xml;base64,{stamp_b64}" alt="Stempel">
                    </div>
                    <div class="pejabat-nama">{dean['name']}</div>
                    <div class="pejabat-nip">{dean['nip']}</div>
                </div>
            </div>
        </div>
        <div class="footer-legal">
            Transkrip akademik sementara ini sah diterbitkan oleh {clean_pt} untuk keperluan verifikasi akademik dan kelengkapan administrasi beasiswa/privilege.
        </div>
    </body>
    </html>
    """
    return await _render_document(html, output_format)
