import re
import requests
from bs4 import BeautifulSoup
import lxml.html
import pandas as pd
from flask import Flask, render_template, request
import sqlite3
import csv
import os
from sklearn.ensemble import RandomForestRegressor

BASE_URL = 'http://www.kyobobook.co.kr/bestSellerNew/bestseller.laf'

def book_genre(genre):
  if genre == "소설" :
    code = "B"
  elif genre == "에세이" :
    code = "C"
  elif genre == "인문" : 
    code = "I"
  elif genre == "정치사회" :
    code = "J"
  elif genre == "예술" :
    code = "Q"
  else : code = "A" # 그 외에는 종합에서 추천

  url=f"{BASE_URL}?mallGb=KOR&linkClass={code}&range=1&kind=0&orderClick=DAb"
  page = requests.get(url)
  soup = BeautifulSoup(page.content,'html.parser')
  root = lxml.html.fromstring(page.content)

  title = root.cssselect('div.title >a > strong') 
  price = root.cssselect('div.price > strong.book_price')
  author = root.cssselect('div.detail > div.author')
  review = root.cssselect('div.review > a')
  star = soup.find_all(class_='review')
  cover = soup.find_all(class_='cover')

  titles=[]
  prices=[]
  authors=[]
  reviews=[]
  stars=[]
  covers = []

  for i in range(len(title)):
    titles.append(title[i].text.strip())
    prices.append(price[i].text.strip())
    authors.append(author[i].text.strip())
    reviews.append(review[i].text.strip().split('개')[0].split('(')[1])

  for i in range(len(star)):
    stars.append(star[i].img['src'])

  for i in range(1,len(cover)):
    covers.append(cover[i].img['src'])

  df = pd.DataFrame({"title":titles,
                     "price":prices,
                     "author":authors,
                     "review":reviews,
                     "genre":genre,
                     "star":stars,
                     "cover":covers})
  return df

a = book_genre('종합')
nov = book_genre('소설')
ess = book_genre('에세이')
human = book_genre('인문')
poli = book_genre('정치사회')
art = book_genre('예술')

df = pd.concat([a,nov,ess,human,poli,art])

def trans(df):
  df.reset_index(drop=True,inplace=True)
  df['id'] = df.index + 1
  df['review'] = df['review'].astype(int)
  df['price']=df['price'].str.replace(',','').str.replace('원','').astype(int)
  return df

trans(df)
#df = df.values.tolist()
df.to_csv("./books.csv",header=True,index=False,encoding='utf-8')

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result.html', methods=['GET','POST'])
def result():
    global df
    if request.method=='GET':
        g = request.args.get('genre')

        conn = sqlite3.connect('BOOK_LIST.db')
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS book")
        cur.execute('CREATE TABLE book(title VARCHAR(100), price INTEGER, author VARCHAR(50), review INTEGER, genre VARCHAR(50), star VARCHAR(1000),cover VARCHAR(1000), bookid INTEGER)')
        
        with open("books.csv", "r",encoding="utf-8") as file:
          reader = csv.DictReader(file)
          for n, r in enumerate(reader):
            t = tuple(r.values())
            cur.execute('INSERT INTO book (title, price, author, review, genre, star, cover, bookid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', t)

        cm = f"""
                    SELECT title, author, price, review, star, cover, bookid
                    FROM book
                    WHERE genre = '{g}'
                    """
        df = pd.read_sql_query(cm, conn)
        #rows = cur.fetchall()
        conn.commit()
        cur.close()
        conn.close()

        # model = RandomForestRegressor()

        # target = 'bookid'
        # features = ['price','review']

        # X_test = df[features]
        # y_test = df[target]
        # row = X_test.sample()
        # model = model.fit(X_test, y_test)
        # re=model.predict(row)
        # number=round(re[0])
        # df = df[df['bookid'] == number]
        row = df.sample()
        row = row.values.tolist()


        
        return render_template('result.html',tt=row,gen=g)
    else: return render_template('result.html')
    


if __name__ == "__main__":
    app.run(debug=True)