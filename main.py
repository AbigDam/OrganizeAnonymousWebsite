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
    <div class="form-container">
        <form method="post" enctype="multipart/form-data">
            <div>
                <label>Enter names of students (one per line):</label><br>
                <textarea name="strings" rows="5" required></textarea>
            </div>
            <div>
                <input type="file" name="zipfile" accept=".zip" required title="Upload a ZIP file containing PDF and/or DOCX files">
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
        if 'zipfile' not in request.files or 'strings' not in request.form:
            return 'Please provide both ZIP file and strings'

        strings = request.form['strings'].split('\n')
        strings = [s.strip() for s in strings if s.strip()]
        if not strings:
            return 'Please enter at least one string'

        print(strings)
        file = request.files['zipfile']
        if file.filename == '':
            return 'No file selected'

        if file and file.filename and file.filename.endswith('.zip'):
            filename = secure_filename(file.filename)
            temp_dir = 'temp_uploads'

            # Create temp directory if it doesn't exist
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            zip_path = os.path.join(temp_dir, filename)
            file.save(zip_path)

            # Extract and process files
            extracted_files = []
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get list of PDF, DOCX and GDOC files from zip
                extracted_files = [
                    f for f in zip_ref.namelist()
                    if f.endswith(('.pdf', '.docx', '.gdoc'))
                ]
                # Extract files
                for doc_file in extracted_files:
                    zip_ref.extract(doc_file, temp_dir)

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
    result_text = result_text.replace(" ##", " \n ##")

    return result_text


# Example usage:

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
