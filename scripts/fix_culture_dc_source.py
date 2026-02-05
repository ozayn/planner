from app import app, db, Event, Venue

def fix_culture_dc_source():
    with app.app_context():
        # Find Culture DC venue
        venue = Venue.query.filter(Venue.name.like('%Culture DC%')).first()
        if not venue:
            print("Culture DC venue not found.")
            return
        
        # Update events for this venue that have source='scraper'
        updated_count = Event.query.filter_by(venue_id=venue.id, source='scraper').update({'source': 'website'})
        db.session.commit()
        print(f"Updated {updated_count} events for Culture DC to have source='website'.")

if __name__ == "__main__":
    fix_culture_dc_source()
