import os
import time
import schedule
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
import ipfshttpclient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/pintrader')
engine = create_engine(DB_URL)

def get_ipfs_client():
    """Connect to IPFS daemon"""
    try:
        return ipfshttpclient.connect('/dns/ipfs/tcp/5001/http')
    except Exception as e:
        logger.error(f"Failed to connect to IPFS daemon: {e}")
        return None

def process_pending_files():
    """Process files that are pending IPFS upload"""
    logger.info("Checking for pending files...")
    
    try:
        # Get connection from pool
        with engine.connect() as conn:
            # Find pending files
            query = text("""
                SELECT id, filename, filepath, user_id 
                FROM file 
                WHERE ipfs_status = 'pending'
                ORDER BY upload_date ASC
                LIMIT 10
            """)
            
            pending_files = conn.execute(query).fetchall()
            
            if not pending_files:
                logger.info("No pending files found")
                return
                
            logger.info(f"Found {len(pending_files)} pending files")
            
            # Connect to IPFS
            client = get_ipfs_client()
            if not client:
                logger.error("Could not connect to IPFS daemon")
                return
                
            for file in pending_files:
                try:
                    # Update status to processing
                    update_query = text("""
                        UPDATE file 
                        SET ipfs_status = 'processing' 
                        WHERE id = :file_id
                    """)
                    conn.execute(update_query, {"file_id": file.id})
                    conn.commit()
                    
                    # Add file to IPFS
                    # Use just the filename, since the volume mount already points to the uploads directory
                    filepath = os.path.join('/app/uploads', os.path.basename(file.filepath))
                    if not os.path.exists(filepath):
                        logger.error(f"File not found: {filepath}")
                        continue
                        
                    result = client.add(filepath)
                    ipfs_hash = result['Hash']
                    
                    # Update database with IPFS hash
                    update_query = text("""
                        UPDATE file 
                        SET ipfs_status = 'completed',
                            multihash = :ipfs_hash
                        WHERE id = :file_id
                    """)
                    conn.execute(update_query, {
                        "file_id": file.id,
                        "ipfs_hash": ipfs_hash
                    })
                    conn.commit()
                    
                    logger.info(f"Successfully processed file {file.filename} (ID: {file.id})")
                    
                except Exception as e:
                    logger.error(f"Error processing file {file.filename} (ID: {file.id}): {e}")
                    # Update status to failed
                    update_query = text("""
                        UPDATE file 
                        SET ipfs_status = 'failed' 
                        WHERE id = :file_id
                    """)
                    conn.execute(update_query, {"file_id": file.id})
                    conn.commit()
            
            client.close()
            
    except Exception as e:
        logger.error(f"Error in process_pending_files: {e}")

def main():
    """Main function to run the processor"""
    logger.info("Starting IPFS processor service")
    
    # Schedule the job to run every minute
    schedule.every(1).minutes.do(process_pending_files)
    
    # Run immediately on startup
    process_pending_files()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
