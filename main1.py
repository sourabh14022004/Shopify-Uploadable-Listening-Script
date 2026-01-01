#!/usr/bin/env python3
"""
shopify_csv_converter.py

Convert messy product CSVs (like "Listings - Moms home.csv") into a Shopify-uploadable CSV
matching the reference template (e.g. product_template_csv_unit_price (2).csv).

Features:
- Promotes a header row if the uploaded CSV has headers as the first data row.
- Detects Title, Cost to Kiddo, MRP, Final Price columns (flexible name matching).
- Detects image columns (product image columns) and size columns (NB, 0-3M, 2-3Y, S, M, etc.).
- Creates variants per size (Option1 name = "Size").
- Cleans handles (slugify; remove trailing size suffix when present).
- First row per product: full product + primary image (Image position = 1).
  Subsequent images become image-only rows (only Handle + Product image URL + Image position).
- Price mapping: Final Price -> Price; MRP -> Compare-at price; Cost to Kiddo -> Cost per item.
  If Final Price missing, can fallback to Cost to Kiddo (configurable).
- Removes inventory-related columns by default to match a working reference import.
- Adds Vendor, Product category, Type, and Size into Tags (comma separated).
- Outputs the CSV in the exact column order of the provided template.

Dependencies:
    pip install pandas

Usage examples:
    # Single file:
    python main1.py --source "Listings - AJ Design.csv" \
        --template "SomerSault_listings1_shopify_final_inventory-fixed.csv" \
        --out "Listings - AJ Design - Converted - Shopify.csv"
    
    # Multiple files (output to directory):
    python main1.py --source "Listings - AJ Design.csv" "Listings - Orange sugar.csv" "Listings - Kid kens (1).csv" \
        --template "SomerSault_listings1_shopify_final_inventory-fixed.csv" \
        --out "./output/"
    
    # Multiple files (auto-generated output names):
    python main1.py --source "Listings - AJ Design.csv" "Listings - Orange sugar.csv" \
        --template "SomerSault_listings1_shopify_final_inventory-fixed.csv"

"""

import argparse
import pandas as pd
import re
import math
from pathlib import Path

# ---------------------------
# Helper functions
# ---------------------------

def slugify(text: str) -> str:
    t = str(text or "").strip().lower()
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"-+", "-", t)
    return t.strip("-")

def detect_header_row(df_raw: pd.DataFrame, max_rows: int = 8):
    """
    Look for a row in the first max_rows rows that contains 'title' or 'brand' etc.
    Returns header_row_index (0-based). Default 0 if nothing found.
    """
    for i in range(min(max_rows, len(df_raw))):
        row_vals = [str(x).strip().lower() for x in df_raw.iloc[i].tolist()]
        if any("title" == v or "title" in v for v in row_vals):
            return i
    return 0

def clean_price(x):
    if x is None:
        return ""
    s = str(x).strip()
    if s == "":
        return ""
    s2 = ''.join(ch for ch in s if ch.isdigit() or ch in ".-")
    if s2 == "":
        return ""
    try:
        return f"{int(s2)}"
    except:
        return s2

def round_to_nearest_9(price_str):
    """
    Round a price string to the nearest 9 (e.g., 1000 -> 999, 1050 -> 1049).
    Returns the rounded price as a string (integer).
    """
    if not price_str or price_str.strip() == "":
        return ""
    try:
        price_float = float(price_str)
        if price_float <= 0:
            return price_str
        # Round to nearest 10 (using standard rounding: round half up), then subtract 1 to get nearest 9
        # Use int((x + 5) / 10) to round half up instead of Python's banker's rounding
        rounded = int((price_float + 5) / 10) * 10 - 1
        # Ensure it doesn't go below 0
        if rounded < 0:
            rounded = 0
        return f"{int(rounded)}"
    except:
        return price_str



def find_col_by_names(cols, names):
    """
    Try to find a column in cols whose normalized name matches any of the names provided.
    """
    cols_norm = {re.sub(r"[^a-z0-9]", "", c.lower()): c for c in cols}
    for name in names:
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        if key in cols_norm:
            return cols_norm[key]
    # fallback: substring match
    for name in names:
        needle = name.lower().replace(" ", "")
        for c in cols:
            if needle in c.lower().replace(" ", ""):
                return c
    return None

