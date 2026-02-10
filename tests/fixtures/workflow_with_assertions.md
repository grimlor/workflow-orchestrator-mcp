# Workflow with Assertions

## Validation Phase

### 🔧 WORKFLOW STEP: Validate data quality
```
Run data quality checks on the target dataset.
Verify row count, null percentage, and schema compliance.
```

### 🛠️ TOOL: data_quality_check

### ✅ ASSERT:
- result.row_count > 1000
- result.null_percentage < 5
- result.schema_valid == true
- result contains "quality_score"

## Report Phase

### 🔧 WORKFLOW STEP: Generate quality report
```
Generate a summary report of data quality results.
```

### 🛠️ TOOLS:
- generate_report
- send_notification

### 📥 INPUTS:
- QUALITY_SCORE: Overall quality score from validation

### 📤 OUTPUTS:
- result.report_url → REPORT_URL

### ✅ ASSERT:
- result.report_url starts with "https://"
- result.notification_sent == true
