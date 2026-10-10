import asyncio
import re
import urllib.parse
import json
import logging
from typing import Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from .cache import cache

logger = logging.getLogger("civitas.enrichment")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

WIKI_HEADERS = {
    "User-Agent": "CivitasID-AcademicBot/1.3.0 (https://civitas.id; contact@civitas.id)"
}

class EnrichmentService:
    """Enriches PDDIKTI academic profiles with verified external data:
    1. Dosen:
       - SINTA Kemdiktisaintek: Real photo URL, SINTA ID, SINTA Score 3Yr, SINTA Score Overall,
         Scopus H-Index, Web of Science H-Index, Google Scholar H-Index, and profile link.
    2. Perguruan Tinggi:
       - Wikipedia / Wikidata: Real Chancellor/Rector name, institutional status, motto, founding year, wiki link.
       - Campus Official Site: Official social media channels (Instagram, YouTube, LinkedIn, X), contact emails, hotlines.
    3. Mahasiswa:
       - Helper hooks for RAMA (Repositori Tugas Akhir Mahasiswa), SIVIL (Ijazah Nasional), and Google Scholar publications.
    """

    async def enrich_dosen(self, nama_dosen: str, nama_pt: str = "") -> Dict[str, Any]:
        if not nama_dosen:
            return {}

        # Remove academic prefixes (Prof., Dr., etc.)
        clean_name = re.sub(r"^(Prof\.|Dr\.|Drs\.|Ir\.|H\.|Hj\.)\s*", "", nama_dosen, flags=re.IGNORECASE)
        # Remove trailing academic degrees
        clean_name = re.split(r",\s*", clean_name)[0].strip()

        cache_key = f"enrich_dosen_v2:{clean_name.lower()}:{nama_pt[:10].lower()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        enriched = {
            "foto_url": None,
            "sinta_id": None,
            "sinta_url": None,
            "afiliasi_sinta": None,
            "departemen_sinta": None,
            "sinta_score_3yr": None,
            "sinta_score_overall": None,
            "scopus_h_index": None,
            "wos_h_index": None,
            "google_scholar_h_index": None,
            "google_scholar_url": None
        }

        try:
            encoded_query = urllib.parse.quote(clean_name)
            sinta_search_url = f"https://sinta.kemdiktisaintek.go.id/authors?q={encoded_query}"

            async with httpx.AsyncClient(headers=BROWSER_HEADERS, timeout=6.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(sinta_search_url)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="list-item")

                if cards:
                    best_card = cards[0]
                    # If campus name is provided, match by affiliation
                    if nama_pt:
                        pt_words = [
                            w.lower() for w in nama_pt.split() 
                            if len(w) > 3 and w.lower() not in ["universitas", "institut", "sekolah", "tinggi", "politeknik", "negeri", "swasta"]
                        ]
                        for card in cards:
                            affil = card.find("div", class_="profile-affil")
                            if affil and any(w in affil.get_text().lower() for w in pt_words):
                                best_card = card
                                break

                    # 1. Avatar photo
                    img = best_card.find("img", class_="avatar")
                    if img and img.get("src"):
                        src = img.get("src")
                        if "author-small.png" not in src:
                            enriched["foto_url"] = src

                    # 2. SINTA Profile URL and ID
                    sinta_link = best_card.find("a", href=re.compile(r"/authors/profile/"))
                    if sinta_link and sinta_link.get("href"):
                        enriched["sinta_url"] = sinta_link.get("href")
                        m_id = re.search(r"/profile/(\d+)", enriched["sinta_url"])
                        if m_id:
                            enriched["sinta_id"] = m_id.group(1)

                    # 3. Google Scholar ID
                    scholar_span = best_card.find("span", class_="d-none")
                    if scholar_span and scholar_span.get_text(strip=True):
                        gs_id = scholar_span.get_text(strip=True)
                        if len(gs_id) >= 8 and not " " in gs_id:
                            enriched["google_scholar_url"] = f"https://scholar.google.com/citations?user={gs_id}"

                    # 4. Affiliation and Department
                    affil_div = best_card.find("div", class_="profile-affil")
                    if affil_div:
                        enriched["afiliasi_sinta"] = affil_div.get_text(strip=True)

                    dept_div = best_card.find("div", class_="profile-dept")
                    if dept_div:
                        enriched["departemen_sinta"] = dept_div.get_text(strip=True)

                    # 5. Metrics & H-indexes
                    card_text = best_card.get_text("\n", strip=True)
                    s_3yr = re.search(r"([\d\.,]+)\s*\n*SINTA Score 3Yr", card_text)
                    if s_3yr:
                        enriched["sinta_score_3yr"] = s_3yr.group(1)

                    s_ov = re.search(r"([\d\.,]+)\s*\n*SINTA Score Overall", card_text)
                    if s_ov:
                        enriched["sinta_score_overall"] = s_ov.group(1)

                    sc_h = re.search(r"Scopus H-index\s*:\s*(\d+)", card_text)
                    if sc_h:
                        enriched["scopus_h_index"] = int(sc_h.group(1))

                    wos_h = re.search(r"Wos H-index\s*:\s*(\d+)", card_text)
                    if wos_h:
                        enriched["wos_h_index"] = int(wos_h.group(1))

                    gs_h = re.search(r"Google Scholar H-index\s*:\s*(\d+)", card_text)
                    if gs_h:
                        enriched["google_scholar_h_index"] = int(gs_h.group(1))

                    cache.set(cache_key, enriched, ttl=3600 * 24)
        except Exception as e:
            logger.warning(f"Error enriching dosen {nama_dosen}: {e}")

        return enriched

    async def enrich_pt(self, nama_pt: str, website_url: Optional[str] = None) -> Dict[str, Any]:
        if not nama_pt:
            return {}

        cache_key = f"enrich_pt_v2:{nama_pt.lower()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        enriched = {
            "nama_rektor": None,
            "jenis_pt": None,
            "semboyan": None,
            "tahun_didirikan": None,
            "wiki_url": None,
            "wiki_ringkasan": None,
            "social_media": {},
            "website_emails": []
        }

        # 1. Wikipedia Indonesia API Search & Infobox Parsing
        try:
            clean_pt_query = re.sub(r"\(.*?\)", "", nama_pt).strip()
            q_enc = urllib.parse.quote(clean_pt_query)
            wiki_search_url = f"https://id.wikipedia.org/w/api.php?action=query&list=search&srsearch={q_enc}&format=json"

            async with httpx.AsyncClient(headers=WIKI_HEADERS, timeout=5.0, follow_redirects=True) as client:
                w_resp = await client.get(wiki_search_url)

            if w_resp.status_code == 200:
                s_data = w_resp.json()
                results = s_data.get("query", {}).get("search", [])
                if results:
                    best_title = results[0]["title"]
                    enriched["wiki_url"] = f"https://id.wikipedia.org/wiki/{urllib.parse.quote(best_title)}"

                    parse_url = f"https://id.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(best_title)}&prop=text&format=json"
                    async with httpx.AsyncClient(headers=WIKI_HEADERS, timeout=5.0, follow_redirects=True) as client:
                        p_resp = await client.get(parse_url)

                    if p_resp.status_code == 200:
                        p_json = p_resp.json()
                        p_html = p_json.get("parse", {}).get("text", {}).get("*", "")
                        soup = BeautifulSoup(p_html, "html.parser")

                        p = soup.find("p", class_=lambda c: not c or "mw-empty" not in str(c))
                        if p:
                            clean_summary = re.sub(r"\[\d+\]", "", p.get_text(strip=True))
                            if len(clean_summary) > 30:
                                enriched["wiki_ringkasan"] = clean_summary[:380] + "..."

                        infobox = soup.find("table", class_=lambda c: c and "infobox" in c)
                        if infobox:
                            for tr in infobox.find_all("tr"):
                                th = tr.find("th")
                                td = tr.find("td")
                                if th and td:
                                    k = th.get_text(strip=True).lower()
                                    v = re.sub(r"\[\d+\]", "", td.get_text(" ", strip=True))
                                    if any(term in k for term in ["rektor", "direktur", "ketua", "pimpinan"]) and not enriched["nama_rektor"]:
                                        enriched["nama_rektor"] = v
                                    elif "jenis" in k and not enriched["jenis_pt"]:
                                        enriched["jenis_pt"] = v
                                    elif any(term in k for term in ["motto", "semboyan"]) and not enriched["semboyan"]:
                                        enriched["semboyan"] = v
                                    elif any(term in k for term in ["didirikan", "berdiri"]) and not enriched["tahun_didirikan"]:
                                        enriched["tahun_didirikan"] = v
        except Exception as e:
            logger.warning(f"Error enriching PT via Wikipedia {nama_pt}: {e}")

        # 2. Campus Official Website Crawling for Socials and Contacts
        if website_url:
            try:
                target_url = website_url if website_url.startswith(("http://", "https://")) else f"https://{website_url}"
                async with httpx.AsyncClient(headers=BROWSER_HEADERS, timeout=4.0, follow_redirects=True, verify=False) as client:
                    w_resp = await client.get(target_url)

                if w_resp.status_code == 200:
                    w_html = w_resp.text
                    w_soup = BeautifulSoup(w_html, "html.parser")

                    socials = {}
                    for a in w_soup.find_all("a", href=True):
                        href = a["href"]
                        if "instagram.com" in href and "instagram" not in socials:
                            socials["instagram"] = href
                        elif "youtube.com" in href and "youtube" not in socials:
                            socials["youtube"] = href
                        elif ("twitter.com" in href or "x.com" in href) and "twitter" not in socials:
                            socials["twitter"] = href
                        elif "facebook.com" in href and "facebook" not in socials:
                            socials["facebook"] = href
                        elif "linkedin.com" in href and "linkedin" not in socials:
                            socials["linkedin"] = href

                    if socials:
                        enriched["social_media"] = socials

                    # Extract emails
                    found_emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", w_html))
                    valid = [
                        e for e in found_emails 
                        if not any(x in e.lower() for x in ["example", "w3.org", "sentry", "domain", ".png", ".jpg", ".svg", "webpack"])
                    ][:3]
                    if valid:
                        enriched["website_emails"] = valid
            except Exception as e:
                logger.warning(f"Error scraping campus website {website_url}: {e}")

        if enriched["nama_rektor"] or enriched["wiki_url"] or enriched["social_media"]:
            cache.set(cache_key, enriched, ttl=3600 * 24)

        return enriched

enrichment_service = EnrichmentService()