def detect_image_columns(cols):
    return [c for c in cols if "product image" in c.lower() or "image" in c.lower() or "image url" in c.lower()]

def detect_size_columns(cols):
    # Common size candidates; match exact header or simple variants
    size_candidates = [
        "NB","0-2M","2-4M","4-6M","0-3M","3-6M","6-9M","6-12M","9-12M","12-18M","18-24M", "0-6M Toys", "6-12M Toys", "12-18M Toys", "18-24M Toys",
        "1-2Y","2-3Y","3-4Y","4-5Y","5-6Y","One Size","S","M","L","XL","XXL","2 Plus","3 Plus","4 Plus","5 Plus","6 Plus","All Ages"
    ]
    size_cols = [c for c in cols if any(re.fullmatch(r"\s*"+re.escape(sc)+r"\s*", c.strip(), flags=re.I) for sc in size_candidates)]
    # fallback: headers that end with m or y (digit patterns)
    for c in cols:
        if c not in size_cols and re.search(r"\d+\s*[-]?\s*\d*\s*[my]$", c.strip(), flags=re.I):
            size_cols.append(c)
    return size_cols

def remove_inventory_like_columns(df: pd.DataFrame):
    inv_keys = set(["inventorypolicy","variantinventorypolicy","inventoryquantity","continuesellingwhenoutofstock","inventorytracker","inventoryquantity"])
    keep = [c for c in df.columns if re.sub(r"[^a-z0-9]","", c.lower()) not in inv_keys]
    return df[keep]

def normalize_size_for_matching(size_str):
    """
    Normalize size string for matching - removes spaces, converts to lowercase, handles variations
    """
    if not size_str:
        return ""
    # Convert to lowercase and remove extra spaces
    normalized = str(size_str).lower().strip()
    # Normalize dashes and spaces - keep structure but normalize
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'\s*-\s*', '-', normalized)
    normalized = re.sub(r'\s*–\s*', '-', normalized)
    normalized = re.sub(r'\s*—\s*', '-', normalized)
    # Remove all spaces for matching
    normalized = normalized.replace(' ', '')
    return normalized

def get_boy_age_group_tags(variants):
    """
    Determine age group tags for boys based on size variants.
    Returns list of age group tags like ["Boy 0-3m", "Boy 3-6m", etc.]
    """
    age_group_tags = []
    
    # Normalize all variants for matching
    normalized_variants = [normalize_size_for_matching(v) for v in variants if v and v != "Default"]
    
    # Define age groups with their size patterns (all variations normalized)
    # Pattern matching: we'll check if the normalized variant contains or matches the pattern
    age_groups = [
        {
            "tag": "Boy 0-3m",
            "patterns": ["nb", "0-2m", "2-4m", "0-3m", "0-6m", "0-6mtoys"]
        },
        {
            "tag": "Boy 3-6m",
            "patterns": ["2-4m", "4-6m", "3-6m","0-6m", "0-6mtoys"]
        },
        {
            "tag": "Boy 6-12m",
            "patterns": ["6-9m", "6-12m", "9-12m", "0-12m", "6-12mtoys"]
        },

        {
            "tag": "Boy 1-2y",
            "patterns": ["12-18m","15-18m", "18-24m", "18m-3y", "1-2y", "1-3y", "12-18mtoys", "18-24mtoys"]
        },
        {
            "tag": "Boy 2-3y",
            "patterns": ["18m-3y", "1-3y", "2-3y", "2-4y", "2-2.5y", "2.5-3y",]
        },
        {
            "tag": "Boy 3-4y",
            "patterns": ["2-4y", "3-4y", "3-3.5y", "3.5-4y"]
        },
        {
            "tag": "Boy 4-5y",
            "patterns": ["3-4y", "4-5y", "5-6y", "5-7y","4-4.5y" "4.5-5y"]
        },
        {
            "tag": "Boy 5+ y",
            "patterns": ["5-6y", "5-7y", "6-7y", "7-8y", "5-5.5y", "5.5-6y"]
        }
    ]
    
    # Check each age group
    for age_group in age_groups:
        # Check if any variant matches any pattern in this age group
        for variant in normalized_variants:
            if not variant:
                continue
            for pattern in age_group["patterns"]:
                # Exact match or pattern is contained in variant
                if pattern == variant or (len(pattern) >= 3 and pattern in variant):
                    if age_group["tag"] not in age_group_tags:
                        age_group_tags.append(age_group["tag"])
                    break
            if age_group["tag"] in age_group_tags:
                break
    
    return age_group_tags

