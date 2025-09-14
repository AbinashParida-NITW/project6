import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
import re
from difflib import SequenceMatcher

@dataclass
class MappingRule:
    source_column: str
    target_column: str
    confidence: float
    transformation: str = "direct"
    learned: bool = False

@dataclass
class CleaningRule:
    column: str
    rule_type: str
    pattern: str
    replacement: str
    confidence: float
    learned: bool = False

class SchemaMapper:
    def __init__(self, rules_file: str = "mapping_rules.json"):
        self.rules_file = rules_file
        self.canonical_schema = self._load_canonical_schema()
        self.learned_mappings = self._load_learned_rules()
        self.cleaning_patterns = self._initialize_cleaning_patterns()
    
    def _load_canonical_schema(self) -> Dict[str, str]:
        """Load canonical schema from the standard format file"""
        try:
            schema_df = pd.read_csv("Project6StdFormat.csv")
            return dict(zip(schema_df['canonical_name'], schema_df['description']))
        except:
            # Fallback schema
            return {
                'order_id': 'Unique order identifier',
                'order_date': 'ISO date of order',
                'customer_id': 'Internal customer id',
                'customer_name': 'Full name',
                'email': 'Contact email',
                'phone': 'Contact phone',
                'billing_address': 'Billing address line',
                'shipping_address': 'Shipping address line',
                'city': 'City',
                'state': 'State/Province', 
                'postal_code': 'Zip/Postal/pin',
                'country': 'Country',
                'product_sku': 'SKU code',
                'product_name': 'Item name',
                'category': 'Category',
                'subcategory': 'Subcategory if any',
                'quantity': 'Units ordered',
                'unit_price': 'Price per unit',
                'currency': 'Currency code',
                'discount_pct': 'Discount fraction (0-1)',
                'tax_pct': 'Tax fraction (0-1)',
                'shipping_fee': 'Shipping amount',
                'total_amount': 'Total amount charged',
                'tax_id': 'Tax/GST/VAT identifier'
            }
    
    def _load_learned_rules(self) -> List[MappingRule]:
        """Load previously learned mapping rules"""
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
                    mappings = [MappingRule(**rule) for rule in data.get('mappings', [])]
                    
                    # Also load column promotions and default values
                    self.column_promotions = data.get('column_promotions', {})
                    self.default_values = data.get('default_values', {})
                    self.learned_cleaning_rules = data.get('cleaning_rules', [])
                    
                    return mappings
            except:
                pass
        
        # Initialize empty if no file
        self.column_promotions = {}
        self.default_values = {}
        self.learned_cleaning_rules = []
        return []
    
    def _save_learned_rules(self):
        """Save learned rules to JSON file"""
        try:
            # Load existing data or create new
            existing_data = {}
            if os.path.exists(self.rules_file):
                try:
                    with open(self.rules_file, 'r') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = {}
            
            data = {
                'mappings': [asdict(rule) for rule in self.learned_mappings],
                'cleaning_rules': existing_data.get('cleaning_rules', []),
                'column_promotions': existing_data.get('column_promotions', {}),
                'default_values': existing_data.get('default_values', {}),
                'updated_at': datetime.now().isoformat()
            }
            
            with open(self.rules_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Failed to save learned rules: {e}")
            return False
    
    def add_learned_mapping(self, source_col: str, target_col: str, confidence: float = 0.95):
        """Add a new learned mapping rule"""
        new_rule = MappingRule(
            source_column=source_col,
            target_column=target_col,
            confidence=confidence,
            learned=True
        )
        
        # Remove existing rule for this source column if any
        self.learned_mappings = [r for r in self.learned_mappings if r.source_column != source_col]
        self.learned_mappings.append(new_rule)
        return self._save_learned_rules()
    
    def promote_column_to_schema(self, column_name: str, canonical_name: str = None):
        """Promote an extra column to be kept in future mappings"""
        try:
            data = {}
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
            
            if 'column_promotions' not in data:
                data['column_promotions'] = {}
            
            target_name = canonical_name if canonical_name else column_name
            data['column_promotions'][column_name] = target_name
            data['updated_at'] = datetime.now().isoformat()
            
            with open(self.rules_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Failed to promote column: {e}")
            return False
    
    def save_default_value_rule(self, column: str, default_value: str, rule_type: str):
        """Save a default value rule for missing columns"""
        try:
            data = {}
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
            
            if 'default_values' not in data:
                data['default_values'] = {}
            
            data['default_values'][column] = {
                'value': default_value,
                'rule_type': rule_type,
                'created_at': datetime.now().isoformat()
            }
            data['updated_at'] = datetime.now().isoformat()
            
            with open(self.rules_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Failed to save default value rule: {e}")
            return False
    
    def _initialize_cleaning_patterns(self) -> List[CleaningRule]:
        """Initialize deterministic cleaning patterns"""
        return [
            CleaningRule('unit_price', 'remove_currency', r'[₹$€£,]', '', 0.9),
            CleaningRule('total_amount', 'remove_currency', r'[₹$€£,]', '', 0.9),
            CleaningRule('discount_pct', 'percentage_to_decimal', r'(\d+)%', r'\1', 0.9),
            CleaningRule('tax_pct', 'percentage_to_decimal', r'(\d+)%', r'\1', 0.9),
            CleaningRule('email', 'fix_spacing', r'\s*@\s*', '@', 0.95),
            CleaningRule('phone', 'standardize_phone', r'[^\d\-\+]', '', 0.8),
        ]
    
    def suggest_mappings(self, input_columns: List[str]) -> List[MappingRule]:
        """Suggest column mappings with confidence scores"""
        suggestions = []
        used_targets = set()  # Track which canonical columns are already mapped
        
        # Sort input columns by priority - exact matches first
        prioritized_columns = sorted(input_columns, key=lambda col: (
            -1 if any(col.lower() == var.lower() for canonical in self.canonical_schema.keys() 
                     for var in self._get_column_variations(canonical)) else 0,
            col.lower()
        ))
        
        for input_col in prioritized_columns:
            best_match = None
            best_confidence = 0.0
            
            # Check learned mappings first (highest priority)
            for learned_rule in self.learned_mappings:
                if learned_rule.source_column.lower() == input_col.lower():
                    if learned_rule.target_column not in used_targets:
                        suggestions.append(learned_rule)
                        used_targets.add(learned_rule.target_column)
                        best_match = learned_rule.target_column
                    break
            
            if best_match:
                continue
            
            # Check promoted columns (extra columns user chose to keep)
            if hasattr(self, 'column_promotions') and input_col in self.column_promotions:
                promoted_target = self.column_promotions[input_col]
                if promoted_target not in used_targets:
                    suggestions.append(MappingRule(
                        source_column=input_col,
                        target_column=promoted_target,
                        confidence=0.98,  # High confidence for promoted columns
                        learned=True
                    ))
                    used_targets.add(promoted_target)
                    continue
            
            # Use similarity matching for new columns
            for canonical_col in self.canonical_schema.keys():
                if canonical_col in used_targets:
                    continue  # Skip already mapped canonical columns
                
                # Direct name similarity
                similarity = SequenceMatcher(None, input_col.lower(), canonical_col.lower()).ratio()
                
                # Common variations - exact match gets high score
                variations = self._get_column_variations(canonical_col)
                for variation in variations:
                    if input_col.lower() == variation.lower():
                        similarity = 0.95  # High score for exact variation match
                        break
                    else:
                        var_similarity = SequenceMatcher(None, input_col.lower(), variation.lower()).ratio()
                        similarity = max(similarity, var_similarity)
                
                # Keyword matching (but not for COUPON_CODE type columns)
                if not input_col.upper().startswith('COUPON'):
                    keywords = self._extract_keywords(canonical_col)
                    for keyword in keywords:
                        if keyword.lower() in input_col.lower():
                            similarity += 0.3
                
                if similarity > best_confidence:
                    best_confidence = similarity
                    best_match = canonical_col
            
            if best_match and best_confidence > 0.4:  # Threshold for suggestions
                suggestions.append(MappingRule(
                    source_column=input_col,
                    target_column=best_match,
                    confidence=min(best_confidence, 0.95)  # Cap confidence
                ))
                used_targets.add(best_match)  # Mark this canonical column as used
        
        return sorted(suggestions, key=lambda x: x.confidence, reverse=True)
    
    def _get_column_variations(self, canonical_col: str) -> List[str]:
        """Get common variations for canonical column names"""
        variations = {
            'order_id': ['Order No', 'OrderID', 'reference', 'order_ref'],
            'order_date': ['OrderDate', 'ordered_on', 'order_date', 'date'],
            'customer_id': ['Cust ID', 'client_ref', 'customer_id', 'cust_id'],
            'customer_name': ['Customer', 'client_name', 'cust_name', 'name'],
            'email': ['E-mail', 'Email', 'contact', 'email_addr'],
            'phone': ['Phone #', 'mobile', 'phone_no', 'contact_no'],
            'billing_address': ['Bill Addr', 'bill_to', 'billing_addr'],
            'shipping_address': ['Ship Addr', 'ship_to', 'shipping_addr'],
            'city': ['City'],
            'state': ['State/Province', 'state', 'province'],
            'postal_code': ['ZIP/Postal', 'pin', 'zip', 'postal'],
            'country': ['Country/Region', 'country', 'region'],
            'product_sku': ['SKU', 'stock_code', 'sku_code'],
            'product_name': ['Item', 'desc', 'description', 'product'],
            'category': ['Cat.', 'category_name', 'cat'],
            'subcategory': ['Subcat', 'sub_category', 'sub_cat'],
            'quantity': ['Qty', 'QTY', 'qty'],
            'unit_price': ['Unit Price', 'price', 'unit_cost'],
            'currency': ['Currency'],
            'discount_pct': ['Disc%', 'discount', 'disc_pct'],
            'tax_pct': ['Tax%', 'gst', 'tax_rate'],
            'shipping_fee': ['Ship Fee', 'logistics_fee', 'shipping'],
            'total_amount': ['Total', 'grand_total', 'amount'],
            'tax_id': ['Reg No', 'GSTIN', 'tax_number']
        }
        return variations.get(canonical_col, [])
    
    def _extract_keywords(self, column_name: str) -> List[str]:
        """Extract keywords from column name for matching"""
        return column_name.replace('_', ' ').split()
    
    def clean_data(self, df: pd.DataFrame, mappings: Dict[str, str]) -> Tuple[pd.DataFrame, List[Dict]]:
        """Clean data using deterministic rules"""
        cleaned_df = df.copy()
        issues_found = []
        
        # First, handle empty cells and data quality issues
        for col in cleaned_df.columns:
            # Clean embedded newlines and carriage returns that break CSV structure
            if cleaned_df[col].dtype == 'object':
                cleaned_df[col] = cleaned_df[col].astype(str).str.replace('\n', ' ', regex=False)
                cleaned_df[col] = cleaned_df[col].str.replace('\r', ' ', regex=False)
                cleaned_df[col] = cleaned_df[col].str.replace('\t', ' ', regex=False)

            # Replace various forms of empty/null values with proper NaN
            cleaned_df[col] = cleaned_df[col].replace('', pd.NA)
            cleaned_df[col] = cleaned_df[col].replace(' ', pd.NA)  # Single space
            cleaned_df[col] = cleaned_df[col].replace('  ', pd.NA)  # Multiple spaces
            
            # Handle 'nan' as string (common in CSV exports)
            if cleaned_df[col].dtype == 'object':
                cleaned_df[col] = cleaned_df[col].replace('nan', pd.NA)
                cleaned_df[col] = cleaned_df[col].replace('NaN', pd.NA)
                cleaned_df[col] = cleaned_df[col].replace('NULL', pd.NA)
                cleaned_df[col] = cleaned_df[col].replace('null', pd.NA)
                cleaned_df[col] = cleaned_df[col].replace('None', pd.NA)
                # Only replace standalone dash (single dash by itself), not dashes in formatted data
                # This preserves phone numbers like +91-9000156794 and date ranges
                cleaned_df[col] = cleaned_df[col].replace(r'^\s*-\s*$', pd.NA, regex=True)
                cleaned_df[col] = cleaned_df[col].replace('N/A', pd.NA)
                cleaned_df[col] = cleaned_df[col].replace('n/a', pd.NA)
        
        for source_col, target_col in mappings.items():
            if source_col not in cleaned_df.columns:
                continue
            
            # Apply relevant cleaning patterns
            for pattern in self.cleaning_patterns:
                if target_col == pattern.column or pattern.column == 'all':
                    before_values = cleaned_df[source_col].fillna('').astype(str).unique()[:5]
                    
                    if pattern.rule_type == 'remove_currency':
                        cleaned_df[source_col] = cleaned_df[source_col].fillna('').astype(str).str.replace(pattern.pattern, pattern.replacement, regex=True)
                    elif pattern.rule_type == 'percentage_to_decimal':
                        def convert_percentage(x):
                            if pd.isna(x):
                                return x
                            str_x = str(x)
                            if '%' in str_x:
                                return float(re.sub(r'(\d+)%', r'\1', str_x)) / 100
                            return x
                        cleaned_df[source_col] = cleaned_df[source_col].apply(convert_percentage)
                    elif pattern.rule_type == 'fix_spacing':
                        cleaned_df[source_col] = cleaned_df[source_col].fillna('').astype(str).str.replace(pattern.pattern, pattern.replacement, regex=True)
                    elif pattern.rule_type == 'fix_xx_pattern':
                        cleaned_df[source_col] = cleaned_df[source_col].fillna('').astype(str).str.replace(pattern.pattern, r'\100\2', regex=True)
                    
                    after_values = cleaned_df[source_col].fillna('').astype(str).unique()[:5]
                    
                    if not all(b == a for b, a in zip(before_values, after_values)):
                        issues_found.append({
                            'column': source_col,
                            'rule': pattern.rule_type,
                            'before_sample': before_values.tolist(),
                            'after_sample': after_values.tolist(),
                            'confidence': pattern.confidence
                        })
        
        # Additional cleaning for common data issues
        for source_col, target_col in mappings.items():
            if source_col in cleaned_df.columns:
                # Clean text fields - remove extra spaces but preserve content
                if target_col in ['customer_name', 'email']:
                    cleaned_df[source_col] = cleaned_df[source_col].astype(str).str.strip()
                    cleaned_df[source_col] = cleaned_df[source_col].str.replace(r'\s+', ' ', regex=True)
                    # Fix email spacing around @
                    if target_col == 'email':
                        cleaned_df[source_col] = cleaned_df[source_col].str.replace(r'\s*@\s*', '@', regex=True)
                
                # Parse dates properly - preserve full date information  
                elif target_col == 'order_date':
                    def parse_date(date_str):
                        if pd.isna(date_str) or str(date_str).strip() == '':
                            return None
                        
                        date_str = str(date_str).strip()
                        
                        # Try different patterns
                        patterns_and_formats = [
                            (r'\d{4}-\d{2}-\d{2}', '%Y-%m-%d'),  # 2025-08-09
                            (r'\d{2}/\d{2}/\d{4}', '%d/%m/%Y'),  # 23/06/2025  
                            (r'\d{2}-\w{3}-\d{4}', '%d-%b-%Y'),  # 25-Mar-2025
                            (r'\d{2} \w{3} \d{4}', '%d %b %Y'),  # 02 Aug 2025
                        ]
                        
                        for pattern, date_format in patterns_and_formats:
                            if re.match(pattern, date_str):
                                try:
                                    parsed = datetime.strptime(date_str, date_format)
                                    return parsed.strftime('%Y-%m-%d')
                                except ValueError:
                                    continue
                        
                        return date_str  # Return original if can't parse
                    
                    cleaned_df[source_col] = cleaned_df[source_col].apply(parse_date)
                
                # DON'T over-clean phone numbers - just standardize format
                elif target_col == 'phone':
                    # Only clean if it's obviously messy, preserve + and digits
                    cleaned_df[source_col] = cleaned_df[source_col].astype(str).str.strip()
                
                # Standardize currency values
                elif target_col == 'currency':
                    currency_map = {'₹': 'INR', 'Rs': 'INR', 'rs': 'INR', 'inr': 'INR', 'INR': 'INR'}
                    cleaned_df[source_col] = cleaned_df[source_col].astype(str).map(currency_map).fillna('INR')
                
                # Clean numeric fields - remove commas and quotes
                elif target_col in ['unit_price', 'total_amount', 'shipping_fee']:
                    cleaned_df[source_col] = cleaned_df[source_col].astype(str).str.replace(r'[",]', '', regex=True)
                    cleaned_df[source_col] = pd.to_numeric(cleaned_df[source_col], errors='coerce')
                
                # Convert percentage strings to decimals  
                elif target_col in ['discount_pct', 'tax_pct']:
                    def clean_percentage(x):
                        if pd.isna(x):
                            return x
                        str_x = str(x).strip()
                        if str_x.endswith('%'):
                            return float(str_x.replace('%', '')) / 100
                        return float(str_x) if str_x else 0
                    cleaned_df[source_col] = cleaned_df[source_col].apply(clean_percentage)
                
                # Clean postal codes - keep all postal codes AS STRINGS including XX patterns
                elif target_col == 'postal_code':
                    def clean_postal(x):
                        if pd.isna(x):
                            return x
                        str_x = str(x).strip()
                        
                        # Skip obvious non-postal data (coupons, etc)
                        if str_x.upper() in ['SAVE10', 'SAVE20', 'DISCOUNT', 'COUPON', 'NAN']:
                            return None
                        
                        # Keep XX pattern postal codes exactly as they are - DON'T change them
                        # 667XX2 should stay 667XX2, not become 66700
                        
                        # Keep any string that looks like a postal code (digits, maybe some letters, including XX)
                        if re.match(r'^[A-Z0-9X\s\-]{3,10}$', str_x.upper()):
                            return str_x  # Keep as original string
                        
                        # Keep pure numeric postal codes AS STRINGS
                        if str_x.isdigit() and len(str_x) >= 3:
                            return str_x  # Return as string, not number
                            
                        return str_x  # Keep anything else as string
                    
                    cleaned_df[source_col] = cleaned_df[source_col].apply(clean_postal)
                    # Ensure postal_code column stays as string type
                    cleaned_df[source_col] = cleaned_df[source_col].astype('string')
        
        # Add intelligent defaults only for truly missing data
        for source_col, target_col in mappings.items():
            if source_col in cleaned_df.columns:
                if target_col == 'country':
                    cleaned_df[source_col] = cleaned_df[source_col].fillna('India')
                elif target_col in ['billing_address', 'shipping_address']:
                    # Use the other address if one is missing
                    other_addr_type = 'shipping_address' if target_col == 'billing_address' else 'billing_address'
                    other_addr_col = [k for k, v in mappings.items() if v == other_addr_type]
                    if other_addr_col and other_addr_col[0] in cleaned_df.columns:
                        cleaned_df[source_col] = cleaned_df[source_col].fillna(cleaned_df[other_addr_col[0]])
        
        return cleaned_df, issues_found
    
    def detect_targeted_fixes(self, df: pd.DataFrame, mappings: Dict[str, str]) -> List[Dict]:
        """Detect specific data issues that need targeted fixes"""
        targeted_fixes = []
        
        for source_col, target_col in mappings.items():
            if source_col not in df.columns:
                continue
            
            # Check for phone number issues
            if target_col == 'phone':
                for idx, value in df[source_col].items():
                    if pd.notna(value):
                        str_val = str(value).strip()
                        # Missing country code
                        if str_val.isdigit() and len(str_val) == 10:
                            targeted_fixes.append({
                                'type': 'phone_missing_country_code',
                                'column': source_col,
                                'row': idx,
                                'current_value': str_val,
                                'suggested_fix': f"+91-{str_val}",
                                'issue': f"Phone number missing country code: {str_val}",
                                'confidence': 0.9,
                                'fix_description': "Add +91- prefix for Indian numbers"
                            })
                        # Invalid format
                        elif str_val.startswith('+') and not re.match(r'\+\d{2}-\d{10}', str_val):
                            formatted = re.sub(r'[^\d+]', '', str_val)
                            if len(formatted) == 13:  # +91xxxxxxxxxx
                                clean_format = f"{formatted[:3]}-{formatted[3:]}"
                                targeted_fixes.append({
                                    'type': 'phone_format_fix',
                                    'column': source_col,
                                    'row': idx,
                                    'current_value': str_val,
                                    'suggested_fix': clean_format,
                                    'issue': f"Phone format inconsistent: {str_val}",
                                    'confidence': 0.85,
                                    'fix_description': "Standardize to +XX-XXXXXXXXXX format"
                                })
            
            # Check for email issues
            elif target_col == 'email':
                for idx, value in df[source_col].items():
                    if pd.notna(value):
                        str_val = str(value).strip()
                        # Spacing around @
                        if ' @ ' in str_val or '@  ' in str_val or '  @' in str_val:
                            fixed = re.sub(r'\s*@\s*', '@', str_val)
                            targeted_fixes.append({
                                'type': 'email_spacing_fix',
                                'column': source_col,
                                'row': idx,
                                'current_value': str_val,
                                'suggested_fix': fixed,
                                'issue': f"Email has spacing issues: {str_val}",
                                'confidence': 0.95,
                                'fix_description': "Remove extra spaces around @"
                            })
            
            # Check for postal code issues
            elif target_col == 'postal_code':
                for idx, value in df[source_col].items():
                    if pd.notna(value):
                        str_val = str(value).strip()
                        # XX pattern
                        if 'XX' in str_val and re.match(r'\d+XX\d+', str_val):
                            options = [
                                str_val.replace('XX', '00'),
                                str_val.replace('XX', '01'),
                                str_val.replace('XX', '10')
                            ]
                            targeted_fixes.append({
                                'type': 'postal_xx_pattern',
                                'column': source_col,
                                'row': idx,
                                'current_value': str_val,
                                'suggested_fix': options[0],  # Default to 00
                                'alternatives': options,
                                'issue': f"Postal code has XX pattern: {str_val}",
                                'confidence': 0.7,
                                'fix_description': "Replace XX with specific digits"
                            })
            
            # Check for date issues
            elif target_col == 'order_date':
                for idx, value in df[source_col].items():
                    if pd.notna(value):
                        str_val = str(value).strip()
                        # Non-standard formats
                        if not re.match(r'\d{4}-\d{2}-\d{2}', str_val):
                            # Try to parse and suggest ISO format
                            parsed_date = None
                            for pattern, fmt in [
                                (r'\d{2}/\d{2}/\d{4}', '%d/%m/%Y'),
                                (r'\d{2} \w{3} \d{4}', '%d %b %Y'),
                                (r'\d{2}-\w{3}-\d{4}', '%d-%b-%Y')
                            ]:
                                if re.match(pattern, str_val):
                                    try:
                                        parsed_date = datetime.strptime(str_val, fmt).strftime('%Y-%m-%d')
                                        break
                                    except:
                                        continue
                            
                            if parsed_date:
                                targeted_fixes.append({
                                    'type': 'date_format_standardize',
                                    'column': source_col,
                                    'row': idx,
                                    'current_value': str_val,
                                    'suggested_fix': parsed_date,
                                    'issue': f"Date format non-standard: {str_val}",
                                    'confidence': 0.9,
                                    'fix_description': "Convert to ISO format (YYYY-MM-DD)"
                                })
        
        return targeted_fixes
    
    def _save_cleaning_rule(self, fix: Dict) -> bool:
        """Save a targeted fix as a reusable cleaning rule"""
        try:
            data = {}
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
            
            if 'cleaning_rules' not in data:
                data['cleaning_rules'] = []
            
            # Create rule from fix
            rule = {
                'type': fix['type'],
                'target_column': fix.get('target_column', fix['column']),
                'pattern': fix.get('pattern', ''),
                'replacement': fix['suggested_fix'],
                'description': fix['fix_description'],
                'confidence': fix['confidence'],
                'created_at': datetime.now().isoformat()
            }
            
            # Avoid duplicates
            existing_rule = next((r for r in data['cleaning_rules'] 
                                if r['type'] == rule['type'] and r['target_column'] == rule['target_column']), None)
            
            if not existing_rule:
                data['cleaning_rules'].append(rule)
                data['updated_at'] = datetime.now().isoformat()
                
                with open(self.rules_file, 'w') as f:
                    json.dump(data, f, indent=2)
                return True
            else:
                return True  # Already exists, consider it saved
                
        except Exception as e:
            print(f"Failed to save cleaning rule: {e}")
            return False
    
    def _save_legacy_cleaning_rule(self, issue: Dict) -> bool:
        """Save a legacy cleaning issue as a rule"""
        try:
            rule = {
                'type': 'legacy_' + issue['rule'],
                'target_column': issue['column'],
                'description': f"Legacy rule for {issue['rule']}",
                'confidence': issue['confidence'],
                'created_at': datetime.now().isoformat()
            }
            
            data = {}
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
            
            if 'cleaning_rules' not in data:
                data['cleaning_rules'] = []
            
            data['cleaning_rules'].append(rule)
            data['updated_at'] = datetime.now().isoformat()
            
            with open(self.rules_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
            
        except Exception as e:
            print(f"Failed to save legacy cleaning rule: {e}")
            return False


def main():
    st.set_page_config(
        page_title="Schema Mapper & Data Quality Fixer",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Clean, minimal header
    st.title("🎯 Schema Mapper & Data Quality Fixer")
    st.markdown("**Upload CSV → Map Columns → Clean Data → Apply Fixes → Download Results**")
    st.divider()
    
    # Initialize session state
    if 'mapper' not in st.session_state:
        st.session_state.mapper = SchemaMapper()
    if 'uploaded_data' not in st.session_state:
        st.session_state.uploaded_data = None
    if 'mappings' not in st.session_state:
        st.session_state.mappings = {}
    if 'cleaned_data' not in st.session_state:
        st.session_state.cleaned_data = None
    if 'applied_fixes' not in st.session_state:
        st.session_state.applied_fixes = {}
    if 'fix_history' not in st.session_state:
        st.session_state.fix_history = []
    
    # File Upload
    st.header("📁 Upload Your CSV File")
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type="csv",
        help="Upload your CSV file to start the mapping and cleaning process"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            # Simple file upload - clear previous session state when new file is uploaded
            if 'uploaded_data' not in st.session_state or not df.equals(st.session_state.uploaded_data):
                # Clear all previous results
                st.session_state.uploaded_data = df
                st.session_state.cleaned_data = None
                st.session_state.mappings = {}  # Clear mappings for new file
                st.session_state.applied_fixes = {}  # Clear applied fixes
                st.session_state.fix_history = []  # Clear fix history
                if 'mapping_suggestions' in st.session_state:
                    del st.session_state.mapping_suggestions
                if 'cleaning_issues' in st.session_state:
                    del st.session_state.cleaning_issues
                if 'targeted_fixes' in st.session_state:
                    del st.session_state.targeted_fixes
            st.success(f"Loaded {len(df)} rows with {len(df.columns)} columns")

            with st.expander("🔍 Preview uploaded data", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
                
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return
    
    if st.session_state.uploaded_data is not None:
        df = st.session_state.uploaded_data
        
        # Column Mapping with Confidence
        st.divider()
        st.header("🎯 Suggested Mappings")
        
        suggested_mappings = st.session_state.mapper.suggest_mappings(df.columns.tolist())
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("✅ Column Mappings")
            
            for i, suggestion in enumerate(suggested_mappings):
                cols = st.columns([2, 2, 1, 1])
                
                with cols[0]:
                    st.text(suggestion.source_column)
                
                with cols[1]:
                    target_options = [''] + list(st.session_state.mapper.canonical_schema.keys())
                    default_idx = target_options.index(suggestion.target_column) if suggestion.target_column in target_options else 0
                    selected_target = st.selectbox(
                        f"Target {i}",
                        target_options,
                        index=default_idx,
                        key=f"mapping_{i}",
                        label_visibility="collapsed"
                    )
                    
                    if selected_target:
                        st.session_state.mappings[suggestion.source_column] = selected_target
                
                with cols[2]:
                    confidence_color = "🟢" if suggestion.confidence > 0.8 else "🟡" if suggestion.confidence > 0.6 else "🔴"
                    st.text(f"{confidence_color} {suggestion.confidence:.1%}")
                
                with cols[3]:
                    if suggestion.learned:
                        st.text("📚 Learned")
                    else:
                        st.text("🆕 New")
            
            # Show Extra Columns (unmapped)
            mapped_sources = {s.source_column for s in suggested_mappings}
            unmapped_columns = [col for col in df.columns if col not in mapped_sources]
            
            if unmapped_columns:
                st.subheader("⚠️ Extra Columns (Not in Canonical Schema)")
                for col in unmapped_columns:
                    cols = st.columns([2, 2, 1])
                    with cols[0]:
                        st.text(f"🔶 {col}")
                    with cols[1]:
                        action = st.selectbox(
                            f"Action for {col}",
                            ["❌ Drop (default)", "➕ Keep as extra column"],
                            key=f"extra_{col}"
                        )
                        if action.startswith("➕"):
                            # User wants to keep this column
                            st.session_state.mappings[col] = col  # Keep with original name
                            # Also save as promoted column for future files
                            if st.button(f"📚 Remember for future files", key=f"remember_{col}"):
                                success = st.session_state.mapper.promote_column_to_schema(col)
                                if success:
                                    st.success(f"✅ {col} will be kept in future files!")
                    with cols[2]:
                        st.text("🔴 Extra")
            
            # Show Missing Canonical Columns
            mapped_targets = set(st.session_state.mappings.values())
            missing_canonical = [col for col in st.session_state.mapper.canonical_schema.keys() 
                               if col not in mapped_targets]
            
            if missing_canonical:
                st.subheader("📋 Missing Canonical Columns")
                st.info("These canonical columns have no source data and will be filled with NaN or defaults:")
                for col in missing_canonical:
                    cols = st.columns([2, 2, 1])
                    with cols[0]:
                        st.text(f"📝 {col}")
                    with cols[1]:
                        if col == 'country':
                            st.text("🇮🇳 Default: India")
                        elif col in ['order_date']:
                            if st.button(f"📅 Set today's date for {col}", key=f"default_{col}"):
                                success = st.session_state.mapper.save_default_value_rule(col, datetime.now().strftime('%Y-%m-%d'), 'current_date')
                                if success:
                                    st.success("✅ Default date rule saved for future files!")
                        else:
                            st.text("❌ Will be NaN")
                    with cols[2]:
                        st.text("⭕ Missing")
        
        with col2:
            st.subheader("Schema Reference")
            schema_items = list(st.session_state.mapper.canonical_schema.items())
            mid_point = len(schema_items) // 2

            col_a, col_b = st.columns(2)

            with col_a:
                for canonical_col, description in schema_items[:mid_point]:
                    st.text(f"**{canonical_col}**")
                    st.caption(description)
                    st.write("")

            with col_b:
                for canonical_col, description in schema_items[mid_point:]:
                    st.text(f"**{canonical_col}**")
                    st.caption(description)
                    st.write("")
        
        # One-Click Clean & Validate
        if st.session_state.mappings:
            st.header("🧹 Clean & Validate")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("**Ready to clean your data?** This will apply standardization rules and detect issues.")
            with col2:
                clean_button = st.button("🚀 Clean Data", type="primary", use_container_width=True)

            if clean_button:
                with st.spinner("Cleaning data..."):
                    cleaned_df, issues = st.session_state.mapper.clean_data(df, st.session_state.mappings)
                    st.session_state.cleaned_data = cleaned_df
                    st.session_state.cleaning_issues = issues

                    # Detect targeted fixes on cleaned data
                    with st.spinner("Detecting targeted fixes..."):
                        targeted_fixes = st.session_state.mapper.detect_targeted_fixes(cleaned_df, st.session_state.mappings)
                        st.session_state.targeted_fixes = targeted_fixes
                
                st.success("✨ Data cleaning completed successfully!")

                # Clean Dashboard-Style Report
                st.markdown("### 📊 Data Quality Report")

                # Main metrics in organized layout
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**📂 Before Processing**")
                    before_col1, before_col2 = st.columns(2)
                    with before_col1:
                        st.metric("📊 Total Records", len(df))
                    with before_col2:
                        st.metric("📂 Original Columns", len(df.columns))

                    # Show sample data issues if any
                    sample_issues = []
                    for col in df.columns:
                        if df[col].dtype == 'object':
                            unique_vals = df[col].astype(str).unique()[:3]
                            if any('₹' in str(val) or '$' in str(val) or '%' in str(val) for val in unique_vals):
                                sample_issues.append(f"{col}: {', '.join(str(v) for v in unique_vals)}")

                    if sample_issues:
                        st.markdown("**⚠️ Issues Detected:**")
                        for issue in sample_issues[:2]:  # Limit to 2 for space
                            st.caption(f"• {issue}")

                with col2:
                    st.markdown("**✨ After Processing**")
                    after_col1, after_col2 = st.columns(2)
                    with after_col1:
                        st.metric("✅ Clean Records", len(cleaned_df))
                    with after_col2:
                        st.metric("🔄 Mapped Columns", len(st.session_state.mappings))

                    # Show applied fixes if any
                    if issues:
                        st.markdown("**🔧 Fixes Applied:**")
                        for issue in issues[:2]:  # Limit to 2 for space
                            st.caption(f"• {issue['column']}: {issue['rule']}")
                    else:
                        st.success("✅ No issues found - data is clean!")
                
                st.divider()

                # Detailed comparison
                with st.expander("🔍 Detailed Before/After Comparison"):
                    for source_col, target_col in st.session_state.mappings.items():
                        if source_col in df.columns:
                            comp_col1, comp_col2 = st.columns(2)
                            
                            with comp_col1:
                                st.write(f"**Before: {source_col}**")
                                st.write(df[source_col].head())
                            
                            with comp_col2:
                                st.write(f"**After: {target_col}**")
                                st.write(cleaned_df[source_col].head())
        
        # Targeted Fix Queue
        if hasattr(st.session_state, 'targeted_fixes') and st.session_state.targeted_fixes:
            st.header("🎯 Targeted Fixes Available")
            st.info(f"💡 Found **{len(st.session_state.targeted_fixes)} specific issues** that can be automatically fixed. Apply individual fixes or bulk apply similar fixes together.")
            
            # Group fixes by type for better organization
            fix_groups = {}
            for fix in st.session_state.targeted_fixes:
                fix_type = fix['type']
                if fix_type not in fix_groups:
                    fix_groups[fix_type] = []
                fix_groups[fix_type].append(fix)
            
            for fix_type, fixes in fix_groups.items():
                with st.expander(f"📝 {fix_type.replace('_', ' ').title()} ({len(fixes)} issues)", expanded=True):
                    for i, fix in enumerate(fixes[:5]):  # Show first 5 of each type
                        cols = st.columns([3, 2, 2, 1])
                        
                        with cols[0]:
                            st.write(f"**Row {fix['row']}**: {fix['issue']}")
                            st.code(f"Current: {fix['current_value']}")
                            st.code(f"Suggested: {fix['suggested_fix']}")
                        
                        with cols[1]:
                            confidence_color = "🟢" if fix['confidence'] > 0.8 else "🟡"
                            st.metric("Confidence", f"{confidence_color} {fix['confidence']:.1%}")
                        
                        with cols[2]:
                            # Apply individual fix
                            individual_key = f"apply_{fix_type}_{i}"
                            # Ensure applied_fixes is initialized
                            if 'applied_fixes' not in st.session_state:
                                st.session_state.applied_fixes = {}
                            if 'fix_history' not in st.session_state:
                                st.session_state.fix_history = []
                            already_applied = st.session_state.applied_fixes.get(individual_key, False)

                            if already_applied:
                                if st.button(f"↩️ Undo Fix", key=f"undo_{individual_key}"):
                                    # Find and restore the original value
                                    for j in range(len(st.session_state.fix_history) - 1, -1, -1):
                                        history_item = st.session_state.fix_history[j]
                                        if (history_item['type'] == 'individual_apply' and
                                            history_item['row'] == fix['row'] and
                                            history_item['column'] == fix['column']):
                                            st.session_state.cleaned_data.loc[fix['row'], fix['column']] = history_item['original_value']
                                            st.session_state.applied_fixes[individual_key] = False
                                            del st.session_state.fix_history[j]
                                            st.success(f"↩️ Undid fix for row {fix['row']}")
                                            st.rerun()
                                            break
                            else:
                                if st.button(f"Apply Fix", key=individual_key):
                                    # Apply fix to the cleaned data
                                    if hasattr(st.session_state, 'cleaned_data'):
                                        # Store original value for undo
                                        original_value = st.session_state.cleaned_data.loc[fix['row'], fix['column']]

                                        # Apply the fix
                                        st.session_state.cleaned_data.loc[fix['row'], fix['column']] = fix['suggested_fix']

                                        # Track applied fix and history
                                        st.session_state.applied_fixes[individual_key] = True
                                        st.session_state.fix_history.append({
                                            'type': 'individual_apply',
                                            'row': fix['row'],
                                            'column': fix['column'],
                                            'original_value': original_value,
                                            'new_value': fix['suggested_fix'],
                                            'timestamp': datetime.now().isoformat()
                                        })


                                        st.success(f"✅ Applied fix to row {fix['row']}")
                                        st.rerun()
                        
                        with cols[3]:
                            # Promote fix to become a rule
                            if st.button(f"📚 Promote", key=f"promote_{fix_type}_{i}"):
                                # Save this fix pattern as a learned rule
                                rule_saved = st.session_state.mapper._save_cleaning_rule(fix)
                                if rule_saved:
                                    st.success("✅ Fix promoted to cleaning pack!")
                                else:
                                    st.error("Failed to save rule")
                    
                    if len(fixes) > 5:
                        st.write(f"... and {len(fixes) - 5} more similar issues")
                        
                        # Bulk apply option for remaining fixes
                        col1, col2 = st.columns(2)

                        bulk_key = f"bulk_apply_{fix_type}"
                        # Ensure applied_fixes is initialized
                        if 'applied_fixes' not in st.session_state:
                            st.session_state.applied_fixes = {}
                        if 'fix_history' not in st.session_state:
                            st.session_state.fix_history = []
                        already_applied = st.session_state.applied_fixes.get(bulk_key, False)

                        with col1:
                            if already_applied:
                                st.success(f"✅ {len(fixes)} fixes applied!")
                            else:
                                if st.button(f"Apply All {len(fixes)} Fixes", key=bulk_key):
                                    if hasattr(st.session_state, 'cleaned_data'):
                                        # Store original values for undo
                                        original_values = []
                                        for fix in fixes:
                                            original_values.append({
                                                'row': fix['row'],
                                                'column': fix['column'],
                                                'original_value': st.session_state.cleaned_data.loc[fix['row'], fix['column']],
                                                'new_value': fix['suggested_fix']
                                            })

                                        # Apply fixes
                                        for fix in fixes:
                                            st.session_state.cleaned_data.loc[fix['row'], fix['column']] = fix['suggested_fix']

                                        # Track applied fixes and history
                                        st.session_state.applied_fixes[bulk_key] = True
                                        st.session_state.fix_history.append({
                                            'type': 'bulk_apply',
                                            'fix_type': fix_type,
                                            'count': len(fixes),
                                            'original_values': original_values,
                                            'timestamp': datetime.now().isoformat()
                                        })

                                        st.success(f"✅ Applied all {len(fixes)} fixes!")
                                        st.rerun()

                        with col2:
                            # Undo button if fixes were applied
                            if already_applied and st.session_state.fix_history:
                                if st.button(f"↩️ Undo All", key=f"undo_{fix_type}"):
                                    # Find the most recent matching fix in history
                                    for i in range(len(st.session_state.fix_history) - 1, -1, -1):
                                        history_item = st.session_state.fix_history[i]
                                        if (history_item['type'] == 'bulk_apply' and
                                            history_item['fix_type'] == fix_type):
                                            # Restore original values
                                            for restore in history_item['original_values']:
                                                st.session_state.cleaned_data.loc[restore['row'], restore['column']] = restore['original_value']

                                            # Remove from applied fixes and history
                                            st.session_state.applied_fixes[bulk_key] = False
                                            del st.session_state.fix_history[i]

                                            st.success(f"↩️ Undid {history_item['count']} fixes!")
                                            st.rerun()
                                            break
        
        # Legacy Leftover Issues (keep for backward compatibility)
        elif hasattr(st.session_state, 'cleaning_issues') and st.session_state.cleaning_issues:
            st.header("🔧 Leftover Issues")
            
            for issue in st.session_state.cleaning_issues:
                with st.expander(f"Fix suggestion for {issue['column']} (Confidence: {issue['confidence']:.1%})"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write("**Before:**")
                        for val in issue['before_sample']:
                            st.code(val)
                    
                    with col2:
                        st.write("**After:**")
                        for val in issue['after_sample']:
                            st.code(val)
                    
                    with col3:
                        if st.button(f"✅ Promote Fix", key=f"promote_{issue['column']}_{issue['rule']}"):
                            # Save as learned rule
                            st.session_state.mapper._save_legacy_cleaning_rule(issue)
                            st.success("Fix promoted to cleaning pack!")
        
        # Download Results
        if st.session_state.cleaned_data is not None:
            st.header("⬇️ Download Cleaned Data")
            
            # Create dataframe with ONLY mapped columns - drop missing and unwanted extra columns
            canonical_order = list(st.session_state.mapper.canonical_schema.keys())
            
            # Only include columns that were successfully mapped
            mapped_df = pd.DataFrame()
            kept_columns = []
            
            # Add mapped canonical columns
            for source_col, target_col in st.session_state.mappings.items():
                if source_col in st.session_state.cleaned_data.columns and target_col in canonical_order:
                    mapped_df[target_col] = st.session_state.cleaned_data[source_col]
                    kept_columns.append(target_col)
            
            # Add any extra columns user explicitly chose to keep
            extra_columns = []
            for source_col, target_col in st.session_state.mappings.items():
                if target_col not in canonical_order:  # Extra column user wants to keep
                    mapped_df[target_col] = st.session_state.cleaned_data[source_col]
                    extra_columns.append(target_col)
                    kept_columns.append(target_col)
            
            # Reorder to match canonical schema order (only kept columns)
            final_order = [col for col in canonical_order if col in kept_columns] + extra_columns
            mapped_df = mapped_df[final_order]
            
            # Track what was dropped for reporting
            st.session_state.dropped_info = {
                'missing_canonical': [col for col in canonical_order if col not in kept_columns],
                'dropped_extra': [col for col in st.session_state.uploaded_data.columns 
                                 if col not in st.session_state.mappings.keys()],
                'kept_columns': kept_columns
            }
            
            # Apply intelligent filling for empty/nan values in mapped columns
            for col in mapped_df.columns:
                if col == 'country':
                    # Force country to be India - don't use any other column data
                    mapped_df[col] = 'India'
                elif col == 'currency' and mapped_df[col].isna().any():
                    mapped_df[col] = mapped_df[col].fillna('INR')
                elif col in ['billing_address', 'shipping_address']:
                    # Use the other address if one is missing
                    other_addr = 'shipping_address' if col == 'billing_address' else 'billing_address' 
                    if other_addr in mapped_df.columns:
                        mapped_df[col] = mapped_df[col].fillna(mapped_df[other_addr])
            
            # Ensure all empty values are properly NaN for CSV export
            mapped_df = mapped_df.replace('', pd.NA)
            mapped_df = mapped_df.replace(' ', pd.NA)
            
            # Standard download (only mapped columns) with proper CSV escaping
            csv_data = mapped_df.to_csv(index=False, na_rep='<NA>', quoting=1, escapechar='\\')  # Proper CSV formatting
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    "📥 Download Cleaned CSV (Standard)",
                    csv_data,
                    f"cleaned_{uploaded_file.name}",
                    "text/csv",
                    help="Download with only successfully mapped columns"
                )
            
            with col2:
                # Create full dataset with all canonical columns (including missing ones as NaN)
                full_canonical_df = pd.DataFrame(index=mapped_df.index)
                canonical_order = list(st.session_state.mapper.canonical_schema.keys())
                
                # Add all canonical columns (mapped ones + missing ones as NaN)
                for col in canonical_order:
                    if col in mapped_df.columns:
                        full_canonical_df[col] = mapped_df[col]
                    else:
                        full_canonical_df[col] = pd.NA  # Missing columns as NaN
                
                # Add any extra columns user chose to keep
                for col in mapped_df.columns:
                    if col not in canonical_order:
                        full_canonical_df[col] = mapped_df[col]
                
                # Ensure consistent NaN handling
                full_canonical_df = full_canonical_df.replace('', pd.NA)
                full_canonical_df = full_canonical_df.replace(' ', pd.NA)
                
                full_csv_data = full_canonical_df.to_csv(index=False, na_rep='<NA>', quoting=1, escapechar='\\')  # Proper CSV formatting
                st.download_button(
                    "📥 Download Complete CSV (All Columns)",
                    full_csv_data,
                    f"complete_{uploaded_file.name}",
                    "text/csv",
                    help="Download with all canonical columns (missing values shown as NaN)"
                )
            
            # Show data quality summary
            st.markdown("**Final Data Summary:**")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Records", len(mapped_df))

            with col2:
                st.metric("Kept Columns", len(mapped_df.columns))
            with col3:
                if len(mapped_df.columns) > 0:
                    missing_data_pct = (mapped_df.isnull().sum().sum() / (len(mapped_df) * len(mapped_df.columns))) * 100
                    st.metric("Data Completeness", f"{100-missing_data_pct:.1f}%")
                else:
                    st.metric("Data Completeness", "0%")
            with col4:
                dropped_count = len(st.session_state.dropped_info['missing_canonical']) + len(st.session_state.dropped_info['dropped_extra'])
                st.metric("Dropped Columns", dropped_count)
            
            # Button to show all columns with drop reasons
            if st.button("📋 Show All Columns & Drop Reasons", type="secondary"):
                st.subheader("📊 Complete Column Analysis")
                
                # Show kept columns
                if st.session_state.dropped_info['kept_columns']:
                    st.write("### ✅ Kept Columns")
                    kept_df = pd.DataFrame({
                        'Column': st.session_state.dropped_info['kept_columns'],
                        'Status': ['✅ Kept'] * len(st.session_state.dropped_info['kept_columns']),
                        'Reason': ['Successfully mapped from source data'] * len(st.session_state.dropped_info['kept_columns'])
                    })
                    st.dataframe(kept_df, use_container_width=True)
                
                # Show dropped missing canonical columns
                if st.session_state.dropped_info['missing_canonical']:
                    st.write("### ❌ Dropped Missing Canonical Columns")
                    missing_reasons = []
                    for col in st.session_state.dropped_info['missing_canonical']:
                        if col == 'state':
                            reason = "No state/province column found in source data"
                        elif col == 'country':
                            reason = "No country column found in source data"
                        elif col == 'currency':
                            reason = "No currency column found in source data"
                        elif col in ['category', 'subcategory']:
                            reason = f"No {col} column found in source data"
                        else:
                            reason = f"No matching column found for {col} in source data"
                        missing_reasons.append(reason)
                    
                    missing_df = pd.DataFrame({
                        'Column': st.session_state.dropped_info['missing_canonical'],
                        'Status': ['❌ Dropped (Missing)'] * len(st.session_state.dropped_info['missing_canonical']),
                        'Reason': missing_reasons
                    })
                    st.dataframe(missing_df, use_container_width=True)
                
                # Show dropped extra columns
                if st.session_state.dropped_info['dropped_extra']:
                    st.write("### ❌ Dropped Extra Columns")
                    extra_reasons = []
                    for col in st.session_state.dropped_info['dropped_extra']:
                        if col.upper().startswith('COUPON'):
                            reason = "Not in canonical schema - user chose to drop (marketing/promo data)"
                        elif 'ID' in col.upper() and 'ORDER' not in col.upper() and 'CUSTOMER' not in col.upper():
                            reason = "Not in canonical schema - appears to be internal ID field"
                        elif col.upper() in ['NOTES', 'COMMENTS', 'REMARKS']:
                            reason = "Not in canonical schema - free text field not standardized"
                        else:
                            reason = "Not in canonical schema - user chose not to map this column"
                        extra_reasons.append(reason)
                    
                    extra_df = pd.DataFrame({
                        'Column': st.session_state.dropped_info['dropped_extra'],
                        'Status': ['❌ Dropped (Extra)'] * len(st.session_state.dropped_info['dropped_extra']),
                        'Reason': extra_reasons
                    })
                    st.dataframe(extra_df, use_container_width=True)
                
                # Summary
                st.write("### 📈 Summary")
                total_original = len(st.session_state.uploaded_data.columns)
                total_kept = len(st.session_state.dropped_info['kept_columns'])
                total_dropped = dropped_count
                
                summary_df = pd.DataFrame({
                    'Metric': ['Original Columns', 'Kept Columns', 'Dropped Columns', 'Retention Rate'],
                    'Value': [
                        total_original,
                        total_kept, 
                        total_dropped,
                        f"{(total_kept/total_original)*100:.1f}%" if total_original > 0 else "0%"
                    ]
                })
                st.dataframe(summary_df, use_container_width=True)
            
            with st.expander("Preview cleaned data"):
                st.dataframe(mapped_df.head())
                
            # Show missing data analysis for mapped columns only
            if len(mapped_df.columns) > 0:
                with st.expander("Missing Data Analysis"):
                    missing_summary = mapped_df.isnull().sum()
                    missing_summary = missing_summary[missing_summary > 0].sort_values(ascending=False)
                    if len(missing_summary) > 0:
                        st.write("**Columns with missing data:**")
                        for col, count in missing_summary.items():
                            pct = (count / len(mapped_df)) * 100
                            st.write(f"• **{col}**: {count} missing ({pct:.1f}%)")
                    else:
                        st.success("✅ No missing data in mapped columns!")

if __name__ == "__main__":
    main()