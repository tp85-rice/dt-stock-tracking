# inputs/

Filled driver sheets, one per ticker: `NVDA_driver_sheet.xlsx`, `SE_driver_sheet.xlsx`, ...

Start from `templates/stock_driver_template.xlsx`. Check a sheet before importing:

```bash
python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx --dry-run
```

The repo is private; keep it that way while this folder holds our research.
