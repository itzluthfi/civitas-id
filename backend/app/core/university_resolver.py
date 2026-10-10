import re
from typing import Dict, Any, Tuple

# Acronym mapping for well-known campuses
KNOWN_ACRONYMS = {
    "institut teknologi adhi tama surabaya": "ITATS",
    "institut teknologi telkom surabaya": "ITTS",
    "universitas telkom": "TEL-U",
    "universitas indonesia": "UI",
    "institut teknologi bandung": "ITB",
    "institut teknologi sepuluh nopember": "ITS",
    "universitas gadjah mada": "UGM",
    "universitas airlangga": "UNAIR",
    "universitas brawijaya": "UB",
    "universitas diponegoro": "UNDIP",
    "universitas padjadjaran": "UNPAD",
    "universitas bina nusantara": "BINUS",
    "universitas gunadarma": "UG",
    "universitas muhammadiyah malang": "UMM",
    "universitas muhammadiyah surakarta": "UMS",
    "universitas islam indonesia": "UII",
    "universitas atma jaya yogyakarta": "UAJY",
    "universitas katolik parahyangan": "UNPAR",
    "universitas kristen petra": "UK PETRA",
    "universitas tarumanagara": "UNTAR",
    "universitas trisakti": "USAKTI",
    "universitas pelita harapan": "UPH"
}

def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

def resolve_acronym(nama_pt: str, sinkatan_pt: str = "") -> str:
    clean_pt = clean_text(nama_pt).lower()
    if sinkatan_pt and clean_text(sinkatan_pt):
        return clean_text(sinkatan_pt).upper()
    if clean_pt in KNOWN_ACRONYMS:
        return KNOWN_ACRONYMS[clean_pt]
    
    # Generic generator from uppercase letters or words
    words = [w for w in clean_pt.split() if w not in ("dan", "of", "the", "in", "di")]
    if len(words) <= 1:
        return clean_pt[:4].upper()
    return "".join(w[0] for w in words).upper()

def extract_city(nama_pt: str) -> str:
    clean_pt = clean_text(nama_pt)
    cities = [
        "Surabaya", "Bandung", "Jakarta", "Yogyakarta", "Semarang", "Malang",
        "Medan", "Makassar", "Palembang", "Surakarta", "Solo", "Denpasar",
        "Bogor", "Depok", "Tangerang", "Bekasi", "Bandar Lampung", "Padang"
    ]
    for city in cities:
        if re.search(rf"\b{city}\b", clean_pt, re.IGNORECASE):
            return city
    return "Indonesia"

def resolve_faculty(prodi: str, nama_pt: str) -> Tuple[str, str]:
    p = clean_text(prodi).lower()
    if any(k in p for k in ("informatika", "komputer", "sistem informasi", "software", "data", "cyber", "teknologi informasi")):
        return ("Fakultas Teknologi Informasi dan Industri", "Faculty of Information Technology and Industry")
    if any(k in p for k in ("elektro", "mesin", "sipil", "industri", "kimia", "arsitektur", "lingkungan", "perkapalan")):
        return ("Fakultas Teknik dan Ilmu Rekayasa", "Faculty of Engineering and Applied Sciences")
    if any(k in p for k in ("ekonomi", "manajemen", "akuntansi", "bisnis", "keuangan", "pemasaran")):
        return ("Fakultas Ekonomi dan Bisnis", "Faculty of Economics and Business")
    if any(k in p for k in ("kedokteran", "kesehatan", "keperawatan", "farmasi", "gizi")):
        return ("Fakultas Kedokteran dan Ilmu Kesehatan", "Faculty of Medicine and Health Sciences")
    if any(k in p for k in ("hukum", "law")):
        return ("Fakultas Hukum", "Faculty of Law")
    if any(k in p for k in ("komunikasi", "sosial", "politik", "hubungan internasional")):
        return ("Fakultas Ilmu Sosial dan Ilmu Politik", "Faculty of Social and Political Sciences")
    if any(k in p for k in ("pendidikan", "keguruan")):
        return ("Fakultas Keguruan dan Ilmu Pendidikan", "Faculty of Teacher Training and Education")
    
    return (f"Fakultas / Jurusan {clean_text(prodi).title()}", f"Faculty of {clean_text(prodi).title()}")

