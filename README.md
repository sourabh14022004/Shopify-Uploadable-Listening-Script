# Shopify CSV Converter

A powerful Python script that converts messy, unstructured product CSV files into Shopify-ready format. Automatically handles product variants, pricing, images, tags, and all Shopify-required fields.

## 🚀 Features

- **Smart CSV Processing**: Automatically detects and promotes headers even when embedded in data rows
- **Flexible Column Detection**: Handles various column naming conventions with intelligent matching
- **Product Variant Management**: Creates proper size variants with consistent handles across all variants
- **Intelligent Pricing**: Rounds prices to nearest 9 (greater than original) and maps pricing fields correctly
- **Image Management**: Organizes primary and additional images with proper positioning
- **Automatic Tagging**: Generates comprehensive tags from vendor, category, type, size, and gender/age indicators
- **Batch Processing**: Process single or multiple CSV files at once
- **Template Matching**: Outputs CSV in exact column order matching your Shopify template

## 📋 Requirements

- Python 3.x
- pandas library

## 🔧 Installation

1. Clone this repository or download the script
2. Install required dependencies:

```bash
pip install pandas
```

Or create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 💻 Usage

### Basic Usage

```bash
python main1.py --source "input.csv" \
    --template "shopify_template.csv" \
    --out "output.csv"
```

### Process Multiple Files

```bash
python main1.py --source "file1.csv" "file2.csv" "file3.csv" \
    --template "shopify_template.csv" \
    --out "./output/"
```

### Auto-generate Output Names

```bash
python main1.py --source "file1.csv" "file2.csv" \
    --template "shopify_template.csv"
```

## 📝 Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--source` | Yes | Source CSV file(s) to convert. Can specify multiple files. |
| `--template` | Yes | Shopify template CSV file to match column order |
| `--out` | No | Output CSV path or directory. If not specified, auto-generates names based on source files |
| `--no-fallback-cost` | No | Disable fallback to Cost when Final Price is missing |

## 🎯 How It Works

### 1. Header Detection
The script automatically searches the first 8 rows for header indicators (like "title", "brand") and promotes the detected row to become column headers.

### 2. Column Mapping
Intelligently detects columns using flexible name matching:
- **Title**: "Title", "Product Title", "Name"
- **Brand**: "Brand Name", "Vendor", "Brand"
- **Pricing**: "Final Price", "MRP", "Cost to Kiddo"
- **Images**: Any column containing "image" or "image url"
- **Sizes**: Automatically detects size columns (NB, 0-3M, S, M, L, etc.)

### 3. Variant Creation
- Creates separate rows for each size variant
- All variants share the same handle (based on product title)
- Sets `Option1 name` = "Size" and `Option1 value` = the size

### 4. Price Processing
- **Price**: Final Price rounded to nearest 9 (greater than original)
  - Example: 999 → 1009, 1000 → 1009, 1005 → 1009
- **Compare-at price**: From MRP column
- **Cost per item**: From Cost to Kiddo column

### 5. Image Organization
- Primary image placed on first variant row (Image position = 1)
- Additional images become separate image-only rows with proper positioning

### 6. Tag Generation
Automatically adds tags from:
- Vendor/Brand name
- Product category
- Type/Subcategory
- Size (for each variant)
- Gender/Age tags (when columns have value = 1):
  - `Boy` = 1 → adds "Boy"
  - `Girl` = 1 → adds "Girl"
  - `Unisex` = 1 → adds "Unisex"
  - `NB` = 1 → adds "Newborn"
  - `Girls + Unisex` = 1 → adds "Girl" and "Unisex"
  - `Boys + Unisex` = 1 → adds "Boy" and "Unisex"

## 📊 Input CSV Format

Your input CSV should contain:
- Product title/name
- Pricing information (Final Price, MRP, Cost)
- Size columns (NB, 0-3M, S, M, L, etc.)
- Image URLs
- Optional: Brand, Category, Type, Gender/Age indicators

## 📤 Output Format

The script generates Shopify-ready CSV with:
- Proper variant structure (one row per size variant)
- Consistent handles (all variants of same product share handle)
- Optimized pricing (rounded to nearest 9)
- Comprehensive tags
- All required Shopify fields populated
- Images properly organized with positioning

## 🔍 Example

**Input CSV:**
```csv
Title,Final Price,MRP,Cost to Kiddo,Boy,Girl,0-3M,3-6M,Image URL
Green Printed Night Suit,999,579,231.5,1,0,1,1,https://image1.jpg
```

**Output CSV:**
```csv
Title,Handle,Price,Compare-at price,Cost per item,Option1 name,Option1 value,Tags,Product image URL,Image position
Green Printed Night Suit,green-printed-night-suit,1009,579,231.5,Size,0-3M,"Brand, Category, Boy",https://image1.jpg,1
Green Printed Night Suit,green-printed-night-suit,1009,579,231.5,Size,3-6M,"Brand, Category, Boy",https://image1.jpg,1
```

## 🛠️ Advanced Features

### Handle Generation
- All variants of the same product share the same handle
- Handles are URL-friendly (slugified from title)
- Example: "Green Printed Night Suit" → `green-printed-night-suit`

### Price Rounding Logic
- Prices are rounded to nearest 9 that is **greater than** the original
- If price already ends with 9, it's kept as is (if greater) or adjusted minimally
- Ensures consistent pricing strategy

### Gender/Age Tag Detection
- Supports columns with asterisks: `*Boy`, `*Girl`, `*Unisex`
- Handles various formats: "Girls + Unisex", "Girls+Unisex", "Boys + Unisex"
- Only adds tags when column value is exactly 1

## 📁 File Structure

```
.
├── main1.py              # Main conversion script
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── SCRIPT_SUMMARY.md     # Detailed script documentation
```

## ⚠️ Notes

- The script removes inventory-related columns by default to match Shopify import requirements
- All variants of the same product will have the same handle, regardless of price differences
- Images are automatically organized: primary image on first variant, additional images as separate rows
- Tags are automatically generated and deduplicated

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available for use.

## 🐛 Troubleshooting

**Issue**: Tags not being added
- **Solution**: Ensure gender/age columns have value exactly `1` (not "1", "1.0", or any other value)

**Issue**: Prices not rounding correctly
- **Solution**: Check that Final Price column contains numeric values

**Issue**: Variants not created
- **Solution**: Ensure size columns contain non-zero values (1, "1", or any non-empty value)

## 📞 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Made with ❤️ for Shopify store owners**

