from app.mongodb import get_db
print("MongoDB connected:", get_db().name)
