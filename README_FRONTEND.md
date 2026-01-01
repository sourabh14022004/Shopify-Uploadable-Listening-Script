# CSV to Shopify Converter - Web Interface

A simple and clean web-based frontend for converting product CSVs to Shopify format.

## Features

- 🎨 Modern, clean UI with drag-and-drop file upload
- 📁 Support for multiple source files
- ⚡ Real-time processing status
- 📥 Direct download of converted files
- ✅ Error handling and validation

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

1. **Upload Template File**: Select or drag & drop your Shopify template CSV file
2. **Upload Source File(s)**: Select or drag & drop one or more source CSV files to convert
3. **Configure Options**: 
   - Check/uncheck "Fallback Price to Cost" option
4. **Convert**: Click the "Convert to Shopify Format" button
5. **Download**: Once conversion is complete, download the converted files

## File Structure

```
csv/
├── app.py              # Flask backend application
├── main1.py            # Core conversion logic
├── templates/
│   └── index.html     # Web frontend
└── requirements.txt   # Python dependencies
```

## Notes

- Maximum file size: 50MB per file
- All uploaded files are temporarily stored and cleaned up after processing
- The application runs on port 5000 by default

