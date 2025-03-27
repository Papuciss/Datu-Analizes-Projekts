from flask import Flask, render_template, request
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Nepieciešams, lai Matplotlib darbotos servera vidē
import matplotlib.pyplot as plt
from peewee import *
from playhouse.shortcuts import model_to_dict
import os

app = Flask(__name__)

# Datubāzes konfigurācija
db = SqliteDatabase('personas.db')

class Personas(Model):
    nosaukums = CharField()
    vecums = IntegerField()
    punkti = IntegerField()

    class Meta:
        database = db

# Izveidojam datubāzi, ja tā vēl neeksistē
if not os.path.exists('personas.db'):
    db.connect()
    db.create_tables([Personas])
    db.close()

# Galvenā lapa
@app.route('/')
def index():
    return render_template('index.html')

# Par projektu lapa
@app.route('/par')
def par_lapa():
    return render_template('par.html')

# Datu ielādes lapa
@app.route('/upload', methods=['GET', 'POST'])
def upload_lapa():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            try:
                if not os.path.exists('static'):
                    os.makedirs('static')
                file.save('static/temp_data.csv')
                df = pd.read_csv('static/temp_data.csv')
                required_columns = ['nosaukums', 'vecums', 'punkti']
                if not all(col in df.columns for col in required_columns):
                    return render_template('error.html', error="CSV failā trūkst nepieciešamās kolonnas: nosaukums, vecums, punkti.")
                db.connect()
                db.drop_tables([Personas])
                db.create_tables([Personas])
                for _, row in df.iterrows():
                    Personas.create(nosaukums=row['nosaukums'], vecums=row['vecums'], punkti=row['punkti'])
                db.close()
            except Exception as e:
                return render_template('error.html', error=f"Kļūda datu ielādē: {str(e)}")
        min_vecums = request.form.get('min_vecums', type=int)
        min_punkti = request.form.get('min_punkti', type=int)
        filtered_df = df
        if min_vecums:
            filtered_df = filtered_df[filtered_df['vecums'] >= min_vecums]
        if min_punkti:
            filtered_df = filtered_df[filtered_df['punkti'] >= min_punkti]
        return render_template('upload.html', data=filtered_df.to_dict('records'))
    return render_template('upload.html', data=None)

# Vizualizācijas lapa ar filtriem
@app.route('/visualize', methods=['GET', 'POST'])
def visualize_lapa():
    try:
        # Ielādējam datus
        df = pd.read_csv('static/temp_data.csv')

        # Pārbaudām, vai ir POST pieprasījums ar filtriem
        if request.method == 'POST':
            min_vecums = request.form.get('min_vecums', type=int)
            min_punkti = request.form.get('min_punkti', type=int)
            filtered_df = df
            if min_vecums:
                filtered_df = filtered_df[filtered_df['vecums'] >= min_vecums]
            if min_punkti:
                filtered_df = filtered_df[filtered_df['punkti'] >= min_punkti]
        else:
            filtered_df = df  # Bez filtriem, ja GET pieprasījums

        # Pārbaudām, vai pēc filtrēšanas ir dati
        if filtered_df.empty:
            return render_template('visualize.html', error="Pēc filtrēšanas nav datu. Lūdzu, maini filtrus vai ielādē citus datus.")

        # Histogramma
        plt.figure(figsize=(8, 6))
        plt.hist(filtered_df['punkti'], bins=5, color='blue', edgecolor='black')
        plt.title('Punktu sadalījums')
        plt.xlabel('Punkti')
        plt.ylabel('Skaits')
        plt.savefig('static/histogram.png')
        plt.close()

        # Stabiņu diagramma
        vecuma_grupas = filtered_df.groupby('vecums')['punkti'].mean()
        plt.figure(figsize=(8, 6))
        vecuma_grupas.plot(kind='bar', color='green')
        plt.title('Vidējie punkti pa vecuma grupām')
        plt.xlabel('Vecums')
        plt.ylabel('Vidējie punkti')
        plt.savefig('static/bar_chart.png')
        plt.close()

        # Pīrāga diagramma
        vecuma_sadalijums = filtered_df['vecums'].value_counts()
        plt.figure(figsize=(8, 6))
        plt.pie(vecuma_sadalijums, labels=vecuma_sadalijums.index, autopct='%1.1f%%', startangle=140)
        plt.title('Vecuma grupu proporcijas')
        plt.savefig('static/pie_chart.png')
        plt.close()

        return render_template('visualize.html', histogram='histogram.png', bar_chart='bar_chart.png', pie_chart='pie_chart.png', error=None)
    except FileNotFoundError:
        return render_template('error.html', error="Vispirms augšupielādē datus.")
    except Exception as e:
        return render_template('error.html', error=f"Kļūda vizualizāciju ģenerēšanā: {str(e)}")

# Vaicājumu lapa
@app.route('/queries')
def queries_lapa():
    try:
        db.connect()
        if Personas.select().count() == 0:
            db.close()
            return render_template('queries.html', augsti_punkti=None, videjais_vecums=None, error="Datubāze ir tukša. Lūdzu, ielādē datus.")
        
        augsti_punkti = Personas.select().where(Personas.punkti > 70)
        videjais_vecums = Personas.select(fn.AVG(Personas.vecums).alias('avg_vecums')).scalar()
        db.close()
        return render_template('queries.html', augsti_punkti=augsti_punkti, videjais_vecums=videjais_vecums, error=None)
    except Exception as e:
        db.close()
        return render_template('error.html', error=f"Kļūda vaicājumu izpildē: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)