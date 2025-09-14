# 🎯 Schema Mapper & Data Quality Fixer

A comprehensive web application built with Streamlit that automatically maps CSV columns to a canonical schema, detects data quality issues, and provides intelligent fixes with undo functionality.

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   pip install streamlit pandas
   ```

2. **Run the Application**
   ```bash
   # Use the provided batch file for proper encoding
   run.bat

   # Or run directly with:
   set PYTHONIOENCODING=utf-8 && streamlit run app.py --server.headless=true --server.port=8899
   ```

3. **Access the Application**
   - Open your browser to `http://localhost:8899`

## 📋 Features

### 🎯 Intelligent Column Mapping
- **Fuzzy Matching**: Uses sequence matching to suggest column mappings
- **Learning System**: Remembers your mapping choices for future files
- **Confidence Scoring**: Shows mapping confidence with color-coded indicators
- **Extra Column Handling**: Option to keep or drop non-canonical columns

### 🧹 Data Quality & Cleaning
- **Automated Cleaning**: Removes currency symbols, fixes spacing, standardizes formats
- **NaN Standardization**: Consistent handling of empty values and null representations
- **Data Type Conversion**: Smart conversion of percentages, currencies, and dates
- **Phone Number Preservation**: Careful cleaning that preserves formatted phone numbers

### 🎯 Targeted Fix System
- **Issue Detection**: Identifies specific data problems with suggested fixes
- **Bulk Operations**: Apply similar fixes across multiple records
- **Undo Functionality**: Complete undo system for individual and bulk fixes
- **Rule Promotion**: Convert fixes into reusable cleaning rules

### 📊 Data Quality Reporting
- **Before/After Analysis**: Visual comparison of data quality metrics
- **Missing Data Analysis**: Detailed breakdown of data completeness
- **Column Analysis**: Complete mapping and dropping reason analysis

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web App                        │
├─────────────────────────────────────────────────────────────┤
│  📁 File Upload  │  🎯 Mapping  │  🧹 Cleaning  │  ⬇️ Export  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SchemaMapper Class                       │
├─────────────────────────────────────────────────────────────┤
│  • Canonical Schema Loading                                 │
│  • Fuzzy Column Matching                                   │
│  • Learning & Rule Management                              │
│  • Data Cleaning Engine                                    │
│  • Targeted Fix Detection                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────┬─────────────────┬─────────────────────────┐
│  📋 Canonical   │  📚 Learning    │    🔧 Cleaning          │
│     Schema      │     Rules       │      Patterns           │
├─────────────────┼─────────────────┼─────────────────────────┤
│ • order_id      │ • Column        │ • Currency removal      │
│ • customer_name │   mappings      │ • Percentage conversion │
│ • email         │ • Cleaning      │ • Phone standardization │
│ • phone         │   rules         │ • Date parsing          │
│ • address       │ • Promotions    │ • Postal code cleaning  │
│ • ...           │ • Defaults      │ • Email spacing fixes   │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Data Flow Architecture

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CSV File  │───▶│  Column Mapping │───▶│ Data Cleaning   │
│   Upload    │    │   Suggestions   │    │   & Issues      │
└─────────────┘    └─────────────────┘    └─────────────────┘
                            │                       │
                            ▼                       ▼
                   ┌─────────────────┐    ┌─────────────────┐
                   │  User Reviews   │    │ Targeted Fixes  │
                   │  & Confirms     │    │   Detection     │
                   │   Mappings      │    │                 │
                   └─────────────────┘    └─────────────────┘
                            │                       │
                            ▼                       ▼
                   ┌─────────────────┐    ┌─────────────────┐
                   │ Apply Mappings  │    │  User Applies   │
                   │   & Clean       │    │ Individual/Bulk │
                   │     Data        │    │     Fixes       │
                   └─────────────────┘    └─────────────────┘
                            │                       │
                            └───────┬───────────────┘
                                    ▼
                           ┌─────────────────┐
                           │ Generate Clean  │
                           │   CSV Output    │
                           │  (Standard &    │
                           │   Complete)     │
                           └─────────────────┘
```

### Session State Management

```
Session State Structure:
├── uploaded_data: Original DataFrame
├── mappings: {source_col: target_col} dictionary
├── cleaned_data: Cleaned DataFrame after processing
├── applied_fixes: {fix_id: boolean} tracking
├── fix_history: List of fix operations for undo
├── mapper: SchemaMapper instance
└── temporary states:
    ├── mapping_suggestions: Suggested mappings
    ├── cleaning_issues: Detected data issues
    └── targeted_fixes: Specific fixable problems
```

## 📁 File Structure

```
schema-mapper-project/
├── app.py                    # Main Streamlit application
├── run.bat                   # Windows batch file for proper encoding
├── Project6StdFormat.csv     # Canonical schema definition
├── mapping_rules.json        # Learned rules and mappings (auto-generated)
├── file_history.json         # Fix history tracking (auto-generated)
├── README.md                 # This documentation
└── test_data/
    ├── Project6InputData1.csv
    ├── Project6InputData2.csv
    └── Project6InputData3.csv
```

## 🎯 Core Classes & Methods

### SchemaMapper Class

#### Key Methods:

**`__init__(rules_file="mapping_rules.json")`**
- Initializes the mapper with canonical schema and learned rules
- Loads cleaning patterns and previous mappings

**`suggest_mappings(input_columns: List[str]) -> List[MappingRule]`**
- Uses fuzzy matching to suggest column mappings
- Prioritizes learned mappings and exact matches
- Returns confidence-scored suggestions

**`clean_data(df: DataFrame, mappings: Dict) -> Tuple[DataFrame, List]`**
- Applies systematic data cleaning rules
- Handles NaN standardization, format fixes
- Returns cleaned data and list of applied changes

**`detect_targeted_fixes(df: DataFrame, mappings: Dict) -> List[Dict]`**
- Identifies specific fixable data issues
- Generates targeted suggestions for common problems
- Supports phone formatting, email spacing, postal codes, dates

#### Data Structures:

**MappingRule**
```python
@dataclass
class MappingRule:
    source_column: str
    target_column: str
    confidence: float
    transformation: str = "direct"
    learned: bool = False