def get_girl_age_group_tags(variants):
    """
    Determine age group tags for girls based on size variants.
    Returns list of age group tags like ["Girl 0-3m", "Girl 3-6m", etc.]
    """
    age_group_tags = []
    
    # Normalize all variants for matching
    normalized_variants = [normalize_size_for_matching(v) for v in variants if v and v != "Default"]
    
    # Define age groups with their size patterns (all variations normalized)
    # Same patterns as boys, but with "Girl" prefix
    age_groups = [
        {
            "tag": "Girl 0-3m",
            "patterns": ["nb", "0-2m", "2-4m", "0-3m", "0-6m", "0-6mtoys"]
        },
        {
            "tag": "Girl 3-6m",
            "patterns": ["2-4m", "24m", "4-6m", "3-6m", "0-6m", "0-6mtoys"]
        },
        {
            "tag": "Girl 6-12m",
            "patterns": ["6-9m", "6-12m", "9-12m", "0-12m", "6-12mtoys"]
        },
        {
            "tag": "Girl 1-2y",
            "patterns": ["12-18m", "15-18m", "18-24m", "18m-3y", "1-2y", "1-3y", "12-18mtoys", "18-24mtoys"]
        },
        {
            "tag": "Girl 2-3y",
            "patterns": ["18m-3y","1-3y", "13y", "2-3y", "2-4y", "2-2.5y", "2.5-3y"]
        },
        {
            "tag": "Girl 3-4y",
            "patterns": ["2-4y", "3-4y", "3-3.5y", "3.5-4y"]
        },
        {
            "tag": "Girl 4-5y",
            "patterns": ["3-4y","4-5y", "5-6y", "5-7y"]
        },
        {
            "tag": "Girl 5+ y",
            "patterns": ["5-6y", "5-7y", "6-7y", "7-8y"]
        }
    ]
    
    # Check each age group
    for age_group in age_groups:
        # Check if any variant matches any pattern in this age group
        for variant in normalized_variants:
            if not variant:
                continue
            for pattern in age_group["patterns"]:
                # Exact match or pattern is contained in variant
                if pattern == variant or (len(pattern) >= 3 and pattern in variant):
                    if age_group["tag"] not in age_group_tags:
                        age_group_tags.append(age_group["tag"])
                    break
            if age_group["tag"] in age_group_tags:
                break
    
    return age_group_tags

# ---------------------------
# Core processing
# ---------------------------

