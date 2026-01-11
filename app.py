import streamlit as st
import pandas as pd
import io
import os
import math
import requests
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

# --- HELPER: GOOGLE DRIVE DIRECT DOWNLOAD ---
def get_drive_direct_url(view_url):
    """Converts Google Drive View URL to Direct Download URL"""
    try:
        file_id = view_url.split('/d/')[1].split('/')[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    except:
        return view_url

# --- 1. LOAD CUSTOM GUJARATI FONT FROM DRIVE ---
@st.cache_resource
def load_custom_fonts():
    # User Provided Font Link (HindVadodara)
    font_drive_url = "https://drive.google.com/file/d/1jVDKtad01ecE6dwitiAlrqR5Ov1YsJzw/view?usp=sharing"
    font_path = "GujaratiFont.ttf"
    
    if not os.path.exists(font_path):
        try:
            download_url = get_drive_direct_url(font_drive_url)
            response = requests.get(download_url)
            if response.status_code == 200:
                with open(font_path, "wb") as f:
                    f.write(response.content)
            else:
                st.error("❌ Failed to download Font from Google Drive.")
                return False
        except Exception as e:
            st.error(f"⚠️ Font error: {e}")
            return False
            
    # Register the Font
    try:
        pdfmetrics.registerFont(TTFont('GujFont', font_path))
        return True
    except Exception as e:
        st.error(f"❌ Font registration failed: {e}")
        return False

# Load fonts on startup
fonts_loaded = load_custom_fonts()

# --- SIDEBAR SETTINGS ---
st.sidebar.title("⚙️ સેટિંગ્સ")
WATERMARK_TEXT = st.sidebar.text_input("Watermark Text", "MURLIDHAR ACADEMY")
TG_LINK = st.sidebar.text_input("Telegram Link", "https://t.me/MurlidharAcademy")
IG_LINK = st.sidebar.text_input("Instagram Link", "https://www.instagram.com/murlidhar_academy_official/")
st.sidebar.divider()
st.sidebar.info("Designed by Harsh Solanki")

# --- MAIN UI ---
st.title("📝 Answer Key & Solution Generator (Gujarati Support)")
st.markdown("તમારું **Question Paper PDF** અને **Answer Key CSV** અપલોડ કરો.")

col1, col2, col3 = st.columns(3)
with col1:
    pdf_file = st.file_uploader("1. Question Paper (PDF)", type=['pdf'])
with col2:
    csv_file = st.file_uploader("2. Answer Key (CSV)", type=['csv'])
with col3:
    img_file_upload = st.file_uploader("3. Background (Optional)", type=['png', 'jpg', 'jpeg'])

# --- DETAILED SOLUTION SECTION ---
st.divider()
st.subheader("📘 Detailed Solutions (સમજૂતી)")
add_solution = st.checkbox("Add Detailed Solutions Page? (વિસ્તૃત સમજૂતી ઉમેરવી છે?)")

solution_text = ""
if add_solution:
    st.info("ℹ️ Format: **No | Answer | Explanation** (તમે ગુજરાતીમાં લખી શકો છો)")
    solution_text = st.text_area(
        "Paste Data Here:", 
        height=200,
        placeholder="1 | A - પાટણ | પાટણ રાણકી વાવ માટે પ્રખ્યાત છે.\n2 | B - ગિરનાર | ગિરનાર જૂનાગઢમાં આવેલો છે."
    )

# --- LOGIC: HANDLE BACKGROUND IMAGE ---
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
            st.info("ℹ️ Using Default Background Image from Google Drive.")
        else:
            st.warning("⚠️ Could not load default background image.")
    except Exception as e:
        st.error(f"Error loading default background: {e}")

# --- PROCESSING ---
if st.button("Generate PDF 🚀"):
    if pdf_file and csv_file and bg_image_data and fonts_loaded:
        try:
            with st.spinner("Processing... Please wait"):
                # 1. READ CSV
                df = pd.read_csv(csv_file)
                key_cols = [c for c in df.columns if c.lower().startswith('key') and c[3:].isdigit()]
                key_cols.sort(key=lambda x: int(x[3:]))
                answers = {}
                if not df.empty:
                    for k in key_cols:
                        q_num = int(k.lower().replace('key', ''))
                        answers[q_num] = str(df.iloc[0][k]).strip()
                total_questions = len(answers)
                
                # 2. CREATE WATERMARK
                packet_wm = io.BytesIO()
                reader_temp = PdfReader(pdf_file)
                page1 = reader_temp.pages[0]
                width = float(page1.mediabox.width)
                height = float(page1.mediabox.height)
                c_wm = canvas.Canvas(packet_wm, pagesize=(width, height))
                c_wm.setFillColor(colors.grey, alpha=0.15)
                # Use Gujarati Font for Watermark too (or keep Helvetica if english)
                c_wm.setFont("GujFont", 60) 
                c_wm.saveState()
                c_wm.translate(width/2, height/2)
                c_wm.rotate(45)
                c_wm.drawCentredString(0, 0, WATERMARK_TEXT)
                c_wm.restoreState()
                c_wm.save()
                packet_wm.seek(0)
                watermark_reader = PdfReader(packet_wm)
                watermark_page = watermark_reader.pages[0]

                # --- 3. GENERATE PAGES ---
                packet_key = io.BytesIO()
                PAGE_W, PAGE_H = A4
                c = canvas.Canvas(packet_key, pagesize=A4)
                
                def draw_page_template(canvas_obj):
                    image_reader = ImageReader(bg_image_data)
                    canvas_obj.drawImage(image_reader, 0, 0, width=PAGE_W, height=PAGE_H)
                    # Links
                    TG_LINK_POS = (10*mm, 5*mm, 110*mm, 50*mm)
                    IG_LINK_POS = (110*mm, 5*mm, 210*mm, 50*mm)
                    canvas_obj.linkURL(TG_LINK, TG_LINK_POS)
                    canvas_obj.linkURL(IG_LINK, IG_LINK_POS)

                # === PAGE 1: ANSWER KEY ===
                draw_page_template(c)
                
                c.setFont("GujFont", 16) # Title in Gujarati Font
                c.setFillColor(colors.white)
                file_name_clean = os.path.splitext(pdf_file.name)[0].replace("_", " ")
                c.drawCentredString(PAGE_W/2, PAGE_H - (63.5 * mm), f"{file_name_clean} | ANSWER KEY")

                # Table Logic
                QUESTIONS_PER_COLUMN = 25
                num_cols_needed = math.ceil(total_questions / QUESTIONS_PER_COLUMN)
                table_data = []
                headers = []
                for _ in range(num_cols_needed):
                    headers.extend(["NO", "ANS"])
                table_data.append(headers)

                for r in range(QUESTIONS_PER_COLUMN):
                    row = []
                    for col_idx in range(num_cols_needed):
                        q_num = col_idx * QUESTIONS_PER_COLUMN + (r + 1)
                        if q_num <= total_questions:
                            row.extend([str(q_num), answers.get(q_num, "-")])
                        else:
                            row.extend(["", ""])
                    table_data.append(row)

                avail_w = PAGE_W - (50 * mm)
                col_w = avail_w / (num_cols_needed * 2)
                t = Table(table_data, colWidths=[col_w] * (num_cols_needed * 2))
                
                # Table Style using Gujarati Font
                style = TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), HexColor("#003366")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'GujFont'), # HEADER FONT
                    ('FONTSIZE', (0,0), (-1,0), 10),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#cccccc")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, HexColor("#f9f9f9")]),
                ])
                
                for i in range(num_cols_needed):
                    col_idx_no = i * 2
                    style.add('FONTNAME', (col_idx_no, 1), (col_idx_no, -1), 'GujFont')
                    style.add('BACKGROUND', (col_idx_no, 1), (col_idx_no, -1), HexColor("#e0e0e0"))
                    style.add('TEXTCOLOR', (col_idx_no, 1), (col_idx_no, -1), colors.black)

                t.setStyle(style)
                w, h = t.wrapOn(c, PAGE_W, PAGE_H)
                t.drawOn(c, (PAGE_W - w)/2, PAGE_H - (63.5 * mm) - 10*mm - h)
                
                c.showPage()

                # === PAGE 2+: DETAILED SOLUTIONS ===
                if add_solution and solution_text.strip():
                    
                    # Style for Gujarati Text Wrapping
                    styles = getSampleStyleSheet()
                    # We create a style that uses our Gujarati Font
                    gu_style = ParagraphStyle(
                        'GujaratiStyle',
                        parent=styles['Normal'],
                        fontName='GujFont', # IMPORTANT
                        fontSize=10,
                        leading=14,
                        alignment=0
                    )

                    sol_headers = ["NO", "ANSWER", "EXPLANATION / SAMJUTI"]
                    
                    sol_data = []
                    lines = solution_text.strip().split('\n')
                    for line in lines:
                        parts = line.split('|')
                        if len(parts) >= 1:
                            no_txt = parts[0].strip()
                            ans_txt = parts[1].strip() if len(parts) > 1 else ""
                            expl_txt = parts[2].strip() if len(parts) > 2 else ""
                            
                            # Wrap text in Paragraph with Gujarati Style
                            row = [
                                Paragraph(no_txt, gu_style),
                                Paragraph(ans_txt, gu_style),
                                Paragraph(expl_txt, gu_style)
                            ]
                            sol_data.append(row)

                    col_widths = [20*mm, 50*mm, 110*mm]
                    x_start = (PAGE_W - sum(col_widths)) / 2
                    y_start = PAGE_H - (63.5 * mm) - 10*mm
                    bottom_margin = 60 * mm
                    
                    # Start Logic
                    draw_page_template(c)
                    c.setFont("GujFont", 16)
                    c.setFillColor(colors.white)
                    c.drawCentredString(PAGE_W/2, PAGE_H - (63.5 * mm), "DETAILED SOLUTIONS")
                    
                    # Header
                    header_t = Table([sol_headers], colWidths=col_widths)
                    header_t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), HexColor("#003366")),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                        ('FONTNAME', (0,0), (-1,0), 'GujFont'),
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
                            c.setFont("GujFont", 16)
                            c.setFillColor(colors.white)
                            c.drawCentredString(PAGE_W/2, PAGE_H - (63.5 * mm), "DETAILED SOLUTIONS")
                            header_t.drawOn(c, x_start, y_start - h_h)
                            current_y = y_start - h_h
                        
                        row_t.drawOn(c, x_start, current_y - h_r)
                        current_y -= h_r

                    c.showPage()

                c.save()
                packet_key.seek(0)
                
                # 4. MERGE
                reader_main = PdfReader(pdf_file)
                reader_key = PdfReader(packet_key)
                writer = PdfWriter()
                
                for page in reader_main.pages:
                    page.merge_page(watermark_page)
                    writer.add_page(page)
                
                for page in reader_key.pages:
                    writer.add_page(page)
                
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                st.success("✅ PDF Generated Successfully!")
                st.download_button(
                    label="Download PDF 📥",
                    data=output_buffer.getvalue(),
                    file_name=f"{os.path.splitext(pdf_file.name)[0]}_WITH_SOLUTION.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"Error occurred: {e}")
    else:
        if not fonts_loaded:
            st.error("⚠️ Font download failed. Check link.")
        else:
            st.warning("⚠️ Please upload PDF and CSV.")
