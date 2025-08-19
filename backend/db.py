from pymongo import MongoClient

MONGO_URI = "mongodb+srv://siyonabansal:7p3KxjlKW9vKfuwY@smartbins.4cojrhu.mongodb.net/?retryWrites=true&w=majority&appName=Smartbins"

client = MongoClient(MONGO_URI)

db = client["smartbins"]

bins_collection = db["bins"]
medicines_collection = db["medicines"]
orders_collection = db["orders"]
