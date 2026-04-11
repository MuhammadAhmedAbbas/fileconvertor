import os
import uuid
import zipfile
import io
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for

# ── PDF / image libraries ──────────────────────────────────────────────────
from pypdf import PdfReader, PdfWriter
import pikepdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
from PIL import Image
from docx import Document as DocxDocument
import fitz  # PyMuPDF

# Try to import Windows-specific COM libraries for high-quality conversion
try:
    import pythoncom
    import win32com.client
    WINDOWS_COM_AVAILABLE = True
except ImportError:
    WINDOWS_COM_AVAILABLE = False
    print("[!] Windows COM components not available. Using fallback conversion methods.")

app = Flask(__name__)

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "outputs"))

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024   # 50 MB

ALLOWED_PDF  = {"pdf"}
ALLOWED_WORD = {"docx"}


# ── Helpers ────────────────────────────────────────────────────────────────

def ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

def allowed(filename: str, types: set) -> bool:
    return ext(filename) in types

def save_upload(file) -> Path:
    name = f"{uuid.uuid4().hex}_{file.filename}"
    path = UPLOAD_DIR / name
    file.save(path)
    return path

def out_path(suffix: str) -> Path:
    return OUTPUT_DIR / f"{uuid.uuid4().hex}{suffix}"

def dl_url(path: Path, dl_name: str) -> str:
    return url_for("download", filename=path.name, name=dl_name)

def err(msg: str, code: int = 400):
    return jsonify({"error": msg}), code

def ok(path: Path, dl_name: str):
    return jsonify({
        "success": True,
        "download_url": dl_url(path, dl_name),
        "file_path": str(path),
        "file_name": dl_name
    })

def convert_word_to_pdf_libreoffice(input_path: Path, output_path: Path):
    """
    Converts a Word document to PDF using LibreOffice in headless mode.
    This is the best cross-platform conversion method for Linux/Docker.
    """
    try:
        # Provide a writable user configuration directory, crucial for Docker running as root
        # We use a unique directory in /tmp for this conversion to avoid clashes
        profile_dir = f"file:///tmp/libreoffice_profile_{uuid.uuid4().hex}"
        
        # LibreOffice command: libreoffice --headless --convert-to pdf --outdir <dir> <file>
        result = subprocess.run([
            'libreoffice',
            f'-env:UserInstallation={profile_dir}',
            '--headless',
            '--invisible',
            '--nologo',
            '--nodefault',
            '--nofirststartwizard',
            '--convert-to', 'pdf',
            '--outdir', str(output_path.parent),
            str(input_path)
        ], capture_output=True, text=True, check=True)
        
        # LibreOffice creates a file with the same name but .pdf extension in the outdir
        generated_pdf = output_path.parent / f"{input_path.stem}.pdf"
        if generated_pdf.exists():
            # Rename it to our desired output path if they differ
            if generated_pdf != output_path:
                if output_path.exists():
                    output_path.unlink()
                generated_pdf.replace(output_path)
            return True
        else:
            print(f"[!] LibreOffice finished but no PDF was found at {generated_pdf}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"[!] LibreOffice conversion failed with code {e.returncode}")
        print(f"[!] STDOUT: {e.stdout}")
        print(f"[!] STDERR: {e.stderr}")
        return False
    except Exception as e:
        print(f"[!] LibreOffice conversion failed: {e}")
        return False


# ── Routes: pages ──────────────────────────────────────────────────────────

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/tools")
def index():
    return render_template("index.html")

@app.route("/merge")
def merge_page():
    return render_template("merge.html")

@app.route("/split")
def split_page():
    return render_template("split.html")

@app.route("/compress")
def compress_page():
    return render_template("compress.html")

@app.route("/rotate")
def rotate_page():
    return render_template("rotate.html")

@app.route("/watermark")
def watermark_page():
    return render_template("watermark.html")

@app.route("/page-numbers")
def page_numbers_page():
    return render_template("page_numbers.html")

@app.route("/protect")
def protect_page():
    return render_template("protect.html")

@app.route("/unlock")
def unlock_page():
    return render_template("unlock.html")

@app.route("/sign")
def sign_page():
    return render_template("sign.html")



@app.route("/pdf-to-word")
def pdf_to_word_page():
    return render_template("pdf_to_word.html")

@app.route("/word-to-pdf")
def word_to_pdf_page():
    return render_template("word_to_pdf.html")


# ── Download ───────────────────────────────────────────────────────────────

@app.route("/download/<filename>")
def download(filename):
    dl_name = request.args.get("name", filename)
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True, download_name=dl_name)


