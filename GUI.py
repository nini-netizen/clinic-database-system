import tkinter as tk
from tkinter import messagebox, scrolledtext
import pyodbc
from datetime import date

#連線
CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=NINI;"             
    "Database=ClinicDB3;"
    "Trusted_Connection=yes;"
)

def get_conn():
    return pyodbc.connect(CONN_STR, autocommit=True)


def to_int(txt: str, label: str):
    """字串→int；若空或非整數則警告並回傳 None"""
    txt = txt.strip()
    if not txt.isdigit():
        messagebox.showwarning("輸入錯誤", f"{label} 必須是整數！")
        return None
    return int(txt)

#GUI
root = tk.Tk()
root.title("ClinicDB3 查詢介面")
root.geometry("920x640")

#左側：新增病患表單
form = tk.LabelFrame(root, text="新增病患", padx=10, pady=10)
form.pack(side="left", fill="y", padx=10, pady=10)

labels = ["姓名", "生日 YYYY-MM-DD", "性別 M/F", "電話", "Email", "地址"]
entries = {}
for i, text in enumerate(labels):
    tk.Label(form, text=text).grid(row=i, column=0, sticky="e")
    ent = tk.Entry(form, width=22)
    ent.grid(row=i, column=1, pady=2)
    entries[text] = ent

def add_patient():
    vals = [e.get().strip() for e in entries.values()]
    if not vals[0] or not vals[1]:
        messagebox.showwarning("必填", "姓名與生日必填")
        return
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO Patients (name,birthday,gender,phone,email,address)
                   VALUES (?,?,?,?,?,?)""",
                vals
            )
        messagebox.showinfo("完成", "病患已新增")
        for e in entries.values():
            e.delete(0, tk.END)
    except Exception as e:
        messagebox.showerror("錯誤", str(e))

tk.Button(form, text="新增", command=add_patient, width=18).grid(row=len(labels), column=0, columnspan=2, pady=8)

#右側：查詢區
query = tk.LabelFrame(root, text="輸入參數", padx=6, pady=6)
query.pack(fill="x", padx=10, pady=6)

var_pid = tk.StringVar()
var_sid = tk.StringVar()
var_vid = tk.StringVar()
var_year = tk.StringVar()

fields = [("病患 ID:", var_pid),
          ("員工 ID:", var_sid),
          ("就診 ID:", var_vid),
          ("年份:",   var_year)]

for i, (lab, var) in enumerate(fields):
    tk.Label(query, text=lab).grid(row=0, column=2*i, padx=2, sticky="e")
    tk.Entry(query, textvariable=var, width=7).grid(row=0, column=2*i+1, padx=2)

#結果
result = scrolledtext.ScrolledText(root, font=("Consolas", 10))
result.pack(fill="both", expand=True, padx=10, pady=8)

def run_query(sql: str, params=()):
    """執行查詢並把結果印到 result"""
    print(f"DEBUG >> {sql} | Params: {params}")
    
    if any(p is None for p in params):   
        result.delete("1.0", tk.END)
        result.insert(tk.END, "(請先輸入有效參數)\n")
        return

    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            headers = [d[0] for d in cur.description]
    except Exception as e:
        messagebox.showerror("查詢錯誤", str(e))
        result.delete("1.0", tk.END)
        result.insert(tk.END, f"查詢錯誤：{e}\n")
        return

    result.delete("1.0", tk.END)
    if not rows:
        result.insert(tk.END, "(查無資料)\n")
        return

    # 處理 None 值
    rows = [
        tuple('' if v is None else (v.strftime('%Y-%m-%d') if isinstance(v, date) else v) for v in r)  
        for r in rows
    ]

    col_widths = [
        max(len(str(r[i])) for r in rows + [headers]) for i in range(len(headers))
    ]
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths) + "\n"
    result.insert(tk.END, fmt.format(*headers))
    result.insert(tk.END, "-" * (sum(col_widths) + 2 * len(col_widths)) + "\n")
    for r in rows:
        result.insert(tk.END, fmt.format(*r))

# --- 查詢按鈕 --- #
btns = [
    ("病患基本資料",
        lambda: run_query("EXEC dbo.sp_PatientInfo ?",
                          (to_int(var_pid.get(), "病患 ID"),))),
    ("指定年份後出生",
        lambda: run_query("EXEC dbo.sp_BornAfterYear ?",
                          (to_int(var_year.get(), "年份"),))),
    ("姓王病患",
        lambda: run_query("SELECT * FROM v_SurnameWang")),
    ("病患就診紀錄",
        lambda: run_query("EXEC dbo.sp_PatientVisitDetail ?",
                          (to_int(var_pid.get(), "病患 ID"),))),
    ("員工指派任務",
        lambda: run_query("EXEC dbo.sp_TasksByCreator ?",
                          (to_int(var_sid.get(), "員工 ID"),))),
    ("就診處方內容",
        lambda: run_query("EXEC dbo.sp_VisitPrescription ?",
                          (to_int(var_vid.get(), "就診 ID"),))),
]

bar = tk.Frame(root, relief="groove", bd=2)  # 按鈕區
bar.pack(fill="x", padx=10, pady=(0, 4))

for i, (txt, cmd) in enumerate(btns):
    tk.Button(bar, text=txt, command=cmd, width=16).grid(row=0, column=i, padx=2, pady=2)

root.mainloop()
