
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, TextAreaField, DateField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange
import csv, io, os, datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from sqlalchemy import or_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///inventory.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-secret-key')
# --- CONFIGURAZIONE DA AGGIUNGERE PER SCALINGO ---

import os

# Secret key (se non esiste già)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me')

# Database URL da variabile ambiente (Scalingo)
db_url = os.getenv('DATABASE_URL', 'sqlite:////tmp/inventory.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Creazione delle tabelle al primo avvio
from app import db  # se questa riga dà errore, la sposto io
with app.app_context():
    db.create_all()

# Health check (per confermare che l'app è avviata)
@app.route('/health')
def health():
    return 'ok', 200


db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Models ---
class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    vat_number = db.Column(db.String(64))        # P.IVA
    tax_code = db.Column(db.String(64))          # CF
    email = db.Column(db.String(200))
    phone = db.Column(db.String(64))
    address = db.Column(db.String(300))
    notes = db.Column(db.Text)
    products = db.relationship('Product', back_populates='supplier_ref')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), unique=True, nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', back_populates='category_ref')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    unit = db.Column(db.String(32), default='pezzi')
    vat = db.Column(db.Integer, default=10)  # % IVA
    cost = db.Column(db.Float, default=0.0)
    price = db.Column(db.Float, default=0.0)
    stock_qty = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)

    prices = db.relationship('PriceListItem', back_populates='product', cascade="all, delete-orphan")
    lots = db.relationship('Lot', back_populates='product', cascade="all, delete-orphan")
    supplier_ref = db.relationship('Supplier', back_populates='products')
    category_ref = db.relationship('Category', back_populates='products')

class PriceList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    channel = db.Column(db.String(32), default='Generale')  # Generale/B2B/B2C/Ho.Re.Ca.
    currency = db.Column(db.String(8), default='EUR')
    notes = db.Column(db.Text)

    items = db.relationship('PriceListItem', back_populates='price_list', cascade="all, delete-orphan")

class PriceListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price_list_id = db.Column(db.Integer, db.ForeignKey('price_list.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)

    price_list = db.relationship('PriceList', back_populates='items')
    product = db.relationship('Product', back_populates='prices')

class Lot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    lot_code = db.Column(db.String(120), nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    qty = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)

    product = db.relationship('Product', back_populates='lots')

# --- Forms ---
class SupplierForm(FlaskForm):
    name = StringField('Ragione sociale', validators=[DataRequired()])
    vat_number = StringField('P.IVA', validators=[Optional()])
    tax_code = StringField('C.F.', validators=[Optional()])
    email = StringField('Email', validators=[Optional()])
    phone = StringField('Telefono', validators=[Optional()])
    address = StringField('Indirizzo', validators=[Optional()])
    notes = TextAreaField('Note', validators=[Optional()])

class CategoryForm(FlaskForm):
    name = StringField('Nome categoria', validators=[DataRequired()])
    description = TextAreaField('Descrizione', validators=[Optional()])

class ProductForm(FlaskForm):
    sku = StringField('SKU', validators=[DataRequired()])
    name = StringField('Nome', validators=[DataRequired()])
    category_id = SelectField('Categoria', coerce=int, validators=[Optional()])
    supplier_id = SelectField('Fornitore', coerce=int, validators=[Optional()])
    unit = StringField('Unità', validators=[Optional()])
    vat = IntegerField('IVA %', validators=[Optional(), NumberRange(min=0, max=100)])
    cost = DecimalField('Costo', places=2, rounding=None, validators=[Optional()])
    price = DecimalField('Prezzo', places=2, rounding=None, validators=[Optional()])
    stock_qty = IntegerField('Giacenza', validators=[Optional()])
    min_stock = IntegerField('Scorta minima', validators=[Optional()])
    notes = TextAreaField('Note', validators=[Optional()])

class PriceListForm(FlaskForm):
    name = StringField('Nome listino', validators=[DataRequired()])
    channel = SelectField('Canale', choices=[('Generale','Generale'), ('B2B','B2B'), ('B2C','B2C'), ('Ho.Re.Ca.','Ho.Re.Ca.')])
    currency = StringField('Valuta', validators=[Optional()])
    notes = TextAreaField('Note', validators=[Optional()])

class LotForm(FlaskForm):
    lot_code = StringField('Lotto', validators=[DataRequired()])
    expiry_date = DateField('Scadenza', validators=[Optional()], format='%Y-%m-%d')
    qty = IntegerField('Quantità', validators=[Optional()])
    notes = TextAreaField('Note', validators=[Optional()])

# --- Utils ---

def ensure_admin_from_env():
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_password = os.getenv('ADMIN_PASSWORD')
    if admin_email and admin_password:
        u = User.query.filter_by(email=admin_email).first()
        if not u:
            u = User(email=admin_email, password_hash=generate_password_hash(admin_password))
            db.session.add(u)
            db.session.commit()

def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

# --- Routes ---

# --- Auth ---
@app.route('/login', methods=['GET','POST'])
\1
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Accesso eseguito', 'success')
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        flash('Credenziali non valide', 'warning')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Disconnesso', 'info')
    return redirect(url_for('login'))

\1@login_required
\2
    low_stock = Product.query.filter(Product.stock_qty <= Product.min_stock, Product.min_stock > 0).count()
    today = datetime.date.today()
    soon = today + datetime.timedelta(days=30)
    expiring = Lot.query.filter(Lot.expiry_date != None, Lot.expiry_date <= soon).count()
    product_count = Product.query.count()
    price_list_count = PriceList.query.count()
    return render_template('index.html',
        product_count=product_count,
        price_list_count=price_list_count,
        low_stock=low_stock,
        expiring=expiring
    )

# --- Suppliers ---
\1@login_required
\2
    q = request.args.get('q','').strip()
    query = Supplier.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Supplier.name.ilike(like), Supplier.email.ilike(like), Supplier.phone.ilike(like)))
    rows = query.order_by(Supplier.name.asc()).all()
    return render_template('suppliers.html', rows=rows, q=q)

