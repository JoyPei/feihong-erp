import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "erp_data.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_no TEXT,                    -- 編號 (如 1-1, 2-1)
        customer_name TEXT NOT NULL,      -- 公司名稱
        agent TEXT,                       -- 代理商
        si TEXT,                          -- SI
        sales_rep TEXT,                   -- 業務
        purchase_date TEXT,               -- 採購日期
        purchase_content TEXT,            -- 採購內容
        payment_stage TEXT,               -- 收款階段
        
        license_no TEXT,                  -- 授權證號
        license_qty TEXT,                 -- 授權數量
        license_period TEXT,              -- 授權期間
        license_expiry TEXT,              -- 授權到期
        
        warranty_no TEXT,                 -- 保固證號
        warranty_period TEXT,             -- 保固期間
        warranty_expiry TEXT,             -- 保固到期日
        warranty_status TEXT,             -- 保固狀態 (保固中 / 即將到期 / 已過期 / 永久授權)
        
        so_no TEXT,                       -- S/O No.
        warranty_engineer TEXT,           -- 保固工程師
        shipping_regulation TEXT,         -- 出貨規章
        remark TEXT,                      -- 備註
        
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 檢查是否已有初始資料，沒有的話植入截圖中的範例資料
    cursor.execute("SELECT COUNT(*) FROM contracts")
    count = cursor.fetchone()[0]
    
    if count == 0:
        seed_data = [
            (
                "1-1", "上銀保經", "", "無", "Jenlin", "2018/09/05",
                "無任何資料僅有trello紀錄購買 70U永久", "全額",
                "LIC-2018-001", "70U", "永久", "永久",
                "WAR-2018-001", "1年", "2019/09/04", "已過期",
                "SO-20180905-01", "陳工程師", "標準出貨規章 A", "無任何資料僅有trello紀錄購買 70U永久"
            ),
            (
                "2-1", "臺北榮總-106S026A", "", "無", "Dennis", "2017/11/16",
                "400MAC+P360*2", "全額",
                "LIC-2017-089", "400MAC", "1年", "2018/11/15",
                "WAR-2017-089", "1年", "2018/11/15", "已過期",
                "SO-20171116-03", "林工程師", "標準出貨規章 B", "第一期已結案"
            ),
            (
                "2-2", "臺北榮總-N107169", "", "無", "Dennis", "2018/12/20",
                "MA一年 (2019/1/1-2019/12/31)", "1-4期",
                "LIC-2018-112", "400MAC", "1年", "2019/12/31",
                "WAR-2018-112", "1年", "2019/12/31", "已過期",
                "SO-20181220-01", "林工程師", "年度維護約", "分期付款第一期"
            ),
            (
                "3-1", "戶政司", "", "飛泓", "Jenlin", "2019/03/23",
                "1000 MAC (P110*6+P220*1)", "全額",
                "LIC-2019-045", "1000MAC", "3年", "2022/03/22",
                "WAR-2019-045", "3年", "2022/03/22", "已過期",
                "SO-20190323-01", "張工程師", "專案特規", "重要政府專案"
            ),
            (
                "4-1", "松下產業", "", "宏碁", "Jenlin", "2018/03/04",
                "400MAC+P110*4", "全額",
                "LIC-2018-023", "400MAC", "1年", "2019/03/03",
                "WAR-2018-023", "1年", "2019/03/03", "已過期",
                "SO-20180304-02", "黃工程師", "標準出貨規章 A", "首期導入"
            ),
            (
                "4-5", "松下產業-MA 2022", "", "宏碁", "Jenlin", "2022/03/20",
                "MA一年 (2022/4/1-2023/3/31)", "全額",
                "LIC-2022-099", "400MAC", "1年", "2023/03/31",
                "WAR-2022-099", "1年", "2023/03/31", "已過期",
                "SO-20220320-01", "黃工程師", "維護合約", "續約"
            ),
            (
                "4-6", "松下產業-MA 2026", "", "宏碁", "Jenlin", "2026/03/16",
                "MA一年 (2026/4/1-2027/3/31)", "全額",
                "LIC-2026-105", "400MAC", "1年", "2027/03/31",
                "WAR-2026-105", "1年", "2027/03/31", "保固中",
                "SO-20260316-01", "黃工程師", "維護合約", "2026年度最新續約合約"
            ),
            (
                "5-1", "智邦科技", "聯強", "微星", "Kevin", "2026/09/10",
                "500U Enterprise 授權 + 專案導入", "1-2期",
                "LIC-2026-312", "500U", "1年", "2027/09/09",
                "WAR-2026-312", "1年", "2026/10/31", "即將到期",
                "SO-20260910-05", "王工程師", "企業旗艦專案規章", "保固即將於本月底到期，洽談維護約中"
            )
        ]
        
        cursor.executemany("""
        INSERT INTO contracts (
            item_no, customer_name, agent, si, sales_rep, purchase_date,
            purchase_content, payment_stage,
            license_no, license_qty, license_period, license_expiry,
            warranty_no, warranty_period, warranty_expiry, warranty_status,
            so_no, warranty_engineer, shipping_regulation, remark
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_data)
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

