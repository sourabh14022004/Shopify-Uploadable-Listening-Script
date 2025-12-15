# Shopify CSV Converter - Script Summary

## Overview
This Python script (`main1.py`) converts messy, unstructured product CSV files into Shopify-ready CSV format that matches a provided template. It automates the complex process of transforming raw product data into a standardized format suitable for bulk import into Shopify.

## Core Functionality

### 1. **CSV Structure Detection & Header Promotion**
- Automatically detects if headers are embedded in the data rows (not in the first row)
- Searches the first 8 rows for header indicators (like "title", "brand")
- Promotes the detected header row to become the actual column headers

### 2. **Intelligent Column Detection**
The script uses flexible name matching to find columns, handling variations in naming:
- **Title**: "Title", "Product Title", "Name"
- **Brand/Vendor**: "Brand Name", "Vendor", "Brand"
- **Categories**: "Product category", "Category", "Subcategory", "Type"
- **Pricing**: "Final Price", "MRP", "Cost to Kiddo", "Cost"
- **Images**: Any column containing "product image", "image", or "image url"
- **Sizes**: Automatically detects size columns (NB, 0-3M, 2-3Y, S, M, L, XL, etc.)

### 3. **Product Variant Generation**
- Creates separate rows for each size variant of a product
- Sets `Option1 name` = "Size" and `Option1 value` = the size (e.g., "0-3M", "S", "M")
- All variants of the same product share the **same handle** (based on product title)
- If no sizes are found, creates a "Default" variant

### 4. **Handle Generation**
- Creates URL-friendly handles by slugifying product titles
- **All variants of the same product share the same handle** (regardless of price differences)
- Example: "Green Printed Night Suit" → `green-printed-night-suit`
- Handles are consistent across all size variants

### 5. **Smart Price Processing**
- **Price Calculation**: 
  - Takes "Final Price" and rounds it to the nearest 9 that is **greater than** the original price
  - If price already ends with 9, keeps it as is (if greater) or adjusts minimally
  - Examples: 999 → 1009, 1000 → 1009, 1005 → 1009
- **Price Mapping**:
  - Final Price → Price (rounded to nearest 9, greater than original)
  - MRP → Compare-at price
  - Cost to Kiddo → Cost per item
- **Fallback**: If Final Price is missing, can use Cost to Kiddo (configurable)

### 6. **Image Management**
- Detects all product image columns
- **Primary image** (first image) is placed on the first variant row with Image position = 1
- **Additional images** become separate image-only rows containing:
  - Handle (to link to product)
  - Product image URL
  - Image position (2, 3, 4, etc.)
- Automatically includes "Size chart" images if present

### 7. **Tag Generation**
Automatically adds tags from multiple sources:
- **Vendor/Brand**: Added from Brand column
- **Product Category**: Added from Category column
- **Type**: Added from Subcategory/Type column
- **Size**: Added for each variant (e.g., "0-3M", "S", "M")
- **Gender/Age Tags** (only when column value = 1):
  - "Boy" column with value 1 → adds "Boy" tag
  - "Girl" column with value 1 → adds "Girl" tag
  - "Unisex" column with value 1 → adds "Unisex" tag
  - "NB" column with value 1 → adds "Newborn" tag
  - "Girls + Unisex" column with value 1 → adds both "Girl" and "Unisex" tags
  - "Boys + Unisex" column with value 1 → adds both "Boy" and "Unisex" tags
  - Handles columns with asterisks (e.g., "*Boy", "*Girl")
  - **Only adds tags when value is exactly 1** (string or number)

### 8. **Metadata & Optional Fields**
- Copies optional metafield columns when present:
  - Fabric, Wash Care, Material, Shelf, Test
  - Variant Image, Variant Weight Unit, Variant Tax Code, Shelf No
- Sets standard Shopify flags:
  - Published on online store: TRUE
  - Status: Active
  - Charge tax: TRUE
  - Requires shipping: TRUE
  - Fulfillment service: manual
  - Gift card: FALSE

### 9. **SEO Optimization**
- Sets SEO title = Product title
- Sets SEO description = Product description (truncated to 320 characters)
- Maps Google Shopping category from Product category

### 10. **Output Formatting**
- Matches the exact column order of the provided template CSV
- Removes inventory-related columns (inventory policy, inventory quantity, etc.)
- Preserves all template columns even if not populated
- Outputs clean, Shopify-ready CSV format

## Key Features

### ✅ **Flexible Input Handling**
- Handles messy, unstructured CSV files
- Works with various column naming conventions
- Automatically detects and promotes headers

### ✅ **Product Variant Management**
- Creates proper size variants for Shopify
- Maintains consistent handles across variants
- Handles products with different prices per variant (same handle, different prices)

### ✅ **Smart Pricing**
- Ensures prices always end with 9
- Guarantees output price is greater than input price
- Handles edge cases (prices already ending in 9)

### ✅ **Comprehensive Tagging**
- Automatic tag generation from multiple sources
- Gender/age tagging based on column values
- Prevents duplicate tags

### ✅ **Batch Processing**
- Can process single or multiple CSV files
- Auto-generates output filenames
- Supports directory-based output

## Usage

```bash
# Single file
python main1.py --source "input.csv" \
    --template "shopify_template.csv" \
    --out "output.csv"

# Multiple files
python main1.py --source "file1.csv" "file2.csv" "file3.csv" \
    --template "shopify_template.csv" \
    --out "./output/"

# Without output path (auto-generates names)
python main1.py --source "file1.csv" "file2.csv" \
    --template "shopify_template.csv"
```

## Dependencies
- Python 3.x
- pandas library

## Output
Produces Shopify-ready CSV files that can be directly imported into Shopify admin, with:
- Proper variant structure
- Consistent handles
- Optimized pricing
- Comprehensive tags
- All required Shopify fields populated

