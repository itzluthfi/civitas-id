import asyncio
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from .cache import cache
from .config import settings

logger = logging.getLogger("civitas.pddikti")

class PDDIKTIClient:
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Initializes the resident Chromium browser and warms up connection."""
        async with self._lock:
            if self._page is not None:
                return
            try:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                self._page = await self._browser.new_page()
                await self._page.goto(settings.PDDIKTI_BASE_URL, wait_until="domcontentloaded", timeout=30000)
                logger.info("PDDIKTI resident browser session established.")
            except Exception as e:
                logger.error(f"Failed to start resident browser: {e}")
                await self.stop()
                raise e

    async def stop(self):
        """Cleanly releases browser resources."""
        async with self._lock:
            if self._page:
                try:
                    await self._page.close()
                except Exception:
                    pass
                self._page = None
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None

    async def _ensure_page(self) -> Page:
        if self._page is None:
            await self.start()
        return self._page

    def sanitize_query(self, query: str) -> str:
        """Sanitizes NIM (removing dots/spaces) or cleans name string."""
        cleaned = query.strip()
        # If looks like a dotted NIM (e.g. 06.2023.1.07722), strip dots
        parts = cleaned.split('.')
        if len(parts) >= 3 and all(p.isdigit() for p in parts):
            return "".join(parts)
        return cleaned

    async def search_mahasiswa(self, query: str) -> List[Dict[str, Any]]:
        clean_q = self.sanitize_query(query)
        cache_key = f"mhs_search:{clean_q.lower()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        encoded_q = urllib.parse.quote(clean_q)
        endpoint = f"/api/pencarian/mhs/{encoded_q}"

        async with self._lock:
            page = await self._ensure_page()
            try:
                data = await page.evaluate(f"""async () => {{
                    const res = await fetch('{endpoint}');
                    if (!res.ok) return [];
                    const json = await res.json();
                    return json.data || json;
                }}""")
            except Exception as e:
                logger.warning(f"Browser fetch failed, re-initializing session: {e}")
                await self.stop()
                page = await self._ensure_page()
                data = await page.evaluate(f"""async () => {{
                    const res = await fetch('{endpoint}');
                    if (!res.ok) return [];
                    const json = await res.json();
                    return json.data || json;
                }}""")

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", data.get("mhs", []))

        if items:
            cache.set(cache_key, items, ttl=settings.CACHE_TTL_SECONDS)
        return items

    async def search_dosen(self, query: str) -> List[Dict[str, Any]]:
        clean_q = self.sanitize_query(query)
        cache_key = f"dosen_search:{clean_q.lower()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        encoded_q = urllib.parse.quote(clean_q)
        endpoint = f"/api/pencarian/dosen/{encoded_q}"

        async with self._lock:
            page = await self._ensure_page()
            data = await page.evaluate(f"""async () => {{
                const res = await fetch('{endpoint}');
                if (!res.ok) return [];
                const json = await res.json();
                return json.data || json;
            }}""")

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", data.get("dosen", []))

        if items:
            cache.set(cache_key, items, ttl=settings.CACHE_TTL_SECONDS)
        return items

    async def get_detail_mahasiswa(self, mhs_id: str) -> Dict[str, Any]:
        cache_key = f"mhs_detail:{mhs_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        async with self._lock:
            page = await self._ensure_page()
            res = await page.evaluate(f"""async (idVal) => {{
                const res = await fetch('/api/detail/mhs', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ id: idVal }})
                }});
                if (!res.ok) return null;
                const json = await res.json();
                return json.data || json;
            }}""", mhs_id)

        if res and isinstance(res, dict):
            # Compute verification URL
            res["verify_url"] = f"{settings.PDDIKTI_BASE_URL}/detail-mahasiswa/{mhs_id}"
            cache.set(cache_key, res, ttl=settings.CACHE_TTL_SECONDS)
            return res
        return {}

    async def get_detail_dosen(self, dosen_id: str) -> Dict[str, Any]:
        cache_key = f"dosen_detail:{dosen_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        async with self._lock:
            page = await self._ensure_page()
            js = """async (idVal) => {
                const postSafe = async (url) => {
                    try {
                        const r = await fetch(url, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ id: idVal })
                        });
                        if (r.ok) {
                            const j = await r.json();
                            return j.data !== undefined ? j.data : j;
                        }
                    } catch(e) {}
                    return null;
                };

                const [profile, study, teaching, penelitian, pengabdian, karya, paten] = await Promise.all([
                    postSafe('/api/dosen/profile'),
                    postSafe('/api/dosen/study-history'),
                    postSafe('/api/dosen/teaching-history'),
                    postSafe('/api/dosen/portofolio/penelitian'),
                    postSafe('/api/dosen/portofolio/pengabdian'),
                    postSafe('/api/dosen/portofolio/karya'),
                    postSafe('/api/dosen/portofolio/paten')
                ]);

                if (!profile) return null;
                const result = { ...(typeof profile === 'object' ? profile : {}) };
                result.study_history = Array.isArray(study) ? study : [];
                result.teaching_history = Array.isArray(teaching) ? teaching : [];
                result.portofolio = {
                    penelitian: Array.isArray(penelitian) ? penelitian : [],
                    pengabdian: Array.isArray(pengabdian) ? pengabdian : [],
                    karya: Array.isArray(karya) ? karya : [],
                    paten: Array.isArray(paten) ? paten : []
                };
                return result;
            }"""
            res = await page.evaluate(js, dosen_id)

        if res and isinstance(res, dict):
            res["verify_url"] = f"{settings.PDDIKTI_BASE_URL}/detail-dosen/{dosen_id}"
            cache.set(cache_key, res, ttl=settings.CACHE_TTL_SECONDS)
            return res
        return {}

    async def search_pt(self, query: str) -> List[Dict[str, Any]]:
        clean_q = self.sanitize_query(query)
        cache_key = f"pt_search:{clean_q.lower()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        encoded_q = urllib.parse.quote(clean_q)
        endpoint = f"/api/pencarian/pt/{encoded_q}"

        async with self._lock:
            page = await self._ensure_page()
            data = await page.evaluate(f"""async () => {{
                const res = await fetch('{endpoint}');
                if (!res.ok) return [];
                const json = await res.json();
                return json.data || json;
            }}""")

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", data.get("pt", []))

        if items:
            cache.set(cache_key, items, ttl=settings.CACHE_TTL_SECONDS)
        return items

    async def get_detail_pt(self, pt_id: str) -> Dict[str, Any]:
        cache_key = f"pt_detail:{pt_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        async with self._lock:
            page = await self._ensure_page()
            js = """async (idVal) => {
                const getSafe = async (url) => {
                    try {
                        const r = await fetch(url);
                        if (r.ok) {
                            const j = await r.json();
                            return j.data !== undefined ? j.data : j;
                        }
                    } catch(e) {}
                    return null;
                };

                const [detail, rasio, mhsStat, costRange, waktuStudi, sarpras, nameHistories] = await Promise.all([
                    getSafe('/api/pt/detail/' + idVal),
                    getSafe('/api/pt/rasio/' + idVal),
                    getSafe('/api/pt/mahasiswa/' + idVal),
                    getSafe('/api/pt/cost-range/' + idVal),
                    getSafe('/api/pt/waktu-studi/' + idVal),
                    getSafe('/api/pt/sarpras-file-name/' + idVal),
                    getSafe('/api/pt/name-histories/' + idVal)
                ]);

                if (!detail) return null;

                const out = { ...(typeof detail === 'object' ? detail : {}) };
                if (rasio) out.rasio = rasio;
                if (mhsStat) out.mahasiswa_stat = mhsStat;
                out.biaya_kuliah = costRange ? (costRange.range_biaya_kuliah || costRange) : null;
                out.waktu_studi = Array.isArray(waktuStudi) ? waktuStudi : [];
                out.sarpras = Array.isArray(sarpras) ? sarpras : [];
                out.name_histories = Array.isArray(nameHistories) ? nameHistories : [];

                let semester = (rasio && rasio.semester) ? String(rasio.semester) : '20251';
                let prodi = await getSafe('/api/pt/prodi/' + idVal + '/' + semester);
                if (!prodi || (Array.isArray(prodi) && prodi.length === 0)) {
                    prodi = await getSafe('/api/pt/prodi/' + idVal + '/20241') || await getSafe('/api/pt/prodi/' + idVal + '/20242');
                }
                out.prodi_list = Array.isArray(prodi) ? prodi : [];
                out.prodi_semester = semester;

                return out;
            }"""
            res = await page.evaluate(js, pt_id)

        if res and isinstance(res, dict):
            res["verify_url"] = f"{settings.PDDIKTI_BASE_URL}/detail-pt/{pt_id}"
            cache.set(cache_key, res, ttl=settings.CACHE_TTL_SECONDS)
            return res
        return {}

pddikti_client = PDDIKTIClient()

