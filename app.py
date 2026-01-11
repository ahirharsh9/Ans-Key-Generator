import streamlit as st
import pandas as pd
import io
import os
import math
import requests
import reportlab.rl_config

# --- 1. CRITICAL CONFIG FOR JODAKSHAR (Must be before other imports) ---
# આ લાઈન જોડાક્ષરો (Complex Script) ને ભેગા કરે છે
reportlab.rl_config.shaped_text = 'uharfbuzz'

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- PAGE CONFIG ---
st.set_page_config(page_title="Murlidhar Academy PDF Tool", page_icon="📝", layout="wide")

# --- HELPER FUNCTIONS ---
def get_drive_direct_url(view_url):
    try:
        if '/d/' in view_url:
            file_id = view_url.split('/d/')[1].split('/')[0]
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    except:
        return view_url
    return view_url

# --- MIXED FONT LOGIC ---
def stylize_text(text):
    """
    અંગ્રેજી શબ્દો માટે English Font અને ગુજરાતી માટે Gujarati Font વાપરે છે.
    """
    if not isinstance(text, str):
        return str(text)
    
    words = text.split(' ')
    styled_words = []
    
    for word in words:
        # Check if word contains Gujarati characters
        is_gujarati = any(ord(char) > 127 for char in word)
        
        if is_gujarati:
            # Gujarati Font
            styled_words.append(f"<font face='GujFont'>{word}</font>")
        else:
            # English Font (Helvetica renders cleaner for English numbers/text)
            styled_words.append(f"<font face='Helvetica'>{word}</font>")
            
    return " ".join(styled_words)

# --- LOAD FONTS (Noto Sans Gujarati - BEST FOR JODAKSHAR) ---
@st.cache_resource
def load_custom_fonts():
    # Noto Sans Gujarati (Bold) - Google Fonts Direct Link
    # આ ફોન્ટમાં જોડાક્ષરોનું કોડિંગ સૌથી સારું હોય છે
    font_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansGujarati/NotoSansGujarati-Bold.ttf"
    font_path = "NotoSansGujarati-Bold.ttf"
    
    if not os.path.exists(font_path):
        try:
            response = requests.get(font_url)
            if response.status_code == 200:
                with open(font_path, "wb") as f:
                    f.write(response.content)
            else:
                st.error("❌ Failed to download Noto Sans Font.")
                return False
        except Exception as e:
            st.error(f"⚠️ Font error: {e}")
            return False
            
    try:
        # Font Register with 'uharfbuzz' awareness implicitly via Config
        pdfmetrics.registerFont(TTFont('GujFont', font_path))
        return True
    except Exception as e:
        st.error(f"❌ Font registration failed: {e}")
        return False

fonts_loaded = load_custom_fonts()

# --- SIDEBAR ---
st.sidebar.title("⚙️ સેટિંગ્સ")
WATERMARK_TEXT = st.sidebar.text_input("Watermark Text", "MURLIDHAR ACADEMY")
TG_LINK = st.sidebar.text_input("Telegram Link", "https://t.me/MurlidharAcademy")
IG_LINK = st.sidebar.text_input("Instagram Link", "https://www.instagram.com/murlidhar_academy_official/")
st.sidebar.divider()
st.sidebar.info("Designed by Harsh Solanki")

# --- MAIN UI ---
st.title("📝 Answer Key & Solution Generator (Fixed Jodakshar)")
st.markdown("તમારું **Question Paper PDF** અને **Answer Key CSV** અપલોડ કરો.")

col1, col2, col3 = st.columns(3)
with col1:
    pdf_file = st.file_uploader("1. Question Paper (PDF)", type=['pdf'])
with col2:
    csv_file = st.file_uploader("2. Answer Key (CSV)", type=['csv'])
with col3:
    img_file_upload = st.file_uploader("3. Background (Optional)", type=['png', 'jpg', 'jpeg'])

st.divider()
st.subheader("📘 Detailed Solutions (સમજૂતી)")
add_solution = st.checkbox("Add Detailed Solutions Page?")

solution_text = ""
if add_solution:
    st.info("ℹ️ Format: **No | Answer | Explanation**")
    solution_text = st.text_area(
        "Paste Data Here:", 
        height=200,
        placeholder="1 | A - પાટણ | પાટણ રાણકી વાવ માટે પ્રખ્યાત છે.\n2 | B - કૌશલ્ય | જીવનનિર્વાહનો ખર્ચ વધુ હોય છે."
    )

