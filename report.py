"""
report.py — Generates Word (.docx) and PDF (.pdf) reports for a single sample.
Template faithfully replicates the official SSP lab test report layout:
  - Top-left SSP company logo
  - Centered underlined title: "TEST REPORT"
  - Metadata block:
      TEST REPORT NO. <sample_id>
      DATE OF REPORT ISSUE: <DD-MM-YYYY>
      TEST REPORT ISSUED TO: M/s <client>
      PRODUCT: <name>
  - 4-column Table: SR. NO. | TEST PARAMETER | RESULT | Method Used
  - Signature Footer: "Analyst Signature" (left) and "Authorised Signatory" (right)
"""

import os
import tempfile
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from database import get_sample, get_sample_results


def _format_date(date_str):
    """Format YYYY-MM-DD into DD-MM-YYYY if valid, otherwise return raw string."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return date_str


def _format_issued_to(received_from):
    """Prefix with 'M/s ' if not already present."""
    if not received_from:
        return ""
    rf = str(received_from).strip()
    if not rf.lower().startswith("m/s"):
        return f"M/s {rf}"
    return rf


def _set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    """Set cell padding in dxa (1 pt = 20 dxa)."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for margin, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{margin}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_cell_borders(cell, sz="4", val="single", color="000000"):
    """Set clean thin solid borders on all 4 sides of a cell."""
    tcPr = cell._element.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    for edge in ['top', 'bottom', 'left', 'right']:
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), val)
        el.set(qn('w:sz'), sz)
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), color)
        borders.append(el)
    tcPr.append(borders)


# ==============================================================================
# DOCX GENERATOR
# ==============================================================================

def _setup_page(section):
    """Configure A4 page dimensions and margins for a document section."""
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.4)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.3)
    section.right_margin = Cm(2.3)


