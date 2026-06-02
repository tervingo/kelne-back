import os
import traceback
from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from db import words_collection, roots_collection

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
    pdf.cell(0, 14, 'Kelnen', align='C', new_x='LMARGIN', new_y='NEXT')
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


# ── Roots PDF ─────────────────────────────────────────────────────────────────

ROOTS_PDF_FILENAME = 'kelnen_konor.pdf'
DROPBOX_ROOTS_DEST = f'/Lenguas/Kelne/{ROOTS_PDF_FILENAME}'

_DEGREES   = ['normal', 'fuerte', 'largo']
_BASE_COLS = [
    {'type': 'nombre', 'voice': None,     'conjugation': None,        'label': 'nombre'},
    {'type': 'verbo',  'voice': 'activa', 'conjugation': 'agentiva',  'label': 'activa·ag'},
    {'type': 'verbo',  'voice': 'activa', 'conjugation': 'receptiva', 'label': 'activa·rec'},
    {'type': 'verbo',  'voice': 'media',  'conjugation': 'agentiva',  'label': 'media·ag'},
    {'type': 'verbo',  'voice': 'media',  'conjugation': 'receptiva', 'label': 'media·rec'},
]


async def _fetch_roots() -> list[dict]:
    roots = []
    async for r in roots_collection.find({}):
        r['_id'] = str(r['_id'])
        roots.append(r)

    all_kelne: set[str] = set()
    for root in roots:
        for base in root.get('bases', []):
            for ref in base.get('derivedWords', []):
                if isinstance(ref, dict) and ref.get('kelne'):
                    all_kelne.add(ref['kelne'])

    words_map: dict[tuple, dict] = {}
    if all_kelne:
        async for w in words_collection.find(
            {'kelne': {'$in': list(all_kelne)}},
            {'_id': 0, 'kelne': 1, 'cat': 1, 'trad': 1},
        ):
            words_map[(w['kelne'], w['cat'])] = w

    for root in roots:
        for base in root.get('bases', []):
            populated = []
            for ref in base.get('derivedWords', []):
                if isinstance(ref, dict):
                    word = words_map.get((ref.get('kelne', ''), ref.get('cat', '')))
                    if word:
                        populated.append(word)
            base['derivedWords'] = populated

    return roots