# ── API: Merge ─────────────────────────────────────────────────────────────

@app.route("/api/merge", methods=["POST"])
def api_merge():
    files = request.files.getlist("files")
    if len(files) < 2:
        return err("Please upload at least 2 PDF files.")
    for f in files:
        if not allowed(f.filename, ALLOWED_PDF):
            return err(f"'{f.filename}' is not a PDF.")
    writer = PdfWriter()
    saved = []
    try:
        for f in files:
            p = save_upload(f)
            saved.append(p)
            reader = PdfReader(str(p))
            for page in reader.pages:
                writer.add_page(page)
        out = out_path(".pdf")
        with open(out, "wb") as fh:
            writer.write(fh)
        return ok(out, "merged.pdf")
    except Exception as e:
        return err(str(e), 500)
    finally:
        for p in saved:
            p.unlink(missing_ok=True)


# ── API: Split ─────────────────────────────────────────────────────────────

@app.route("/api/split", methods=["POST"])
def api_split():
    f = request.files.get("file")
    if not f or not allowed(f.filename, ALLOWED_PDF):
        return err("Please upload a valid PDF file.")
    mode   = request.form.get("mode", "all")   # "all" or "range"
    ranges = request.form.get("ranges", "")
    p = save_upload(f)
    try:
        reader = PdfReader(str(p))
        total  = len(reader.pages)
        zip_out = out_path(".zip")

        if mode == "range" and ranges.strip():
            # Parse comma-separated ranges like "1-3,5,7-9"
            pages_to_extract = set()
            for part in ranges.split(","):
                part = part.strip()
                if "-" in part:
                    a, b = part.split("-", 1)
                    pages_to_extract.update(range(int(a)-1, int(b)))
                else:
                    pages_to_extract.add(int(part)-1)
            pages_to_extract = sorted(p2 for p2 in pages_to_extract if 0 <= p2 < total)
        else:
            pages_to_extract = list(range(total))

        tmp_files = []
        for i in pages_to_extract:
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            tmp = out_path(f"_page{i+1}.pdf")
            with open(tmp, "wb") as fh:
                writer.write(fh)
            tmp_files.append(tmp)

        with zipfile.ZipFile(zip_out, "w") as zf:
            for tf in tmp_files:
                zf.write(tf, tf.name)

        for tf in tmp_files:
            tf.unlink(missing_ok=True)

        return ok(zip_out, "split_pages.zip")
    except Exception as e:
        return err(str(e), 500)
    finally:
        p.unlink(missing_ok=True)


# ── API: Compress ──────────────────────────────────────────────────────────

