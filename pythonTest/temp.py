from flask import Flask, request, render_template, redirect, session, flash, url_for
from database import get_db_connection #عبارة عن دالة مهمتها  انشاء اتالمع الداتا بيز 
from functools import wraps
from flask_socketio import SocketIO, emit, join_room
from flask_session import Session
from datetime import timedelta
import sqlite3
import random
import json


app = Flask(__name__)
app.secret_key = 'secret'  # مهم للجلسات



app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['SESSION_PERMANENT'] = True


Session(app)

# إعداد SocketIO بدون eventlet على Windows
socketio = SocketIO(app, async_mode='threading', manage_session=False)
#---------------------------------------------------------------------------------------------------------------------



# إعداد المسار الافتراضي ليحول إلى القائمة مباشرة
@app.route('/')
def index():
    return "<script>window.location.href='/login';</script>"




def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('يجب تسجيل الدخول أولاً')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



#---------------------------------------------------------------------------------------------------------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        specialty = request.form['specialty']
        phone = request.form['phone']
        password = request.form['password']
        if len(password)<8 :
                flash("كلمة المرور اقل من 8 احرف")
                return redirect(url_for('signup')) 
        if len(phone)<10 :
                flash("رقم الهاتف غير صحيح")   
                return redirect(url_for('signup')) 

        # إدخال البيانات في قاعدة البيانات
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO User (name, specialty, phone_number, password)
                VALUES (?, ?, ?, ?)
            ''', (name, specialty, phone, password))
            conn.commit()
        
            # استرجاع بيانات المستخدم الجديد
            cursor.execute("SELECT * FROM User WHERE phone_number=? AND password=?", (phone, password))
            user = cursor.fetchone()
        
            # تخزين البيانات في الجلسة
            if user:
                session['user_id'] = user['id']
                session['name'] = user['name']
                session['specialty'] = user['specialty']
                session['phone_number'] = user['phone_number']
        
        except sqlite3.Error as e:
            flash(f'حدث خطأ: {e}', 'error')
        finally:
            conn.close()


        return redirect(url_for('homepage'))  # إعادة توجيه لنفس الصفحة بعد التسجيل
    
    return render_template('signup.html' , pagetitle="Sign up")



#---------------------------------------------------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.permanent = True

        phone_number = request.form['phoneNumber']
        password = request.form['password']

        conn = get_db_connection() # connection with database
        cursor = conn.cursor() #cursor pointer بساعدني بتنفيذ الquery
        cursor.execute("SELECT * FROM User WHERE phone_number=? AND password=?", (phone_number, password)) # ? using to avoid sql injection
        user = cursor.fetchone()
        conn.close() # deconnection with database
        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['specialty'] = user['specialty']
            session['phone_number'] = user['phone_number']
            session['role_id'] = user['role_id']
            
            
            return redirect('/home') #بنستخدمها لما يكون طريقة الدخول POST
        else:
            flash('رقم الهاتف أو كلمة المرور غير صحيحة') # لازم اعرضها بالhtml 
            return redirect('/login')
    
    return render_template('login.html', pagetitle="Log In")  #بنستخدمها لما يون طريقة الدخول GET زي LOGIN


#---------------------------------------------------------------------------------------------------------------------

@app.route('/forgetPassword')
def forgetPassword():
    return render_template('forgetPassword.html', pagetitle="Forget Password")


#---------------------------------------------------------------------------------------------------------------------

@app.route('/home')
@login_required
def homepage():
    return render_template('home.html', pagetitle="Home")


#---------------------------------------------------------------------------------------------------------------------


@app.route('/account')
@login_required
def account():
    return "<h1>صفحة Account</h1>"



#--------------------------------------------------------------------------------------------------------------------- 




@app.route('/timer')
@login_required
def timer():
    return "<h1>صفحة Timer</h1>"


#---------------------------------------------------------------------------------------------------------------------

@app.route('/logout')
def logout():
    session.clear()  # حذف كل بيانات الجلسة
    return redirect(url_for('login'))  # رجوع لصفحة تسجيل الدخول


#---------------------------------------------------------------------------------------------------------------------

@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    
    
    if request.method == 'POST':
        content = request.form['content']
        if not content:
            flash('الرجاء إدخال ملاحظاتك')
            return redirect(url_for('feedback'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO Feedback (user_id,content)
                VALUES (?, ?)
            ''', (session['user_id'], content))
            conn.commit()
            flash('شكراً لملاحظاتك!', 'success')
        except sqlite3.Error as e:
            flash(f'حدث خطأ: {e}', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('feedback'))
    
    return render_template('feedback.html', pagetitle="تقديم ملاحظات")