def _build_sample_section(doc, sample, results):
    """
    Build one sample's report section into an existing Document.
    Adds: logo, title, metadata, results table, and signature footer.
    Reused by both single-sample and combined-report generators.
    """
    # 1. Top-Left Logo
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'logo.png')
    if os.path.exists(logo_path):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_logo.paragraph_format.space_before = Pt(0)
        p_logo.paragraph_format.space_after = Pt(8)
        run_logo = p_logo.add_run()
        run_logo.add_picture(logo_path, width=Cm(2.36))

    # 2. Title: TEST REPORT (Arial Bold 15pt, Centered, Underlined)
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(18)
    r_title = p_title.add_run("TEST REPORT")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(15)
    r_title.bold = True
    r_title.underline = True
    r_title.font.color.rgb = RGBColor(0, 0, 0)

    # 3. Metadata Lines (Calibri Bold 11pt, clean line spacing)
    formatted_date = _format_date(sample['date_received'])
    issued_to = _format_issued_to(sample['received_from'])

    metadata_lines = [
        f"TEST REPORT NO. {sample['sample_id']}",
        f"DATE OF REPORT ISSUE: {formatted_date}",
        f"TEST REPORT ISSUED TO: {issued_to}",
        f"PRODUCT: {sample['name']}"
    ]

    for line in metadata_lines:
        p_meta = doc.add_paragraph()
        p_meta.paragraph_format.space_before = Pt(0)
        p_meta.paragraph_format.space_after = Pt(7)
        p_meta.paragraph_format.line_spacing = 1.15
        r_meta = p_meta.add_run(line)
        r_meta.font.name = "Calibri"
        r_meta.font.size = Pt(11)
        r_meta.bold = True
        r_meta.font.color.rgb = RGBColor(0, 0, 0)

    # Small spacer before table
    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(4)
    p_spacer.paragraph_format.space_after = Pt(0)

    # 4. Table: 4 Columns
    # Widths: 1.7cm, 5.3cm, 4.2cm, 4.2cm (Total 15.4 cm)
    col_widths = [Cm(1.7), Cm(5.3), Cm(4.2), Cm(4.2)]
    num_rows = 1 + (len(results) if results else 1)
    table = doc.add_table(rows=num_rows, cols=4)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header Row
    headers = [
        ("SR. NO.", WD_ALIGN_PARAGRAPH.CENTER, "Calibri", 11),
        ("TEST PARAMETER", WD_ALIGN_PARAGRAPH.CENTER, "Arial", 11),
        ("RESULT", WD_ALIGN_PARAGRAPH.CENTER, "Arial", 11),
        ("Method Used", WD_ALIGN_PARAGRAPH.CENTER, "Arial", 11)
    ]

    header_row = table.rows[0]
    trPr = header_row._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:tblHeader'))
    trPr.append(OxmlElement('w:cantSplit'))

    for j, (h_text, align, font_name, font_size) in enumerate(headers):
        cell = header_row.cells[j]
        cell.width = col_widths[j]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _set_cell_margins(cell, top=100, bottom=100, left=80, right=80)
        _set_cell_borders(cell)

        p = cell.paragraphs[0]
        p.alignment = align
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(h_text)
        run.bold = True
        run.font.name = font_name
        run.font.size = Pt(font_size)
        run.font.color.rgb = RGBColor(0, 0, 0)

    # Data Rows
    if results:
        for i, r in enumerate(results, start=1):
            row = table.rows[i]
            r_trPr = row._tr.get_or_add_trPr()
            r_trPr.append(OxmlElement('w:cantSplit'))

            row_data = [
                (f"{i}.", WD_ALIGN_PARAGRAPH.LEFT),
                (str(r['name']), WD_ALIGN_PARAGRAPH.LEFT),
                (str(r['result']), WD_ALIGN_PARAGRAPH.CENTER),
                (str(r['method']) if r['method'] else "", WD_ALIGN_PARAGRAPH.CENTER)
            ]

            for j, (val, align) in enumerate(row_data):
                cell = row.cells[j]
                cell.width = col_widths[j]
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                _set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
                _set_cell_borders(cell)

                p = cell.paragraphs[0]
                p.alignment = align
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.05

                # Support multiline results like Loose / Tapped
                lines = val.split("\n")
                for line_idx, line in enumerate(lines):
                    if line_idx > 0:
                        p = cell.add_paragraph()
                        p.alignment = align
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.space_after = Pt(2)
                        p.paragraph_format.line_spacing = 1.05
                    run = p.add_run(line.strip())
                    run.bold = True
                    run.font.name = "Calibri"
                    run.font.size = Pt(11)
                    run.font.color.rgb = RGBColor(0, 0, 0)
    else:
        row = table.rows[1]
        for j in range(4):
            cell = row.cells[j]
            cell.width = col_widths[j]
            _set_cell_borders(cell)

    # Fix all column widths across rows
    for row in table.rows:
        for j, w in enumerate(col_widths):
            row.cells[j].width = w

    # 5. Signatures Footer
    num_items = len(results) if results else 0
    spacer_pt = max(50, 240 - (num_items * 13))

    p_sig_space = doc.add_paragraph()
    p_sig_space.paragraph_format.space_before = Pt(spacer_pt)
    p_sig_space.paragraph_format.space_after = Pt(0)

    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_table.autofit = False

    # Left: Analyst Signature
    cell_left = sig_table.rows[0].cells[0]
    cell_left.width = Cm(7.7)
    p_l = cell_left.paragraphs[0]
    p_l.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_l = p_l.add_run("Analyst Signature")
    r_l.bold = True
    r_l.font.name = "Calibri"
    r_l.font.size = Pt(11)
    r_l.font.color.rgb = RGBColor(0, 0, 0)

    # Right: Authorised Signatory
    cell_right = sig_table.rows[0].cells[1]
    cell_right.width = Cm(7.7)
    p_r = cell_right.paragraphs[0]
    p_r.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_r = p_r.add_run("Authorised Signatory")
    r_r.bold = True
    r_r.font.name = "Calibri"
    r_r.font.size = Pt(11)
    r_r.font.color.rgb = RGBColor(0, 0, 0)

    # Remove borders from signature table
    for cell in (cell_left, cell_right):
        tcPr = cell._element.get_or_add_tcPr()
        borders = OxmlElement('w:tcBorders')
        for edge in ['top', 'bottom', 'left', 'right']:
            el = OxmlElement(f'w:{edge}')
            el.set(qn('w:val'), 'none')
            borders.append(el)
        tcPr.append(borders)


def generate_docx_report(sample_id):
    """
    Build a .docx report matching the real SSP test report template.
    Returns the file path to the generated Word document.
    """
    sample = get_sample(sample_id)
    if not sample:
        raise ValueError(f"Sample {sample_id} not found")

    results = get_sample_results(sample_id)
    doc = Document()

    # Page Setup (A4)
    _setup_page(doc.sections[0])

    # Build the single sample's section
    _build_sample_section(doc, sample, results)

    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, f'{sample_id}_report.docx')
    doc.save(filepath)
    return filepath


def generate_combined_docx_report(sample_ids):
    """
    Build a combined .docx report with one section per sample, separated by page breaks.
    Reuses the same section-building logic as the single-sample report.
    Returns the file path to the generated Word document.
    """
    if not sample_ids:
        raise ValueError("No sample IDs provided")

    doc = Document()

    # Page Setup (A4) for the first section
    _setup_page(doc.sections[0])

    for idx, sample_id in enumerate(sample_ids):
        sample = get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample {sample_id} not found")

        results = get_sample_results(sample_id)

        # Add a page break before each sample after the first
        if idx > 0:
            doc.add_page_break()

        _build_sample_section(doc, sample, results)

    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, 'combined_report.docx')
    doc.save(filepath)
    return filepath


# Backward compatibility alias
generate_report = generate_docx_report