@app.route("/api/compress", methods=["POST"])
def api_compress():
    f = request.files.get("file")
    if not f or not allowed(f.filename, ALLOWED_PDF):
        return err("Please upload a valid PDF file.")
    p = save_upload(f)
    out = out_path(".pdf")
    try:
        with pikepdf.open(str(p)) as pdf:
            pdf.save(str(out), compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
        return ok(out, "compressed.pdf")
    except Exception as e:
        return err(str(e), 500)
    finally:
        p.unlink(missing_ok=True)


# ── API: Rotate ────────────────────────────────────────────────────────────

@app.route("/api/rotate", methods=["POST"])
def api_rotate():
    f = request.files.get("file")
    if not f or not allowed(f.filename, ALLOWED_PDF):
        return err("Please upload a valid PDF file.")
    try:
        angle = int(request.form.get("angle", 90))
        if angle not in (90, 180, 270):
            return err("Angle must be 90, 180, or 270.")
    except ValueError:
        return err("Invalid angle value.")
    p = save_upload(f)
    out = out_path(".pdf")
    try:
        reader = PdfReader(str(p))
        writer = PdfWriter()
        for page in reader.pages:
            page.rotate(angle)
            writer.add_page(page)
        with open(out, "wb") as fh:
            writer.write(fh)
        return ok(out, "rotated.pdf")
    except Exception as e:
        return err(str(e), 500)
    finally:
        p.unlink(missing_ok=True)


# ── API: Watermark ─────────────────────────────────────────────────────────

@app.route("/api/watermark", methods=["POST"])
def api_watermark():
    f = request.files.get("file")
    if not f or not allowed(f.filename, ALLOWED_PDF):
        return err("Please upload a valid PDF file.")
    text    = request.form.get("text", "WATERMARK").strip() or "WATERMARK"
    opacity = float(request.form.get("opacity", 0.3))
    p = save_upload(f)
    out = out_path(".pdf")
    try:
        # Build watermark PDF in memory
        wm_buf = io.BytesIO()
        reader = PdfReader(str(p))
        first  = reader.pages[0]
        w = float(first.mediabox.width)
        h = float(first.mediabox.height)

        c_obj = canvas.Canvas(wm_buf, pagesize=(w, h))
        c_obj.setFont("Helvetica-Bold", 48)
        c_obj.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
        c_obj.saveState()
        c_obj.translate(w / 2, h / 2)
        c_obj.rotate(45)
        c_obj.drawCentredString(0, 0, text)
        c_obj.restoreState()
        c_obj.save()
        wm_buf.seek(0)

        wm_reader = PdfReader(wm_buf)
        wm_page   = wm_reader.pages[0]

        writer = PdfWriter()
        for page in reader.pages:
            page.merge_page(wm_page)
            writer.add_page(page)
        with open(out, "wb") as fh:
            writer.write(fh)
        return ok(out, "watermarked.pdf")
    except Exception as e:
        return err(str(e), 500)
    finally:
        p.unlink(missing_ok=True)


# ── API: Page Numbers ──────────────────────────────────────────────────────

@app.route("/api/page-numbers", methods=["POST"])
def api_page_numbers():
    f = request.files.get("file")
    if not f or not allowed(f.filename, ALLOWED_PDF):
        return err("Please upload a valid PDF file.")
    position = request.form.get("position", "bottom-center")
    p = save_upload(f)
    out = out_path(".pdf")
    try:
        reader = PdfReader(str(p))
        writer = PdfWriter()

        for i, page in enumerate(reader.pages, start=1):
            w = float(page.mediabox.width)
            h = float(page.mediabox.height)

            # Build number overlay
            buf = io.BytesIO()
            c_obj = canvas.Canvas(buf, pagesize=(w, h))
            c_obj.setFont("Helvetica", 12)
            c_obj.setFillColor(Color(0, 0, 0))
            label = str(i)

            margin = 20
            if position == "bottom-center":
                c_obj.drawCentredString(w / 2, margin, label)
            elif position == "bottom-right":
                c_obj.drawRightString(w - margin, margin, label)
            elif position == "bottom-left":
                c_obj.drawString(margin, margin, label)
            elif position == "top-center":
                c_obj.drawCentredString(w / 2, h - margin, label)
            elif position == "top-right":
                c_obj.drawRightString(w - margin, h - margin, label)
            elif position == "top-left":
                c_obj.drawString(margin, h - margin, label)
            c_obj.save()
            buf.seek(0)

            num_page = PdfReader(buf).pages[0]
            page.merge_page(num_page)
            writer.add_page(page)

        with open(out, "wb") as fh:
            writer.write(fh)
        return ok(out, "page_numbers.pdf")
    except Exception as e:
        return err(str(e), 500)
    finally:
        p.unlink(missing_ok=True)


# ── API: Protect ───────────────────────────────────────────────────────────

@app.route("/api/protect", methods=["POST"])
def api_protect():
    f = request.files.get("file")
    if not f or not allowed(f.filename, ALLOWED_PDF):
        return err("Please upload a valid PDF file.")
    password = request.form.get("password", "").strip()
    if not password:
        return err("Please enter a password.")
    p = save_upload(f)
    out = out_path(".pdf")
    try:
        reader = PdfReader(str(p))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)
        with open(out, "wb") as fh:
            writer.write(fh)
        return ok(out, "protected.pdf")
    except Exception as e:
        return err(str(e), 500)
    finally:
        p.unlink(missing_ok=True)


