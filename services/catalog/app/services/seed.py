from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase


async def seed_catalog(db: AsyncIOMotorDatabase) -> None:
    current_time = datetime.now(timezone.utc)
    show_start = current_time.replace(
        hour=18, minute=30, second=0, microsecond=0
    )
    if show_start <= current_time:
        show_start += timedelta(days=1)

    cities = [
        {"_id": "city_hyd", "name": "Hyderabad", "state": "Telangana", "country": "India"},
        {"_id": "city_blr", "name": "Bengaluru", "state": "Karnataka", "country": "India"},
    ]
    for city in cities:
        await db.cities.update_one({"_id": city["_id"]}, {"$set": city}, upsert=True)

    cinemas = [
        {
            "_id": "cin_pvr_01",
            "city_id": "city_hyd",
            "name": "PVR ICON: Next Galleria",
            "address": "Panjagutta, Hyderabad",
        },
        {
            "_id": "cin_amb_01",
            "city_id": "city_hyd",
            "name": "AMB Cinemas",
            "address": "Gachibowli, Hyderabad",
        },
    ]
    for cinema in cinemas:
        await db.cinemas.update_one(
            {"_id": cinema["_id"]}, {"$set": cinema}, upsert=True
        )

    hall = {
        "_id": "hall_audi_2",
        "cinema_id": "cin_pvr_01",
        "name": "Audi 2 (IMAX)",
        "total_seats": 120,
        "layout": {
            "rows": [
                {
                    "row_label": "A",
                    "tier": "RECLINER",
                    "seats": [
                        {"seat_number": 1, "type": "STANDARD"},
                        {"seat_number": 2, "type": "STANDARD"},
                        {"type": "AISLE"},
                        {"seat_number": 3, "type": "STANDARD"},
                    ],
                }
            ]
        },
    }
    await db.halls.update_one({"_id": hall["_id"]}, {"$set": hall}, upsert=True)

    movie = {
        "_id": "mov_inception",
        "title": "Inception",
        "duration_minutes": 148,
        "rating": "UA",
        "languages": ["English", "Hindi"],
        "formats": ["IMAX 2D", "2D"],
    }
    await db.movies.update_one({"_id": movie["_id"]}, {"$set": movie}, upsert=True)

    show = {
        "_id": "show_991823",
        "movie_id": "mov_inception",
        "cinema_id": "cin_pvr_01",
        "hall_id": "hall_audi_2",
        "start_time": show_start,
        "end_time": show_start + timedelta(minutes=148),
        "language": "English",
        "format": "IMAX 2D",
        "pricing": {"RECLINER": 450.0, "PRIME": 280.0, "CLASSIC": 180.0},
    }
    await db.shows.update_one({"_id": show["_id"]}, {"$set": show}, upsert=True)