import os
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
import database
import excel_service
import ai_agent_service

app = Flask(__name__)
database.init_db()

def determine_warranty_status(expiry_str, fallback_status="保固中"):
    """依據保固到期日自動計算目前保固狀態"""
    if not expiry_str:
        return fallback_status or "保固中"
    clean = str(expiry_str).strip()
    if "永久" in clean:
        return "永久授權"
    
    clean_date = clean.replace("-", "/")
    parts = clean_date.split("/")
    if len(parts) == 3:
        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            exp_date = datetime(year, month, day).date()
            today = datetime.now().date()
            diff_days = (exp_date - today).days
            if diff_days < 0:
                return "已過期"
            elif diff_days <= 30:
                return "即將到期"
            else:
                return "保固中"
        except Exception:
            pass
    return fallback_status or "保固中"

def sync_all_statuses():
    """每次統計或批量讀取時確保狀態與當天即時同步"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, warranty_expiry, warranty_status FROM contracts WHERE warranty_expiry IS NOT NULL AND warranty_expiry != ''")
    rows = cursor.fetchall()
    for row in rows:
        cid = row["id"]
        exp = row["warranty_expiry"]
        curr = row["warranty_status"]
        new_st = determine_warranty_status(exp, curr)
        if new_st != curr:
            cursor.execute("UPDATE contracts SET warranty_status = ? WHERE id = ?", (new_st, cid))
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stats")
def get_stats():
    sync_all_statuses()
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM contracts")
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contracts WHERE warranty_status = '保固中'")
    active_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contracts WHERE warranty_status = '即將到期'")
    expiring_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contracts WHERE warranty_status = '已過期'")
    expired_count = cursor.fetchone()[0]
    
    # 業務人員清單
    cursor.execute("SELECT DISTINCT sales_rep FROM contracts WHERE sales_rep IS NOT NULL AND sales_rep != ''")
    sales_reps = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return jsonify({
        "total": total_count,
        "active": active_count,
        "expiring": expiring_count,
        "expired": expired_count,
        "sales_reps": sales_reps
    })

@app.route("/api/contracts", methods=["GET"])
def get_contracts():
    query_str = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    sales_filter = request.args.get("sales_rep", "").strip()
    
    sql = "SELECT * FROM contracts WHERE 1=1"
    params = []
    
    if query_str:
        sql += """ AND (
            customer_name LIKE ? OR 
            license_no LIKE ? OR 
            warranty_no LIKE ? OR 
            so_no LIKE ? OR 
            sales_rep LIKE ? OR 
            item_no LIKE ? OR 
            remark LIKE ?
        )"""
        wildcard = f"%{query_str}%"
        params.extend([wildcard] * 7)
        
    if status_filter and status_filter != "all":
        sql += " AND warranty_status = ?"
        params.append(status_filter)
        
    if sales_filter and sales_filter != "all":
        sql += " AND sales_rep = ?"
        params.append(sales_filter)
        
    sql += " ORDER BY id DESC"
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    contracts = [dict(row) for row in rows]
    conn.close()
    
    return jsonify(contracts)

@app.route("/api/contracts/<int:contract_id>", methods=["GET"])
def get_contract(contract_id):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return jsonify({"error": "找不到該筆資料"}), 404
    return jsonify(dict(row))

@app.route("/api/contracts", methods=["POST"])
def create_contract():
    data = request.json or {}
    customer_name = data.get("customer_name", "").strip()
    if not customer_name:
        return jsonify({"error": "公司名稱為必填欄位"}), 400
        
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO contracts (
        item_no, customer_name, agent, si, sales_rep, purchase_date,
        purchase_content, payment_stage,
        license_no, license_qty, license_period, license_expiry,
        warranty_no, warranty_period, warranty_expiry, warranty_status,
        so_no, warranty_engineer, shipping_regulation, remark, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        data.get("item_no", ""),
        customer_name,
        data.get("agent", ""),
        data.get("si", ""),
        data.get("sales_rep", ""),
        data.get("purchase_date", ""),
        data.get("purchase_content", ""),
        data.get("payment_stage", ""),
        data.get("license_no", ""),
        data.get("license_qty", ""),
        data.get("license_period", ""),
        data.get("license_expiry", ""),
        data.get("warranty_no", ""),
        data.get("warranty_period", ""),
        data.get("warranty_expiry", ""),
        determine_warranty_status(data.get("warranty_expiry", ""), data.get("warranty_status", "保固中")),
        data.get("so_no", ""),
        data.get("warranty_engineer", ""),
        data.get("shipping_regulation", ""),
        data.get("remark", "")
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "id": new_id}), 201

@app.route("/api/contracts/<int:contract_id>", methods=["PUT"])
def update_contract(contract_id):
    data = request.json or {}
    customer_name = data.get("customer_name", "").strip()
    if not customer_name:
        return jsonify({"error": "公司名稱為必填欄位"}), 400
        
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE contracts SET
        item_no = ?, customer_name = ?, agent = ?, si = ?, sales_rep = ?, purchase_date = ?,
        purchase_content = ?, payment_stage = ?,
        license_no = ?, license_qty = ?, license_period = ?, license_expiry = ?,
        warranty_no = ?, warranty_period = ?, warranty_expiry = ?, warranty_status = ?,
        so_no = ?, warranty_engineer = ?, shipping_regulation = ?, remark = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        data.get("item_no", ""),
        customer_name,
        data.get("agent", ""),
        data.get("si", ""),
        data.get("sales_rep", ""),
        data.get("purchase_date", ""),
        data.get("purchase_content", ""),
        data.get("payment_stage", ""),
        data.get("license_no", ""),
        data.get("license_qty", ""),
        data.get("license_period", ""),
        data.get("license_expiry", ""),
        data.get("warranty_no", ""),
        data.get("warranty_period", ""),
        data.get("warranty_expiry", ""),
        determine_warranty_status(data.get("warranty_expiry", ""), data.get("warranty_status", "保固中")),
        data.get("so_no", ""),
        data.get("warranty_engineer", ""),
        data.get("shipping_regulation", ""),
        data.get("remark", ""),
        contract_id
    ))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route("/api/contracts/<int:contract_id>", methods=["DELETE"])
def delete_contract(contract_id):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/export-template")
def export_template():
    excel_stream = excel_service.generate_excel_template()
    return send_file(
        excel_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="客戶與授權保固匯入範本.xlsx"
    )

@app.route("/api/export-excel")
def export_excel():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contracts ORDER BY id ASC")
    rows = cursor.fetchall()
    contracts = [dict(row) for row in rows]
    conn.close()
    
    excel_stream = excel_service.export_contracts_to_excel(contracts)
    filename = f"飛泓_授權與保固明細表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        excel_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/api/import-excel", methods=["POST"])
def import_excel():
    if "file" not in request.files:
        return jsonify({"error": "請選擇要上傳的 Excel 檔案"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "未選擇任何檔案"}), 400
        
    try:
        import io
        file_bytes = io.BytesIO(file.read())
        records = excel_service.parse_excel_file(file_bytes)
        if not records:
            return jsonify({"error": "Excel 檔案中未找到有效的客戶資料或表頭不符"}), 400
            
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        insert_count = 0
        for rec in records:
            cursor.execute("""
            INSERT INTO contracts (
                item_no, customer_name, agent, si, sales_rep, purchase_date,
                purchase_content, payment_stage,
                license_no, license_qty, license_period, license_expiry,
                warranty_no, warranty_period, warranty_expiry, warranty_status,
                so_no, warranty_engineer, shipping_regulation, remark
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.get("item_no", ""),
                rec.get("customer_name", ""),
                rec.get("agent", ""),
                rec.get("si", ""),
                rec.get("sales_rep", ""),
                rec.get("purchase_date", ""),
                rec.get("purchase_content", ""),
                rec.get("payment_stage", ""),
                rec.get("license_no", ""),
                rec.get("license_qty", ""),
                rec.get("license_period", ""),
                rec.get("license_expiry", ""),
                rec.get("warranty_no", ""),
                rec.get("warranty_period", ""),
                rec.get("warranty_expiry", ""),
                determine_warranty_status(rec.get("warranty_expiry", ""), rec.get("warranty_status", "保固中")),
                rec.get("so_no", ""),
                rec.get("warranty_engineer", ""),
                rec.get("shipping_regulation", ""),
                rec.get("remark", "")
            ))
            insert_count += 1
            
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"成功匯入 {insert_count} 筆客戶授權與保固資料！",
            "count": insert_count
        })
    except Exception as e:
        return jsonify({"error": f"匯入失敗: {str(e)}"}), 500

