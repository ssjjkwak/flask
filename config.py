import os

BASE_DIR = os.path.dirname(__file__)

SQLALCHEMY_DATABASE_URI = 'sqlite:///{}'.format(os.path.join(BASE_DIR, 'pybo.db'))

username = 'ssjjkwak'
password = 'rhkr0728@@'
hostname = '219.255.132.72'
port = '80'
database = 'SYNOPEX_FILTER_TEST'
driver = 'ODBC Driver 17 for SQL Server'

SQLALCHEMY_BINDS = {
    'mssql': 'mssql+pyodbc://ssjjkwak:rhkr0728%40%40@219.255.132.72:80/SYNOPEX_FILTER_TEST?driver=ODBC+Driver+17+for+SQL+Server'
}

SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "dev"