# --- BACKEND LOGIC ---
DEFAULT_BG_URL = "https://drive.google.com/file/d/1NUwoSCN2OIWgjPQMPX1VileweKzta_HW/view?usp=sharing"
bg_image_data = None

if img_file_upload:
    bg_image_data = img_file_upload
else:
    try:
        direct_url = get_drive_direct_url(DEFAULT_BG_URL)
        response = requests.get(direct_url)
        if response.status_code == 200:
            bg_image_data = io.BytesIO(response.content)
            st.info("ℹ️ Using Default Background Image.")
    except:
        pass

if st.button("Generate PDF 🚀"):
    if pdf_file and csv_file and bg_image_data and fonts_loaded:
        try:
            with st.spinner("Processing... Please wait"):
                # CSV Processing
                df = pd.read_csv(csv_file)
                key_cols = [c for c in df.columns if c.lower().startswith('key') and c[3:].isdigit()]
                key_cols.sort(key=lambda x: int(x[3:]))
                answers = {}
                if not df.empty:
                    for k in key_cols:
                        q_num = int(k.lower().replace('key', ''))
                        answers[q_num] = str(df.iloc[0][k]).strip()
                total_questions = len(answers)
                
                # Watermark
                packet_wm = io.BytesIO()
                reader_temp = PdfReader(pdf_file)
                page1 = reader_temp.pages[0]
                width = float(page1.mediabox.width)
                height = float(page1.mediabox.height)
                c_wm = canvas.Canvas(packet_wm, pagesize=(width, height))
                c_wm.setFillColor(colors.grey, alpha=0.15)
                c_wm.setFont("Helvetica-Bold", 60) # English Watermark
                c_wm.saveState()
                c_wm.translate(width/2, height/2)
                c_wm.rotate(45)
                c_wm.drawCentredString(0, 0, WATERMARK_TEXT)
                c_wm.restoreState()
                c_wm.save()
                packet_wm.seek(0)
                watermark_reader = PdfReader(packet_wm)
                watermark_page = watermark_reader.pages[0]

                # --- GENERATE PDF ---
                packet_key = io.BytesIO()
                PAGE_W, PAGE_H = A4
                c = canvas.Canvas(packet_key, pagesize=A4)
                
                def draw_page_template(canvas_obj):
                    image_reader = ImageReader(bg_image_data)
                    canvas_obj.drawImage(image_reader, 0, 0, width=PAGE_W, height=PAGE_H)
                    canvas_obj.linkURL(TG_LINK, (10*mm, 5*mm, 110*mm, 50*mm))
                    canvas_obj.linkURL(IG_LINK, (110*mm, 5*mm, 210*mm, 50*mm))

                # === PAGE 1: ANSWER KEY ===
                draw_page_template(c)
                c.setFont("Helvetica-Bold", 16)
                c.setFillColor(colors.white)
                file_name_clean = os.path.splitext(pdf_file.name)[0].replace("_", " ")
                c.drawCentredString(PAGE_W/2, PAGE_H - (63.5 * mm), f"{file_name_clean} | ANSWER KEY")

                # Table Setup
                QUESTIONS_PER_COLUMN = 25
                num_cols_needed = math.ceil(total_questions / QUESTIONS_PER_COLUMN)
                table_data = []
                headers = []
                for _ in range(num_cols_needed):
                    headers.extend(["NO", "ANS"])
                table_data.append(headers)

                # Process Rows for Key
                for r in range(QUESTIONS_PER_COLUMN):
                    row = []
                    for col_idx in range(num_cols_needed):
                        q_num = col_idx * QUESTIONS_PER_COLUMN + (r + 1)
                        if q_num <= total_questions:
                            ans_val = answers.get(q_num, "-")
                            # Use stylize_text
                            p_style = ParagraphStyle('KeyStyle', fontName='Helvetica', fontSize=10, alignment=1)
                            styled_ans = Paragraph(stylize_text(ans_val), p_style)
                            
                            row.extend([str(q_num), styled_ans])
                        else:
                            row.extend(["", ""])
                    table_data.append(row)

                avail_w = PAGE_W - (50 * mm)
                col_w = avail_w / (num_cols_needed * 2)
                t = Table(table_data, colWidths=[col_w] * (num_cols_needed * 2))
                
                style = TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), HexColor("#003366")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#cccccc")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, HexColor("#f9f9f9")]),
                ])
                for i in range(num_cols_needed):
                    col_idx_no = i * 2
                    style.add('FONTNAME', (col_idx_no, 1), (col_idx_no, -1), 'Helvetica-Bold')
                    style.add('BACKGROUND', (col_idx_no, 1), (col_idx_no, -1), HexColor("#e0e0e0"))
                    style.add('TEXTCOLOR', (col_idx_no, 1), (col_idx_no, -1), colors.black)
                
                t.setStyle(style)
                w, h = t.wrapOn(c, PAGE_W, PAGE_H)
                t.drawOn(c, (PAGE_W - w)/2, PAGE_H - (63.5 * mm) - 10*mm - h)
                c.showPage()

                # === PAGE 2+: DETAILED SOLUTIONS ===
                if add_solution and solution_text.strip():
                    styles = getSampleStyleSheet()
                    # Base style
                    base_style = ParagraphStyle(
                        'MixedStyle',
                        parent=styles['Normal'],
                        fontName='Helvetica', 
                        fontSize=10,
                        leading=14,
                        alignment=0
                    )

                    sol_headers = ["NO", "ANSWER", "EXPLANATION"]
                    
                    sol_data = []
                    lines = solution_text.strip().split('\n')
                    for line in lines:
                        parts = line.split('|')
                        if len(parts) >= 1:
                            no_txt = parts[0].strip()
                            ans_txt = parts[1].strip() if len(parts) > 1 else ""
                            expl_txt = parts[2].strip() if len(parts) > 2 else ""
                            
                            row = [
                                Paragraph(stylize_text(no_txt), base_style),
                                Paragraph(stylize_text(ans_txt), base_style),
                                Paragraph(stylize_text(expl_txt), base_style)
                            ]
                            sol_data.append(row)

                    col_widths = [20*mm, 50*mm, 110*mm]
                    x_start = (PAGE_W - sum(col_widths)) / 2
                    y_start = PAGE_H - (63.5 * mm) - 10*mm
                    bottom_margin = 60 * mm
                    
                    draw_page_template(c)
                    c.setFont("Helvetica-Bold", 16)
                    c.setFillColor(colors.white)
                    c.drawCentredString(PAGE_W/2, PAGE_H - (63.5 * mm), "DETAILED SOLUTIONS")
                    
                    header_t = Table([sol_headers], colWidths=col_widths)
                    header_t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), HexColor("#003366")),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ]))
                    w_h, h_h = header_t.wrapOn(c, PAGE_W, PAGE_H)
                    header_t.drawOn(c, x_start, y_start - h_h)
                    current_y = y_start - h_h
                    
                    for row in sol_data:
                        row_t = Table([row], colWidths=col_widths)
                        row_t.setStyle(TableStyle([
                            ('GRID', (0,0), (-1,-1), 0.5, HexColor("#cccccc")),
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('BACKGROUND', (0,0), (0,-1), HexColor("#e0e0e0")),
                        ]))
                        w_r, h_r = row_t.wrapOn(c, PAGE_W, PAGE_H)
                        
                        if current_y - h_r < bottom_margin:
                            c.showPage()
                            draw_page_template(c)
                            c.setFont("Helvetica-Bold", 16)
                            c.setFillColor(colors.white)
                            c.drawCentredString(PAGE_W/2, PAGE_H - (63.5 * mm), "DETAILED SOLUTIONS")
                            header_t.drawOn(c, x_start, y_start - h_h)
                            current_y = y_start - h_h
                        
                        row_t.drawOn(c, x_start, current_y - h_r)
                        current_y -= h_r

                    c.showPage()

                c.save()
                packet_key.seek(0)
                
                # Merge
                reader_main = PdfReader(pdf_file)
                reader_key = PdfReader(packet_key)
                writer = PdfWriter()
                for p in reader_main.pages:
                    p.merge_page(watermark_page)
                    writer.add_page(p)
                for p in reader_key.pages:
                    writer.add_page(p)
                
                out_pdf = io.BytesIO()
                writer.write(out_pdf)
                st.success("✅ PDF Generated!")
                st.download_button("Download PDF 📥", out_pdf.getvalue(), f"{os.path.splitext(pdf_file.name)[0]}_SOL.pdf", "application/pdf")

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please upload files.")
