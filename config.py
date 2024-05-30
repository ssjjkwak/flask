import os
from urllib.parse import quote_plus

BASE_DIR = os.path.dirname(__file__)

username = 'ssjjkwak'
password = 'synopex%4024!!'
hostname = '219.255.132.65'
port = '1433'
database = 'ERP_WEB'
driver = 'ODBC Driver 17 for SQL Server'

encoded_password = quote_plus(password)

SQLALCHEMY_DATABASE_URI = f'mssql+pyodbc://ssjjkwak:synopex%4024!!@219.255.132.65:1433/ERP_WEB?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes'


SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "dev"