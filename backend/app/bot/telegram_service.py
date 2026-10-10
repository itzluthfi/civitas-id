import asyncio
import logging
from typing import Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from ..core.config import settings
from ..core.pddikti_client import pddikti_client
from ..core import document_generator

logger = logging.getLogger("civitas.bot")

dp = Dispatcher()
bot_instance: Optional[Bot] = None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "CivitasID Bot — Layanan Verifikasi & Generator Dokumen Akademik PDDIKTI.\n\n"
        "Perintah yang tersedia:\n"
        "• /cari <NIM / Nama Mahasiswa>\n"
        "• /dosen <NIDN / Nama Dosen>\n"
        "• /help — Menampilkan panduan penggunaan",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "*Panduan Penggunaan CivitasID Bot:*\n\n"
        "1. Ketik `/cari <NIM atau Nama>` (Contoh: `/cari 062023107722` atau `/cari Hamid Mahmudin`).\n"
        "2. Pilih mahasiswa dari daftar yang ditemukan.\n"
        "3. Tekan tombol dokumen (SKMA Bilingual, SKMA Standar, KTM, atau Transkrip) untuk mengunduh PDF secara instan.",
        parse_mode="Markdown"
    )

@dp.message(Command("cari"))
async def cmd_cari(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Format salah. Gunakan: `/cari <NIM atau Nama>`", parse_mode="Markdown")
        return

    query = parts[1].strip()
    status_msg = await message.answer(f"Mencari data '{query}' di basis data PDDIKTI Kemdiktisaintek...")

    try:
        results = await pddikti_client.search_mahasiswa(query)
        if not results:
            await status_msg.edit_text(f"Tidak ada data mahasiswa ditemukan untuk '{query}'.")
            return

        # Show up to 5 top results
        top_results = results[:5]
        text_lines = ["*Hasil Pencarian PDDIKTI:*\n"]
        buttons = []

        for idx, item in enumerate(top_results, 1):
            nama = item.get("nama", "N/A")
            nim = item.get("nim", "N/A")
            prodi = item.get("nama_prodi", "N/A")
            pt = item.get("sinkatan_pt") or item.get("nama_pt", "N/A")
            mhs_id = item.get("id")

            text_lines.append(f"{idx}. *{nama}* ({nim})\n   _{prodi} — {pt}_")
            buttons.append([
                InlineKeyboardButton(
                    text=f"Pilih: {nama[:20]} ({nim})",
                    callback_data=f"sel_mhs:{mhs_id}"
                )
            ])

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await status_msg.edit_text("\n".join(text_lines), reply_markup=kb, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error during bot search: {e}")
        await status_msg.edit_text("Terjadi kesalahan saat menghubungi server PDDIKTI.")

@dp.callback_query(F.data.startswith("sel_mhs:"))
async def on_select_mhs(callback: types.CallbackQuery):
    mhs_id = callback.data.split(":", 1)[1]
    await callback.answer("Memuat rincian data...")

    try:
        detail = await pddikti_client.get_detail_mahasiswa(mhs_id)
        if not detail:
            await callback.message.answer("Gagal memuat detail mahasiswa.")
            return

        nama = detail.get("nama", "N/A")
        nim = detail.get("nim", "N/A")
        pt = detail.get("nama_pt", "N/A")
        prodi = detail.get("prodi", "N/A")
        jenjang = detail.get("jenjang", "Sarjana")
        status = detail.get("status_saat_ini", "Aktif")
        verify_url = detail.get("verify_url", "https://pddikti.kemdiktisaintek.go.id")

        card_text = (
            f"*PROFIL MAHASISWA TERVERIFIKASI*\n\n"
            f"• *Nama*: {nama}\n"
            f"• *NIM*: {nim}\n"
            f"• *Perguruan Tinggi*: {pt}\n"
            f"• *Program Studi*: {prodi} ({jenjang})\n"
            f"• *Status Keaktifan*: {status}\n\n"
            f"Pilih dokumen yang ingin diunduh langsung:"
        )

        buttons = [
            [
                InlineKeyboardButton(text="SKMA Bilingual (PDF)", callback_data=f"doc:skma_bilingual:{mhs_id}"),
                InlineKeyboardButton(text="SKMA Standar (PDF)", callback_data=f"doc:skma_id:{mhs_id}")
            ],
            [
                InlineKeyboardButton(text="KTM Digital (PDF)", callback_data=f"doc:ktm:{mhs_id}"),
                InlineKeyboardButton(text="Transkrip Akademik (PDF)", callback_data=f"doc:transcript:{mhs_id}")
            ],
            [
                InlineKeyboardButton(text="Verifikasi PDDIKTI Resmi", url=verify_url)
            ]
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.answer(card_text, reply_markup=kb, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error fetching student detail: {e}")
        await callback.message.answer("Gagal mengambil data dari server.")

@dp.callback_query(F.data.startswith("doc:"))
async def on_download_doc(callback: types.CallbackQuery):
    _, template_type, mhs_id = callback.data.split(":", 2)
    await callback.answer("Memproses pembuatan dokumen PDF...")
    status_msg = await callback.message.answer("Sedang merender dokumen PDF resmi...")

    try:
        detail = await pddikti_client.get_detail_mahasiswa(mhs_id)
        if not detail:
            await status_msg.edit_text("Data mahasiswa tidak valid.")
            return

        nim = detail.get("nim", "mhs")
        if template_type == "skma_bilingual":
            pdf_bytes = await document_generator.generate_skma_bilingual(detail, output_format="pdf")
            filename = f"SKMA_Bilingual_{nim}.pdf"
            caption = f"Surat Keterangan Mahasiswa Aktif (Bilingual) - {detail.get('nama')}"
        elif template_type == "skma_id":
            pdf_bytes = await document_generator.generate_skma_standard(detail, output_format="pdf")
            filename = f"SKMA_Standar_{nim}.pdf"
            caption = f"Surat Keterangan Mahasiswa Aktif (Standar) - {detail.get('nama')}"
        elif template_type == "ktm":
            pdf_bytes = await document_generator.generate_ktm_digital(detail, output_format="pdf")
            filename = f"KTM_Digital_{nim}.pdf"
            caption = f"Kartu Tanda Mahasiswa Digital - {detail.get('nama')}"
        elif template_type == "transcript":
            pdf_bytes = await document_generator.generate_transcript(detail, output_format="pdf")
            filename = f"Transkrip_Akademik_{nim}.pdf"
            caption = f"Transkrip Akademik Sementara - {detail.get('nama')}"
        else:
            await status_msg.edit_text("Template tidak dikenali.")
            return

        file = BufferedInputFile(pdf_bytes, filename=filename)
        await callback.message.answer_document(document=file, caption=caption)
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Error rendering document in bot: {e}")
        await status_msg.edit_text("Gagal memproses dokumen.")

async def start_bot(token: Optional[str] = None):
    bot_token = token or settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.warning("[Telegram Bot] TELEGRAM_BOT_TOKEN tidak dikonfigurasi. Bot tidak diaktifkan.")
        return

    global bot_instance
    bot_instance = Bot(token=bot_token)
    logger.info("[Telegram Bot] Memulai service bot Telegram...")
    await dp.start_polling(bot_instance)

if __name__ == "__main__":
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else settings.TELEGRAM_BOT_TOKEN
    if not token:
        print("Penggunaan: python -m app.bot.telegram_service <TELEGRAM_BOT_TOKEN> atau set di .env")
        sys.exit(1)
    asyncio.run(start_bot(token))
