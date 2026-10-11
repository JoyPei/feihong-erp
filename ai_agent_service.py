import database
from datetime import datetime

def run_ai_agent_query(query_text):
    """
    Ragic 風格的內建 AI Agent：
    具備「查資料、抓異常、產報表、業務分析」核心能力。
    """
    query = (query_text or "").strip().lower()
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contracts ORDER BY id ASC")
    all_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    total = len(all_rows)
    today = datetime.now().date()

    # 1. 抓異常或缺漏
    if any(k in query for k in ["異常", "缺漏", "檢查", "問題", "沒填", "漏填", "incomplete", "error"]):
        missing_so = [r for r in all_rows if not r.get("so_no")]
        missing_expiry = [r for r in all_rows if not r.get("warranty_expiry")]
        missing_rep = [r for r in all_rows if not r.get("sales_rep")]
        
        flagged_ids = list(set([r["id"] for r in (missing_so + missing_expiry + missing_rep)]))
        
        reply = f"### ⚠️ AI Agent 系統資料完整性檢測報告\n\n"
        reply += f"AI Agent 已掃描全系統 **{total}** 筆合約記錄，發現以下 **{len(flagged_ids)}** 筆需補全資料：\n\n"
        
        if missing_so:
            reply += f"**1. 未填寫 S/O No. ({len(missing_so)} 筆)：**\n"
            for r in missing_so[:5]:
                reply += f"- **{r['customer_name']}** (編號: {r['item_no'] or '未填'})\n"
            if len(missing_so) > 5:
                reply += f"- ...等共 {len(missing_so)} 筆\n"
            reply += "\n"
            
        if missing_expiry:
            reply += f"**2. 未設定保固到期日 ({len(missing_expiry)} 筆)：**\n"
            for r in missing_expiry[:5]:
                reply += f"- **{r['customer_name']}** (業務: {r['sales_rep'] or '未指派'})\n"
            reply += "\n"

        if not flagged_ids:
            reply = f"### ✅ 檢查完成：目前資料庫中所有合約之關鍵欄位皆填寫完整，未發現重大異常！"

        return {
            "reply": reply,
            "matched_ids": flagged_ids,
            "action_type": "anomaly_check"
        }

    # 2. 查即將到期 / 過期
    elif any(k in query for k in ["即將到期", "快到期", "到期", "續約", "expir"]):
        expiring = [r for r in all_rows if r.get("warranty_status") == "即將到期"]
        expired = [r for r in all_rows if r.get("warranty_status") == "已過期"]
        
        matched_ids = [r["id"] for r in expiring]
        
        reply = f"### 🚨 AI Agent 保固與續約追蹤提醒\n\n"
        reply += f"根據今日系統即時計算：\n"
        reply += f"- ⚡ **30天內即將到期合約：{len(expiring)} 筆**（建議業務優先洽談維護約）\n"
        reply += f"- ⏳ **已過期歷史合約：{len(expired)} 筆**\n\n"
        
        if expiring:
            reply += "**即將到期客戶名單：**\n"
            for r in expiring:
                reply += f"- 📌 **{r['customer_name']}** ｜ 到期日: `{r['warranty_expiry']}` ｜ 業務: `{r['sales_rep'] or '未指派'}` ｜ 證號: `{r['warranty_no'] or '無'}`\n"
        else:
            reply += "目前沒有 30 天內即將到期的客戶。\n"

        return {
            "reply": reply,
            "matched_ids": matched_ids,
            "action_type": "expiring_contracts"
        }

    # 3. 產週報 / 彙整報告
    elif any(k in query for k in ["週報", "月報", "報告", "總結", "彙整", "report", "summary"]):
        active_cnt = sum(1 for r in all_rows if r.get("warranty_status") == "保固中")
        expiring_cnt = sum(1 for r in all_rows if r.get("warranty_status") == "即將到期")
        expired_cnt = sum(1 for r in all_rows if r.get("warranty_status") == "已過期")
        
        # 統計各業務
        reps_stat = {}
        for r in all_rows:
            rep = r.get("sales_rep") or "未指派"
            reps_stat[rep] = reps_stat.get(rep, 0) + 1
            
        top_reps = sorted(reps_stat.items(), key=lambda x: x[1], reverse=True)
        
        reply = f"### 📊 飛泓科技 - 進銷存與授權保固彙整週報 (AI Agent 自動生成)\n\n"
        reply += f"**一、全域營運總結：**\n"
        reply += f"- 累計管理合約總數：**{total}** 筆\n"
        reply += f"- 🟢 正常保固中：**{active_cnt}** 筆 ({(active_cnt/total*100):.1f}%)\n"
        reply += f"- 🟡 即將到期警示：**{expiring_cnt}** 筆 ({(expiring_cnt/total*100):.1f}%)\n"
        reply += f"- ⚪ 已過期歷史合約：**{expired_cnt}** 筆 ({(expired_cnt/total*100):.1f}%)\n\n"
        
        reply += f"**二、業務案件量分佈：**\n"
        for rep, count in top_reps:
            reply += f"- 👤 **{rep}**：{count} 筆客戶合約\n"
        reply += "\n"
        
        reply += f"**三、本週行動建議 (Action Items)：**\n"
        if expiring_cnt > 0:
            reply += f"1. 立即跟進 **{expiring_cnt}** 筆即將到期之客戶，寄發維護續約報價單。\n"
        reply += f"2. 建議針對歷史過期客戶進行年度系統版本升級促銷。\n"

        return {
            "reply": reply,
            "matched_ids": [r["id"] for r in all_rows],
            "action_type": "weekly_report"
        }

    # 4. 業務績效或專屬分析
    elif any(k in query for k in ["業務", "銷售", "jenlin", "dennis", "kevin", "業績"]):
        reps_stat = {}
        for r in all_rows:
            rep = r.get("sales_rep") or "未指派"
            if rep not in reps_stat:
                reps_stat[rep] = {"total": 0, "active": 0, "customers": []}
            reps_stat[rep]["total"] += 1
            if r.get("warranty_status") == "保固中":
                reps_stat[rep]["active"] += 1
            reps_stat[rep]["customers"].append(r["customer_name"])

        reply = f"### 👥 AI Agent 業務合約分佈洞察\n\n"
        for rep, data in sorted(reps_stat.items(), key=lambda x: x[1]["total"], reverse=True):
            reply += f"#### 🔹 業務人員: **{rep}**\n"
            reply += f"- 負責合約筆數：**{data['total']}** 筆 (有效保固: {data['active']} 筆)\n"
            top_cust = list(dict.fromkeys(data['customers']))[:4]
            reply += f"- 代表客戶：{', '.join(top_cust)}\n\n"

        return {
            "reply": reply,
            "matched_ids": [r["id"] for r in all_rows],
            "action_type": "sales_insight"
        }

    # 5. 特定公司或關鍵字查詢
    else:
        matched = []
        for r in all_rows:
            combined = f"{r.get('customer_name','')} {r.get('license_no','')} {r.get('warranty_no','')} {r.get('so_no','')} {r.get('purchase_content','')} {r.get('sales_rep','')}".lower()
            if query in combined:
                matched.append(r)
                
        if matched:
            reply = f"### 🔍 AI Agent 查找到 {len(matched)} 筆符合「{query_text}」的合約：\n\n"
            for r in matched[:8]:
                reply += f"- **{r['customer_name']}** (編號: `{r['item_no'] or '-'}`) ｜ 狀態: `{r['warranty_status']}` ｜ 業務: `{r['sales_rep'] or '-'}` ｜ 到期日: `{r['warranty_expiry'] or '-'}`\n"
            if len(matched) > 8:
                reply += f"- ...等共 {len(matched)} 筆\n"
            reply += f"\n💡 *已自動在下方列表篩選出這些項目。*"
            return {
                "reply": reply,
                "matched_ids": [r["id"] for r in matched],
                "action_type": "filter_results"
            }
        else:
            return {
                "reply": f"🤖 我是 Ragic 內建 AI Agent，您輸入了「{query_text}」。目前未找到直接關聯的合約。\n\n您可以點擊下方快捷按鈕，由我為您執行：\n- 🔍 抓出即將到期合約\n- ⚠️ 檢查缺漏與異常\n- 📊 自動產生進銷存週報\n- 👥 業務合約佔比分析",
                "matched_ids": [],
                "action_type": "not_found"
            }

