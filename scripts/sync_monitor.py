#!/usr/bin/env python3
"""
Database Sync Monitor
Monitors and alerts on database synchronization issues
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Event, Venue, City, Source

class SyncMonitor:
    """Monitors database synchronization between local and deployed environments"""
    
    def __init__(self):
        self.local_env = self._detect_local_environment()
        self.deployed_url = "https://planner.ozayn.com"
        
    def _detect_local_environment(self) -> bool:
        """Detect if running locally"""
        return not (
            os.getenv('RAILWAY_ENVIRONMENT') is not None or
            os.getenv('DATABASE_URL', '').startswith('postgresql://') or
            'railway.app' in os.getenv('RAILWAY_PUBLIC_DOMAIN', '')
        )
    
    def get_local_stats(self) -> Dict:
        """Get local database statistics"""
        if not self.local_env:
            return {}
        
        with app.app_context():
            return {
                'cities_count': City.query.count(),
                'venues_count': Venue.query.count(),
                'sources_count': Source.query.count(),
                'events_count': Event.query.count(),
                'environment': 'Local/SQLite',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_deployed_stats(self) -> Dict:
        """Get deployed database statistics"""
        try:
            # Get cities count
            cities_response = requests.get(f"{self.deployed_url}/api/cities", timeout=10)
            cities_count = len(cities_response.json()) if cities_response.status_code == 200 else 0
            
            # Get sources count (need city_id parameter)
            sources_response = requests.get(f"{self.deployed_url}/api/sources?city_id=1", timeout=10)
            sources_count = len(sources_response.json()) if sources_response.status_code == 200 else 0
            
            # Get venues count (need city_id parameter)
            venues_response = requests.get(f"{self.deployed_url}/api/venues?city_id=1", timeout=10)
            venues_count = len(venues_response.json()) if venues_response.status_code == 200 else 0
            
            # Get events count (need city_id parameter)
            events_response = requests.get(f"{self.deployed_url}/api/events?city_id=1", timeout=10)
            events_count = len(events_response.json()) if events_response.status_code == 200 else 0
            
            return {
                'cities_count': cities_count,
                'venues_count': venues_count,
                'sources_count': sources_count,
                'events_count': events_count,
                'environment': 'Deployed/PostgreSQL',
                'timestamp': datetime.now().isoformat(),
                'api_status': 'connected'
            }
            
        except Exception as e:
            return {
                'environment': 'Deployed/PostgreSQL',
                'timestamp': datetime.now().isoformat(),
                'api_status': f'error: {str(e)}'
            }
    
    def compare_databases(self) -> Dict:
        """Compare local and deployed database statistics"""
        local_stats = self.get_local_stats()
        deployed_stats = self.get_deployed_stats()
        
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'local': local_stats,
            'deployed': deployed_stats,
            'sync_status': 'unknown',
            'issues': [],
            'recommendations': []
        }
        
        if not local_stats or not deployed_stats.get('api_status') == 'connected':
            comparison['sync_status'] = 'error'
            comparison['issues'].append('Unable to connect to one or both databases')
            return comparison
        
        # Compare counts
        for table in ['cities_count', 'venues_count', 'sources_count', 'events_count']:
            local_count = local_stats.get(table, 0)
            deployed_count = deployed_stats.get(table, 0)
            
            if local_count != deployed_count:
                comparison['issues'].append(
                    f"{table.replace('_count', '')}: Local={local_count}, Deployed={deployed_count}"
                )
        
        # Determine sync status
        if not comparison['issues']:
            comparison['sync_status'] = 'synced'
        else:
            comparison['sync_status'] = 'out_of_sync'
            
            # Generate recommendations
            if comparison['issues']:
                comparison['recommendations'].append(
                    "Run: python scripts/unified_data_manager.py --force"
                )
                comparison['recommendations'].append(
                    "Check data integrity: python scripts/schema_validator.py --report"
                )
        
        return comparison
    
    def check_data_freshness(self) -> Dict:
        """Check if data appears to be recently updated"""
        freshness_check = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'overall_fresh': True
        }
        
        if self.local_env:
            with app.app_context():
                # Check latest created_at timestamps
                latest_city = City.query.order_by(City.created_at.desc()).first()
                latest_source = Source.query.order_by(Source.created_at.desc()).first()
                latest_venue = Venue.query.order_by(Venue.created_at.desc()).first()
                
                freshness_check['checks']['cities'] = {
                    'latest_created': latest_city.created_at.isoformat() if latest_city else None,
                    'count': City.query.count()
                }
                
                freshness_check['checks']['sources'] = {
                    'latest_created': latest_source.created_at.isoformat() if latest_source else None,
                    'count': Source.query.count()
                }
                
                freshness_check['checks']['venues'] = {
                    'latest_created': latest_venue.created_at.isoformat() if latest_venue else None,
                    'count': Venue.query.count()
                }
                
                # Check if data is older than 7 days
                cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                cutoff_date = cutoff_date.replace(day=cutoff_date.day - 7)
                
                for table_name, check_data in freshness_check['checks'].items():
                    if check_data['latest_created']:
                        latest_date = datetime.fromisoformat(check_data['latest_created'].replace('Z', '+00:00'))
                        if latest_date < cutoff_date:
                            freshness_check['overall_fresh'] = False
                            freshness_check['checks'][table_name]['stale'] = True
        
        return freshness_check
    
    def generate_sync_report(self) -> str:
        """Generate a comprehensive sync report"""
        comparison = self.compare_databases()
        freshness = self.check_data_freshness()
        
        report = []
        report.append("🔄 DATABASE SYNC MONITORING REPORT")
        report.append("=" * 50)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("")
        
        # Sync status
        status_emoji = "✅" if comparison['sync_status'] == 'synced' else "❌"
        report.append(f"{status_emoji} Sync Status: {comparison['sync_status'].upper()}")
        report.append("")
        
        # Database statistics
        report.append("📊 Database Statistics:")
        report.append("-" * 25)
        
        if comparison['local']:
            report.append("Local Database:")
            for key, value in comparison['local'].items():
                if key != 'timestamp':
                    report.append(f"  {key}: {value}")
        
        if comparison['deployed'].get('api_status') == 'connected':
            report.append("Deployed Database:")
            for key, value in comparison['deployed'].items():
                if key not in ['timestamp', 'api_status']:
                    report.append(f"  {key}: {value}")
        else:
            report.append(f"Deployed Database: {comparison['deployed'].get('api_status', 'Unknown')}")
        
        report.append("")
        
        # Issues
        if comparison['issues']:
            report.append("⚠️ Sync Issues:")
            report.append("-" * 20)
            for issue in comparison['issues']:
                report.append(f"  - {issue}")
            report.append("")
        
        # Recommendations
        if comparison['recommendations']:
            report.append("💡 Recommendations:")
            report.append("-" * 20)
            for rec in comparison['recommendations']:
                report.append(f"  - {rec}")
            report.append("")
        
        # Data freshness
        if freshness['checks']:
            report.append("🕒 Data Freshness:")
            report.append("-" * 20)
            for table, check in freshness['checks'].items():
                if 'stale' in check:
                    report.append(f"  ⚠️ {table}: Data appears stale")
                else:
                    report.append(f"  ✅ {table}: Data appears fresh")
        
        return "\n".join(report)

def main():
    """Main function for sync monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Sync Monitor')
    parser.add_argument('--report', action='store_true', help='Generate full sync report')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--check-only', action='store_true', help='Only check sync status')
    
    args = parser.parse_args()
    
    monitor = SyncMonitor()
    
    if args.report:
        report = monitor.generate_sync_report()
        print(report)
    elif args.check_only:
        comparison = monitor.compare_databases()
        if args.json:
            print(json.dumps(comparison, indent=2))
        else:
            print(f"Sync Status: {comparison['sync_status']}")
            if comparison['issues']:
                print("Issues:")
                for issue in comparison['issues']:
                    print(f"  - {issue}")
    else:
        # Default: show comparison
        comparison = monitor.compare_databases()
        if args.json:
            print(json.dumps(comparison, indent=2))
        else:
            print("🔄 Database Sync Comparison:")
            print(f"Status: {comparison['sync_status']}")
            if comparison['issues']:
                print("Issues:")
                for issue in comparison['issues']:
                    print(f"  - {issue}")
    
    return 0 if comparison['sync_status'] == 'synced' else 1

if __name__ == '__main__':
    sys.exit(main())