\1@login_required
\2
    form = SupplierForm()
    if form.validate_on_submit():
        s = Supplier(**form.data)
        db.session.add(s)
        db.session.commit()
        flash('Fornitore creato', 'success')
        return redirect(url_for('suppliers'))
    return render_template('supplier_form.html', form=form, action='Nuovo')

\1@login_required
\2
    s = Supplier.query.get_or_404(sid)
    form = SupplierForm(obj=s)
    if form.validate_on_submit():
        form.populate_obj(s)
        db.session.commit()
        flash('Fornitore aggiornato', 'success')
        return redirect(url_for('suppliers'))
    return render_template('supplier_form.html', form=form, action='Modifica')

\1@login_required
\2
    s = Supplier.query.get_or_404(sid)
    if s.products:
        flash('Impossibile eliminare: ci sono prodotti collegati.', 'warning')
        return redirect(url_for('suppliers'))
    db.session.delete(s)
    db.session.commit()
    flash('Fornitore eliminato', 'info')
    return redirect(url_for('suppliers'))

# --- Categories ---
\1@login_required
\2
    rows = Category.query.order_by(Category.name.asc()).all()
    return render_template('categories.html', rows=rows)

\1@login_required
\2
    form = CategoryForm()
    if form.validate_on_submit():
        c = Category(**form.data)
        db.session.add(c)
        db.session.commit()
        flash('Categoria creata', 'success')
        return redirect(url_for('categories'))
    return render_template('category_form.html', form=form, action='Nuova')

\1@login_required
\2
    c = Category.query.get_or_404(cid)
    form = CategoryForm(obj=c)
    if form.validate_on_submit():
        form.populate_obj(c)
        db.session.commit()
        flash('Categoria aggiornata', 'success')
        return redirect(url_for('categories'))
    return render_template('category_form.html', form=form, action='Modifica')

\1@login_required
\2
    c = Category.query.get_or_404(cid)
    if c.products:
        flash('Impossibile eliminare: ci sono prodotti collegati.', 'warning')
        return redirect(url_for('categories'))
    db.session.delete(c)
    db.session.commit()
    flash('Categoria eliminata', 'info')
    return redirect(url_for('categories'))

# --- Products ---
def load_choices(form):
    form.category_id.choices = [(-1, '— Nessuna —')] + [(c.id, c.name) for c in Category.query.order_by(Category.name.asc()).all()]
    form.supplier_id.choices = [(-1, '— Nessuno —')] + [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name.asc()).all()]

\1@login_required
\2
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    query = Product.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.ilike(like), Product.sku.ilike(like)))
    if category:
        query = query.join(Category, isouter=True).filter(Category.name == category)
    items = query.order_by(Product.name.asc()).all()
    categories = db.session.query(Category.name).order_by(Category.name.asc()).all()
    categories = [c[0] for c in categories]
    return render_template('products.html', items=items, q=q, category=category, categories=categories)

