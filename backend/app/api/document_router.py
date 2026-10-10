from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Dict, Any, Literal
from ..core import document_generator

router = APIRouter(prefix="/api/generate", tags=["Academic Document Generator"])

class GenerateRequest(BaseModel):
    template: Literal["skma_id", "skma_bilingual", "ktm", "transcript"]
    student_data: Dict[str, Any]

@router.post("/pdf")
async def generate_pdf(req: GenerateRequest):
    data = req.student_data
    if req.template == "skma_id":
        content = await document_generator.generate_skma_standard(data, output_format="pdf")
        filename = f"SKMA_{data.get('nim', 'document')}.pdf"
    elif req.template == "skma_bilingual":
        content = await document_generator.generate_skma_bilingual(data, output_format="pdf")
        filename = f"SKMA_Bilingual_{data.get('nim', 'document')}.pdf"
    elif req.template == "ktm":
        content = await document_generator.generate_ktm_digital(data, output_format="pdf")
        filename = f"KTM_Digital_{data.get('nim', 'document')}.pdf"
    elif req.template == "transcript":
        content = await document_generator.generate_transcript(data, output_format="pdf")
        filename = f"Transkrip_{data.get('nim', 'document')}.pdf"
    else:
        raise HTTPException(status_code=400, detail="Template tidak dikenali")

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.post("/png")
async def generate_png(req: GenerateRequest):
    data = req.student_data
    if req.template == "skma_id":
        content = await document_generator.generate_skma_standard(data, output_format="png")
        filename = f"SKMA_{data.get('nim', 'document')}.png"
    elif req.template == "skma_bilingual":
        content = await document_generator.generate_skma_bilingual(data, output_format="png")
        filename = f"SKMA_Bilingual_{data.get('nim', 'document')}.png"
    elif req.template == "ktm":
        content = await document_generator.generate_ktm_digital(data, output_format="png")
        filename = f"KTM_Digital_{data.get('nim', 'document')}.png"
    elif req.template == "transcript":
        content = await document_generator.generate_transcript(data, output_format="png")
        filename = f"Transkrip_{data.get('nim', 'document')}.png"
    else:
        raise HTTPException(status_code=400, detail="Template tidak dikenali")

    return Response(
        content=content,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