# ── API: Unlock ────────────────────────────────────────────────────────────

@app.route("/api/unlock", methods=["POST"])
def api_unlock():
    f = request.files.get("file")
    if not f or not allowed(f.filename, ALLOWED_PDF):
        return err("Please upload a valid PDF file.")
    password = request.form.get("password", "").strip()
    p = save_upload(f)
    out = out_path(".pdf")
    try:
        try:
            pdf = pikepdf.open(str(p), password=password)
        except pikepdf.PasswordError:
            return err("Incorrect password. Please try again.")
        pdf.save(str(out))
        pdf.close()
        return ok(out, "unlocked.pdf")
    except Exception as e:
        return err(str(e), 500)
    finally:
        p.unlink(missing_ok=True)




# ── API: PDF to Word ───────────────────────────────────────────────────────

@app.route("/api/pdf-to-word", methods=["POST"])
def api_pdf_to_word():
    f = request.files.get("file")
    if not f or not allowed(f.filename, ALLOWED_PDF):
        return err("Please upload a valid PDF file.")
    
    p = save_upload(f)
    out = out_path(".docx")
    word = None
    
    try:
        # 1. Attempt High Quality conversion via Microsoft Word COM (Best for layout)
        if WINDOWS_COM_AVAILABLE:
            try:
                print(f"[*] Starting high-quality PDF to Word conversion for {f.filename}...")
                pythoncom.CoInitialize()
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                
                # Word can open PDF files directly and convert them
                abs_p = str(p.absolute())
                abs_out = str(out.absolute())
                
                # Open PDF
                doc = word.Documents.Open(abs_p)
                
                # Save as DOCX (Format 16)
                doc.SaveAs(abs_out, FileFormat=16) 
                doc.Close()
                print("[+] Word PDF-to-Word conversion successful.")
                
                return ok(out, "converted.docx")
                
            except Exception as com_err:
                print(f"[!] Word COM PDF-to-Word failed: {com_err}")
                # Fallback to pdf2docx
        
        # 2. Fallback to pdf2docx for environments without Word or if Word fails
        print("[*] Falling back to pdf2docx for conversion...")
        from pdf2docx import Converter
        cv = Converter(str(p))
        cv.convert(str(out))
        cv.close()
        return ok(out, "converted.docx")
            
    except Exception as e:
        print(f"[!!] PDF-to-Word conversion failure: {e}")
        return err(str(e), 500)
    finally:
        # Cleanup Word (Windows only)
        if WINDOWS_COM_AVAILABLE and word:
            try:
                word.Quit()
            except:
                pass
        if WINDOWS_COM_AVAILABLE:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

        # Cleanup upload
        p.unlink(missing_ok=True)


# ── API: PDF to Word (improved) ────────────────────────────────────────────



# ── API: Word to PDF ───────────────────────────────────────────────────────

