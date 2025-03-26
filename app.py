from flask import Flask, request, render_template_string
import zipfile
import os
from werkzeug.utils import secure_filename
import random
import string
import PyPDF2
import docx
import json

app = Flask(__name__)

# Basic HTML template with file upload form
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Essay Processor</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 20px auto; padding: 0 20px; }
        .form-container { margin: 20px 0; }
        .result { white-space: pre-wrap; background: #f0f0f0; padding: 15px; margin-top: 20px; }
        textarea { width: 100%; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Essay Processor</h1>


<h3> Steps to submitting essays: </h3>

<h4>1. Go to google classroom assignemnt</h4> <img src = "https://assets.onecompiler.app/439vx5wbx/3x2zp2yd7/image_2025-03-26_012550996.png">
<h4>2. Click on student work</h4> <img src = "https://assets.onecompiler.app/439vx5wbx/3x2zp2yd7/image_2025-03-26_012620267.png">
<h4>3. Click on the folder icon, below "accepting submissions"</h4> <img src = "https://assets.onecompiler.app/439vx5wbx/3x2zp2yd7/image_2025-03-26_012643368.png">
<h4>4. Download the google drive folder </h4> <img src = "https://assets.onecompiler.app/439vx5wbx/3x2zp2yd7/image_2025-03-26_012708255.png">

<h4>5. Repeat for another google classroom assignment</h4>

<h4>6. Attatch both folders here and press "process essays" </h4>

<h4>7. Copy and paste the generated text and email it to my email!  Thanks!</h4>

    <div class="form-container">
        <form method="post" enctype="multipart/form-data">
            <div>
                <label>Enter names of students (one per line):</label><br>
                <textarea name="strings" rows="5" required></textarea>
            </div>
            <div>
                <label>First ZIP file:</label><br>
                <input type="file" name="zipfile1" accept=".zip" required title="Upload first ZIP file containing PDF and/or DOCX files">
            </div>
            <div>
                <label>Second ZIP file:</label><br>
                <input type="file" name="zipfile2" accept=".zip" required title="Upload second ZIP file containing PDF and/or DOCX files">
            </div>
            <button type="submit">Process Essays</button>
        </form>
    </div>
    {% if result %}
    <div class="result">
        {{ result }}
    </div>
    {% endif %}
</body>
</html>
'''


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    result = None
    if request.method == 'POST':
        if 'zipfile1' not in request.files or 'zipfile2' not in request.files or 'strings' not in request.form:
            return 'Please provide both ZIP files and strings'

        strings = request.form['strings'].split('\n')
        strings = [s.strip() for s in strings if s.strip()]
        if not strings:
            return 'Please enter at least one string'

        file1 = request.files['zipfile1']
        file2 = request.files['zipfile2']
        
        if file1.filename == '' or file2.filename == '':
            return 'Please select both ZIP files'

        if file1.filename.endswith('.zip') and file2.filename.endswith('.zip'):
            temp_dir = 'temp_uploads'

            # Create temp directory if it doesn't exist
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            # Extract and process files from both ZIPs
            extracted_files = []
            
            # Process first ZIP
            zip_path1 = os.path.join(temp_dir, secure_filename(file1.filename))
            file1.save(zip_path1)
            with zipfile.ZipFile(zip_path1, 'r') as zip_ref:
                files1 = [f for f in zip_ref.namelist() if f.endswith(('.pdf', '.docx', '.gdoc'))]
                for doc_file in files1:
                    zip_ref.extract(doc_file, temp_dir)
                extracted_files.extend(files1)
            
            # Process second ZIP
            zip_path2 = os.path.join(temp_dir, secure_filename(file2.filename))
            file2.save(zip_path2)
            with zipfile.ZipFile(zip_path2, 'r') as zip_ref:
                files2 = [f for f in zip_ref.namelist() if f.endswith(('.pdf', '.docx', '.gdoc'))]
                for doc_file in files2:
                    zip_ref.extract(doc_file, temp_dir)
                extracted_files.extend(files2)

            # Read file contents and process them
            try:
                print("Extracted files:", extracted_files)
                file_contents = {}
                for file in extracted_files:
                    file_path = os.path.join(temp_dir, file)
                    if file.endswith('.pdf'):
                        with open(file_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            text = ""
                            for page in pdf_reader.pages:
                                text += page.extract_text()
                            file_contents[file] = file + " " + text

                    elif file.endswith('.docx'):
                        doc = docx.Document(file_path)
                        text = " ".join(
                            [paragraph.text for paragraph in doc.paragraphs])
                        file_contents[file] = file + " " + text
                    elif file.endswith('.gdoc'):
                        with open(file_path, 'r') as f:
                            gdoc_json = json.loads(f.read())
                            # Google Docs export as JSON with document content
                            if 'doc' in gdoc_json:
                                text = gdoc_json['doc']['body']
                                file_contents[file] = file + " " + text

                result = process_pdfs(strings, file_contents)
                print("Processing result:", result)
            except Exception as e:
                result = f"Error processing files: {str(e)}"
                print("Error:", e)
            finally:
                # Clean up
                import shutil
                shutil.rmtree(temp_dir)

    return render_template_string(HTML_TEMPLATE, result=result)


def generate_random_numbers(strings):
    """Generate unique random numbers for each string."""
    return {s: ''.join(random.choices(string.digits, k=10)) for s in strings}


def process_pdfs(strings, pdf_contents):
    """Process PDFs according to the specified steps."""
    name_to_number = generate_random_numbers(strings)
    result_text = ""

    for filename, text in pdf_contents.items():
        # Find the first occurrence of a Name
        found_name = None
        for word in text.split():
            if word in name_to_number:
                found_name = word
                break
        if found_name:
            result_text += f"##{found_name} {text}"

    # Step 3: Replace Names with Numbers
    for name, number in name_to_number.items():
        result_text = result_text.replace(name, number)

    result_text = result_text.replace("\n", " ")
    result_text = result_text.replace(" ##", " \n \n ##")

    return result_text


# Example usage:

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