def _build_roots_pdf(roots: list[dict]) -> bytes:
    reg  = _find(_FONT_CANDIDATES)
    bold = _find(_BOLD_CANDIDATES)

    pdf = FPDF(orientation='L')
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False)

    if reg:
        pdf.add_font('Main', style='',  fname=reg)
        pdf.add_font('Main', style='B', fname=bold or reg)
        F = 'Main'
    else:
        F = 'Helvetica'

    W_LABEL = 20
    W_COL   = 49
    H_TRANS = 4.5
    H_WORD  = 3.5
    V_PAD   = 1.5
    H_HDR   = 6

    sorted_roots = sorted(roots, key=lambda r: r.get('root', '').lower())

    # Pre-create one link object per root
    # Página 1 = índice, página 2+i = raíz i — pre-asignamos destino
    links = []
    for i in range(len(sorted_roots)):
        lnk = pdf.add_link()
        pdf.set_link(lnk, page=2 + i, y=0)
        links.append(lnk)

    # ── Índice ────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font(F, 'B', 22)
    pdf.cell(0, 11, 'Kelnen konosalto', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)
    pdf.set_font(F, 'B', 13)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 7, 'Índice de raíces', new_x='LMARGIN', new_y='NEXT')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    N_COLS     = 4
    COL_W      = pdf.epw / N_COLS
    ENTRY_H    = 6.5
    y_toc      = pdf.get_y()
    max_rows   = int((pdf.eph - (y_toc - pdf.t_margin)) / ENTRY_H)

    for i, (root, link) in enumerate(zip(sorted_roots, links)):
        col = i // max_rows
        row = i % max_rows
        if col >= N_COLS:
            break   # más de N_COLS*max_rows raíces: se cortaría (raro)
        xi = pdf.l_margin + col * COL_W
        yi = y_toc + row * ENTRY_H
        pdf.set_xy(xi, yi)
        pdf.set_font(F, 'B', 9)
        pdf.set_text_color(40, 80, 180)
        pdf.cell(COL_W, ENTRY_H, root.get('root', '').upper(), link=link)
        pdf.set_text_color(0, 0, 0)

    # ── Páginas de raíces ─────────────────────────────────────────────────────

    def find_base(bases, degree, col):
        for b in bases:
            if (b.get('degree') == degree and
                    b.get('type') == col['type'] and
                    b.get('voice') == col['voice'] and
                    b.get('conjugation') == col['conjugation']):
                return b
        return None

    def draw_root(root: dict):
        bases = root.get('bases', [])
        notes = root.get('notes', '') or ''

        pdf.set_font(F, 'B', 18)
        pdf.cell(0, 9, root.get('root', '').upper(), new_x='LMARGIN', new_y='NEXT')
        if notes:
            pdf.set_font(F, '', 9)
            pdf.set_text_color(130, 130, 130)
            pdf.cell(0, 5, notes, new_x='LMARGIN', new_y='NEXT')
            pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

        x_label = pdf.l_margin
        x_cols  = [x_label + W_LABEL + i * W_COL for i in range(len(_BASE_COLS))]
        y_hdr   = pdf.get_y()

        # header row
        pdf.set_fill_color(60, 60, 60)
        pdf.set_font(F, 'B', 7.5)
        pdf.set_text_color(210, 210, 210)
        pdf.rect(x_label, y_hdr, W_LABEL, H_HDR, style='FD')
        for xi, col in zip(x_cols, _BASE_COLS):
            pdf.rect(xi, y_hdr, W_COL, H_HDR, style='FD')
            pdf.set_xy(xi, y_hdr)
            pdf.cell(W_COL, H_HDR, col['label'], align='C')
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(x_label, y_hdr + H_HDR)

        for degree in _DEGREES:
            row_bases = [find_base(bases, degree, col) for col in _BASE_COLS]
            max_words = max(
                (min(len(b.get('derivedWords', [])), 3) for b in row_bases if b),
                default=0,
            )
            row_h = V_PAD + H_TRANS + max_words * H_WORD + V_PAD
            y0    = pdf.get_y()

            pdf.set_fill_color(45, 45, 45)
            pdf.rect(x_label, y0, W_LABEL, row_h, style='F')
            pdf.rect(x_label, y0, W_LABEL, row_h)
            pdf.set_font(F, 'B', 8)
            pdf.set_text_color(180, 180, 180)
            pdf.set_xy(x_label, y0 + (row_h - 4) / 2)
            pdf.cell(W_LABEL, 4, degree, align='C')
            pdf.set_text_color(0, 0, 0)

            for xi, base in zip(x_cols, row_bases):
                pdf.rect(xi, y0, W_COL, row_h)
                if base:
                    translation = base.get('translation', '')
                    words = base.get('derivedWords', [])[:3]
                    pdf.set_font(F, 'B', 8)
                    pdf.set_xy(xi + 0.5, y0 + V_PAD)
                    pdf.cell(W_COL - 1, H_TRANS, translation[:28], align='C')
                    pdf.set_font(F, '', 7)
                    pdf.set_text_color(100, 100, 100)
                    for j, w in enumerate(words):
                        text = f"{w.get('kelne', '')} = {w.get('trad', '')}"
                        pdf.set_xy(xi + 0.5, y0 + V_PAD + H_TRANS + j * H_WORD)
                        pdf.cell(W_COL - 1, H_WORD, text[:32], align='C')
                    pdf.set_text_color(0, 0, 0)

            pdf.set_xy(pdf.l_margin, y0 + row_h)

    for i, root in enumerate(sorted_roots):
        pdf.add_page()
        draw_root(root)

    return bytes(pdf.output())


# ── Dropbox upload ─────────────────────────────────────────────────────────────

def _upload_dropbox(pdf_bytes: bytes, dest: str) -> bool:
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
        dest,
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

        pdf_bytes   = _build_pdf(words)
        roots       = await _fetch_roots()
        roots_bytes = _build_roots_pdf(roots)

        dropbox_status = 'skipped'
        try:
            ok1 = _upload_dropbox(pdf_bytes,   DROPBOX_DEST)
            ok2 = _upload_dropbox(roots_bytes, DROPBOX_ROOTS_DEST)
            dropbox_status = 'ok' if (ok1 and ok2) else 'skipped'
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
