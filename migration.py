"""
Mevcut veritabanını v7 için günceller.
Çalıştır: python migration.py
"""
import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), 'database', 'fatura.db')

if not os.path.exists(db_path):
    print("Veritabani bulunamadi, app.py calistirinca otomatik olusacak.")
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    migrations = [
        "ALTER TABLE kullanici ADD COLUMN sifre_hash TEXT",
        "ALTER TABLE fatura ADD COLUMN odeme_notu TEXT",
        "ALTER TABLE fatura ADD COLUMN atanan_id INTEGER REFERENCES kullanici(id)",
        """CREATE TABLE IF NOT EXISTS fatura_proje (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fatura_id INTEGER NOT NULL REFERENCES fatura(id),
            ana_proje_id INTEGER REFERENCES ana_proje(id),
            alt_proje_id INTEGER REFERENCES alt_proje(id),
            sira INTEGER DEFAULT 1
        )""",
    ]

    for sql in migrations:
        try:
            cur.execute(sql)
            print(f"OK: {sql.strip()[:60]}")
        except Exception as e:
            print(f"ATLA (zaten var): {str(e)[:60]}")

    conn.commit()
    conn.close()
    print("\nMigration tamamlandi. Simdi python app.py calistirabilirsiniz.")