#---------------------------------------------------------------------------------------------------------------------


@app.route('/Showfeedbacks')
@login_required
def show_feedbacks():
    selected_month = request.args.get('month')  # يستقبل قيمة الشهر من رابط الصفحة، مثلا ?month=7

    conn = get_db_connection()  # اتصال بقاعدة البيانات
    cursor = conn.cursor()

    if selected_month and selected_month.isdigit():
        month_str = selected_month.zfill(2)  # يحول 7 إلى '07' لأن strftime('%m') يعيد رقم الشهر 2 خانات
        query = """
        SELECT Feedback.content, Feedback.feedback_date, User.name
        FROM Feedback
        JOIN User ON Feedback.user_id = User.id
        WHERE strftime('%m', Feedback.feedback_date) = ?
        ORDER BY Feedback.feedback_date DESC
        """
        cursor.execute(query, (month_str,))
    else:
        query = """
        SELECT Feedback.content, Feedback.feedback_date, User.name
        FROM Feedback
        JOIN User ON Feedback.user_id = User.id
        ORDER BY Feedback.feedback_date DESC
        """
        cursor.execute(query)

    feedbacks = cursor.fetchall()
    conn.commit()
    conn.close()

    return render_template('showfeedback.html', pagetitle="الملاحظات", feedbacks=feedbacks, selected_month=selected_month)



#---------------------------------------------------------------------------------------------------------------------




@app.route('/checkout')
@login_required
def show_checkout():
    confirmed_order = session.get('confirmed_order')
    if not confirmed_order:
        return "عذرًا، لا يوجد طلب مؤكد. يرجى العودة للقائمة وتأكيد الطلب أولاً."

    conn = get_db_connection()
    total = 0
    detailed_cart = []

    for cart_item in confirmed_order:
        item = conn.execute('SELECT * FROM MenuItem WHERE id = ?', (cart_item['id'],)).fetchone()
        if item:
            base_price = item['price'] or 0

            custom_price_extra = 0.0
            for ing_type, chosen_option in cart_item.get('custom_options', {}).items():
                row = conn.execute('''
                    SELECT co.extra_price FROM customizable_options co
                    JOIN customizable_ingredients ci ON co.customizable_ingredient_id = ci.id
                    WHERE ci.name = ? AND co.name = ?
                ''', (ing_type, chosen_option)).fetchone()
                if row:
                    custom_price_extra += row['extra_price'] or 0

            unit_final_price = base_price + custom_price_extra
            item_total = unit_final_price * cart_item['quantity']
            total += item_total

            detailed_cart.append({
                'name': item['name'],
                'price': base_price,
                'quantity': cart_item['quantity'],
                'fixed_ingredients': cart_item.get('fixed_ingredients', []),
                'custom_options': cart_item.get('custom_options', {}),
                'custom_price_extra': custom_price_extra,
                'item_total': item_total,
                'image': item['image'],
            })

    conn.close()

    order_number = random.randint(1000, 9999)
    estimated_time =  "30 دقيقة تقريباً"

    
    session.pop('confirmed_order', None)
    session.modified = True

    return render_template('checkout.html', cart_items=detailed_cart, total=total, order_number=order_number, estimated_time=estimated_time)


#---------------------------------------------------------------------------------------------------------------------

@app.route('/menu')
@login_required
def show_menu():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM category').fetchall()
    menu_data = {}
    for cat in categories:
        items = conn.execute('SELECT * FROM MenuItem WHERE category_id = ?', (cat['id'],)).fetchall()
        menu_data[cat['name']] = [dict(item) for item in items]
    conn.close()
    return render_template('menu.html', menu_data=menu_data)


