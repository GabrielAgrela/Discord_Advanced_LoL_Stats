# CHERRY Match Queue Feature

## Problem
The CHERRY game mode in League of Legends has a unique characteristic where matches may not be immediately available in the Riot API after a player leaves the game. Unlike other game modes, CHERRY matches can continue running even after a player is eliminated, and the match data only becomes available once the entire game is finished.

This caused the bot to display "Error Fetching Match Data" messages for CHERRY matches, even though the matches would eventually become available.

## Solution
Implemented a queue system that handles delayed CHERRY match availability:

### 1. Pending Matches Queue
- **Database Table**: `pending_matches` stores CHERRY matches that failed to fetch initially
- **Automatic Queueing**: When a CHERRY match fails to fetch, it's automatically added to the queue instead of showing an error
- **Retry Logic**: A background process periodically attempts to fetch queued matches every 5 minutes
- **Attempt Limiting**: Maximum of 10 retry attempts per match to prevent infinite loops
- **Auto Cleanup**: Matches older than 7 days are automatically removed from the queue

### 2. Database Schema
```sql
CREATE TABLE pending_matches (
    match_id TEXT PRIMARY KEY,
    game_mode TEXT NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### 3. New Database Operations
- `add_pending_match()`: Add a match to the queue
- `get_pending_matches()`: Retrieve all pending matches
- `update_pending_match_attempt()`: Increment attempt counter
- `remove_pending_match()`: Remove processed match from queue
- `cleanup_old_pending_matches()`: Remove old entries

### 4. User Experience
**Before:**
```
❌ Error Fetching Match Data
Could not retrieve details for game EUW1_7465446017.
```

**After:**
```
⏳ CHERRY Match Queued
Match EUW1_7465446017 has been added to the processing queue.
CHERRY matches may take longer to become available in the API.
```

**When Available:**
```
🎮 CHERRY Match Found - Processing...
Match data is now available. Generating player cards...
```

### 5. New Slash Commands
- `/check_pending_matches`: View all matches currently in the queue
- `/retry_pending_match <match_id>`: Manually retry a specific match

### 6. Background Processing
- **Loop Frequency**: Checks pending matches every 5 minutes
- **Smart Processing**: Only processes matches that haven't exceeded retry limit
- **Error Handling**: Gracefully handles Discord message/channel deletions
- **Logging**: Comprehensive logging for debugging and monitoring

### 7. Files Modified
- `src/models/models.py`: Added `PendingMatch` dataclass
- `src/models/DatabaseStructure.py`: Added pending_matches table schema
- `src/cogs/DatabaseOperations.py`: Added pending match database operations
- `src/cogs/Loops.py`: Modified game processing logic and added retry loop
- `src/cogs/Commands.py`: Added management commands

### 8. Benefits
- **No More False Errors**: CHERRY matches no longer show error messages
- **Automatic Processing**: Matches are processed as soon as they become available
- **User Transparency**: Clear messaging about queue status
- **Administrative Control**: Manual retry and monitoring capabilities
- **Resource Efficient**: Limited retry attempts and automatic cleanup prevent resource waste

### 9. Configuration
- **Retry Interval**: 5 minutes (configurable in `process_pending_matches()`)
- **Max Attempts**: 10 retries per match
- **Cleanup Period**: 7 days for old matches
- **Queue Limit**: No hard limit, but filtered by attempt count

This solution ensures that CHERRY matches are processed reliably while providing clear feedback to users about the status of their games.