\1@login_required
\2
    form = ProductForm()
    load_choices(form)
    if form.validate_on_submit():
        data = form.data.copy()
        if data['category_id'] == -1: data['category_id'] = None
        if data['supplier_id'] == -1: data['supplier_id'] = None
        p = Product(**data)
        db.session.add(p)
        db.session.commit()
        flash('Prodotto creato', 'success')
        return redirect(url_for('products'))
    return render_template('product_form.html', form=form, action='Nuovo')

\1@login_required
\2
    p = Product.query.get_or_404(pid)
    form = ProductForm(obj=p)
    load_choices(form)
    if form.validate_on_submit():
        data = form.data.copy()
        form.populate_obj(p)
        if data['category_id'] == -1: p.category_id = None
        if data['supplier_id'] == -1: p.supplier_id = None
        db.session.commit()
        flash('Prodotto aggiornato', 'success')
        return redirect(url_for('products'))
    return render_template('product_form.html', form=form, action='Modifica')

\1@login_required
\2
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash('Prodotto eliminato', 'info')
    return redirect(url_for('products'))

# --- Lots ---
\1@login_required
\2
    p = Product.query.get_or_404(pid)
    return render_template('product_lots.html', p=p)

\1@login_required
\2
    p = Product.query.get_or_404(pid)
    form = LotForm()
    if form.validate_on_submit():
        lot = Lot(product_id=p.id,
                  lot_code=form.lot_code.data,
                  expiry_date=form.expiry_date.data,
                  qty=form.qty.data or 0,
                  notes=form.notes.data)
        db.session.add(lot)
        p.stock_qty = (p.stock_qty or 0) + (lot.qty or 0)
        db.session.commit()
        flash('Lotto aggiunto', 'success')
    else:
        flash('Compila correttamente i dati lotto', 'warning')
    return redirect(url_for('product_lots', pid=p.id))

\1@login_required
\2
    p = Product.query.get_or_404(pid)
    lot = Lot.query.get_or_404(lid)
    qty = lot.qty or 0
    db.session.delete(lot)
    p.stock_qty = max(0, (p.stock_qty or 0) - qty)
    db.session.commit()
    flash('Lotto eliminato', 'info')
    return redirect(url_for('product_lots', pid=p.id))

# --- Import/Export Products ---
\1@login_required
\2
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['sku','name','category','supplier','unit','vat','cost','price','stock_qty','min_stock','notes'])
    for p in Product.query.order_by(Product.name.asc()).all():
        cw.writerow([
            p.sku,p.name,
            (p.category_ref.name if p.category_ref else ''),
            (p.supplier_ref.name if p.supplier_ref else ''),
            p.unit or '',p.vat or 0,p.cost or 0,p.price or 0,p.stock_qty or 0,p.min_stock or 0,(p.notes or '').replace('\n',' ')[:500]
        ])
    output = io.BytesIO(si.getvalue().encode('utf-8-sig'))
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='products_export.csv')

\1@login_required
\2
    file = request.files.get('file')
    if not file:
        flash('Nessun file selezionato', 'warning')
        return redirect(url_for('products'))
    stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
    reader = csv.DictReader(stream)
    count = 0
    for row in reader:
        sku = row.get('sku')
        if not sku: 
            continue
        p = Product.query.filter_by(sku=sku).first()
        if not p:
            p = Product(sku=sku, name=row.get('name',''))
            db.session.add(p)
        p.name = row.get('name','')
        # match/create category & supplier by name if provided
        cat_name = (row.get('category') or '').strip()
        sup_name = (row.get('supplier') or '').strip()
        if cat_name:
            c = Category.query.filter_by(name=cat_name).first()
            if not c:
                c = Category(name=cat_name)
                db.session.add(c)
                db.session.flush()
            p.category_id = c.id
        if sup_name:
            s = Supplier.query.filter_by(name=sup_name).first()
            if not s:
                s = Supplier(name=sup_name)
                db.session.add(s)
                db.session.flush()
            p.supplier_id = s.id

        p.unit = row.get('unit') or 'pezzi'
        try: p.vat = int(row.get('vat') or 0)
        except: p.vat = 0
        try: p.cost = float(row.get('cost') or 0)
        except: p.cost = 0
        try: p.price = float(row.get('price') or 0)
        except: p.price = 0
        try: p.stock_qty = int(row.get('stock_qty') or 0)
        except: p.stock_qty = 0
        try: p.min_stock = int(row.get('min_stock') or 0)
        except: p.min_stock = 0
        p.notes = row.get('notes') or None
        count += 1
    db.session.commit()
    flash(f'Import completato: {count} righe', 'success')
    return redirect(url_for('products'))