#---------------------------------------------------------------------------------------------------------------------
@app.route('/customize/<int:item_id>', methods=['GET', 'POST'])
@login_required
def customize_item(item_id):
    conn = get_db_connection()
    item = conn.execute('''
        SELECT i.*, c.name as category FROM MenuItem i
        JOIN category c ON i.category_id = c.id
        WHERE i.id = ?
    ''', (item_id,)).fetchone()
    if not item:
        conn.close()
        return "العنصر غير موجود", 404

    item = dict(item)

    fixed_ings = conn.execute('''
        SELECT fi.id, fi.name FROM fixed_ingredients fi
        JOIN item_fixed_ingredients ifi ON fi.id = ifi.fixed_ingredient_id
        WHERE ifi.item_id = ?
    ''', (item_id,)).fetchall()
    fixed_ings = [dict(f) for f in fixed_ings]

    customizable_opts = conn.execute('''
        SELECT co.id, co.name, ci.name as ingredient_type, co.extra_price FROM customizable_options co
        JOIN customizable_ingredients ci ON co.customizable_ingredient_id = ci.id
        JOIN item_customizable_options ico ON co.id = ico.customizable_option_id
        WHERE ico.item_id = ?
        ORDER BY ci.name
    ''', (item_id,)).fetchall()
    customizable_opts = [dict(c) for c in customizable_opts]

    customization_options = {}
    for opt in customizable_opts:
        ing_type = opt['ingredient_type'].strip()  # يحذف المساحات والسطر الجديد
        customization_options.setdefault(ing_type, []).append({
            'id': opt['id'],
            'name': opt['name'],
            'extra_price': opt['extra_price'] or 0
        })


    # ------------------- هنا صار برا اللوب -------------------
    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 1))
        cursor = conn.cursor()

        order_id = session.get('order_id')
        if not order_id:
            cursor.execute('INSERT INTO orders (user_id) VALUES (?)', (session['user_id'],))

            order_id = cursor.lastrowid
            session['order_id'] = order_id

        for i in range(quantity):
            selected_fixed = []
            for f in fixed_ings:
                if request.form.get(f'fixed_{f["id"]}_{i}') == 'on':
                    selected_fixed.append(f['name'])

            selected_custom = []
            extra_price = 0.0
            for ing_type, options in customization_options.items():
                selected_option_id = request.form.get(f'custom_{ing_type}_{i}')
                if selected_option_id:
                    selected_option = next((o for o in options if str(o['id']) == selected_option_id), None)
                    if selected_option:
                        selected_custom.append({'ingredient_name': ing_type, 'option_name': selected_option['name']})
                        extra_price += float(selected_option.get('extra_price') or 0)

            notes = request.form.get(f'notes_{i}', '')
            details_json = json.dumps({
                'fixed_ingredients': selected_fixed,
                'custom_options': selected_custom,
                'notes': notes
            }, ensure_ascii=False)

            base_price = item['price'] or 0
            cursor.execute('''
                INSERT INTO order_details (order_id, item_id, base_price, extra_price, details_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, item_id, base_price, extra_price, details_json))

        conn.commit()
        conn.close()
        return redirect(url_for('view_cart'))

    conn.close()
    print(customization_options)
    return render_template('customize.html',
                           item=item,
                           fixed_ingredients=fixed_ings,
                           customization_options=customization_options)




#---------------------------------------------------------------------------------------------------------------------

@app.route('/cart')
@login_required
def view_cart():
    conn = get_db_connection()
    cart_items = []
    total = 0.0
    rows = conn.execute('''
        SELECT od.id as order_detail_id, i.name as item_name, od.base_price, od.extra_price, od.details_json
        FROM order_details od
        JOIN MenuItem i ON od.item_id = i.id
        ORDER BY od.id DESC
    ''').fetchall()

    for row in rows:
        row = dict(row)
        details = json.loads(row['details_json']) if row['details_json'] else {}
        fixed_ingredients = details.get('fixed_ingredients', [])
        custom_options = details.get('custom_options', [])
        notes = details.get('notes', '')
        total_price = row['base_price'] + row['extra_price']
        total += total_price

        cart_items.append({
            'order_detail_id': row['order_detail_id'],
            'item_name': row['item_name'],
            'base_price': row['base_price'],
            'extra_price': row['extra_price'],
            'fixed_ingredients': fixed_ingredients,
            'custom_options': custom_options,
            'notes': notes,
            'total_price': total_price,
            'quantity': 1  # لأننا أدخلنا كل وحدة كصف مستقل
        })
    conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total)


#---------------------------------------------------------------------------------------------------------------------

@app.route('/cart/delete/<int:order_detail_id>', methods=['POST'])
@login_required
def delete_cart_item(order_detail_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM order_details WHERE id = ?', (order_detail_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_cart'))


#---------------------------------------------------------------------------------------------------------------------

@app.route('/confirm', methods=['GET', 'POST'])
@login_required
def confirm_order():
   # conn = get_db_connection()
   # conn.execute('DELETE FROM order_details')
   # conn.commit()
   # conn.close()
    return render_template('order_confirmed.html')


#---------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run()

