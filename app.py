
import sqlite3
import os
import csv
from io import StringIO, TextIOWrapper
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response
 
app = Flask(__name__)
app.secret_key = "telematics_erp_secret_key"
DB_NAME = "database.db"
 
# --- 1. تهيئة قاعدة البيانات والترقية التلقائية للأعمدة ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name_model TEXT,
            serial_vin TEXT UNIQUE,
            counter_val REAL,
            counter_type TEXT,
            status TEXT DEFAULT 'جاهز'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            company TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT UNIQUE,
            part_name TEXT,
            quantity INTEGER,
            min_quantity INTEGER,
            unit_price REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            technician TEXT,
            fault_diagnosis TEXT,
            status TEXT DEFAULT 'قيد التشخيص',
            date_created TEXT,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            item_type TEXT,
            description TEXT,
            quantity INTEGER,
            unit_price REAL,
            total_price REAL,
            FOREIGN KEY(order_id) REFERENCES work_orders(id)
        )
    ''')
    
    missing_columns = [
        ("work_orders", "technician TEXT"),
        ("work_orders", "fault_diagnosis TEXT"),
        ("work_orders", "date_created TEXT"),
        ("vehicles", "counter_type TEXT")
    ]
    
    for table, col in missing_columns:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
            
    conn.commit()
    conn.close()
 
init_db()
 
WORKSHOP_NAME = "ورشة الهدى لصيانة السيارات والآليات"
 
# --- 2. القالب الرئيسي (Bootstrap 5 RTL) ---
MAIN_LAYOUT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورشة الهدى لصيانة السيارات والآليات</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <style>
        body { font-family: sans-serif; background-color: #f4f6f9; }
        .sidebar { min-height: 100vh; background-color: #1e293b; color: #fff; }
        .sidebar a { color: #cbd5e1; text-decoration: none; padding: 12px 20px; display: block; border-radius: 6px; margin-bottom: 4px; }
        .sidebar a:hover, .sidebar a.active { background-color: #3b82f6; color: #fff; }
        .card-stat { border: none; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 sidebar p-3 d-none d-md-block">
                <h4 class="text-center fw-bold text-white mb-4"><i class="bi bi-gear-wide-connected"></i> ورشة الهدى</h4>
                <hr class="border-secondary">
                <a href="/" class="{{ 'active' if page == 'dashboard' }}"><i class="bi bi-speedometer2 me-2"></i> لوحة التحكم</a>
                <a href="/work_orders" class="{{ 'active' if page == 'orders' }}"><i class="bi bi-tools me-2"></i> أوامر الشغل</a>
                <a href="/vehicles" class="{{ 'active' if page == 'vehicles' }}"><i class="bi bi-truck me-2"></i> الأسطول والمعدات</a>
                <a href="/inventory" class="{{ 'active' if page == 'inventory' }}"><i class="bi bi-box-seam me-2"></i> المخزون وقطع الغيار</a>
                <a href="/clients" class="{{ 'active' if page == 'clients' }}"><i class="bi bi-people me-2"></i> العملاء والشركات</a>
                <hr class="border-secondary">
                <a href="/logout" class="text-danger"><i class="bi bi-box-arrow-right me-2"></i> خروج</a>
            </div>
 
            <div class="col-md-10 ms-sm-auto p-4">
                {% with messages = get_flashed_messages(with_categories=true) %}
                  {% if messages %}
                    {% for cat, msg in messages %}
                      <div class="alert alert-{{ cat }} alert-dismissible fade show" role="alert">
                        {{ msg }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                      </div>
                    {% endfor %}
                  {% endif %}
                {% endwith %}
 
                {{ content | safe }}
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
 
# --- 3. المسارات الرئيسية ---
 
@app.route('/')
def dashboard():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    total_vehicles = cursor.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
    active_orders = cursor.execute("SELECT COUNT(*) FROM work_orders WHERE status != 'مكتمل'").fetchone()[0]
    low_stock = cursor.execute("SELECT COUNT(*) FROM inventory WHERE quantity <= min_quantity").fetchone()[0]
    
    recent_orders = cursor.execute('''
        SELECT wo.id, v.name_model, wo.technician, wo.status, wo.date_created 
        FROM work_orders wo JOIN vehicles v ON wo.vehicle_id = v.id 
        ORDER BY wo.id DESC LIMIT 5
    ''').fetchall()
    conn.close()
 
    content = f"""
    <h3 class="fw-bold mb-4">نظرة عامة على الورشة</h3>
    <div class="row g-3 mb-4">
        <div class="col-md-4">
            <div class="card card-stat bg-primary text-white p-3">
                <h6>إجمالي الآليات والسيارات</h6><h2 class="fw-bold mb-0">{total_vehicles}</h2>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card card-stat bg-warning text-dark p-3">
                <h6>أوامر الصيانة النشطة</h6><h2 class="fw-bold mb-0">{active_orders}</h2>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card card-stat bg-danger text-white p-3">
                <h6>تنبيهات نواقص المخزون</h6><h2 class="fw-bold mb-0">{low_stock}</h2>
            </div>
        </div>
    </div>
 
    <div class="card shadow-sm border-0">
        <div class="card-header bg-white fw-bold d-flex justify-content-between align-items-center">
            <span>آخر أوامر الشغل المفتوحة</span>
            <a href="/export/orders/excel" class="btn btn-sm btn-outline-success"><i class="bi bi-file-earmark-excel"></i> تصدير Excel</a>
        </div>
        <div class="card-body p-0">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr><th>رقم الأمر</th><th>المعدة</th><th>الفني</th><th>الحالة</th><th>التاريخ</th></tr>
                </thead>
                <tbody>
    """
    for o in recent_orders:
        content += f"<tr><td>#{o[0]}</td><td>{o[1]}</td><td>{o[2]}</td><td><span class='badge bg-info'>{o[3]}</span></td><td>{o[4]}</td></tr>"
    content += "</tbody></table></div></div>"
    
    return render_template_string(MAIN_LAYOUT, page="dashboard", content=content)
 
@app.route('/vehicles', methods=['GET', 'POST'])
def vehicles():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
 
    if request.method == 'POST':
        try:
            cursor.execute(
                "INSERT INTO vehicles (category, name_model, serial_vin, counter_val, counter_type) VALUES (?, ?, ?, ?, ?)",
                (request.form['category'], request.form['name_model'], request.form['serial_vin'], float(request.form['counter_val']), request.form['counter_type'])
            )
            conn.commit()
            flash("تم إضافة المعدة بنجاح", "success")
        except sqlite3.IntegrityError:
            flash("الرقم التسلسلي / VIN مكرر", "danger")
        return redirect('/vehicles')
 
    vehs = cursor.execute("SELECT * FROM vehicles").fetchall()
    conn.close()
 
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 class="fw-bold">إدارة الأسطول والمعدات</h3>
        <div>
            <a href="/export/vehicles/excel" class="btn btn-outline-success me-1"><i class="bi bi-download"></i> تصدير Excel</a>
            <button class="btn btn-outline-info me-2" data-bs-toggle="modal" data-bs-target="#importVehModal"><i class="bi bi-upload"></i> استيراد CSV</button>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addVehModal"><i class="bi bi-plus-circle"></i> إضافة معدة</button>
        </div>
    </div>
    <div class="card shadow-sm border-0"><div class="card-body p-0">
        <table class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr><th>#</th><th>التصنيف</th><th>الموديل</th><th>السيريال / VIN</th><th>العداد</th><th>الحالة</th></tr>
            </thead>
            <tbody>
    """
    for v in vehs:
        c_type = v[5] if len(v) > 5 and v[5] else ""
        content += f"<tr><td>{v[0]}</td><td>{v[1]}</td><td>{v[2]}</td><td><code>{v[3]}</code></td><td>{v[4]} {c_type}</td><td><span class='badge bg-success'>{v[6] if len(v) > 6 else 'جاهز'}</span></td></tr>"
    content += f"""
            </tbody>
        </table>
    </div></div>
 
    <!-- Modal إضافة معدة -->
    <div class="modal fade" id="addVehModal" tabindex="-1"><div class="modal-dialog"><form class="modal-content" method="POST">
        <div class="modal-header"><h5 class="modal-title">تسجيل معدة جديدة</h5></div>
        <div class="modal-body">
            <select name="category" class="form-select mb-2" required>
                <option value="آلية ثقيلة">آلية ثقيلة (CAT / Volvo / XCMG)</option>
                <option value="سيارة خفيفة">سيارة خفيفة</option>
                <option value="مولد / شاحنة">مولد / شاحنة</option>
            </select>
            <input type="text" name="name_model" class="form-control mb-2" placeholder="الموديل (مثال: CAT 320D)" required>
            <input type="text" name="serial_vin" class="form-control mb-2" placeholder="الرقم التسلسلي / VIN" required>
            <input type="number" step="0.1" name="counter_val" class="form-control mb-2" placeholder="قراءة العداد الحالية" required>
            <select name="counter_type" class="form-select mb-2">
                <option value="ساعة عمل">ساعة عمل (Hours)</option>
                <option value="كيلومتر">كيلومتر (KM)</option>
            </select>
        </div>
        <div class="modal-footer"><button type="submit" class="btn btn-primary">حفظ المعدة</button></div>
    </form></div></div>
 
    <!-- Modal استيراد CSV -->
    <div class="modal fade" id="importVehModal" tabindex="-1"><div class="modal-dialog"><form class="modal-content" method="POST" action="/import/vehicles" enctype="multipart/form-data">
        <div class="modal-header"><h5 class="modal-title">استيراد معدات من ملف CSV</h5></div>
        <div class="modal-body">
            <p class="small text-muted mb-2">تنسيق الأعمدة المطلوب في ملف CSV:<br><code>التصنيف, الموديل, السيريال, قراءة العداد, نوع العداد</code></p>
            <input type="file" name="file" class="form-control" accept=".csv" required>
        </div>
        <div class="modal-footer"><button type="submit" class="btn btn-info text-white">بدء الاستيراد</button></div>
    </form></div></div>
    """
    return render_template_string(MAIN_LAYOUT, page="vehicles", content=content)
 
@app.route('/work_orders', methods=['GET', 'POST'])
def work_orders():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
 
    if request.method == 'POST':
        cursor.execute(
            "INSERT INTO work_orders (vehicle_id, technician, fault_diagnosis, date_created) VALUES (?, ?, ?, ?)",
            (request.form['vehicle_id'], request.form['technician'], request.form['fault_diagnosis'], datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()
        flash("تم فتح أمر شغل جديد", "success")
        return redirect('/work_orders')
 
    vehicles_list = cursor.execute("SELECT id, name_model, serial_vin FROM vehicles").fetchall()
    orders = cursor.execute('''
        SELECT wo.id, v.name_model, v.serial_vin, wo.technician, wo.fault_diagnosis, wo.status, wo.date_created
        FROM work_orders wo JOIN vehicles v ON wo.vehicle_id = v.id ORDER BY wo.id DESC
    ''').fetchall()
    conn.close()
 
    veh_opts = "".join([f"<option value='{v[0]}'>{v[1]} ({v[2]})</option>" for v in vehicles_list])
 
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 class="fw-bold">أوامر الشغل (Job Cards)</h3>
        <div>
            <a href="/export/orders/excel" class="btn btn-outline-success me-2"><i class="bi bi-download"></i> تصدير Excel</a>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addOrderModal"><i class="bi bi-plus-circle"></i> أمر شغل جديد</button>
        </div>
    </div>
    <div class="card shadow-sm border-0"><div class="card-body p-0">
        <table class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr><th>#</th><th>المعدة</th><th>السيريال</th><th>الفني</th><th>التشخيص</th><th>الحالة</th><th>التاريخ</th><th>الإجراءات</th></tr>
            </thead>
            <tbody>
    """
    for o in orders:
        content += f"""
        <tr>
            <td>#{o[0]}</td>
            <td>{o[1]}</td>
            <td><code>{o[2]}</code></td>
            <td>{o[3]}</td>
            <td>{o[4]}</td>
            <td><span class='badge bg-warning text-dark'>{o[5]}</span></td>
            <td>{o[6]}</td>
            <td>
                <a href='/order_details/{o[0]}' class='btn btn-sm btn-outline-primary me-1'>التفاصيل</a>
                <a href='/export/order_pdf/{o[0]}' target='_blank' class='btn btn-sm btn-outline-danger'><i class='bi bi-file-pdf'></i> PDF</a>
            </td>
        </tr>
        """
    content += f"""
            </tbody>
        </table>
    </div></div>
 
    <div class="modal fade" id="addOrderModal" tabindex="-1"><div class="modal-dialog"><form class="modal-content" method="POST">
        <div class="modal-header"><h5 class="modal-title">فتح أمر شغل صيانة</h5></div>
        <div class="modal-body">
            <label class="form-label">اختر المعدة:</label>
            <select name="vehicle_id" class="form-select mb-2" required>{veh_opts if veh_opts else '<option value="">لا توجد معدات مسجلة</option>'}</select>
            <input type="text" name="technician" class="form-control mb-2" placeholder="اسم الفني / المهندس" required>
            <textarea name="fault_diagnosis" class="form-control mb-2" placeholder="وصف العطل وتشخيص الصيانة" rows="3" required></textarea>
        </div>
        <div class="modal-footer"><button type="submit" class="btn btn-primary">إصدار أمر الشغل</button></div>
    </form></div></div>
    """
    return render_template_string(MAIN_LAYOUT, page="orders", content=content)
 
@app.route('/order_details/<int:order_id>', methods=['GET', 'POST'])
def order_details(order_id):
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
 
    if request.method == 'POST':
        qty = int(request.form.get('quantity', 1))
        u_price = float(request.form['unit_price'])
        cursor.execute(
            "INSERT INTO order_items (order_id, item_type, description, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, request.form['item_type'], request.form['description'], qty, u_price, qty * u_price)
        )
        conn.commit()
        return redirect(f'/order_details/{order_id}')
 
    order = cursor.execute('''
        SELECT wo.id, v.name_model, v.serial_vin, wo.technician, wo.fault_diagnosis, wo.status, wo.date_created
        FROM work_orders wo JOIN vehicles v ON wo.vehicle_id = v.id WHERE wo.id = ?
    ''', (order_id,)).fetchone()
 
    items = cursor.execute("SELECT item_type, description, quantity, unit_price, total_price FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    conn.close()
 
    total_sum = sum(i[4] for i in items)
 
    content = f"""
    <div class="card shadow-sm border-0 mb-4"><div class="card-body">
        <div class="d-flex justify-content-between align-items-center">
            <h4><b>أمر شغل رقم #{order[0]}</b></h4>
            <div>
                <a href="/export/order_pdf/{order[0]}" target="_blank" class="btn btn-danger me-2"><i class="bi bi-file-pdf"></i> طباعة / حفظ PDF</a>
            </div>
        </div><hr>
        <div class="row">
            <div class="col-md-4"><b>المعدة:</b> {order[1]} ({order[2]})</div>
            <div class="col-md-4"><b>الفني:</b> {order[3]}</div>
            <div class="col-md-4"><b>التاريخ:</b> {order[6]}</div>
        </div>
        <div class="mt-2"><b>التشخيص:</b> {order[4]}</div>
    </div></div>
 
    <div class="card shadow-sm border-0 mb-4"><div class="card-body p-0">
        <table class="table table-bordered mb-0">
            <thead><tr><th>النوع</th><th>البيان</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr></thead>
            <tbody>
    """
    for i in items:
        content += f"<tr><td>{i[0]}</td><td>{i[1]}</td><td>{i[2]}</td><td>${i[3]:.2f}</td><td>${i[4]:.2f}</td></tr>"
    content += f"""
            <tr class="table-light"><td colspan="4" class="text-end"><b>الإجمالي:</b></td><td><b class="text-primary">${total_sum:.2f}</b></td></tr>
            </tbody>
        </table>
    </div></div>
 
    <div class="card shadow-sm border-0 p-3">
        <h5>إضافة بنود للفاتورة</h5>
        <form method="POST" class="row g-2">
            <div class="col-md-3">
                <select name="item_type" class="form-select"><option value="صيانة/يد">أجرة يد / صيانة</option><option value="قطع غيار">قطع غيار</option></select>
            </div>
            <div class="col-md-4"><input type="text" name="description" class="form-control" placeholder="الوصف" required></div>
            <div class="col-md-2"><input type="number" name="quantity" class="form-control" value="1" placeholder="الكمية"></div>
            <div class="col-md-2"><input type="number" step="0.1" name="unit_price" class="form-control" placeholder="السعر" required></div>
            <div class="col-md-1"><button type="submit" class="btn btn-success w-100">+</button></div>
        </form>
    </div>
    """
    return render_template_string(MAIN_LAYOUT, page="orders", content=content)
 
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
 
    if request.method == 'POST':
        try:
            cursor.execute(
                "INSERT INTO inventory (part_number, part_name, quantity, min_quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                (request.form['part_number'], request.form['part_name'], int(request.form['quantity']), int(request.form['min_quantity']), float(request.form['unit_price']))
            )
            conn.commit()
            flash("تم إضافة القطعة للمخزون", "success")
        except sqlite3.IntegrityError:
            flash("رقم القطعة مسجل مسبقاً", "danger")
        return redirect('/inventory')
 
    parts = cursor.execute("SELECT * FROM inventory").fetchall()
    conn.close()
 
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 class="fw-bold">مخزون قطع الغيار</h3>
        <div>
            <a href="/export/inventory/excel" class="btn btn-outline-success me-1"><i class="bi bi-download"></i> تصدير Excel</a>
            <button class="btn btn-outline-info me-2" data-bs-toggle="modal" data-bs-target="#importInvModal"><i class="bi bi-upload"></i> استيراد CSV</button>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addPartModal"><i class="bi bi-plus-circle"></i> إضافة قطعة</button>
        </div>
    </div>
    <div class="card shadow-sm border-0"><div class="card-body p-0">
        <table class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr><th>رقم القطعة</th><th>الاسم</th><th>الكمية المتاحة</th><th>حد الإنذار</th><th>السعر</th></tr>
            </thead>
            <tbody>
    """
    for p in parts:
        content += f"<tr><td><code>{p[1]}</code></td><td>{p[2]}</td><td><b>{p[3]}</b></td><td>{p[4]}</td><td>${p[5]:.2f}</td></tr>"
    content += f"""
            </tbody>
        </table>
    </div></div>
 
    <!-- Modal إضافة قطعة -->
    <div class="modal fade" id="addPartModal" tabindex="-1"><div class="modal-dialog"><form class="modal-content" method="POST">
        <div class="modal-header"><h5 class="modal-title">تسجيل قطعة غيار</h5></div>
        <div class="modal-body">
            <input type="text" name="part_number" class="form-control mb-2" placeholder="Part No" required>
            <input type="text" name="part_name" class="form-control mb-2" placeholder="اسم القطعة" required>
            <input type="number" name="quantity" class="form-control mb-2" placeholder="الكمية" required>
            <input type="number" name="min_quantity" class="form-control mb-2" placeholder="حد التنبيه" value="2" required>
            <input type="number" step="0.1" name="unit_price" class="form-control mb-2" placeholder="سعر البيع" required>
        </div>
        <div class="modal-footer"><button type="submit" class="btn btn-primary">حفظ</button></div>
    </form></div></div>
 
    <!-- Modal استيراد CSV مخزون -->
    <div class="modal fade" id="importInvModal" tabindex="-1"><div class="modal-dialog"><form class="modal-content" method="POST" action="/import/inventory" enctype="multipart/form-data">
        <div class="modal-header"><h5 class="modal-title">استيراد مخزون من ملف CSV</h5></div>
        <div class="modal-body">
            <p class="small text-muted mb-2">تنسيق الأعمدة المطلوب في ملف CSV:<br><code>رقم القطعة, اسم القطعة, الكمية, حد الإنذار, السعر</code></p>
            <input type="file" name="file" class="form-control" accept=".csv" required>
        </div>
        <div class="modal-footer"><button type="submit" class="btn btn-info text-white">بدء الاستيراد</button></div>
    </form></div></div>
    """
    return render_template_string(MAIN_LAYOUT, page="inventory", content=content)
 
@app.route('/clients', methods=['GET', 'POST'])
def clients():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
 
    if request.method == 'POST':
        cursor.execute("INSERT INTO clients (name, phone, company) VALUES (?, ?, ?)", (request.form['name'], request.form['phone'], request.form['company']))
        conn.commit()
        flash("تم إضافة العميل بنجاح", "success")
        return redirect('/clients')
 
    cls = cursor.execute("SELECT * FROM clients").fetchall()
    conn.close()
 
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 class="fw-bold">سجل العملاء والشركات</h3>
        <div>
            <a href="/export/clients/excel" class="btn btn-outline-success me-1"><i class="bi bi-download"></i> تصدير Excel</a>
            <button class="btn btn-outline-info me-2" data-bs-toggle="modal" data-bs-target="#importClientModal"><i class="bi bi-upload"></i> استيراد CSV</button>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addClientModal"><i class="bi bi-plus-circle"></i> إضافة عميل</button>
        </div>
    </div>
    <div class="card shadow-sm border-0"><div class="card-body p-0">
        <table class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr><th>#</th><th>اسم العميل</th><th>الهاتف</th><th>الشركة / الجهة</th></tr>
            </thead>
            <tbody>
    """
    for c in cls:
        content += f"<tr><td>{c[0]}</td><td>{c[1]}</td><td>{c[2]}</td><td>{c[3]}</td></tr>"
    content += f"""
            </tbody>
        </table>
    </div></div>
 
    <!-- Modal إضافة عميل -->
    <div class="modal fade" id="addClientModal" tabindex="-1"><div class="modal-dialog"><form class="modal-content" method="POST">
        <div class="modal-header"><h5 class="modal-title">إضافة عميل جديد</h5></div>
        <div class="modal-body">
            <input type="text" name="name" class="form-control mb-2" placeholder="اسم العميل" required>
            <input type="text" name="phone" class="form-control mb-2" placeholder="رقم الهاتف" required>
            <input type="text" name="company" class="form-control mb-2" placeholder="اسم الشركة / المؤسسة">
        </div>
        <div class="modal-footer"><button type="submit" class="btn btn-primary">حفظ البيانات</button></div>
    </form></div></div>
 
    <!-- Modal استيراد CSV عملاء -->
    <div class="modal fade" id="importClientModal" tabindex="-1"><div class="modal-dialog"><form class="modal-content" method="POST" action="/import/clients" enctype="multipart/form-data">
        <div class="modal-header"><h5 class="modal-title">استيراد عملاء من ملف CSV</h5></div>
        <div class="modal-body">
            <p class="small text-muted mb-2">تنسيق الأعمدة المطلوب في ملف CSV:<br><code>اسم العميل, رقم الهاتف, اسم الشركة</code></p>
            <input type="file" name="file" class="form-control" accept=".csv" required>
        </div>
        <div class="modal-footer"><button type="submit" class="btn btn-info text-white">بدء الاستيراد</button></div>
    </form></div></div>
    """
    return render_template_string(MAIN_LAYOUT, page="clients", content=content)
 
# --- 4. مسارات تصدير Excel (CSV) ---
 
@app.route('/export/<module>/excel')
def export_excel(module):
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    si = StringIO()
    si.write('\ufeff') # UTF-8 BOM لدعم اللغة العربية في Excel
    writer = csv.writer(si)
 
    if module == "orders":
        writer.writerow(['رقم الأمر', 'المعدة', 'السيريال', 'الفني', 'التشخيص', 'الحالة', 'التاريخ'])
        data = cursor.execute('''
            SELECT wo.id, v.name_model, v.serial_vin, wo.technician, wo.fault_diagnosis, wo.status, wo.date_created
            FROM work_orders wo JOIN vehicles v ON wo.vehicle_id = v.id ORDER BY wo.id DESC
        ''').fetchall()
    elif module == "vehicles":
        writer.writerow(['التصنيف', 'الموديل', 'السيريال / VIN', 'العداد', 'نوع العداد', 'الحالة'])
        data = cursor.execute("SELECT category, name_model, serial_vin, counter_val, counter_type, status FROM vehicles").fetchall()
    elif module == "inventory":
        writer.writerow(['رقم القطعة', 'الاسم', 'الكمية', 'حد التنبيه', 'السعر'])
        data = cursor.execute("SELECT part_number, part_name, quantity, min_quantity, unit_price FROM inventory").fetchall()
    elif module == "clients":
        writer.writerow(['اسم العميل', 'رقم الهاتف', 'الشركة'])
        data = cursor.execute("SELECT name, phone, company FROM clients").fetchall()
    else:
        conn.close()
        return "تصدير غير معروف", 400
 
    conn.close()
    for row in data:
        writer.writerow(row)
 
    output = Response(si.getvalue(), mimetype="text/csv; charset=utf-8")
    output.headers["Content-Disposition"] = f"attachment; filename={module}_export.csv"
    return output
 
# --- 5. مسارات استيراد البيانات من CSV ---
 
@app.route('/import/<module>', methods=['POST'])
def import_csv(module):
    if 'user' not in session: return redirect('/login')
    file = request.files.get('file')
    if not file or not file.filename.endswith('.csv'):
        flash("يرجى رفع ملف CSV صحيح", "danger")
        return redirect(f'/{module}')
 
    try:
        stream = TextIOWrapper(file.stream, encoding='utf-8-sig')
        reader = csv.reader(stream)
        header = next(reader, None) # تجاوز السطر الأول (العناوين)
 
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        imported_count = 0
 
        if module == "vehicles":
            for row in reader:
                if len(row) >= 4:
                    cursor.execute(
                        "INSERT OR REPLACE INTO vehicles (category, name_model, serial_vin, counter_val, counter_type) VALUES (?, ?, ?, ?, ?)",
                        (row[0].strip(), row[1].strip(), row[2].strip(), float(row[3] or 0), row[4].strip() if len(row)>4 else "ساعة عمل")
                    )
                    imported_count += 1
        elif module == "inventory":
            for row in reader:
                if len(row) >= 5:
                    cursor.execute(
                        "INSERT OR REPLACE INTO inventory (part_number, part_name, quantity, min_quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                        (row[0].strip(), row[1].strip(), int(row[2] or 0), int(row[3] or 0), float(row[4] or 0))
                    )
                    imported_count += 1
        elif module == "clients":
            for row in reader:
                if len(row) >= 2:
                    cursor.execute(
                        "INSERT INTO clients (name, phone, company) VALUES (?, ?, ?)",
                        (row[0].strip(), row[1].strip(), row[2].strip() if len(row)>2 else "")
                    )
                    imported_count += 1
 
        conn.commit()
        conn.close()
        flash(f"تم استيراد {imported_count} سجل بنجاح!", "success")
    except Exception as e:
        flash(f"حدث خطأ أثناء قراءة الملف: {str(e)}", "danger")
 
    return redirect(f'/{module}')
 
# --- 6. مسار طباعة/حفظ PDF لتقارير الصيانة ---
 
@app.route('/export/order_pdf/<int:order_id>')
def export_order_pdf(order_id):
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    order = cursor.execute('''
        SELECT wo.id, v.name_model, v.serial_vin, wo.technician, wo.fault_diagnosis, wo.status, wo.date_created
        FROM work_orders wo JOIN vehicles v ON wo.vehicle_id = v.id WHERE wo.id = ?
    ''', (order_id,)).fetchone()
 
    items = cursor.execute("SELECT item_type, description, quantity, unit_price, total_price FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    conn.close()
 
    total_sum = sum(i[4] for i in items)
 
    pdf_template = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تقرير أمر شغل #{{ order[0] }}</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
        <style>
            body { font-family: sans-serif; padding: 30px; background: #fff; }
            .header-title { border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; }
            @media print { .no-print { display: none !important; } }
        </style>
    </head>
    <body>
        <div class="text-end mb-3 no-print">
            <button onclick="window.print()" class="btn btn-primary"><i class="bi bi-printer"></i> طباعة / حفظ كـ PDF</button>
        </div>
        
        <div class="header-title d-flex justify-content-between align-items-center">
            <div>
                <h2><b>ورشة الهدى لصيانة السيارات والآليات</b></h2>
                <p class="mb-0 text-muted">تقرير صيانة وتقييم الفاتورة</p>
            </div>
            <div class="text-start">
                <h4>أمر شغل: #{{ order[0] }}</h4>
                <small>التاريخ: {{ order[6] }}</small>
            </div>
        </div>
 
        <div class="row my-4">
            <div class="col-6">
                <p><b>المعدة / الموديل:</b> {{ order[1] }}</p>
                <p><b>السيريال / VIN:</b> {{ order[2] }}</p>
            </div>
            <div class="col-6">
                <p><b>الفني المسؤول:</b> {{ order[3] }}</p>
                <p><b>حالة الأمر:</b> {{ order[5] }}</p>
            </div>
            <div class="col-12 mt-2">
                <p><b>تشخيص العطل:</b> {{ order[4] }}</p>
            </div>
        </div>
 
        <table class="table table-bordered my-4">
            <thead class="table-light">
                <tr><th>النوع</th><th>البيان</th><th>الكمية</th><th>سعر الوحدة</th><th>الإجمالي</th></tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td>{{ item[0] }}</td>
                    <td>{{ item[1] }}</td>
                    <td>{{ item[2] }}</td>
                    <td>${{ "%.2f"|format(item[3]) }}</td>
                    <td>${{ "%.2f"|format(item[4]) }}</td>
                </tr>
                {% endfor %}
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="4" class="text-end"><b>المبلغ الإجمالي:</b></td>
                    <td><b>${{ "%.2f"|format(total_sum) }}</b></td>
                </tr>
            </tfoot>
        </table>
 
        <div class="row mt-5 text-center">
            <div class="col-6"><p>توقيع المهندس الفني: ........................</p></div>
            <div class="col-6"><p>توقيع الاعتماد / المستلم: ........................</p></div>
        </div>
    </body>
    </html>
    """
    return render_template_string(pdf_template, order=order, items=items, total_sum=total_sum)
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == "admin" and request.form.get('password') == "123456":
            session['user'] = "admin"
            return redirect('/')
        flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")
    return render_template_string("""
    <!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css"></head>
    <body class="bg-dark text-white d-flex align-items-center vh-100">
        <div class="container text-center" style="max-width: 380px;">
            <div class="card bg-secondary text-white p-4 shadow-lg">
                <h3 class="mb-3">ورشة الهدى لصيانة السيارات والآليات</h3>
                <form method="POST">
                    <input type="text" name="username" class="form-control mb-3" placeholder="اسم المستخدم" required>
                    <input type="password" name="password" class="form-control mb-3" placeholder="كلمة المرور" required>
                    <button type="submit" class="btn btn-primary w-100">دخول النظام</button>
                </form>
            </div>
        </div>
    </body></html>
    """)
 
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')
 
if __name__ == '__main__':
    app.run()