def generate_dynamic_stamp_svg(nama_pt: str, city: str, acronym: str) -> str:
    clean_pt = clean_text(nama_pt).upper()
    # Limit to 38 chars for arc text
    if len(clean_pt) > 40:
        clean_pt = clean_pt[:38] + "..."

    return f"""<svg width="140" height="140" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <path id="stampTop" d="M 22,100 A 78,78 0 1,1 178,100" fill="none"/>
    <path id="stampBottom" d="M 178,100 A 78,78 0 1,1 22,100" fill="none"/>
  </defs>
  <g transform="rotate(-12 100 100)" opacity="0.86">
    <circle cx="100" cy="100" r="92" fill="none" stroke="#003366" stroke-width="3.5"/>
    <circle cx="100" cy="100" r="84" fill="none" stroke="#003366" stroke-width="1.2"/>
    <circle cx="100" cy="100" r="54" fill="none" stroke="#003366" stroke-width="1.2"/>
    <text font-family="'Times New Roman', serif" font-size="9.5" font-weight="bold" fill="#003366" letter-spacing="1">
      <textPath href="#stampTop" startOffset="50%" text-anchor="middle">{clean_pt}</textPath>
    </text>
    <text font-family="'Times New Roman', serif" font-size="10" font-weight="bold" fill="#003366" letter-spacing="1.2">
      <textPath href="#stampBottom" startOffset="50%" text-anchor="middle">★ {city.upper()} - TERVERIFIKASI ★</textPath>
    </text>
    <text x="100" y="96" font-family="'Times New Roman', serif" font-size="15" font-weight="bold" fill="#003366" text-anchor="middle">{acronym}</text>
    <text x="100" y="112" font-family="'Times New Roman', serif" font-size="8" font-weight="bold" fill="#003366" text-anchor="middle">PDDIKTI RESMI</text>
  </g>
</svg>"""

def generate_university_crest_svg(acronym: str, nama_pt: str) -> str:
    """Generates a prestigious, high-resolution vector emblem/crest for any university."""
    return f"""<svg width="100" height="100" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="crestGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#002b49"/>
      <stop offset="100%" stop-color="#001827"/>
    </linearGradient>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#d97706"/>
    </linearGradient>
  </defs>
  <!-- Outer double ring with gear/star laurels -->
  <circle cx="60" cy="60" r="56" fill="url(#crestGrad)" stroke="url(#goldGrad)" stroke-width="2.5"/>
  <circle cx="60" cy="60" r="50" fill="none" stroke="#ffffff" stroke-width="0.8" stroke-dasharray="2,2" opacity="0.6"/>
  <!-- Central Heraldic Shield -->
  <path d="M 60,25 C 78,25 90,32 90,52 C 90,75 60,94 60,94 C 60,94 30,75 30,52 C 30,32 42,25 60,25 Z"
        fill="#ffffff" stroke="url(#goldGrad)" stroke-width="1.8"/>
  <!-- Torch and Book motif -->
  <path d="M 46,65 Q 60,58 74,65 L 74,70 Q 60,63 46,70 Z" fill="#002b49"/>
  <path d="M 60,40 L 64,55 L 56,55 Z" fill="url(#goldGrad)"/>
  <circle cx="60" cy="37" r="3" fill="#ef4444"/>
  <!-- University Acronym Text -->
  <text x="60" y="55" font-family="'Times New Roman', serif" font-size="11" font-weight="900" fill="#002b49" text-anchor="middle" letter-spacing="0.5">
    {acronym[:5]}
  </text>
  <!-- Star at bottom -->
  <polygon points="60,98 62,103 67,103 63,106 65,111 60,108 55,111 57,106 53,103 58,103" fill="url(#goldGrad)"/>
</svg>"""

def get_dean_info(nama_pt: str, prodi: str) -> Dict[str, str]:
    clean_pt = clean_text(nama_pt).lower()
    acronym = resolve_acronym(nama_pt)
    faculty_id, faculty_en = resolve_faculty(prodi, nama_pt)
    return {
        "title_id": f"Dekan {faculty_id},",
        "title_en": f"Dean of {faculty_en},",
        "name": "Dr. Ir. Bambang Hermanto, M.T.",
        "nip": f"NIP/NIDN: 07{abs(hash(clean_pt)) % 90000000 + 10000000}"
    }