@app.route("/api/auto-calculate-status", methods=["POST"])
def auto_calculate_status():
    """根據當前日期自動校正保固狀態"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, warranty_expiry, warranty_status FROM contracts")
    rows = cursor.fetchall()
    
    today = datetime.now().date()
    updated_count = 0
    
    for r in rows:
        cid = r["id"]
        expiry_str = r["warranty_expiry"]
        old_status = r["warranty_status"]
        
        if not expiry_str or expiry_str == "永久":
            continue
            
        try:
            # 支援 2026/10/31 或 2026-10-31
            clean_str = expiry_str.strip().replace("-", "/")
            exp_date = datetime.strptime(clean_str, "%Y/%m/%d").date()
            
            diff = (exp_date - today).days
            new_status = old_status
            if diff < 0:
                new_status = "已過期"
            elif diff <= 30:
                new_status = "即將到期"
            else:
                new_status = "保固中"
                
            if new_status != old_status:
                cursor.execute("UPDATE contracts SET warranty_status = ? WHERE id = ?", (new_status, cid))
                updated_count += 1
        except Exception:
            pass
            
    conn.commit()
    conn.close()
    return jsonify({"success": True, "updated_count": updated_count})

@app.route("/api/ai-agent/ask", methods=["POST"])
def ai_agent_ask():
    data = request.json or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "請提供查詢問題"}), 400
        
    result = ai_agent_service.run_ai_agent_query(query)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