# --- Price Lists / PDF + Channel ---
\1@login_required
\2
    channel = request.args.get('channel','').strip()
    query = PriceList.query
    if channel:
        query = query.filter(PriceList.channel == channel)
    lists = query.order_by(PriceList.name.asc()).all()
    channels = ['Generale','B2B','B2C','Ho.Re.Ca.']
    return render_template('pricelists.html', lists=lists, channels=channels, channel=channel)

\1@login_required
\2
    form = PriceListForm()
    if form.validate_on_submit():
        pl = PriceList(**form.data)
        db.session.add(pl)
        db.session.commit()
        flash('Listino creato', 'success')
        return redirect(url_for('pricelists'))
    return render_template('pricelist_form.html', form=form, action='Nuovo')

\1@login_required
\2
    pl = PriceList.query.get_or_404(lid)
    form = PriceListForm(obj=pl)
    if form.validate_on_submit():
        form.populate_obj(pl)
        db.session.commit()
        flash('Listino aggiornato', 'success')
        return redirect(url_for('pricelists'))
    return render_template('pricelist_form.html', form=form, action='Modifica')

\1@login_required
\2
    pl = PriceList.query.get_or_404(lid)
    db.session.delete(pl)
    db.session.commit()
    flash('Listino eliminato', 'info')
    return redirect(url_for('pricelists'))

\1@login_required
\2
    pl = PriceList.query.get_or_404(lid)
    products = Product.query.order_by(Product.name.asc()).all()
    existing = {item.product_id: item for item in pl.items}
    return render_template('pricelist_detail.html', pl=pl, products=products, existing=existing)

\1@login_required
\2
    pl = PriceList.query.get_or_404(lid)
    product_id = int(request.form.get('product_id'))
    price_value = request.form.get('price')
    if price_value is None or price_value == '':
        item = PriceListItem.query.filter_by(price_list_id=pl.id, product_id=product_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            flash('Prezzo rimosso', 'info')
        return redirect(url_for('pricelist_detail', lid=lid))
    price = float(price_value or 0)
    item = PriceListItem.query.filter_by(price_list_id=pl.id, product_id=product_id).first()
    if not item:
        item = PriceListItem(price_list_id=pl.id, product_id=product_id, price=price)
        db.session.add(item)
    else:
        item.price = price
    db.session.commit()
    flash('Prezzo aggiornato', 'success')
    return redirect(url_for('pricelist_detail', lid=lid))

\1@login_required
\2
    pl = PriceList.query.get_or_404(lid)
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['listino', 'canale', 'sku', 'prodotto', 'prezzo', 'valuta'])
    for item in pl.items:
        cw.writerow([pl.name, pl.channel, item.product.sku, item.product.name, item.price, pl.currency])
    output = io.BytesIO(si.getvalue().encode('utf-8-sig'))
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=f'{pl.name}_export.csv')

\1@login_required
\2
    pl = PriceList.query.get_or_404(lid)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    title = f"Listino: {pl.name} • {pl.channel} ({pl.currency})"
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*cm, height-2*cm, title)
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, height-2.7*cm, f"Generato: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")

    y = height - 3.5*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, "SKU")
    c.drawString(6*cm, y, "Prodotto")
    c.drawRightString(width-4*cm, y, "Prezzo")
    y -= 0.5*cm
    c.setFont("Helvetica", 10)

    items = sorted(pl.items, key=lambda it: (it.product.name or "").lower())
    for item in items:
        line_height = 0.6*cm
        if y < 3*cm:
            c.showPage()
            y = height - 2*cm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2*cm, y, "SKU")
            c.drawString(6*cm, y, "Prodotto")
            c.drawRightString(width-4*cm, y, "Prezzo")
            y -= 0.5*cm
            c.setFont("Helvetica", 10)
        c.drawString(2*cm, y, item.product.sku or "")
        c.drawString(6*cm, y, item.product.name or "")
        c.drawRightString(width-4*cm, y, f"{item.price:.2f} {pl.currency}")
        y -= line_height

    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{pl.name}.pdf", mimetype="application/pdf")

# --- Reports: Expiring Lots ---
\1@login_required
\2
    # params: days (default 30), category(optional), supplier(optional)
    try:
        days = int(request.args.get('days','30'))
    except:
        days = 30
    category = request.args.get('category','').strip()
    supplier = request.args.get('supplier','').strip()

    today = datetime.date.today()
    until = today + datetime.timedelta(days=days)

    query = Lot.query.join(Product)
    query = query.filter(Lot.expiry_date != None, Lot.expiry_date <= until)
    if category:
        query = query.join(Category, Product.category_id == Category.id).filter(Category.name == category)
    if supplier:
        query = query.join(Supplier, Product.supplier_id == Supplier.id).filter(Supplier.name == supplier)

    lots = query.order_by(Lot.expiry_date.asc()).all()

    categories = [c[0] for c in db.session.query(Category.name).order_by(Category.name.asc()).all()]
    suppliers = [s[0] for s in db.session.query(Supplier.name).order_by(Supplier.name.asc()).all()]

    return render_template('report_expiring.html', lots=lots, days=days, category=category, supplier=supplier, categories=categories, suppliers=suppliers)