def process_file(source_csv: str, template_csv: str, out_csv: str, fallback_price_to_cost: bool = True):
    src_path = Path(source_csv)
    tpl_path = Path(template_csv)
    out_path = Path(out_csv)

    # read source raw (no header) to allow header promotion
    raw = pd.read_csv(src_path, header=None, dtype=str).fillna("")
    header_row_idx = detect_header_row(raw, max_rows=8)
    header_row = raw.iloc[header_row_idx].astype(str).tolist()
    df = raw[header_row_idx+1:].copy().reset_index(drop=True)
    # assign header (use header row entries or generated names)
    df.columns = [str(h).strip() if str(h).strip()!="" else f"unnamed_{i}" for i,h in enumerate(header_row)]

    # load template to preserve column order
    tpl = pd.read_csv(tpl_path, dtype=str).fillna("")
    template_cols = list(tpl.columns)
    
    # Add new optional metafield/support columns if they don't exist in template.
    # These map to the new Shopify export headers we received.
    optional_extra_cols = {
        "Fabric": ["Fabric", "Fabric (product.metafields.custom.fabric)"],
        "Wash Care": ["Wash Care", "Wash care", "Wash Care (product.metafields.custom.wash_care)"],
        "Material": ["Material", "Material (product.metafields.custom.material)"],
        "Shelf": ["Shelf", "Shelf (product.metafields.custom.shelf)"],
        "Test": ["Test", "Test (product.metafields.custom.test)"],
        "Variant Image": ["Variant Image", "Variant image"],
        "Variant Weight Unit": ["Variant Weight Unit", "Variant weight unit"],
        "Variant Tax Code": ["Variant Tax Code", "Variant tax code"],
        "Shelf No": ["Shelf No", "Shelf Number"],
        "Sizes": ["Sizes", "Size"]
    }
    for col_name in optional_extra_cols.keys():
        if col_name not in template_cols:
            template_cols.append(col_name)
    
    # Add inventory, status, and SKU columns if they don't exist in template
    inventory_cols = ["Inventory tracker", "Inventory policy", "Inventory quantity", "Status", "SKU"]
    for col_name in inventory_cols:
        if col_name not in template_cols:
            template_cols.append(col_name)

    # auto-detect columns
    cols = list(df.columns)
    title_col = find_col_by_names(cols, ["Title","Product Title","Name"])
    brand_col = find_col_by_names(cols, ["Brand Name","Vendor","Brand"])
    prodcat_col = find_col_by_names(cols, ["Product category","Category"])
    subcat_col = find_col_by_names(cols, ["Subcategory","Sub Category","Type"])
    subsub_col = find_col_by_names(cols, ["Sub Sub Category","SubSubCategory"])
    # Detect columns with asterisks for tags
    # Search for columns that match these patterns (handling asterisks)
    subcat_col = find_col_by_names(cols, ["Subcategory","Sub Category","Type"])
    subsubcategory_col = find_col_by_names(cols, ["Sub Sub Category","SubSubCategory"])
    season_col = find_col_by_names(cols, ["Season", "Season"])
    campaign_col = find_col_by_names(cols, ["Campaign"])
    sizes_col = find_col_by_names(cols, ["Sizes", "Size"])
    milestone_dev_col = find_col_by_names(cols, ["Milestone Development", "Milestone development"])
    make_col = find_col_by_names(cols, ["Make"])
    # Detect age columns (2+, 3+, 4+, 5+, 6+, All Ages)
    age_2plus_col = find_col_by_names(cols, ["2 Plus"])
    age_3plus_col = find_col_by_names(cols, ["3 Plus"])
    age_4plus_col = find_col_by_names(cols, ["4 Plus"])
    age_5plus_col = find_col_by_names(cols, ["5 Plus"])
    age_6plus_col = find_col_by_names(cols, ["6 Plus"])
    all_ages_col = find_col_by_names(cols, ["All Ages"])
    drop_active_col = find_col_by_names(cols, ["DROP_ACTIVE", "Drop Active", "drop_active"])

    # Detect inventory and status columns
    inventory_tracker_col = find_col_by_names(cols, ["Inventory tracker", "Inventory Tracker"])
    inventory_policy_col = find_col_by_names(cols, ["Inventory policy", "Inventory Policy"])
    inventory_quantity_col = find_col_by_names(cols, ["Inventory quantity", "Inventory Quantity"])
    status_col = find_col_by_names(cols, ["Status"])
    sku_col = find_col_by_names(cols, ["SKU", "Sku", "sku"])
    cost_col = find_col_by_names(cols, ["Cost to Kiddo","Cost"])
    mrp_col = find_col_by_names(cols, ["MRP"])
    final_col = find_col_by_names(cols, ["Selling Price"])

    image_cols = detect_image_columns(cols)
    size_cols = detect_size_columns(cols)

    # Ensure we have a title column
    if not title_col:
        # pick a column with non-numeric content as Title
        for c in cols:
            sample = df[c].astype(str).str.strip().head(10).tolist()
            if any(s and not s.isdigit() for s in sample):
                title_col = c
                break
        if not title_col:
            title_col = cols[0]

    # Prepare title column
    df[title_col] = df[title_col].astype(str)
    
    # determine template handle column name (like 'URL handle' or 'Handle')
    handle_template_col = next((c for c in template_cols if "handle" in re.sub(r"[^a-z0-9]","", c.lower())), None)

    out_rows = []
    for _, row in df.iterrows():
        title = str(row.get(title_col,"")).strip()
        if title == "" or title.lower() == "nan":
            continue
        
        # Create handle based only on title - all variants of same product share same handle
        handle_base = slugify(title)
        # find sizes for this row
        variants = []
        for sc in size_cols:
            val = row.get(sc, "")
            if isinstance(val, str):
                if val.strip() not in ["", "0", "nan"]:
                    variants.append(sc.strip())
            else:
                try:
                    if not math.isnan(float(val)) and float(val) != 0:
                        variants.append(sc.strip())
                except:
                    pass
        if not variants:
            variants = ["Default"]

        images = []
        for ic in image_cols:
            url = str(row.get(ic,"")).strip()
            if url and url.lower() != "nan" and url not in images:
                images.append(url)
        # Add Size chart to images if it exists
        size_chart_col = find_col_by_names(cols, ["Size chart", "Size Chart", "Sizechart"])
        if size_chart_col and size_chart_col in df.columns:
            size_chart_url = str(row.get(size_chart_col,"")).strip()
            if size_chart_url and size_chart_url.lower() != "nan" and size_chart_url not in images:
                images.append(size_chart_url)
        primary_image = images[0] if images else ""

        # Get prices directly from this row
        final_price = clean_price(row.get(final_col, "")) if final_col else ""
        mrp_price = clean_price(row.get(mrp_col, "")) if mrp_col else ""
        cost_price = clean_price(row.get(cost_col, "")) if cost_col else ""
        
        first_variant = True
        # Get base SKU from source if available, otherwise generate from handle
        base_sku = ""
        if sku_col and sku_col in df.columns:
            base_sku = str(row.get(sku_col, "")).strip()
        if not base_sku or base_sku.lower() == "nan":
            # Generate base SKU from handle (uppercase)
            base_sku = handle_base.upper()

        for size in variants:
            out = {c: "" for c in template_cols}
            out["Title"] = title
            if handle_template_col:
                out[handle_template_col] = handle_base
            
            # Generate unique SKU per variant
            if "SKU" in template_cols:
                if size != "Default":
                    # Create unique SKU: base_sku + normalized size
                    size_normalized = slugify(size).upper().replace("-", "")
                    sku = f"{base_sku}-{size_normalized}"
                else:
                    # For default/no size variant, use base SKU
                    sku = base_sku
                out["SKU"] = sku

            # Description composes common fields if available (excluding Fabric and Wash Care)
            desc_parts = []
            for p in ["Product Specifcation","Product Specification","Product specification"]:
                if p in df.columns and str(row.get(p,"")).strip():
                    desc_parts.append(str(row.get(p,"")).strip())
            out["Description"] = "\n\n".join(desc_parts)
            
            # Copy optional metafield/support columns when present in source
            for out_col, name_candidates in optional_extra_cols.items():
                source_col = find_col_by_names(cols, name_candidates)
                out[out_col] = str(row.get(source_col, "")).strip() if source_col else ""
            
            # Copy inventory and status columns from source
            if inventory_tracker_col and inventory_tracker_col in df.columns:
                out["Inventory tracker"] = str(row.get(inventory_tracker_col, "")).strip()
            if inventory_policy_col and inventory_policy_col in df.columns:
                out["Inventory policy"] = str(row.get(inventory_policy_col, "")).strip()
            if inventory_quantity_col and inventory_quantity_col in df.columns:
                out["Inventory quantity"] = str(row.get(inventory_quantity_col, "")).strip()
            if status_col and status_col in df.columns:
                out["Status"] = str(row.get(status_col, "")).strip()

            if brand_col and brand_col in df.columns:
                out["Vendor"] = row.get(brand_col,"")
            if prodcat_col and prodcat_col in df.columns:
                out["Product category"] = row.get(prodcat_col,"")
            if subcat_col and subcat_col in df.columns:
                out["Type"] = row.get(subcat_col,"") or row.get(subsub_col,"")
            # tags: existing tags (if template has Tags) + vendor + category + type + size
            if "Tags" in template_cols:
                tags = []
                # existing tags in source? we don't expect original tags in final file; but keep if present
                # Add vendor, product category, type, size
                for valcol in [brand_col, prodcat_col, subcat_col]:
                    if valcol and valcol in df.columns:
                        v = str(row.get(valcol,"")).strip()
                        if v and v.lower()!="nan":
                            tags.append(v)
                # Note: Individual size tags (like "0 - 3 M") are NOT added to tags
                # Only age group tags (like "Boy 0-3m") are added later
                
                # Helper function to check if value is exactly 1
                def is_value_one(val):
                    """Check if value is exactly 1 (string or number)"""
                    if val is None:
                        return False
                    val_str = str(val).strip()
                    if not val_str or val_str.lower() == "nan":
                        return False
                    try:
                        # Only accept exactly 1 (as integer or float 1.0)
                        num_val = float(val_str)
                        return num_val == 1.0
                    except (ValueError, TypeError):
                        return False
                
                # Add Subcategory*, Sub Sub Category*, *Season, Campaign, Sizes, Milestone Development, Make, and age columns to tags
                tag_columns = [
                    (subsubcategory_col, "Subcategory*"),
                    (subsubcategory_col, "Sub Sub Category*"),
                    (season_col, "*Season"),
                    (campaign_col, "Campaign"),
                    (sizes_col, "Sizes"),
                    (milestone_dev_col, "Milestone Development"),
                    (make_col, "Make"),
                    (age_2plus_col, "2 Plus"),
                    (age_3plus_col, "3 Plus"),
                    (age_4plus_col, "4 Plus"),
                    (age_5plus_col, "5 Plus"),
                    (age_6plus_col, "6 Plus"),
                    (all_ages_col, "All Ages")
                ]
                # Age columns that should only be added when value is 1
                age_tag_names = ["2 Plus", "3 Plus", "4 Plus", "5 Plus", "6 Plus", "All Ages"]
                
                for col, col_name in tag_columns:
                    if col and col in df.columns:
                        val = str(row.get(col, "")).strip()
                        if val and val.lower() != "nan":
                            # For age columns, only add if value is 1
                            if col_name in age_tag_names:
                                if is_value_one(val):
                                    tags.append(col_name)
                            else:
                                # For other columns, add the value directly
                                tags.append(val)
                
                # Add toy-specific sizes to tags (0-6M Toys, 6-12M Toys, 12-18M Toys, 18-24M Toys)
                toy_size_patterns = ["0-6M Toys", "6-12M Toys", "12-18M Toys", "18-24M Toys"]
                for variant in variants:
                    if variant != "Default":
                        # Check if variant matches any toy size pattern
                        for toy_pattern in toy_size_patterns:
                            if toy_pattern.lower() in variant.lower() or variant.lower() in toy_pattern.lower():
                                if variant not in tags:
                                    tags.append(variant)
                                break
                
                # Add DROP_ACTIVE tag if column value is True
                if drop_active_col and drop_active_col in df.columns:
                    drop_active_val = str(row.get(drop_active_col, "")).strip()
                    if drop_active_val.lower() == "true":
                        if "DROP_ACTIVE" not in tags:
                            tags.append("DROP_ACTIVE")
                
                # Add Boy, Girl, Unisex, NB tags ONLY when their columns have value 1
                # Also handle "Girls + Unisex" and "Boys + Unisex" columns
                
                for col in df.columns:
                    col_stripped = col.strip()
                    # Remove asterisks and normalize spacing
                    col_normalized = re.sub(r'[*\s]+', '', col_stripped).lower()
                    
                    # Get the value for this column
                    val = row.get(col, "")
                    
                    # Only proceed if value is exactly 1
                    if not is_value_one(val):
                        continue
                    
                    # Check for "Girls + Unisex" or "Girls+Unisex" column (handle various formats)
                    if "girls" in col_normalized and "unisex" in col_normalized:
                        if "Girl" not in tags:
                            tags.append("Girl")
                        if "Unisex" not in tags:
                            tags.append("Unisex")
                    
                    # Check for "Boys + Unisex" or "Boys+Unisex" column (handle various formats)
                    elif "boys" in col_normalized and "unisex" in col_normalized:
                        if "Boy" not in tags:
                            tags.append("Boy")
                        if "Unisex" not in tags:
                            tags.append("Unisex")
                    
                    # Check for individual columns (handle asterisks like *Boy, *Girl, *Unisex)
                    elif col_normalized == "boy" or col_normalized == "boys":
                        if "Boy" not in tags:
                            tags.append("Boy")
                    elif col_normalized == "girl" or col_normalized == "girls":
                        if "Girl" not in tags:
                            tags.append("Girl")
                    elif col_normalized == "unisex":
                        if "Unisex" not in tags:
                            tags.append("Unisex")
                    elif col_normalized == "nb" or col_normalized == "newborn":
                        if "Newborn" not in tags:
                            tags.append("Newborn")
                    # Check for age columns (2+, 3+, 4+, 5+, 6+, All Ages)
                    # Handle columns like "2+", "*2+", "2 +", "2 Plus", "*2 Plus", etc.
                    # Always add tags as "2 Plus", "3 Plus", etc.
                    col_clean = col_stripped.replace("*", "").replace(" ", "").strip().lower()
                    if col_clean == "2+" or col_clean == "2plus" or col_normalized == "2plus":
                        if "2 Plus" not in tags:
                            tags.append("2 Plus")
                    elif col_clean == "3+" or col_clean == "3plus" or col_normalized == "3plus":
                        if "3 Plus" not in tags:
                            tags.append("3 Plus")
                    elif col_clean == "4+" or col_clean == "4plus" or col_normalized == "4plus":
                        if "4 Plus" not in tags:
                            tags.append("4 Plus")
                    elif col_clean == "5+" or col_clean == "5plus" or col_normalized == "5plus":
                        if "5 Plus" not in tags:
                            tags.append("5 Plus")
                    elif col_clean == "6+" or col_clean == "6plus" or col_normalized == "6plus":
                        if "6 Plus" not in tags:
                            tags.append("6 Plus")
                    elif "allages" in col_normalized or "all ages" in col_stripped.lower():
                        if "All Ages" not in tags:
                            tags.append("All Ages")
                
                # Add age group tags for boys based on size variants
                if "Boy" in tags:
                    age_group_tags = get_boy_age_group_tags(variants)
                    for age_tag in age_group_tags:
                        if age_tag not in tags:
                            tags.append(age_tag)
                
                # Add age group tags for girls based on size variants
                if "Girl" in tags:
                    age_group_tags = get_girl_age_group_tags(variants)
                    for age_tag in age_group_tags:
                        if age_tag not in tags:
                            tags.append(age_tag)
                
                out["Tags"] = ", ".join(dict.fromkeys(tags))

            out["Published on online store"] = "TRUE" if "Published on online store" in template_cols else out.get("Published on online store","")
            # Use Status from source CSV if available, otherwise default to "Active" if column exists
            if "Status" in template_cols and not out.get("Status", "").strip():
                out["Status"] = "Active"

            out["Option1 name"] = "Size" if size != "Default" else ""
            out["Option1 value"] = size if size != "Default" else ""

            # Pricing: Final -> Price, MRP -> Compare-at price, Cost -> Cost per item
            # Price equals selling price rounded to nearest 9
            if final_price:
                price_val = round_to_nearest_9(final_price)
            elif cost_price and fallback_price_to_cost:
                price_val = round_to_nearest_9(cost_price)
            else:
                price_val = ""
            out["Price"] = price_val
            out["Compare-at price"] = mrp_price
            out["Cost per item"] = cost_price

            # standard flags
            if "Charge tax" in template_cols:
                out["Charge tax"] = "TRUE"
            if "Requires shipping" in template_cols:
                out["Requires shipping"] = "TRUE"
            if "Fulfillment service" in template_cols:
                out["Fulfillment service"] = "manual"
            if "Gift card" in template_cols:
                out["Gift card"] = "FALSE"

            out["SEO title"] = title
            out["SEO description"] = out["Description"][:320] if out["Description"] else ""
            if "Google Shopping / Google product category" in template_cols:
                out["Google Shopping / Google product category"] = out.get("Product category","")

            # place primary image on first variant
            if first_variant and primary_image:
                for c in template_cols:
                    nc = re.sub(r"[^a-z0-9]","", c.lower())
                    if "productimageurl" in nc or "imagesrc" in nc or nc=="image" or "productimage" in nc:
                        out[c] = primary_image
                        # set image position if a column exists
                        for cc in template_cols:
                            if "position" in cc.lower() and "image" in cc.lower():
                                out[cc] = 1
                                break
                        break
                first_variant = False

            out_rows.append(out)

        # add extra images as image-only rows (Handle + Product image URL + Image position)
        pos = 2
        for extra in images[1:]:
            img_row = {c: "" for c in template_cols}
            if handle_template_col:
                img_row[handle_template_col] = handle_base
            for c in template_cols:
                nc = re.sub(r"[^a-z0-9]","", c.lower())
                if "productimageurl" in nc or "imagesrc" in nc or nc=="image" or "productimage" in nc:
                    img_row[c] = extra
                    break
            for cc in template_cols:
                if "position" in cc.lower() and "image" in cc.lower():
                    img_row[cc] = pos
                    break
            out_rows.append(img_row)
            pos += 1

    out_df = pd.DataFrame(out_rows, columns=template_cols)

    # drop inventory-like columns to match the working file (if present)
    # But preserve explicitly added inventory columns: Inventory tracker, Inventory policy, Inventory quantity, Status
    inv_keys = set(["inventorypolicy","variantinventorypolicy","inventoryquantity","continuesellingwhenoutofstock","inventorytracker"])
    preserve_cols = set(["inventorytracker", "inventorypolicy", "inventoryquantity", "status"])
    keep_cols = []
    for c in out_df.columns:
        col_normalized = re.sub(r"[^a-z0-9]","", c.lower())
        # Keep column if it's in preserve list OR not in removal list
        if col_normalized in preserve_cols or col_normalized not in inv_keys:
            keep_cols.append(c)
    out_df = out_df[keep_cols]

    out_df.to_csv(out_path, index=False)
    print(f"Wrote {len(out_df)} rows to {out_path}")

