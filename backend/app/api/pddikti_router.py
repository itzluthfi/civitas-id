from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
import urllib.parse
from ..core.pddikti_client import pddikti_client
from ..core.enrichment_service import enrichment_service

router = APIRouter(prefix="/api", tags=["PDDIKTI Live Explorer"])

@router.get("/search/mhs", response_model=List[Dict[str, Any]])
async def search_mahasiswa(q: str = Query(..., min_length=2, description="NIM atau Nama Mahasiswa")):
    results = await pddikti_client.search_mahasiswa(q)
    return results

@router.get("/search/dosen", response_model=List[Dict[str, Any]])
async def search_dosen(q: str = Query(..., min_length=2, description="NIDN atau Nama Dosen")):
    results = await pddikti_client.search_dosen(q)
    return results

@router.get("/search/pt", response_model=List[Dict[str, Any]])
async def search_pt(q: str = Query(..., min_length=2, description="Kode atau Nama Perguruan Tinggi")):
    results = await pddikti_client.search_pt(q)
    return results

@router.get("/detail/mhs/{mhs_id}", response_model=Dict[str, Any])
async def get_detail_mhs(mhs_id: str):
    data = await pddikti_client.get_detail_mahasiswa(mhs_id)
    if not data:
        raise HTTPException(status_code=404, detail="Data mahasiswa tidak ditemukan di PDDIKTI")
    
    nama_mhs = data.get("nama") or ""
    nama_pt = data.get("nama_pt") or ""
    data["rama_search_url"] = f"https://rama.kemdiktisaintek.go.id/search?q={urllib.parse.quote(nama_mhs)}"
    data["sivil_url"] = "https://ijazah.kemdiktisaintek.go.id"
    data["scholar_search_url"] = f"https://scholar.google.com/scholar?q={urllib.parse.quote(nama_mhs + ' ' + nama_pt)}"
    return data

@router.get("/detail/dosen/{dosen_id}", response_model=Dict[str, Any])
async def get_detail_dosen(dosen_id: str):
    data = await pddikti_client.get_detail_dosen(dosen_id)
    if not data:
        raise HTTPException(status_code=404, detail="Data dosen tidak ditemukan di PDDIKTI")
    
    nama_dosen = data.get("nama_dosen") or data.get("nama") or ""
    nama_pt = data.get("nama_pt") or data.get("sinkatan_pt") or ""
    try:
        enriched = await enrichment_service.enrich_dosen(nama_dosen, nama_pt)
        if enriched:
            data.update(enriched)
    except Exception:
        pass

    return data

@router.get("/detail/pt/{pt_id}", response_model=Dict[str, Any])
async def get_detail_pt(pt_id: str):
    data = await pddikti_client.get_detail_pt(pt_id)
    if not data:
        raise HTTPException(status_code=404, detail="Data perguruan tinggi tidak ditemukan di PDDIKTI")
    
    nama_pt = data.get("nama_pt") or data.get("nm_lemb") or ""
    website = data.get("website") or ""
    try:
        enriched = await enrichment_service.enrich_pt(nama_pt, website)
        if enriched:
            data.update(enriched)
    except Exception:
        pass

    return data