\1@login_required
\2
    days = int(request.args.get('days','30'))
    category = request.args.get('category','').strip()
    supplier = request.args.get('supplier','').strip()

    today = datetime.date.today()
    until = today + datetime.timedelta(days=days)

    query = Lot.query.join(Product)
    query = query.filter(Lot.expiry_date != None, Lot.expiry_date <= until)
    if category:
        query = query.join(Category, Product.category_id == Category.id).filter(Category.name == category)
    if supplier:
        query = query.join(Supplier, Product.supplier_id == Supplier.id).filter(Supplier.name == supplier)

    lots = query.order_by(Lot.expiry_date.asc()).all()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['scadenza','sku','prodotto','lotto','quantita','categoria','fornitore'])
    for l in lots:
        cw.writerow([
            l.expiry_date.strftime('%Y-%m-%d') if l.expiry_date else '',
            l.product.sku, l.product.name, l.lot_code, l.qty,
            (l.product.category_ref.name if l.product.category_ref else ''),
            (l.product.supplier_ref.name if l.product.supplier_ref else '')
        ])
    output = io.BytesIO(si.getvalue().encode('utf-8-sig'))
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=f'expiring_{days}d.csv')

\1@login_required
\2
    days = int(request.args.get('days','30'))
    category = request.args.get('category','').strip()
    supplier = request.args.get('supplier','').strip()

    today = datetime.date.today()
    until = today + datetime.timedelta(days=days)

    query = Lot.query.join(Product)
    query = query.filter(Lot.expiry_date != None, Lot.expiry_date <= until)
    if category:
        query = query.join(Category, Product.category_id == Category.id).filter(Category.name == category)
    if supplier:
        query = query.join(Supplier, Product.supplier_id == Supplier.id).filter(Supplier.name == supplier)

    lots = query.order_by(Lot.expiry_date.asc()).all()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    title = f"Report Scadenze (entro {days} giorni)"
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*cm, height-2*cm, title)
    c.setFont("Helvetica", 10)
    filters = []
    if category: filters.append(f"Categoria: {category}")
    if supplier: filters.append(f"Fornitore: {supplier}")
    c.drawString(2*cm, height-2.7*cm, " • ".join(filters))
    c.drawString(2*cm, height-3.2*cm, f"Generato: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")

    y = height - 4.2*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, "Scadenza")
    c.drawString(5*cm, y, "Prodotto (SKU)")
    c.drawString(11*cm, y, "Lotto")
    c.drawRightString(width-2*cm, y, "Q.tà")
    y -= 0.5*cm
    c.setFont("Helvetica", 10)

    for l in lots:
        line_h = 0.6*cm
        if y < 3*cm:
            c.showPage()
            y = height - 2*cm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2*cm, y, "Scadenza")
            c.drawString(5*cm, y, "Prodotto (SKU)")
            c.drawString(11*cm, y, "Lotto")
            c.drawRightString(width-2*cm, y, "Q.tà")
            y -= 0.5*cm
            c.setFont("Helvetica", 10)

        scad = l.expiry_date.strftime('%d/%m/%Y') if l.expiry_date else '—'
        c.drawString(2*cm, y, scad)
        prod = f"{l.product.name} ({l.product.sku})"
        c.drawString(5*cm, y, prod[:40])
        c.drawString(11*cm, y, (l.lot_code or '')[:12])
        c.drawRightString(width-2*cm, y, str(l.qty or 0))
        y -= line_h

    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"report_scadenze_{days}d.pdf", mimetype="application/pdf")

# Init DB
@app.cli.command('init-db')
def init_db():
    db.create_all()
    ensure_admin_from_env()
    if not PriceList.query.filter_by(name='Listino Base').first():
        db.session.add(PriceList(name='Listino Base', channel='Generale', currency='EUR', notes='Listino di default'))
        db.session.commit()
    print('Database inizializzato.')

# --- Filters ---
@app.template_filter('fmtmoney')
def fmtmoney(value):
    try:
        return f"{float(value):.2f}"
    except:
        return "0.00"
