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
from reportlab.platypus import Table, TableStyle
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader

# --- PAGE CONFIG ---
st.set_page_config(page_title="Murlidhar Academy PDF Tool", page_icon="📝", layout="wide")

# --- HELPER: GOOGLE DRIVE DIRECT DOWNLOAD ---
def get_drive_direct_url(view_url):
    """Converts Google Drive View URL to Direct Download URL"""
    file_id = view_url.split('/d/')[1].split('/')[0]
    return f"https://drive.google.com/uc?export=download&id={file_id}"

# --- SIDEBAR SETTINGS ---
st.sidebar.title("⚙️ સેટિંગ્સ")
WATERMARK_TEXT = st.sidebar.text_input("Watermark Text", "MURLIDHAR ACADEMY")
TG_LINK = st.sidebar.text_input("Telegram Link", "https://t.me/MurlidharAcademy")
IG_LINK = st.sidebar.text_input("Instagram Link", "https://www.instagram.com/murlidhar_academy_official/")
st.sidebar.divider()
st.sidebar.info("Designed by Harsh Solanki")

# --- MAIN UI ---
st.title("📝 Answer Key Generator - Murlidhar Academy")
st.markdown("તમારું **Question Paper PDF** અને **Answer Key CSV** અપલોડ કરો.")

col1, col2, col3 = st.columns(3)
with col1:
    pdf_file = st.file_uploader("1. Question Paper (PDF)", type=['pdf'])
with col2:
    csv_file = st.file_uploader("2. Answer Key (CSV)", type=['csv'])
with col3:
    img_file_upload = st.file_uploader("3. Background (Optional)", type=['png', 'jpg', 'jpeg'])

# --- LOGIC: HANDLE BACKGROUND IMAGE ---
# Default Google Drive Image Link
DEFAULT_BG_URL = "https://drive.google.com/file/d/1NUwoSCN2OIWgjPQMPX1VileweKzta_HW/view?usp=sharing"

bg_image_data = None

if img_file_upload:
    bg_image_data = img_file_upload
else:
    # Use Default Image from Google Drive
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
    if pdf_file and csv_file and bg_image_data:
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
                # Standard Font
                c_wm.setFont("Helvetica-Bold", 60) 
                c_wm.saveState()
                c_wm.translate(width/2, height/2)
                c_wm.rotate(45)
                c_wm.drawCentredString(0, 0, WATERMARK_TEXT)
                c_wm.restoreState()
                c_wm.save()
                packet_wm.seek(0)
                watermark_reader = PdfReader(packet_wm)
                watermark_page = watermark_reader.pages[0]

                # 3. CREATE ANSWER KEY PAGE
                packet_key = io.BytesIO()
                PAGE_W, PAGE_H = A4
                c = canvas.Canvas(packet_key, pagesize=A4)
                
                # Draw Background
                image_reader = ImageReader(bg_image_data)
                c.drawImage(image_reader, 0, 0, width=PAGE_W, height=PAGE_H)
                
                # Title
                c.setFont("Helvetica-Bold", 16) # Standard Font
                c.setFillColor(colors.white)
                file_name_clean = os.path.splitext(pdf_file.name)[0].replace("_", " ")
                full_title = f"{file_name_clean} | ANSWER KEY"
                
                # Layout Config
                TITLE_Y_mm_from_top = 63.5
                TABLE_SPACE_AFTER_TITLE_mm = 10
                LEFT_MARGIN_mm = 25
                RIGHT_MARGIN_mm = 25
                QUESTIONS_PER_COLUMN = 25
                
                title_y = PAGE_H - (TITLE_Y_mm_from_top * mm)
                c.drawCentredString(PAGE_W/2, title_y, full_title)
                
                # Table Data
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

                available_width = PAGE_W - (LEFT_MARGIN_mm * mm) - (RIGHT_MARGIN_mm * mm)
                single_col_width = available_width / (num_cols_needed * 2)

                t = Table(table_data, colWidths=[single_col_width] * (num_cols_needed * 2))

                # Table Style (Using Standard Fonts)
                HEADER_BG_COLOR = "#003366"
                NO_COL_BG_COLOR = "#e0e0e0"
                
                style = TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), HexColor(HEADER_BG_COLOR)),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), # Standard Font
                    ('FONTSIZE', (0,0), (-1,0), 10),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('GRID', (0,0), (-1,-1), 0.5, HexColor("#cccccc")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, HexColor("#f9f9f9")]),
                ])

                for i in range(num_cols_needed):
                    col_idx_no = i * 2
                    col_idx_ans = i * 2 + 1
                    style.add('FONTNAME', (col_idx_no, 1), (col_idx_no, -1), 'Helvetica-Bold')
                    style.add('BACKGROUND', (col_idx_no, 1), (col_idx_no, -1), HexColor(NO_COL_BG_COLOR))
                    style.add('TEXTCOLOR', (col_idx_no, 1), (col_idx_no, -1), colors.black)
                    style.add('FONTNAME', (col_idx_ans, 1), (col_idx_ans, -1), 'Helvetica')

                t.setStyle(style)
                w, h = t.wrapOn(c, PAGE_W, PAGE_H)
                table_y = title_y - (TABLE_SPACE_AFTER_TITLE_mm * mm) - h
                t.drawOn(c, (PAGE_W - w)/2, table_y)

                # Links
                TG_LINK_POS_mm = (10, 5, 110, 50)
                IG_LINK_POS_mm = (110, 5, 210, 50)
                def get_rect(pos_tuple):
                    return (pos_tuple[0]*mm, pos_tuple[1]*mm, pos_tuple[2]*mm, pos_tuple[3]*mm)
                
                c.linkURL(TG_LINK, get_rect(TG_LINK_POS_mm))
                c.linkURL(IG_LINK, get_rect(IG_LINK_POS_mm))
                
                c.showPage()
                c.save()
                packet_key.seek(0)
                
                # 4. MERGE PDFS
                reader_main = PdfReader(pdf_file)
                reader_key = PdfReader(packet_key)
                writer = PdfWriter()
                
                for page in reader_main.pages:
                    page.merge_page(watermark_page)
                    writer.add_page(page)
                
                writer.add_page(reader_key.pages[0])
                
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                st.success("✅ PDF Generated Successfully!")
                st.download_button(
                    label="Download PDF 📥",
                    data=output_buffer.getvalue(),
                    file_name=f"{os.path.splitext(pdf_file.name)[0]}_WITH_KEY.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"Error occurred: {e}")
    else:
        st.warning("⚠️ Please upload PDF and CSV.")
