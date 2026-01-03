import fitz  # PyMuPDF
import io
import os
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT

class PDFSurgeon:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.page = self.doc[0]  # Targeting first page
        self.width = self.page.rect.width
        self.height = self.page.rect.height
        
        # Define Assets Directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(current_dir, "assets")
        self._register_fonts()

    def _register_fonts(self):
        """Attempts to load LaTeX fonts. Falls back to Times if missing."""
        self.font_reg = "Times-Roman"
        self.font_bold = "Times-Bold"
        self.font_italic = "Times-Italic"
        
        try:
            reg_path = os.path.join(self.assets_dir, "cmr10.ttf")
            bold_path = os.path.join(self.assets_dir, "cmb10.ttf")
            
            if os.path.exists(reg_path) and os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont('CMR', reg_path))
                pdfmetrics.registerFont(TTFont('CMB', bold_path))
                self.font_reg = 'CMR'
                self.font_bold = 'CMB'
                print("✅ [PDFSurgeon] LaTeX fonts loaded.")
            else:
                print(f"⚠️ [PDFSurgeon] LaTeX fonts not found in {self.assets_dir}. Using Times-Roman.")
        except Exception as e:
            print(f"⚠️ [PDFSurgeon] Font loading error: {e}")

    def _markdown_to_reportlab(self, text):
        """Converts Markdown bold/italic to ReportLab XML tags."""
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)      # Italic
        return text.replace('\n', '<br/>')

    def find_section_bounds(self, start_header: str, end_header: str = None):
        """
        Locates the vertical space between two headers.
        """
        # 1. Find Start Header
        try:
            start_areas = self.page.search_for(start_header)
            if not start_areas:
                # Try fuzzy/case-insensitive search if exact match fails
                # For now, just return None
                print(f"   ⚠️ Header '{start_header}' not found.")
                return None
            
            y_top = start_areas[0].y1 + 10  # Start 10px below the header
            
            # 2. Find End Header
            y_bottom = self.height - 50 # Default to near bottom of page
            
            if end_header:
                end_areas = self.page.search_for(end_header)
                if end_areas:
                    y_bottom = end_areas[0].y0 - 10 # Stop 10px above next header
            
            height_available = y_bottom - y_top
            
            if height_available < 50:
                print("   ⚠️ Section too tight (<50px).")
                return None
                
            return {
                "x": 50, # Left margin assumption
                "y": y_top,
                "w": self.width - 100, # Right margin assumption
                "h": height_available
            }
            
        except Exception as e:
            print(f"   ❌ Error finding bounds: {e}")
            return None

    def create_patch_stream(self, text, bounds, font_size=10):
        """
        Generates a FULL PAGE transparent PDF with text at the correct absolute position.
        Mapping PyMuPDF (Top-Left) -> ReportLab (Bottom-Left) coordinates.
        """
        packet = io.BytesIO()
        
        # Canvas Size = Full Page Size
        # This ensures 1:1 overlay without scaling
        c = canvas.Canvas(packet, pagesize=(self.width, self.height))
        
        from reportlab.lib import colors
        
        formatted_text = self._markdown_to_reportlab(text)
        
        style = ParagraphStyle(
            name='Resume_Body',
            fontName=self.font_reg,
            fontSize=font_size,
            leading=font_size * 1.2,
            alignment=TA_LEFT,
            textColor=colors.blue
        )
        
        p = Paragraph(formatted_text, style)
        
        # Wrap text within the available width
        # This calculates the actual height the text will occupy
        available_width = bounds["w"]
        available_height = bounds["h"]
        
        text_w, text_h = p.wrap(available_width, available_height)
        
        if text_h > available_height:
             return None # Signal overflow
             
        # CALCULATE COORDINATES
        # PyMuPDF Y starts from Top. ReportLab Y starts from Bottom.
        # We want the text TOP to be at bounds['y']
        
        # ReportLab Y for the TOP of the text box:
        rl_y_top = self.height - bounds["y"]
        
        # ReportLab Y for the BOTTOM of the text box (where drawOn draws):
        rl_y_draw = rl_y_top - text_h
        
        # X coordinate
        rl_x = bounds["x"]
        
        p.drawOn(c, rl_x, rl_y_draw)
        c.save()
        packet.seek(0)
        
        return packet, available_width, available_height
        
    def replace_section(self, section_name: str, new_text: str, next_section_name: str = None):
        """
        Redacts the old section and overlays the new text using Full-Page Overlay.
        """
        print(f"   🔪 replacing section: {section_name} -> {next_section_name or 'End of Page'}")
        
        # 1. Find Bounds (PyMuPDF coordinates)
        bounds = self.find_section_bounds(section_name, next_section_name)
        if not bounds: return False
        
        # 2. Generate Full-Page Patch with Auto-Fit
        patch_stream = None
        
        # Try resizing fonts 10 -> 8
        for fs in [10, 9.5, 9, 8.5, 8]:
            result = self.create_patch_stream(new_text, bounds, font_size=fs)
            if result:
                patch_stream = result[0] # We just need the stream
                if fs < 10:
                    print(f"   📉 Auto-fitted text with font-size {fs}pt")
                break
        
        if not patch_stream:
            print(f"   ⚠️ Content too long for section '{section_name}'. available_h={bounds['h']}")
            return False 
            
        # 3. Redact Old Content (Clean Slate)
        # We still use the bounds to white-out the old text
        rect = fitz.Rect(bounds["x"], bounds["y"], bounds["x"] + bounds["w"], bounds["y"] + bounds["h"])
        self.page.add_redact_annot(rect, fill=(1, 1, 1))
        self.page.apply_redactions()
        
        # 4. Overlay New Content (Full Page 1:1)
        patch_doc = fitz.open("pdf", patch_stream.read())
        
        # Overlay on the full page rect
        self.page.show_pdf_page(self.page.rect, patch_doc, 0)
        
        print(f"   ✅ Section '{section_name}' patched successfully.")
        return True

    def save(self, output_path):
        self.doc.save(output_path)
        self.doc.close()

# Backward compatibility
def generate_pdf(data, path): return path