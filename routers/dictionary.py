import os
import traceback
from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from db import words_collection

router = APIRouter(prefix='/api/dictionary', tags=['dictionary'])

PDF_FILENAME = 'es-ke-taulseberjo.pdf'
DROPBOX_DEST = f'/Lenguas/Kelne/{PDF_FILENAME}'
APP_KEY      = 'gr6xmm34rgxsy6x'

# DejaVuSans covers the full Latin Extended range (ý, ý, etc.)
_FONT_CANDIDATES = [
    # Linux (Render)
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf',
    '/usr/share/fonts/TTF/DejaVuSans.ttf',
    # Windows
    'C:/Windows/Fonts/calibri.ttf',
    'C:/Windows/Fonts/arial.ttf',
    'C:/Windows/Fonts/segoeui.ttf',
]
_BOLD_CANDIDATES = [
    # Linux (Render)
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf',
    '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
    # Windows
    'C:/Windows/Fonts/calibrib.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
    'C:/Windows/Fonts/segoeuib.ttf',
]

def _find(paths: list[str]) -> str | None:
    return next((p for p in paths if os.path.exists(p)), None)


def _tag(w: dict) -> str:
    parts = [w.get('cat', '')]
    if w.get('clase'):
        parts.append(w['clase'])
    raiz = w.get('raiz')
    if raiz:
        if isinstance(raiz, list):
            parts.append('√' + '+'.join(r.upper() for r in raiz))
        else:
            parts.append('√' + raiz.upper())
    return '·'.join(filter(None, parts))


def _build_pdf(words: list[dict]) -> bytes:
    reg  = _find(_FONT_CANDIDATES)
    bold = _find(_BOLD_CANDIDATES)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(22, 22, 22)

    if reg:
        pdf.add_font('Main', style='',  fname=reg)
        pdf.add_font('Main', style='B', fname=bold or reg)
        F = 'Main'
    else:
        F = 'Helvetica'

    # ── Portada ──────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font(F, 'B', 28)
    pdf.cell(0, 14, 'Kelnena', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font(F, '', 18)
    pdf.cell(0, 10, 'Taulseberjo', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(10)
    pdf.set_font(F, '', 12)
    pdf.cell(0, 8, 'Kelne → Español  /  Español → Kelne', align='C',
             new_x='LMARGIN', new_y='NEXT')

    # ── Helpers ──────────────────────────────────────────────────────────
    def section_title(title: str):
        pdf.add_page()
        pdf.set_font(F, 'B', 15)
        pdf.set_fill_color(55, 55, 55)
        pdf.set_text_color(220, 220, 220)
        pdf.cell(0, 10, title, new_x='LMARGIN', new_y='NEXT', fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    last_letter = [None]

    def letter_break(first: str):
        if first != last_letter[0]:
            last_letter[0] = first
            pdf.ln(2)
            pdf.set_font(F, 'B', 12)
            pdf.set_text_color(160, 100, 40)
            pdf.cell(0, 6, first.upper(), new_x='LMARGIN', new_y='NEXT')
            pdf.set_text_color(0, 0, 0)

    def entry_ke(w: dict):
        kelne = w.get('kelne', '')
        trad  = w.get('trad',  '')
        tag   = _tag(w)
        letter_break(kelne[0].lower() if kelne else '?')
        pdf.set_font(F, 'B', 10)
        pdf.write(5.5, kelne + '  ')
        if tag:
            pdf.set_font(F, '', 8.5)
            pdf.set_text_color(130, 85, 30)
            pdf.write(5.5, f'[{tag}]  ')
            pdf.set_text_color(0, 0, 0)
        pdf.set_font(F, '', 10)
        pdf.write(5.5, trad)
        pdf.ln(5.5)

    def entry_ek(w: dict):
        kelne = w.get('kelne', '')
        trad  = w.get('trad',  '')
        tag   = _tag(w)
        letter_break(trad[0].lower() if trad else '?')
        pdf.set_font(F, 'B', 10)
        pdf.write(5.5, trad + '  ')
        pdf.set_font(F, '', 10)
        pdf.set_text_color(80, 80, 80)
        pdf.write(5.5, '→  ')
        pdf.set_text_color(0, 0, 0)
        pdf.write(5.5, kelne + '  ')
        if tag:
            pdf.set_font(F, '', 8.5)
            pdf.set_text_color(130, 85, 30)
            pdf.write(5.5, f'[{tag}]')
            pdf.set_text_color(0, 0, 0)
        pdf.ln(5.5)

    # ── Sección 1: Kelne → Español ───────────────────────────────────────
    last_letter[0] = None
    section_title('Kelne → Español')
    for w in sorted(words, key=lambda x: x.get('kelne', '').lower()):
        entry_ke(w)

    # ── Sección 2: Español → Kelne ───────────────────────────────────────
    last_letter[0] = None
    section_title('Español → Kelne')
    for w in sorted(words, key=lambda x: x.get('trad', '').lower()):
        entry_ek(w)

    return bytes(pdf.output())


def _upload_dropbox(pdf_bytes: bytes) -> bool:
    import dropbox as dbx_lib
    refresh_token = os.getenv('DROPBOX_REFRESH_TOKEN')
    app_secret    = os.getenv('DROPBOX_APP_SECRET')
    if not refresh_token or not app_secret:
        print('DROPBOX_REFRESH_TOKEN o DROPBOX_APP_SECRET no encontrados en entorno')
        return False
    dbx = dbx_lib.Dropbox(
        oauth2_refresh_token=refresh_token,
        app_key=APP_KEY,
        app_secret=app_secret,
    )
    meta = dbx.files_upload(
        pdf_bytes,
        DROPBOX_DEST,
        mode=dbx_lib.files.WriteMode.overwrite,
    )
    print(f'Subido a Dropbox: {meta.path_display}  ({meta.size} bytes)')
    return True


@router.get('/pdf')
async def generate_dictionary():
    try:
        words = []
        async for w in words_collection.find({}, {'_id': 0, 'kelne': 1, 'trad': 1, 'cat': 1, 'clase': 1, 'raiz': 1}):
            words.append(w)

        pdf_bytes = _build_pdf(words)

        dropbox_status = 'skipped'
        try:
            uploaded = _upload_dropbox(pdf_bytes)
            dropbox_status = 'ok' if uploaded else 'skipped'
        except Exception as e:
            dropbox_status = f'error: {e}'
            print(f'Dropbox upload falló: {e}')

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type='application/pdf',
            headers={
                'Content-Disposition':   f'attachment; filename="{PDF_FILENAME}"',
                'X-Dropbox-Status':      dropbox_status,
                'Access-Control-Expose-Headers': 'X-Dropbox-Status',
            },
        )
    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        raise HTTPException(status_code=500, detail=f'{type(e).__name__}: {e}')