@app.route("/api/word-to-pdf", methods=["POST"])
def api_word_to_pdf():
    f = request.files.get("file")
    if not f or not allowed(f.filename, ALLOWED_WORD):
        return err("Please upload a valid Word (.docx) file.")
    
    p = save_upload(f)
    out = out_path(".pdf")
    word = None
    
    try:
        # 1. Attempt High Quality conversion via Microsoft Word COM
        if WINDOWS_COM_AVAILABLE:
            try:
                print(f"[*] Starting high-quality conversion for {f.filename}...")
                pythoncom.CoInitialize()
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                
                # Open document
                abs_p = str(p.absolute())
                abs_out = str(out.absolute())
                doc = word.Documents.Open(abs_p)
                
                # Save as PDF (Format 17)
                doc.SaveAs(abs_out, FileFormat=17)
                doc.Close()
                print("[+] Word conversion successful.")
                
                return ok(out, "converted.pdf")
                
            except Exception as com_err:
                print(f"[!] Word COM failed: {com_err}")
                # Fallback to manual extraction
        
        # 2. Attempt LibreOffice conversion (Best for Linux/Docker)
        if not WINDOWS_COM_AVAILABLE:
            print("[*] Attempting LibreOffice conversion...")
            if convert_word_to_pdf_libreoffice(p, out):
                print("[+] LibreOffice conversion successful.")
                return ok(out, "converted.pdf")
            else:
                print("[!] LibreOffice conversion failed.")
                return err("Server error: High-fidelity PDF conversion failed.", 500)

            
    except Exception as e:
        print(f"[!!] Total conversion failure: {e}")
        return err(str(e), 500)
    finally:
        # Cleanup Word (Windows only)
        if WINDOWS_COM_AVAILABLE and word:
            try:
                word.Quit()
            except:
                pass
        if WINDOWS_COM_AVAILABLE:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

        # Cleanup upload
        p.unlink(missing_ok=True)


# ── API: Sign PDF ──────────────────────────────────────────────────────────

@app.route("/api/sign", methods=["POST"])
def api_sign():
    pdf_file = request.files.get("pdf")
    sig_file = request.files.get("signature")
    
    if not pdf_file or not allowed(pdf_file.filename, ALLOWED_PDF):
        return err("Please upload a valid PDF file.")
    # Check if a signature file was uploaded. If not, maybe use a default or error
    if not sig_file:
         return err("Please upload a signature image.")
         
    page_num = int(request.form.get("page", 1)) - 1
    position = request.form.get("position", "bottom-right")
    
    p_pdf = save_upload(pdf_file)
    p_sig = save_upload(sig_file)
    out = out_path(".pdf")
    
    try:
        doc = fitz.open(str(p_pdf))
        if page_num < 0 or page_num >= len(doc):
            return err(f"Invalid page number. PDF has {len(doc)} pages.")
            
        page = doc[page_num]
        w, h = page.rect.width, page.rect.height
        
        # Default signature size
        sig_w, sig_h = 150, 75
        margin = 50
        
        if position == "bottom-right":
            pos_rect = fitz.Rect(w - sig_w - margin, h - sig_h - margin, w - margin, h - margin)
        elif position == "bottom-left":
            pos_rect = fitz.Rect(margin, h - sig_h - margin, margin + sig_w, h - margin)
        elif position == "top-right":
            pos_rect = fitz.Rect(w - sig_w - margin, margin, w - margin, margin + sig_h)
        elif position == "top-left":
            pos_rect = fitz.Rect(margin, margin, margin + sig_w, margin + sig_h)
        else:
            pos_rect = fitz.Rect(w/2 - sig_w/2, h/2 - sig_h/2, w/2 + sig_w/2, h/2 + sig_h/2)
            
        page.insert_image(pos_rect, filename=str(p_sig))
        doc.save(str(out))
        doc.close()
        
        return ok(out, "signed.pdf")
    except Exception as e:
        return err(str(e), 500)
    finally:
        p_pdf.unlink(missing_ok=True)
        p_sig.unlink(missing_ok=True)




# ── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