# ---------------------------
# CLI
# ---------------------------

def main():
    parser = argparse.ArgumentParser(description="Convert messy listing CSV(s) into Shopify template CSV.")
    parser.add_argument("--source", required=True, nargs='+', 
                        help="Source CSV file(s) (messy) path(s). Can specify multiple files.")
    parser.add_argument("--template", required=True, help="Shopify template CSV to use for columns/order")
    parser.add_argument("--out", help="Output CSV path or directory. If directory, output files will be named automatically. If not specified, outputs will be named based on source files.")
    parser.add_argument("--no-fallback-cost", dest="fallback", action="store_false",
                        help="Do NOT fallback Price to Cost to Kiddo when Final Price is missing")
    args = parser.parse_args()
    
    # Determine output paths
    source_files = args.source
    template_path = args.template
    
    # If --out is a directory or not specified, generate output names from source files
    if args.out:
        out_path = Path(args.out)
        if out_path.is_dir() or (not out_path.exists() and out_path.suffix == ""):
            # Treat as directory - generate output names
            out_dir = out_path if out_path.is_dir() else out_path
            if not out_dir.exists():
                out_dir.mkdir(parents=True, exist_ok=True)
            output_paths = []
            for src_file in source_files:
                src_path = Path(src_file)
                out_file = out_dir / f"{src_path.stem} - Converted - Shopify.csv"
                output_paths.append(str(out_file))
        else:
            # Single output file specified - use for first file only, warn if multiple
            if len(source_files) > 1:
                print(f"Warning: Multiple source files provided but single output specified. Only processing first file: {source_files[0]}")
                source_files = [source_files[0]]
            output_paths = [args.out]
    else:
        # No output specified - generate names based on source files in current directory
        output_paths = []
        for src_file in source_files:
            src_path = Path(src_file)
            out_file = src_path.parent / f"{src_path.stem} - Converted - Shopify.csv"
            output_paths.append(str(out_file))
    
    # Process each file
    for i, source_file in enumerate(source_files):
        output_file = output_paths[i] if i < len(output_paths) else None
        if not output_file:
            # Generate default output name
            src_path = Path(source_file)
            output_file = str(src_path.parent / f"{src_path.stem} - Converted - Shopify.csv")
        
        print(f"\nProcessing: {source_file}")
        print(f"Output: {output_file}")
        try:
            process_file(source_file, template_path, output_file, fallback_price_to_cost=args.fallback)
        except Exception as e:
            print(f"Error processing {source_file}: {e}")
            continue
    
    print(f"\nCompleted processing {len(source_files)} file(s).")

if __name__ == "__main__":
    main()