```

**CleaningRule**
```python
@dataclass
class CleaningRule:
    column: str
    rule_type: str
    pattern: str
    replacement: str
    confidence: float
    learned: bool = False
```

## 🧹 Data Cleaning Pipeline

### Stage 1: Basic Normalization
1. **Empty Value Standardization**: `'', ' ', 'nan', 'NULL', etc. → pd.NA`
2. **Text Cleaning**: Remove embedded newlines, tabs, extra spaces
3. **Special Character Handling**: Preserve formatted data while cleaning

### Stage 2: Type-Specific Cleaning
1. **Currency Fields**: Remove symbols (`₹$€£`), handle commas
2. **Percentages**: Convert `"15%"` → `0.15`
3. **Phone Numbers**: Standardize format while preserving international codes
4. **Email Addresses**: Fix spacing around `@` symbol
5. **Dates**: Parse various formats → ISO standard (`YYYY-MM-DD`)
6. **Postal Codes**: Handle XX patterns, preserve as strings

### Stage 3: Intelligent Defaults
1. **Country**: Auto-fill with "India" if missing
2. **Currency**: Default to "INR"
3. **Address Sync**: Use billing address for shipping if missing (and vice versa)

## 🎯 Targeted Fix System

### Fix Categories:

**Phone Number Fixes**
- Missing country code detection
- Format standardization (`+91-9876543210`)
- Invalid character removal

**Email Fixes**
- Spacing around `@` symbol
- Domain validation
- Format standardization

**Postal Code Fixes**
- XX pattern resolution (`667XX2` → `667002`)
- Format validation
- String preservation

**Date Fixes**
- Non-ISO format detection
- Multiple format parsing
- Standardization to `YYYY-MM-DD`

### Fix Application Modes:

1. **Individual Apply**: Fix single records with undo capability
2. **Bulk Apply**: Apply same fix type across multiple records
3. **Rule Promotion**: Convert fixes into permanent cleaning rules

## 📊 Data Quality Metrics

### Before Processing:
- Total Records
- Original Columns
- Sample Data Issues

### After Processing:
- Clean Records
- Mapped Columns
- Applied Fixes Summary

### Final Analysis:
- Data Completeness Percentage
- Dropped Columns Count
- Missing Data Breakdown

## 🔄 Session Management

### File Upload Behavior:
- **New File Detection**: Compare DataFrame equality
- **State Reset**: Clear previous mappings, fixes, and results
- **Learning Retention**: Keep learned rules across sessions

### Undo System:
- **Individual Undo**: Restore single cell values
- **Bulk Undo**: Restore multiple changes in one operation
- **History Tracking**: Complete audit trail of all changes

## 📤 Export Options

### Standard CSV:
- Only successfully mapped columns
- Canonical schema order
- NaN representation for empty values

### Complete CSV:
- All canonical columns (with NaN for missing)
- Extra columns user chose to keep
- Full schema compliance

## 🎨 UI Design Philosophy

### Clean & Minimal:
- Focused workflow: Upload → Map → Clean → Fix → Download
- Progressive disclosure of complex features
- Color-coded confidence indicators

### User Experience:
- **Visual Feedback**: Progress indicators, success messages
- **Error Prevention**: Confirmation for destructive actions
- **Flexibility**: Multiple export options, undo capabilities

## 🔧 Configuration

### Canonical Schema:
- Defined in `Project6StdFormat.csv`
- 25 standard e-commerce fields
- Extensible through column promotion

### Cleaning Patterns:
- Currency symbol removal
- Percentage conversion
- Phone standardization
- Email format fixes
- Date parsing rules

### Learning System:
- Automatic rule saving in `mapping_rules.json`
- Confidence-based suggestions
- User preference memory

## 🚀 Advanced Features

### Learning & Adaptation:
- Column mapping memory across sessions
- Cleaning rule promotion system
- User preference learning

### Data Integrity:
- Complete undo system
- Audit trail for all changes
- Original data preservation

### Scalability:
- Efficient processing of large CSVs
- Streaming data display
- Memory-conscious operations

## 🐛 Troubleshooting

### Common Issues:

**Unicode Errors**
- Use `run.bat` for proper encoding
- Ensure `PYTHONIOENCODING=utf-8` is set

**Session State Issues**
- Refresh the page to reset all states
- Check browser console for JavaScript errors

**CSV Export Problems**
- Verify column mappings are complete
- Check for special characters in data

### Performance:
- Large files (>10MB) may take longer to process
- Consider chunking very large datasets
- Monitor memory usage during processing

## 📈 Future Enhancements

### Planned Features:
- **Multiple File Processing**: Batch processing capability
- **Advanced Validation**: Custom validation rules
- **API Integration**: REST API for automated processing
- **Machine Learning**: Enhanced mapping suggestions
- **Cloud Storage**: Direct cloud file integration

### Architecture Improvements:
- **Database Backend**: Replace JSON with SQLite
- **Caching System**: Redis integration for performance
- **User Management**: Multi-user support
- **Logging**: Comprehensive audit logging

---

## 📄 License

This project is intended for educational and internal use. Please ensure compliance with your organization's data handling policies.

## 🤝 Contributing

This is a specialized internal tool. For modifications or enhancements, please follow the established code patterns and maintain backward compatibility with existing learned rules.