import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime

# 欄位定義：資料庫欄位名稱 -> Excel 表頭名稱
FIELD_MAPPING = [
    ("item_no", "編號"),
    ("customer_name", "公司名稱"),
    ("agent", "代理商"),
    ("si", "SI"),
    ("sales_rep", "業務"),
    ("purchase_date", "採購日期"),
    ("purchase_content", "採購內容"),
    ("payment_stage", "收款階段"),
    ("license_no", "授權證號"),
    ("license_qty", "授權數量"),
    ("license_period", "授權期間"),
    ("license_expiry", "授權到期"),
    ("warranty_no", "保固證號"),
    ("warranty_period", "保固期間"),
    ("warranty_expiry", "保固到期日"),
    ("warranty_status", "保固狀態"),
    ("so_no", "S/O No."),
    ("warranty_engineer", "保固工程師"),
    ("shipping_regulation", "出貨規章"),
    ("remark", "備註"),
]

HEADER_TO_FIELD = {excel_title.strip(): field_name for field_name, excel_title in FIELD_MAPPING}
# 增加別名相容
HEADER_TO_FIELD["客戶名稱"] = "customer_name"
HEADER_TO_FIELD["SO No."] = "so_no"
HEADER_TO_FIELD["SO No"] = "so_no"
HEADER_TO_FIELD["SO編號"] = "so_no"
HEADER_TO_FIELD["保固到期"] = "warranty_expiry"

def generate_excel_template():
    """產生空白 Excel 範本"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "客戶與授權保固資料"
    
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Microsoft JhengHei", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # 寫入表頭
    for col_idx, (_, header_name) in enumerate(FIELD_MAPPING, 1):
        cell = ws.cell(row=1, column=col_idx, value=header_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        
        # 調整適當欄寬
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(len(header_name) * 3, 15)

    ws.row_dimensions[1].height = 28

    # 寫入一行範例說明
    example_row = [
        "1-1", "範例科技股份有限公司", "某某代理", "某某SI", "王大明", "2026/01/15",
        "500U Enterprise 企業授權", "全額", "LIC-2026-001", "500U", "1年", "2027/01/14",
        "WAR-2026-001", "1年", "2027/01/14", "保固中", "SO-20260115-01", "李工程師", "標準出貨規章", "新客戶簽約"
    ]
    for col_idx, val in enumerate(example_row, 1):
        cell = ws.cell(row=2, column=col_idx, value=val)
        cell.font = Font(name="Microsoft JhengHei", size=10, color="595959")
        cell.border = thin_border
        cell.alignment = Alignment(vertical="center")
    
    ws.row_dimensions[2].height = 22

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def export_contracts_to_excel(contracts):
    """將現有資料匯出為 Excel"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "授權與保固明細表"

    header_fill = PatternFill(start_color="2A4365", end_color="2A4365", fill_type="solid")
    header_font = Font(name="Microsoft JhengHei", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # 寫入表頭
    for col_idx, (_, header_name) in enumerate(FIELD_MAPPING, 1):
        cell = ws.cell(row=1, column=col_idx, value=header_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(len(header_name) * 3, 16)

    ws.row_dimensions[1].height = 28

    # 斑馬紋樣式
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    for row_idx, contract in enumerate(contracts, 2):
        is_even = (row_idx % 2 == 0)
        for col_idx, (field_key, _) in enumerate(FIELD_MAPPING, 1):
            val = contract.get(field_key, "") if isinstance(contract, dict) else contract[field_key]
            cell = ws.cell(row=row_idx, column=col_idx, value=str(val) if val is not None else "")
            cell.font = Font(name="Microsoft JhengHei", size=10)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")
            if not is_even:
                cell.fill = alt_fill
        ws.row_dimensions[row_idx].height = 22

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def parse_excel_file(file_stream):
    """解析上傳的 Excel 檔案為記錄清單"""
    wb = openpyxl.load_workbook(file_stream, data_only=True)
    ws = wb.active
    
    headers = []
    # 讀取第 1 列的表頭
    for col in range(1, ws.max_column + 1):
        val = ws.cell(row=1, column=col).value
        headers.append(str(val).strip() if val else "")

    records = []
    for row in range(2, ws.max_row + 1):
        row_dict = {}
        has_content = False
        
        for col, header in enumerate(headers, 1):
            if not header:
                continue
            field_name = HEADER_TO_FIELD.get(header)
            if not field_name:
                continue
            
            raw_val = ws.cell(row=row, column=col).value
            if raw_val is not None:
                val_str = str(raw_val).strip()
                # 處理日期物件
                if isinstance(raw_val, datetime):
                    val_str = raw_val.strftime("%Y/%m/%d")
                if val_str != "":
                    has_content = True
                row_dict[field_name] = val_str
            else:
                row_dict[field_name] = ""
        
        # 只保留有公司名稱或有填寫內容的列
        if has_content and row_dict.get("customer_name"):
            records.append(row_dict)
            
    return records

